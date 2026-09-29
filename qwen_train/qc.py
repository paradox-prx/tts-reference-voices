#!/usr/bin/env python3
"""Quality-check a manifest: audio measurements for every utterance and, optionally, ASR agreement with the transcript.

    python -m qwen_train.qc --manifest data/x/manifest.jsonl [--asr large-v3 --device cuda] [--apply]

Per utterance (written to qc.jsonl next to the manifest, resumable):
    peak_dbfs, rms_dbfs, clip_frac (samples at |x| >= 0.99), lead_sil_s / trail_sil_s (below -45 dBFS),
    max_sil_s (longest internal silence), dc_offset, nan
    asr_text, cer (character error rate, whitespace and punctuation removed), wer   (with --asr)

--apply writes manifest_qc.jsonl = the manifest minus rows over the thresholds (reasons in dropped_qc.jsonl):
audio checks plus a per-speaker pace check (Arabic-script letters per second, robust z-score over the speaker's clips;
it flags transcripts far too short or long for their audio, e.g. a truncated transcript). Both are free.

The ASR agreement (--asr) is a diagnostic, NOT a default filter: on this project's Gemini-made transcripts Whisper
was the wrong side in 5 of the 6 worst disagreements (it collapses repeated phrases and restarts that the speaker
really says, and hallucinates on some clips; docs/EXPERIMENTS.md V12). Only use --max-cer if the transcripts come
from a weaker source than Whisper.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf

PUNCT = re.compile(r"[\s،؛؟۔.,;:!?\"'()\[\]{}\-–—«»]+")


def strip_punct(s: str) -> str:
    return PUNCT.sub("", s)


def edit_distance(a, b) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(ref: str, hyp: str) -> float:
    r, h = strip_punct(ref), strip_punct(hyp)
    return edit_distance(r, h) / max(1, len(r))


def wer(ref: str, hyp: str) -> float:
    r = [strip_punct(w) for w in ref.split() if strip_punct(w)]
    h = [strip_punct(w) for w in hyp.split() if strip_punct(w)]
    return edit_distance(r, h) / max(1, len(r))


def load_mono(path: str):
    x, sr = sf.read(path, dtype="float32", always_2d=True)
    return x.mean(axis=1), sr


def audio_measures(path: str, sil_db: float = -45.0) -> dict:
    x, sr = load_mono(path)
    n = len(x)
    if n == 0:
        return {"nan": True, "seconds": 0.0}
    nan = bool(np.isnan(x).any())
    x = np.nan_to_num(x)
    peak = float(np.abs(x).max())
    rms = float(np.sqrt(np.mean(x ** 2)))
    frame = max(1, int(sr * 0.02))
    nf = n // frame
    if nf:
        f = x[:nf * frame].reshape(nf, frame)
        fdb = 20 * np.log10(np.sqrt((f ** 2).mean(axis=1)) + 1e-9)
        voiced = fdb > sil_db
        lead = int(np.argmax(voiced)) if voiced.any() else nf
        trail = int(np.argmax(voiced[::-1])) if voiced.any() else nf
        best = run = 0
        for v in voiced[lead:nf - trail]:
            run = 0 if v else run + 1
            best = max(best, run)
    else:
        lead = trail = best = 0
    return {"nan": nan, "seconds": round(n / sr, 3), "sr": sr,
            "peak_dbfs": round(20 * math.log10(peak + 1e-9), 1), "rms_dbfs": round(20 * math.log10(rms + 1e-9), 1),
            "clip_frac": round(float((np.abs(x) >= 0.99).mean()), 5), "lead_sil_s": round(lead * frame / sr, 2),
            "trail_sil_s": round(trail * frame / sr, 2), "max_sil_s": round(best * frame / sr, 2),
            "dc_offset": round(float(x.mean()), 4)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", default=None, help="qc.jsonl path (default: next to the manifest)")
    ap.add_argument("--asr", default=None, help="faster-whisper model, e.g. large-v3 (default: audio checks only)")
    ap.add_argument("--asr-compute", default=None, help="float16 | int8_float16 | int8 (default by device)")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--beam", type=int, default=1)
    ap.add_argument("--language", default="ur")
    ap.add_argument("--workers", type=int, default=8, help="threads for the audio measurements")
    ap.add_argument("--limit", type=int, default=0, help="only the first N utterances not yet checked")
    ap.add_argument("--apply", action="store_true", help="write manifest_qc.jsonl with the thresholds below")
    ap.add_argument("--max-cer", type=float, default=0.0, help="drop rows with ASR CER above this (0 = off, default)")
    ap.add_argument("--max-pace-z", type=float, default=3.5,
                    help="drop rows whose letters/second is further than this many robust SDs from the speaker's median (0 = off)")
    ap.add_argument("--max-clip", type=float, default=0.01)
    ap.add_argument("--max-lead", type=float, default=2.0)
    ap.add_argument("--max-trail", type=float, default=2.5)
    ap.add_argument("--max-sil", type=float, default=3.0)
    ap.add_argument("--min-rms", type=float, default=-40.0)
    a = ap.parse_args(argv)

    manifest = Path(a.manifest)
    out = Path(a.out) if a.out else manifest.with_name("qc.jsonl")
    rows = [json.loads(l) for l in open(manifest, encoding="utf-8")]
    done = {}
    if out.exists():
        for l in open(out, encoding="utf-8"):
            r = json.loads(l)
            done[r["id"]] = r
    todo = [r for r in rows if r["id"] not in done or (a.asr and "cer" not in done[r["id"]])]
    if a.limit:
        todo = todo[:a.limit]
    print(f"{len(rows)} rows, {len(done)} already checked, {len(todo)} to do", flush=True)

    asr = None
    if a.asr and todo:
        from faster_whisper import WhisperModel
        compute = a.asr_compute or ("float16" if a.device == "cuda" else "int8")
        asr = WhisperModel(a.asr, device=a.device, compute_type=compute)

    t0 = time.time()
    with open(out, "a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=a.workers) as ex:
        def measure(r):
            try:
                return r, audio_measures(r["audio"])
            except Exception as exc:  # noqa: BLE001
                return r, {"error": str(exc)}
        for i, (r, m) in enumerate(ex.map(measure, todo), 1):
            rec = done.get(r["id"], {}) | {"id": r["id"]} | m
            if asr is not None and "error" not in m:
                segs, _ = asr.transcribe(r["audio"], language=a.language, beam_size=a.beam, vad_filter=False,
                                         condition_on_previous_text=False)
                hyp = " ".join(s.text.strip() for s in segs)
                rec |= {"asr_text": hyp, "cer": round(cer(r["text"], hyp), 4), "wer": round(wer(r["text"], hyp), 4)}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            done[r["id"]] = rec
            if i % 200 == 0 or i == len(todo):
                el = time.time() - t0
                print(f"  {i}/{len(todo)} {el:.0f}s eta {el / i * (len(todo) - i):.0f}s", flush=True)

    # summary
    recs = [done[r["id"]] for r in rows if r["id"] in done]
    def pct(xs, p):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(p / 100 * (len(xs) - 1)))] if xs else None
    print(f"checked {len(recs)}/{len(rows)}")
    for k in ("rms_dbfs", "peak_dbfs", "clip_frac", "lead_sil_s", "trail_sil_s", "max_sil_s", "cer", "wer"):
        xs = [x[k] for x in recs if isinstance(x.get(k), (int, float))]
        if xs:
            print(f"  {k:12s} p10 {pct(xs, 10)} p50 {pct(xs, 50)} p90 {pct(xs, 90)} max {max(xs)}")

    if a.apply:
        import statistics
        letters = lambda t: len(re.findall(r"[\u0600-\u06FF]", t))  # noqa: E731
        pace_z = {}
        if a.max_pace_z:
            by_spk = {}
            for r in rows:
                if r.get("duration"):
                    by_spk.setdefault(r["speaker"], []).append((r["id"], letters(r["text"]) / r["duration"]))
            for spk, vals in by_spk.items():
                med = statistics.median(v for _, v in vals)
                mad = statistics.median(abs(v - med) for _, v in vals) or 1e-6
                for uid, v in vals:
                    pace_z[uid] = (v - med) / (1.4826 * mad)
        kept, dropped = [], []
        for r in rows:
            q = done.get(r["id"])
            why = []
            if q is None:
                why.append("unchecked")
            else:
                if q.get("error") or q.get("nan"):
                    why.append("unreadable")
                if q.get("clip_frac", 0) > a.max_clip:
                    why.append("clipping")
                if q.get("lead_sil_s", 0) > a.max_lead:
                    why.append("leading_silence")
                if q.get("trail_sil_s", 0) > a.max_trail:
                    why.append("trailing_silence")
                if q.get("max_sil_s", 0) > a.max_sil:
                    why.append("internal_silence")
                if q.get("rms_dbfs", 0) < a.min_rms:
                    why.append("too_quiet")
                if a.max_cer and "cer" in q and q["cer"] > a.max_cer:
                    why.append("transcript_mismatch")
                if a.max_pace_z and abs(pace_z.get(r["id"], 0.0)) > a.max_pace_z:
                    why.append("pace_outlier")
            (dropped if why else kept).append((r, why, q))
        with open(manifest.with_name("manifest_qc.jsonl"), "w", encoding="utf-8") as f:
            for r, _, q in kept:
                f.write(json.dumps(r | ({"cer": q["cer"]} if q and "cer" in q else {}), ensure_ascii=False) + "\n")
        with open(manifest.with_name("dropped_qc.jsonl"), "w", encoding="utf-8") as f:
            for r, why, q in dropped:
                f.write(json.dumps(r | {"reason": why, "qc": q}, ensure_ascii=False) + "\n")
        import collections
        c = collections.Counter(w for _, why, _ in dropped for w in why)
        hours = sum(r["duration"] for r, _, _ in kept) / 3600
        print(f"applied: kept {len(kept)} ({hours:.2f} h), dropped {len(dropped)}: {dict(c)} -> manifest_qc.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
