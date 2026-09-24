#!/usr/bin/env python3
"""Smoke test for a RUNNING qwen-tts baseline server (server/baseline/qwen_tts_server.py). Starts nothing.

    python server/baseline/smoke.py --url http://127.0.0.1:8093 --out /path/to/smoke-dir

Checks GET /health and GET /v1/audio/voices, then sends:
  1. english   voice=trump, language English
  2. urdu      voice=shehbaz, language Auto
  3. inline    ref_audio = data: URL of voices/trump/references/qwen3-tts.wav + its transcript, language English
  4. concurrent  4 requests at once (trump, shehbaz, trump, shehbaz): one dynamic batch is expected
Prints latency, audio seconds, RTF and the X-Baseline-* headers (batch size, queue ms, codec frames, ...) per request,
saves each WAV as <out>/<name>.wav (the server's AI-generated label is verified; a WAV without it is re-labelled
before saving) and writes every number to <out>/smoke.json. Exit code 0 only if every step passed.

Standard library only, so any Python 3.10+ runs it. Generated audio is AI-generated speech: keep it out of git and
never publish it.
"""

from __future__ import annotations

import argparse
import base64
import json
import struct
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AI_LABEL = "AI-generated speech (Qwen3-TTS voice clone). Not a real recording."
PKT = timezone(timedelta(hours=5), "PKT")

EN_1 = "Good morning. This is a short test of the baseline voice clone server."
UR_1 = "آج موسم بہت خوشگوار ہے، اور ہم شام کو پارک میں سیر کے لیے جائیں گے۔"
EN_INLINE = "The inline reference path should sound just like the registered voice."
CONCURRENT = [
    ("trump", "English", "We will review the numbers again on Friday afternoon."),
    ("shehbaz", "Auto", "پاکستان کی معیشت میں بہتری کے آثار نظر آ رہے ہیں۔"),
    ("trump", "English", "Thank you all for coming here today, it means a great deal."),
    ("shehbaz", "Auto", "ہم سب کو مل کر اپنے ملک کی ترقی کے لیے کام کرنا ہوگا۔"),
]


def now() -> str:
    return datetime.now(PKT).isoformat(timespec="seconds")


def http(method: str, url: str, body: dict | None = None, timeout: float = 600.0) -> tuple[int, dict, bytes, float]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload, status, headers = r.read(), r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        payload, status, headers = e.read(), e.code, dict(e.headers)
    return status, {k.lower(): v for k, v in headers.items()}, payload, time.perf_counter() - t0


def wav_info(data: bytes) -> dict:
    """Sample rate, channels, bits, PCM bytes and the LIST/INFO ICMT comment of a WAV payload."""
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("not a WAV payload")
    out: dict = {"comment": None}
    pos = 12
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            _, out["channels"], out["sample_rate"] = struct.unpack("<HHI", body[:8])
            out["bits"] = struct.unpack("<H", body[14:16])[0]
        elif cid == b"LIST" and body[:4] == b"INFO":
            p = 4
            while p + 8 <= len(body):
                sid, ssize = body[p:p + 4], struct.unpack("<I", body[p + 4:p + 8])[0]
                if sid == b"ICMT":
                    out["comment"] = body[p + 8:p + 8 + ssize].rstrip(b"\0").decode("utf-8", "replace")
                p += 8 + ssize + (ssize & 1)
        elif cid == b"data":
            out["pcm"] = body
        pos += 8 + size + (size & 1)
    return out


def labelled_wav(pcm: bytes, sr: int) -> bytes:
    text = AI_LABEL.encode() + b"\0"
    text += b"\0" * (len(text) & 1)
    info = b"INFO" + b"ICMT" + struct.pack("<I", len(text)) + text
    lst = b"LIST" + struct.pack("<I", len(info)) + info
    fmt = struct.pack("<HHIIHH", 1, 1, sr, sr * 2, 2, 16)
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + lst
    pad = b"\0" * (len(pcm) & 1)
    return (b"RIFF" + struct.pack("<I", len(body) + 8 + len(pcm) + len(pad)) + body + b"data"
            + struct.pack("<I", len(pcm)) + pcm + pad)


