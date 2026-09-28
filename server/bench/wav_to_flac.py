#!/usr/bin/env python3
"""Convert the WAV takes under results dirs to FLAC in place, losslessly and verified: each FLAC is decoded and
compared sample for sample with the WAV before the WAV is deleted, the AI-generated label of the WAV's LIST/INFO
comment goes into the FLAC's COMMENT tag, and the `file` fields of requests*.jsonl, scores.jsonl and takes_all.jsonl
next to the audio are rewritten from .wav to .flac (the eval tools read FLAC through soundfile). Frees ~50 % of the
space; nothing is lost.

    python server/bench/wav_to_flac.py server/results [--workers 8] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import struct
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf


def wav_comment(path: Path) -> str | None:
    data = path.read_bytes()[:4096]
    pos = 12
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if cid == b"LIST" and data[pos + 8:pos + 12] == b"INFO":
            sub = pos + 12
            end = min(len(data), pos + 8 + size)
            while sub + 8 <= end:
                sid, ssize = data[sub:sub + 4], struct.unpack("<I", data[sub + 4:sub + 8])[0]
                if sid == b"ICMT":
                    return data[sub + 8:sub + 8 + ssize].split(b"\0")[0].decode("utf-8", "replace")
                sub += 8 + ssize + (ssize & 1)
            return None
        if cid == b"data":
            return None
        pos += 8 + size + (size & 1)
    return None


def convert(wav: Path) -> tuple[str, int, int, str]:
    """(path, wav bytes, flac bytes, status)."""
    flac = wav.with_suffix(".flac")
    try:
        x, sr = sf.read(wav, dtype="int16", always_2d=True)
        comment = wav_comment(wav)
        with sf.SoundFile(flac, "w", samplerate=sr, channels=x.shape[1], format="FLAC", subtype="PCM_16") as f:
            if comment:
                f.comment = comment
            f.write(x)
        y, sr2 = sf.read(flac, dtype="int16", always_2d=True)
        if sr2 != sr or y.shape != x.shape or not np.array_equal(x, y):
            flac.unlink(missing_ok=True)
            return (str(wav), wav.stat().st_size, 0, "MISMATCH, kept WAV")
        wsize, fsize = wav.stat().st_size, flac.stat().st_size
        wav.unlink()
        return (str(wav), wsize, fsize, "ok")
    except Exception as exc:  # noqa: BLE001
        flac.unlink(missing_ok=True)
        return (str(wav), wav.stat().st_size if wav.exists() else 0, 0, f"ERROR {type(exc).__name__}: {exc}")


def rewrite_manifests(root: Path) -> int:
    n = 0
    for name in ("requests.jsonl", "requests.partial.jsonl", "scores.jsonl", "takes_all.jsonl"):
        for f in root.rglob(name):
            lines = f.read_text(encoding="utf-8").splitlines()
            out, changed = [], False
            for line in lines:
                if not line.strip():
                    out.append(line)
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    out.append(line)
                    continue
                v = r.get("file")
                if isinstance(v, str) and v.endswith(".wav"):
                    cand = (f.parent / v) if not os.path.isabs(v) else Path(v)
                    if cand.with_suffix(".flac").exists() and not cand.exists():
                        r["file"] = v[:-4] + ".flac"
                        changed = True
                out.append(json.dumps(r, ensure_ascii=False))
            if changed:
                f.write_text("\n".join(out) + "\n", encoding="utf-8")
                n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="+", type=Path)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    wavs = [w for root in args.roots for w in root.rglob("*.wav")]
    total = sum(w.stat().st_size for w in wavs)
    print(f"{len(wavs)} WAVs, {total / 1e9:.2f} GB")
    if args.dry_run:
        return
    saved = 0
    bad = []
    with ProcessPoolExecutor(args.workers) as pool:
        for i, (path, wsize, fsize, status) in enumerate(pool.map(convert, wavs, chunksize=8), 1):
            if status != "ok":
                bad.append((path, status))
            else:
                saved += wsize - fsize
            if i % 500 == 0:
                print(f"  {i}/{len(wavs)} converted, {saved / 1e9:.2f} GB freed", flush=True)
    for root in args.roots:
        print(f"{root}: {rewrite_manifests(root)} manifest files rewritten")
    print(f"done: {len(wavs) - len(bad)} converted, {saved / 1e9:.2f} GB freed, {len(bad)} kept as WAV")
    for path, status in bad[:20]:
        print("  ", path, status)


if __name__ == "__main__":
    main()
