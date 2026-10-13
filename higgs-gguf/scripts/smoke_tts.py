#!/usr/bin/env python3
"""Fixed-seed voice-clone smoke test against a Higgs engine; saves every take and the numbers.

    python scripts/smoke_tts.py --url http://127.0.0.1:8096 --out results/03_load/q8_0

Phase 1 sends the fixed texts one at a time with fixed seeds (comparable across engines: same inputs, no batching
effects). Phase 2 sends a concurrent burst (--burst, default 8) to check the engine holds up under batching.
Writes <out>/<id>.wav, <out>/takes.json (latency, audio seconds, RTF, sha256 per take) and <out>/summary.json.
The reference is higgs-studio's `callagent` voice cut to its reference.json window (27.1 s, Urdu).
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import hashlib
import io
import json
import time
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICE = ROOT.parent / "higgs-studio" / "voices" / "callagent"

TEXTS = [
    ("ur_weather", "آج موسم بہت خوشگوار ہے اور ہوا میں ہلکی ٹھنڈک محسوس ہو رہی ہے۔"),
    ("ur_ivr", "براہِ کرم اپنی شکایت درج کروانے کے لیے ایک دبائیں، یا ہمارے نمائندے سے بات کرنے کے لیے دو دبائیں۔"),
    ("ur_health", "صحت مند زندگی کے لیے روزانہ ورزش، پوری نیند اور متوازن خوراک بہت ضروری ہے۔ <|prosody:pause|> "
                  "چھوٹی چھوٹی عادتیں بڑا فرق ڈالتی ہیں۔"),
    ("en_order", "Thank you for calling. Your order has been shipped and should arrive within three working days."),
    ("en_fox", "The quick brown fox jumps over the lazy dog, while the weather stays pleasant all afternoon."),
]
SEED = 1234


def reference() -> tuple[bytes, str]:
    ref = json.loads((VOICE / "reference.json").read_text())
    with wave.open(str(VOICE / ref["clip"])) as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        w.setpos(int(ref["start"] * sr))
        frames = w.readframes(int((ref["end"] - ref["start"]) * sr))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as o:
        o.setnchannels(ch)
        o.setsampwidth(sw)
        o.setframerate(sr)
        o.writeframes(frames)
    return buf.getvalue(), ref["text"]


def wav_seconds(b: bytes) -> float:
    try:
        with wave.open(io.BytesIO(b)) as w:
            return w.getnframes() / w.getframerate()
    except Exception:
        return 0.0


def speak(url: str, text: str, ref_wav: bytes, ref_text: str, seed: int, timeout: float) -> tuple[int, bytes, float]:
    body = {"input": text, "ref_audio": "data:audio/wav;base64," + base64.b64encode(ref_wav).decode(),
            "ref_text": ref_text, "response_format": "wav", "seed": seed,
            "extra_params": {"temperature": 0.8, "top_k": 50, "top_p": 1.0}}
    req = urllib.request.Request(f"{url}/v1/audio/speech", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), time.perf_counter() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read(), time.perf_counter() - t0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8096")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="", help="free text stored in summary.json (e.g. weights used)")
    ap.add_argument("--burst", type=int, default=8, help="concurrent requests in phase 2 (0 = skip)")
    ap.add_argument("--timeout", type=float, default=300)
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ref_wav, ref_text = reference()
    takes = []

    def record(tid: str, text: str, seed: int, phase: str, status: int, data: bytes, dt: float) -> None:
        ok = status == 200 and data[:4] == b"RIFF"
        secs = wav_seconds(data) if ok else 0.0
        if ok:
            (out / f"{tid}.wav").write_bytes(data)
        else:
            (out / f"{tid}.error.txt").write_bytes(data[:4000])
        takes.append({"id": tid, "phase": phase, "text": text, "seed": seed, "status": status, "ok": ok,
                      "latency_s": round(dt, 3), "audio_s": round(secs, 3), "rtf": round(dt / secs, 3) if secs else None,
                      "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest() if ok else None})
        print(f"  {tid:22s} {status} {dt:6.2f}s -> {secs:5.2f}s audio", flush=True)

    print(f"phase 1: {len(TEXTS)} sequential takes, seed {SEED}")
    for tid, text in TEXTS:
        record(tid, text, SEED, "sequential", *speak(a.url, text, ref_wav, ref_text, SEED, a.timeout))

    if a.burst:
        print(f"phase 2: burst of {a.burst} concurrent takes")
        jobs = [(f"burst{i:02d}_{TEXTS[i % len(TEXTS)][0]}", TEXTS[i % len(TEXTS)][1], SEED + 1 + i)
                for i in range(a.burst)]
        t0 = time.perf_counter()
        with cf.ThreadPoolExecutor(a.burst) as ex:
            futs = {ex.submit(speak, a.url, text, ref_wav, ref_text, seed, a.timeout): (tid, text, seed)
                    for tid, text, seed in jobs}
            for f in cf.as_completed(futs):
                tid, text, seed = futs[f]
                record(tid, text, seed, "burst", *f.result())
        burst_wall = time.perf_counter() - t0
    else:
        burst_wall = None

    good = [t for t in takes if t["ok"]]
    summary = {"url": a.url, "label": a.label, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
               "takes": len(takes), "ok": len(good), "failed": len(takes) - len(good),
               "audio_s_total": round(sum(t["audio_s"] for t in good), 2),
               "sequential_mean_rtf": round(sum(t["rtf"] for t in good if t["phase"] == "sequential")
                                            / max(1, sum(1 for t in good if t["phase"] == "sequential")), 3),
               "burst": a.burst, "burst_wall_s": round(burst_wall, 2) if burst_wall else None,
               "reference": {"voice": "callagent", "seconds": round(wav_seconds(ref_wav), 2)}}
    (out / "takes.json").write_text(json.dumps(takes, ensure_ascii=False, indent=1) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary))
    raise SystemExit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