def speech(args, name: str, body: dict, out: Path) -> dict:
    started = now()
    status, headers, payload, latency = http("POST", args.url.rstrip("/") + "/v1/audio/speech", body, args.timeout)
    rec = {"name": name, "started": started, "status": status, "latency_s": round(latency, 3),
           "request": {k: (v if k != "ref_audio" else f"<data URL, {len(v)} chars>") for k, v in body.items()},
           "headers": {k: v for k, v in headers.items() if k.startswith("x-")}, "ok": False}
    if status != 200:
        rec["error"] = payload.decode("utf-8", "replace")[:500]
        return rec
    try:
        info = wav_info(payload)
    except ValueError as exc:
        rec["error"] = f"bad WAV: {exc}"
        return rec
    pcm = info.pop("pcm", b"")
    sr = info.get("sample_rate") or 0
    audio_s = len(pcm) / (2 * sr) if sr else 0.0
    rec |= {"bytes": len(payload), "sample_rate": sr, "channels": info.get("channels"), "bits": info.get("bits"),
            "audio_s": round(audio_s, 3), "rtf": round(latency / audio_s, 3) if audio_s else None,
            "wav_label_ok": info["comment"] == AI_LABEL, "header_label_ok": headers.get("x-ai-generated") == "true"}
    data = payload if rec["wav_label_ok"] else labelled_wav(pcm, sr)
    path = out / f"{name}.wav"
    path.write_bytes(data)
    rec["saved"] = str(path)
    frames = headers.get("x-baseline-codec-frames")
    rec["frames_match_audio"] = frames is not None and abs(int(frames) * 1920 - len(pcm) // 2) <= 1
    rec["ok"] = (rec["wav_label_ok"] and rec["header_label_ok"] and sr == 24000 and rec["channels"] == 1
                 and rec["bits"] == 16 and audio_s > 0.3 and rec["frames_match_audio"])
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True, help="baseline server, e.g. http://127.0.0.1:8093")
    ap.add_argument("--out", type=Path, required=True, help="directory for the WAVs and smoke.json (keep out of git)")
    ap.add_argument("--voices-dir", type=Path, default=REPO / "voices")
    ap.add_argument("--timeout", type=float, default=900.0, help="per-request timeout, seconds")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report: dict = {"url": args.url, "started": now(), "steps": {}}
    base = args.url.rstrip("/")

    status, _, payload, lat = http("GET", base + "/health", timeout=30)
    report["steps"]["health"] = {"status": status, "body": payload.decode("utf-8", "replace"),
                                 "latency_s": round(lat, 3), "ok": status == 200}
    status, _, payload, _ = http("GET", base + "/v1/audio/voices", timeout=30)
    voices = json.loads(payload) if status == 200 else {}
    report["steps"]["voices"] = {"status": status, "voices": voices.get("voices"),
                                 "ok": status == 200 and {"trump", "shehbaz"} <= set(voices.get("voices") or [])}
    status, _, payload, _ = http("GET", base + "/v1/baseline/info", timeout=30)
    report["server_info_before"] = json.loads(payload) if status == 200 else {"status": status}

    ref = json.loads((args.voices_dir / "trump/references/references.json").read_text(encoding="utf-8"))["qwen3-tts"]
    ref_b64 = "data:audio/wav;base64," + base64.b64encode(
        (args.voices_dir / "trump/references" / ref["file"]).read_bytes()).decode()
    base_body = {"task_type": "Base", "response_format": "wav"}
    report["steps"]["english"] = speech(args, "english_trump",
                                        {**base_body, "input": EN_1, "voice": "trump", "language": "English"}, args.out)
    report["steps"]["urdu"] = speech(args, "urdu_shehbaz",
                                     {**base_body, "input": UR_1, "voice": "shehbaz", "language": "Auto"}, args.out)
    report["steps"]["inline"] = speech(args, "inline_trump_ref",
                                       {**base_body, "input": EN_INLINE, "ref_audio": ref_b64, "ref_text": ref["text"],
                                        "language": "English"}, args.out)

    results: list = [None] * len(CONCURRENT)
    barrier = threading.Barrier(len(CONCURRENT))

    def worker(i: int) -> None:
        voice, lang, text = CONCURRENT[i]
        barrier.wait()
        results[i] = speech(args, f"concurrent_{i}_{voice}",
                            {**base_body, "input": text, "voice": voice, "language": lang}, args.out)

    t0 = time.perf_counter()
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(CONCURRENT))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - t0
    audio = sum(r.get("audio_s") or 0 for r in results)
    report["steps"]["concurrent"] = {
        "requests": results, "wall_s": round(wall, 3), "audio_s_total": round(audio, 3),
        "throughput_x_realtime": round(audio / wall, 3) if wall else None,
        "batch_sizes": [r["headers"].get("x-baseline-batch-size") for r in results],
        "batch_ids": [r["headers"].get("x-baseline-batch-id") for r in results],
        "ok": all(r["ok"] for r in results)}
    status, _, payload, _ = http("GET", base + "/v1/baseline/info", timeout=30)
    report["server_info_after"] = json.loads(payload) if status == 200 else {"status": status}
    report["finished"] = now()
    report["ok"] = all(s["ok"] for s in report["steps"].values())
    (args.out / "smoke.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"health {report['steps']['health']['status']}  voices {report['steps']['voices']['voices']}")
    print(f"{'request':<26}{'http':>5}{'lat_s':>8}{'audio_s':>8}{'rtf':>7}{'batch':>6}{'queue_ms':>9}{'frames':>7}"
          f"{'gen_ms':>9}  label")
    rows = [report["steps"][k] for k in ("english", "urdu", "inline")] + results
    for r in rows:
        h = r["headers"]
        print(f"{r['name']:<26}{r['status']:>5}{r['latency_s']:>8.2f}{r.get('audio_s') or 0:>8.2f}"
              f"{r.get('rtf') or 0:>7.2f}{h.get('x-baseline-batch-size', '-'):>6}{h.get('x-baseline-queue-ms', '-'):>9}"
              f"{h.get('x-baseline-codec-frames', '-'):>7}{h.get('x-baseline-gen-ms', '-'):>9}  "
              f"{'ok' if r.get('wav_label_ok') and r.get('header_label_ok') else 'MISSING'}"
              + ("" if r["ok"] else f"  FAIL {r.get('error', '')[:120]}"))
    c = report["steps"]["concurrent"]
    print(f"concurrent: wall {c['wall_s']} s, audio {c['audio_s_total']} s, {c['throughput_x_realtime']}x realtime, "
          f"batch sizes {c['batch_sizes']}")
    print(f"{'PASS' if report['ok'] else 'FAIL'}: {args.out / 'smoke.json'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
