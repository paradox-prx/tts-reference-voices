#!/usr/bin/env python3
"""Per-call latency of a running QC sidecar: POSTs one clip n times with c in flight, as the gateway does.

    eval/run.sh eval/qc_latency.py --url http://127.0.0.1:8092 -n 10 -c 1 --out eval/calibration/qc_latency_cuda.json
    eval/run.sh eval/qc_latency.py --clip trump/trump_01.wav --seconds 10 -n 5

Reports client wall time (p50 / p90 / max, ms) and the server's own breakdown (ms: audio, asr, sim, total), plus the
sidecar's /health (device, models). The clip's transcript comes from voices/<voice>/clips.json (cut to --seconds of
audio, the transcript is then only approximate, which does not change the latency).
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "qc"))
sys.path.insert(0, str(HERE))

from stats import describe  # noqa: E402
from tts_qc import paths  # noqa: E402
from tts_qc.audio import read_wav  # noqa: E402


def main() -> int:
    import httpx

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8092")
    ap.add_argument("--clip", default="shehbaz/shehbaz_02.wav", help="voices/<voice>/<file>")
    ap.add_argument("--seconds", type=float, default=0, help="cut the clip to this many seconds (0 = whole clip)")
    ap.add_argument("--checks", default="asr,sim,audio")
    ap.add_argument("-n", type=int, default=5)
    ap.add_argument("-c", type=int, default=1)
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--timeout", type=float, default=300)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    voice, name = args.clip.split("/", 1)
    clips = json.loads((paths.voices_dir() / voice / "clips.json").read_text(encoding="utf-8"))["clips"]
    text = next(c["text"] for c in clips if c["file"] == name)
    lang = json.loads((paths.voices_dir() / voice / "voice.json").read_text(encoding="utf-8"))["language"]
    pcm, sr = read_wav(paths.voices_dir() / voice / name)
    if args.seconds:
        pcm = pcm[: int(args.seconds * sr)]
    body = {"voice": voice, "lang": lang, "text": text, "sample_rate": sr,
            "pcm_b64": base64.b64encode(pcm.astype("<i2").tobytes()).decode(), "checks": args.checks.split(",")}
    client = httpx.Client(base_url=args.url, timeout=args.timeout, trust_env=False)
    health = client.get("/health").json()

    def call(i: int) -> dict:
        t0 = time.perf_counter()
        r = client.post("/v1/qc", json={**body, "request_id": f"lat{i}"})
        wall = (time.perf_counter() - t0) * 1000
        r.raise_for_status()
        out = r.json()
        return {"wall_ms": round(wall, 1), "ms": out["ms"], "pass": out["pass"], "reasons": out["reasons"]}

    for i in range(args.warmup):
        call(-1 - i)
    t0 = time.perf_counter()
    with ThreadPoolExecutor(args.c) as ex:
        calls = list(ex.map(call, range(args.n)))
    wall = time.perf_counter() - t0
    audio_s = len(pcm) / sr
    result = {
        "measured_at": datetime.now(ZoneInfo("Asia/Karachi")).isoformat(timespec="seconds"),
        "url": args.url, "health": health, "clip": args.clip, "audio_s": round(audio_s, 2), "lang": lang,
        "checks": body["checks"], "n": args.n, "concurrency": args.c, "warmup": args.warmup,
        "wall_ms": describe([c["wall_ms"] for c in calls]),
        "server_ms": {k: describe([c["ms"][k] for c in calls]) for k in ("audio", "asr", "sim", "total")},
        "throughput_x_realtime": round(args.n * audio_s / wall, 2), "passes": sum(c["pass"] for c in calls),
        "reasons": sorted({r for c in calls for r in c["reasons"]}), "calls": calls,
    }
    print(json.dumps({k: v for k, v in result.items() if k != "calls"}, ensure_ascii=False, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
