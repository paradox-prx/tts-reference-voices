#!/usr/bin/env python3
"""Speaker-similarity calibration on the real reference clips, for both SIM models, and the comparison with the eval
research's numbers (eval-tooling.md findings 18 and 21, measured there on CPU with torchaudio resampling).

    CUDA_VISIBLE_DEVICES= eval/run.sh eval/sim_eval.py --device cpu     # -> eval/calibration/sim_calibration_cpu.json
    eval/run.sh eval/sim_eval.py --device cuda --out eval/calibration/sim_calibration_cuda.json

Same embedding path as the sidecar and score_run.py (tts_qc: PyAV resample to 16 kHz, energy-VAD trim of leading and
trailing silence with a 0.1 s margin, one clip per forward pass). Measured per model:
  shehbaz_heldout_clip_vs_prompt       each clip NOT in the prompt (02-06) vs references/qwen3-tts.wav
  shehbaz_inprompt_clip_vs_prompt      clips 01, 07, 08 (inside the prompt audio) vs the prompt
  shehbaz_heldout_leave1out_vs_centroid  each held-out clip vs the centroid of the other held-out clips
  shehbaz_prompt_vs_heldout_centroid   the prompt vs the held-out centroid (what SIM-heldout compares against)
  trump_half1_vs_half2                 first vs second half of trump_01 (trump has no held-out clip)
  trump_clip_vs_prompt                 trump_01 vs its own prompt (the same audio after the Kaggle cleaning)
  cross_trump_vs_shehbaz_*             different speakers (and languages)
  short_crop_shehbaz02_vs_prompt       the first 2 / 3 / 5 s of shehbaz_02 vs the prompt (duration dependence)
  x_realtime                           seconds of audio embedded per second of wall time
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "qc"))

from tts_qc import paths  # noqa: E402
from tts_qc.audio import ASR_RATE, read_wav, to_16k, trim_16k  # noqa: E402
from tts_qc.checks import audio_checks  # noqa: E402
from tts_qc.sim import Embedder, centroid, cosine  # noqa: E402
from tts_qc.voices import load_voices  # noqa: E402

# eval-tooling.md (research run, CPU fp32, torchaudio resample): for the comparison block
RESEARCH = {
    "large": {"shehbaz_heldout_clip_vs_prompt": [0.896, 0.939], "shehbaz_heldout_leave1out_vs_centroid": [0.927, 0.951],
              "shehbaz_prompt_vs_heldout_centroid": 0.952, "trump_half1_vs_half2": 0.908,
              "cross_speaker": [0.106, 0.182],
              "short_crop_shehbaz02_vs_prompt": {"2s": 0.676, "3s": 0.733, "5s": 0.807},
              "full_shehbaz02_vs_prompt": 0.903, "x_realtime_cpu8": 15},
    "base": {"same_speaker": [0.975, 0.994], "cross_speaker": [0.746, 0.799], "short_crop_2s": 0.951,
             "trump_half1_vs_half2": 0.994, "x_realtime_cpu8": 37.8},
}


def load16(path: Path) -> np.ndarray:
    pcm, sr = read_wav(path)
    a = audio_checks(pcm, sr)
    return trim_16k(to_16k(pcm, sr), a["lead_sil_s"], a["trail_sil_s"])


def rng(values) -> list[float]:
    v = list(values)
    return [round(min(v), 3), round(max(v), 3)]


def calibrate(model: str, device: str) -> dict:
    voices = load_voices(paths.voices_dir(), paths.pace_file())
    sh, tr = voices["shehbaz"], voices["trump"]
    t0 = time.perf_counter()
    emb = Embedder(model, paths.models_dir(), device)
    load_s = time.perf_counter() - t0
    wavs = {p.name: load16(p) for p in sorted((paths.voices_dir() / "shehbaz").glob("*.wav"))}
    sh_prompt, tr_prompt = load16(sh.prompt), load16(tr.prompt)
    tr_clip = load16(paths.voices_dir() / "trump" / "trump_01.wav")
    half = len(tr_clip) // 2
    s02 = wavs["shehbaz_02.wav"]
    t0 = time.perf_counter()
    audio_s = 0.0

    def e(w: np.ndarray) -> np.ndarray:
        nonlocal audio_s
        audio_s += len(w) / ASR_RATE
        return emb(w)

    E = {k: e(w) for k, w in wavs.items()}
    P = e(sh_prompt)
    held = [p.name for p in sh.heldout]
    cen = centroid([E[k] for k in held])
    T, T1, T2, TP = e(tr_clip), e(tr_clip[:half]), e(tr_clip[half:]), e(tr_prompt)
    crops = {f"{s}s": round(cosine(e(s02[: s * ASR_RATE]), P), 3) for s in (2, 3, 5)}
    took = time.perf_counter() - t0
    res = {
        "model": model, "device": device, "load_s": round(load_s, 1), "embed_s": round(took, 1),
        "audio_s": round(audio_s, 1), "x_realtime": round(audio_s / took, 1),
        "heldout_clips": held, "prompt_clips": list(sh.prompt_clips),
        "shehbaz_heldout_clip_vs_prompt": {k: round(cosine(E[k], P), 3) for k in held},
        "shehbaz_inprompt_clip_vs_prompt": {k: round(cosine(v, P), 3) for k, v in E.items() if k not in held},
        "shehbaz_heldout_leave1out_vs_centroid": {
            k: round(cosine(E[k], centroid([E[q] for q in held if q != k])), 3) for k in held},
        "shehbaz_prompt_vs_heldout_centroid": round(cosine(P, cen), 3),
        "trump_half1_vs_half2": round(cosine(T1, T2), 3),
        "trump_clip_vs_prompt": round(cosine(T, TP), 3),
        "cross_trump_vs_shehbaz_prompt": round(cosine(T, P), 3),
        "cross_trump_prompt_vs_shehbaz_prompt": round(cosine(TP, P), 3),
        "cross_trump_vs_shehbaz_clips": {k: round(cosine(T, v), 3) for k, v in E.items()},
        "short_crop_shehbaz02_vs_prompt": {**crops, "full": round(cosine(E["shehbaz_02.wav"], P), 3)},
    }
    same = list(res["shehbaz_heldout_clip_vs_prompt"].values()) + list(res["shehbaz_inprompt_clip_vs_prompt"].values())
    cross = list(res["cross_trump_vs_shehbaz_clips"].values()) + [res["cross_trump_vs_shehbaz_prompt"]]
    res["summary"] = {"same_speaker_vs_prompt": rng(same),
                      "heldout_vs_prompt": rng(res["shehbaz_heldout_clip_vs_prompt"].values()),
                      "leave1out_vs_centroid": rng(res["shehbaz_heldout_leave1out_vs_centroid"].values()),
                      "cross_speaker": rng(cross), "margin_same_min_minus_cross_max": round(min(same) - max(cross), 3)}
    res["research"] = RESEARCH[model]
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", default="large,base")
    ap.add_argument("--device", choices=("cuda", "cpu"), default="cpu")
    ap.add_argument("--threads", type=int, default=8, help="torch threads on CPU")
    ap.add_argument("--out", default=None, help="default eval/calibration/sim_calibration_<device>.json")
    args = ap.parse_args()
    import torch
    torch.set_num_threads(args.threads)
    out = Path(args.out or HERE / "calibration" / f"sim_calibration_{args.device}.json")
    results = {"about": __doc__.split("\n\n")[0], "threads": args.threads, "torch": torch.__version__,
               "models": {}}
    for m in args.models.split(","):
        r = calibrate(m, args.device)
        results["models"][m] = r
        print(json.dumps({k: r[k] for k in ("model", "x_realtime", "summary", "shehbaz_prompt_vs_heldout_centroid",
                                            "trump_half1_vs_half2", "short_crop_shehbaz02_vs_prompt")}), flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
