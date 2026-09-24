#!/usr/bin/env python3
"""Self-check of the eval / QC stack in ONE process: faster-whisper large-v3 (CTranslate2, cuBLAS 12) and WavLM
(torch cu130, cuBLAS 13) on the same GPU; transcribes and embeds one reference clip; reports timings, memory and
which cuBLAS libraries got loaded. Run it through run.sh (it puts the venv's cuBLAS 12 on LD_LIBRARY_PATH):

    eval/run.sh eval/gpu_check.py                          # cuda, float16, both SIM models, 2 CT2 workers
    CUDA_VISIBLE_DEVICES=0 eval/run.sh eval/gpu_check.py --workers 4 --sim base
    CUDA_VISIBLE_DEVICES= eval/run.sh eval/gpu_check.py --device cpu        # plumbing only (int8, no GPU)

Writes eval/calibration/gpu_check_<device>.json (and prints it). Exit code 0 = every step worked. GPU memory:
torch.cuda.max_memory_allocated covers only torch (WavLM); CTranslate2 allocates outside torch, so the process
total comes from torch.cuda.mem_get_info deltas and from nvidia-smi's per-process figure.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "qc"))

from tts_qc import paths  # noqa: E402


def mapped(fragment: str) -> list[str]:
    with open("/proc/self/maps") as f:
        return sorted({line.split()[-1] for line in f if fragment in line and "/" in line})


def cublas_versions() -> dict:
    """Version of every libcublas.so.* mapped into this process (cublasGetProperty needs no GPU)."""
    out = {}
    for path in mapped("libcublas.so"):
        try:
            lib = ctypes.CDLL(path)
            v, parts = ctypes.c_int(), []
            for prop in (0, 1, 2):
                lib.cublasGetProperty(prop, ctypes.byref(v))
                parts.append(v.value)
            out[path] = ".".join(map(str, parts))
        except OSError as exc:
            out[path] = f"error: {exc}"
    return out


def smi_process_mib() -> int | None:
    try:
        q = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=10).stdout
        for line in q.splitlines():
            pid, mem = [x.strip() for x in line.split(",")]
            if int(pid) == os.getpid():
                return int(mem)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    ap.add_argument("--device-index", type=int, default=0)
    ap.add_argument("--compute", default=None, help="CT2 compute type (default float16 on cuda, int8 on cpu)")
    ap.add_argument("--workers", type=int, default=2, help="CT2 workers; the check also runs `workers` clips at once")
    ap.add_argument("--cpu-threads", type=int, default=8)
    ap.add_argument("--sim", default="base,large")
    ap.add_argument("--clip", default="shehbaz/shehbaz_02.wav", help="voices/<...> clip (text from clips.json)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    env = {k: os.environ.get(k) for k in ("CUDA_VISIBLE_DEVICES", "LD_LIBRARY_PATH")}
    report: dict = {"device": args.device, "env": env,
                    "steps": {}, "ok": False}
    steps = report["steps"]

    def step(name: str, fn):
        t0 = time.perf_counter()
        try:
            value = fn()
            steps[name] = {"ok": True, "s": round(time.perf_counter() - t0, 3), **(value or {})}
            print(f"[ok] {name}: {json.dumps(steps[name], ensure_ascii=False)[:400]}", flush=True)
            return value
        except Exception as exc:
            steps[name] = {"ok": False, "s": round(time.perf_counter() - t0, 3),
                           "error": f"{type(exc).__name__}: {exc}"}
            print(f"[FAIL] {name}: {steps[name]['error']}", flush=True)
            raise

    try:
        import torch
        cuda = args.device == "cuda"

        def torch_info():
            info = {"torch": torch.__version__, "cuda_build": torch.version.cuda,
                    "available": torch.cuda.is_available()}
            if cuda:
                if not torch.cuda.is_available():
                    raise RuntimeError("torch sees no CUDA device (CUDA_VISIBLE_DEVICES?)")
                torch.cuda.set_device(args.device_index)
                free, total = torch.cuda.mem_get_info()
                info |= {"gpu": torch.cuda.get_device_name(), "free_mib": free >> 20, "total_mib": total >> 20}
            return info

        base_free = step("torch", torch_info).get("free_mib")

        def ct2_info():
            import ctranslate2
            info = {"ctranslate2": ctranslate2.__version__, "cuda_devices": ctranslate2.get_cuda_device_count(),
                    "cpu_compute_types": sorted(ctranslate2.get_supported_compute_types("cpu"))}
            if info["cuda_devices"]:
                info["cuda_compute_types"] = sorted(ctranslate2.get_supported_compute_types("cuda", args.device_index))
            elif cuda:
                raise RuntimeError("ctranslate2 sees no CUDA device")
            return info

        step("ctranslate2", ct2_info)

        from tts_qc.scorer import Scorer, ScorerConfig
        sims = tuple(s for s in args.sim.split(",") if s and s != "none")
        cfg = ScorerConfig(device=args.device, device_index=args.device_index, asr_compute=args.compute,
                           workers=args.workers, cpu_threads=args.cpu_threads, sim_models=sims)
        scorer = Scorer(cfg)

        def load():
            scorer.load()
            info = {"load_s": scorer.load_s, "asr": scorer.asr.describe()}
            if cuda:
                torch.cuda.synchronize()
                info["free_mib_after"] = torch.cuda.mem_get_info()[0] >> 20
                info["used_by_process_mib"] = base_free - info["free_mib_after"]
            return info

        step("load_models", load)

        voice, name = args.clip.split("/", 1)
        clips = json.loads((paths.voices_dir() / voice / "clips.json").read_text(encoding="utf-8"))["clips"]
        text = next(c["text"] for c in clips if c["file"] == name)
        lang = scorer.voices[voice].lang
        from tts_qc.audio import read_wav
        pcm, sr = read_wav(paths.voices_dir() / voice / name)

        def score(n: int):
            def one():
                return scorer.score(pcm, sr, text, lang, voice, pace=False)
            if cuda:
                torch.cuda.reset_peak_memory_stats()
            t0 = time.perf_counter()
            with ThreadPoolExecutor(n) as ex:
                results = list(ex.map(lambda _: one(), range(n)))
            wall = time.perf_counter() - t0
            m, ms = results[-1]
            info = {"clips": n, "audio_s": round(len(pcm) / sr, 2), "wall_s": round(wall, 3),
                    "x_realtime": round(n * len(pcm) / sr / wall, 1), "ms_last": ms,
                    "wer": m.get("wer"), "cer_nospace": m.get("cer_nospace"), "asr_text": m.get("asr_text"),
                    **{k: m[k] for k in m if k.startswith("sim_prompt") or k.startswith("sim_heldout")}}
            if cuda:
                info |= {"torch_max_allocated_mib": torch.cuda.max_memory_allocated() >> 20,
                         "torch_reserved_mib": torch.cuda.memory_reserved() >> 20,
                         "process_used_mib": base_free - (torch.cuda.mem_get_info()[0] >> 20),
                         "nvidia_smi_process_mib": smi_process_mib()}
            return info

        step("score_cold", lambda: score(1))

        def libraries():
            info = {"cublas": cublas_versions(), "ctranslate2_lib": mapped("libctranslate2")}
            if cuda and not any(".so.12" in p for p in info["cublas"]):
                raise RuntimeError(f"no libcublas.so.12 mapped after a CUDA transcription: {info['cublas']}")
            if cuda and not any(".so.13" in p for p in info["cublas"]):
                raise RuntimeError(f"no libcublas.so.13 mapped after a CUDA embedding: {info['cublas']}")
            return info

        step("libraries", libraries)
        step("score_warm", lambda: score(1))
        step(f"score_parallel_{args.workers}", lambda: score(args.workers))
        report["ok"] = True
    except Exception:
        report["ok"] = False
    out = Path(args.out or HERE / "calibration" / f"gpu_check_{args.device}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{'OK' if report['ok'] else 'FAILED'} -> {out}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
