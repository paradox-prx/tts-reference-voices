#!/usr/bin/env python3
"""Derive a training manifest from dataset folders in the XTTS layout.

Each folder holds `wavs/...` and one or more CSVs, either

    audio_file|text|speaker_name        (pipe-separated; paths relative to the folder)
    audio,text[,language]               (comma-separated; speaker then comes from the wavs/<speaker>/ folder)

Example:

    python -m qwen_train.derive --name urdu300 --out data/urdu300 \
        --folder /data/female-data-50-hrs-preprocessed --folder /data/batch2 --folder /data/samples \
        --csv-glob '*_cleaned.csv' --speaker-from column --eval-frac 0.02 --holdout-speakers speaker-8

Writes to --out:
    manifest.jsonl   one row per kept utterance: id, audio (absolute path), text (normalised), text_raw, speaker,
                     duration, sr, channels, split (train | eval | holdout), source (folder tag, csv)
    dropped.jsonl    rows left out, with the reason
    speakers.json    per speaker: utterances, hours, split counts
    stats.md         the summary printed at the end

Splits: `eval` takes --eval-frac of every speaker's utterances (between --eval-min and --eval-max per speaker) with a
fixed seed; `holdout` takes whole speakers named in --holdout-speakers (never trained: they measure cloning of unseen
voices). Everything else is `train`.
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import json
import os
import random
import struct
import sys
import time
from pathlib import Path

from .text import normalize_urdu, script_profile

csv.field_size_limit(10**9)
AUDIO_EXT = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}
JUNK = str.maketrans({c: " " for c in "#*_/@&+|~^<>[]{}\\"})


def wav_header(path: str):
    """(sr, channels, seconds) from the RIFF header, without reading the samples. None if not a plain WAV."""
    with open(path, "rb") as f:
        head = f.read(4096)
    if head[:4] != b"RIFF" or head[8:12] != b"WAVE":
        return None
    i, sr, ch, bps, data = 12, None, None, None, None
    while i + 8 <= len(head):
        cid, size = head[i:i + 4], struct.unpack("<I", head[i + 4:i + 8])[0]
        if cid == b"fmt ":
            ch, sr = struct.unpack("<HI", head[i + 10:i + 16])
            bps = struct.unpack("<H", head[i + 22:i + 24])[0]
        elif cid == b"data":
            data = size
            break
        i += 8 + size + (size & 1)
    if not (sr and ch and bps):
        return None
    if data is None or data == 0 or data == 0xFFFFFFFF:  # streamed / unfinished header: use the file size
        data = os.path.getsize(path) - 44
    return sr, ch, data / (sr * ch * bps / 8)


def audio_info(path: str):
    info = wav_header(path) if path.lower().endswith(".wav") else None
    if info is None:
        import soundfile as sf  # slower path: non-WAV or odd headers
        meta = sf.info(path)
        info = (meta.samplerate, meta.channels, meta.duration)
    return info


def read_rows(csv_path: Path):
    """Yield (audio_relpath, text, speaker_or_None, language_or_None) from either CSV dialect."""
    with open(csv_path, encoding="utf-8", newline="") as f:
        first = f.readline()
        f.seek(0)
        delim = "|" if first.count("|") >= 2 else ","
        reader = csv.reader(f, delimiter=delim)
        header = next(reader, None)
        if header is None:
            return
        cols = [h.strip().lower() for h in header]
        if "text" not in cols:  # header-less file: assume audio|text|speaker
            cols = ["audio_file", "text", "speaker_name"][:len(header)]
            f.seek(0)
            reader = csv.reader(f, delimiter=delim)
        ai = next((i for i, c in enumerate(cols) if c in ("audio_file", "audio", "path", "file")), 0)
        ti = cols.index("text")
        si = next((i for i, c in enumerate(cols) if c in ("speaker_name", "speaker")), None)
        li = next((i for i, c in enumerate(cols) if c == "language"), None)
        for row in reader:
            if len(row) <= max(ai, ti):
                continue
            yield (row[ai].strip(), row[ti], row[si].strip() if si is not None and len(row) > si else None,
                   row[li].strip() if li is not None and len(row) > li else None)


def speaker_from_path(rel: str) -> str | None:
    parts = Path(rel).parts
    if len(parts) >= 3 and parts[0] == "wavs":
        return parts[1]
    if len(parts) >= 2:
        return parts[-2]
    return None


def clean_speaker(name: str) -> str:
    return name.strip().lstrip("@").strip().lower().replace(" ", "_")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="dataset name (goes into utterance ids)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--folder", action="append", required=True, help="dataset folder (repeatable)")
    ap.add_argument("--csv-glob", default="*_cleaned.csv", help="which CSVs of each folder to read (default: %(default)s)")
    ap.add_argument("--speaker-from", choices=("column", "folder"), default="column",
                    help="speaker identity: the speaker_name column (default) or the wavs/<speaker>/ folder")
    ap.add_argument("--speaker-prefix", action="store_true",
                    help="prefix speaker names with the folder tag (when the same label means different people)")
    ap.add_argument("--speaker", default=None, help="constant speaker name for every row (single-speaker folders)")
    ap.add_argument("--speaker-map", default=None,
                    help="assignments.jsonl from `qwen_train.speakers cluster`: speakers re-tagged by voice (keyed by audio path)")
    ap.add_argument("--keep-multi-voice", action="store_true", help="keep clips the speaker map flags as containing 2+ voices")
    ap.add_argument("--min-dur", type=float, default=0.8)
    ap.add_argument("--max-dur", type=float, default=30.0)
    ap.add_argument("--min-chars", type=int, default=3)
    ap.add_argument("--max-chars", type=int, default=500)
    ap.add_argument("--min-urdu-frac", type=float, default=0.0,
                    help="drop texts with a smaller share of Arabic-script letters (default 0: keep Latin / English rows too)")
    ap.add_argument("--allow-sr", default="", help="comma list of sample rates to keep (default: any)")
    ap.add_argument("--no-spell-numbers", action="store_true")
    ap.add_argument("--eval-frac", type=float, default=0.02)
    ap.add_argument("--eval-min", type=int, default=5)
    ap.add_argument("--eval-max", type=int, default=200)
    ap.add_argument("--holdout-speakers", default="", help="comma list of speakers kept entirely out of training")
    ap.add_argument("--seed", type=int, default=1234)
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    allow_sr = {int(x) for x in a.allow_sr.split(",") if x.strip()}
    holdout = {clean_speaker(s) for s in a.holdout_speakers.split(",") if s.strip()}
    t0 = time.time()
    spk_map = {}
    if a.speaker_map:
        for l in open(a.speaker_map, encoding="utf-8"):
            m = json.loads(l)
            spk_map[str(Path(m["audio"]).resolve())] = m
        print(f"speaker map: {len(spk_map)} clips re-tagged by voice")
    kept, dropped = [], []
    seen_paths: set[str] = set()
    reasons = collections.Counter()
    n_read = 0
    for folder in a.folder:
        folder = Path(folder).resolve()
        tag = folder.name
        csvs = sorted(glob.glob(str(folder / a.csv_glob)))
        if not csvs:
            print(f"warning: no CSV matches {a.csv_glob} in {folder}", file=sys.stderr)
        for c in csvs:
            for rel, text_raw, spk_col, lang in read_rows(Path(c)):
                n_read += 1
                path = str((folder / rel).resolve()) if not os.path.isabs(rel) else rel
                row = {"id": f"{a.name}/{tag}/{Path(rel).with_suffix('').as_posix()}", "audio": path, "text_raw": text_raw,
                       "source": f"{tag}/{Path(c).name}", "language": lang}
                if Path(path).suffix.lower() not in AUDIO_EXT:
                    reasons["not_audio"] += 1; dropped.append(row | {"reason": "not_audio"}); continue
                if path in seen_paths:
                    reasons["duplicate_path"] += 1; dropped.append(row | {"reason": "duplicate_path"}); continue
                if not os.path.exists(path):
                    reasons["missing_file"] += 1; dropped.append(row | {"reason": "missing_file"}); continue
                if a.speaker:
                    spk = a.speaker
                elif a.speaker_from == "column" and spk_col:
                    spk = spk_col
                else:
                    spk = speaker_from_path(rel) or spk_col or "unknown"
                spk = clean_speaker(spk)
                if a.speaker_prefix:
                    spk = f"{tag}:{spk}"
                ref_ok = True
                if spk_map:
                    m = spk_map.get(path)
                    if m is None:
                        reasons["not_in_speaker_map"] += 1; dropped.append(row | {"reason": "not_in_speaker_map"}); continue
                    if m["multi_voice"] and not a.keep_multi_voice:
                        reasons["multi_voice"] += 1; dropped.append(row | {"reason": "multi_voice"}); continue
                    row["orig_speaker"] = spk
                    spk, ref_ok = m["speaker"], bool(m["ref_ok"])
                text = normalize_urdu(text_raw.translate(JUNK), spell_numbers=not a.no_spell_numbers)
                prof = script_profile(text)
                if len(text) < a.min_chars or len(text) > a.max_chars:
                    reasons["text_length"] += 1; dropped.append(row | {"reason": "text_length", "chars": len(text)}); continue
                if prof["letters"] == 0 or prof["urdu"] / prof["letters"] < a.min_urdu_frac:
                    reasons["not_urdu"] += 1; dropped.append(row | {"reason": "not_urdu", "profile": prof}); continue
                try:
                    sr, ch, dur = audio_info(path)
                except Exception as exc:  # noqa: BLE001 - every unreadable file is a dropped row
                    reasons["unreadable"] += 1; dropped.append(row | {"reason": f"unreadable: {exc}"}); continue
                if allow_sr and sr not in allow_sr:
                    reasons["sample_rate"] += 1; dropped.append(row | {"reason": "sample_rate", "sr": sr}); continue
                if dur < a.min_dur or dur > a.max_dur:
                    reasons["duration"] += 1; dropped.append(row | {"reason": "duration", "duration": round(dur, 2)}); continue
                seen_paths.add(path)
                kept.append(row | {"text": text, "speaker": spk, "ref_ok": ref_ok, "duration": round(dur, 3), "sr": sr, "channels": ch,
                                   "chars": len(text), "urdu_frac": round(prof["urdu"] / prof["letters"], 3)})

    # splits
    rng = random.Random(a.seed)
    by_spk: dict[str, list[dict]] = collections.defaultdict(list)
    for r in kept:
        by_spk[r["speaker"]].append(r)
    for spk, rows in by_spk.items():
        if spk in holdout:
            for r in rows:
                r["split"] = "holdout"
            continue
        n_eval = min(a.eval_max, max(a.eval_min, round(len(rows) * a.eval_frac))) if len(rows) >= 2 * a.eval_min else 0
        idx = list(range(len(rows)))
        rng.shuffle(idx)
        eval_idx = set(idx[:n_eval])
        for i, r in enumerate(rows):
            r["split"] = "eval" if i in eval_idx else "train"
    missing_holdout = holdout - set(by_spk)
    if missing_holdout:
        print(f"warning: holdout speakers not found: {sorted(missing_holdout)}", file=sys.stderr)

    with open(out / "manifest.jsonl", "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out / "dropped.jsonl", "w", encoding="utf-8") as f:
        for r in dropped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    speakers = {}
    for spk, rows in sorted(by_spk.items()):
        splits = collections.Counter(r["split"] for r in rows)
        speakers[spk] = {"utterances": len(rows), "hours": round(sum(r["duration"] for r in rows) / 3600, 2),
                         "mean_seconds": round(sum(r["duration"] for r in rows) / len(rows), 2), **splits}
    (out / "speakers.json").write_text(json.dumps(speakers, indent=1, ensure_ascii=False))

    hours = sum(r["duration"] for r in kept) / 3600
    lines = [f"# {a.name}: derived {time.strftime('%Y-%m-%d %H:%M')} from {', '.join(a.folder)}", "",
             f"rows read {n_read}, kept {len(kept)} ({hours:.2f} h), dropped {len(dropped)}: "
             + ", ".join(f"{k} {v}" for k, v in reasons.most_common()), "",
             "| speaker | utterances | hours | mean s | train | eval | holdout |", "|---|---|---|---|---|---|---|"]
    for spk, s in speakers.items():
        lines.append(f"| {spk} | {s['utterances']} | {s['hours']} | {s['mean_seconds']} | {s.get('train', 0)} | "
                     f"{s.get('eval', 0)} | {s.get('holdout', 0)} |")
    srs = collections.Counter(r["sr"] for r in kept)
    chans = collections.Counter(r["channels"] for r in kept)
    durs = sorted(r["duration"] for r in kept)
    if durs:
        lines += ["", f"sample rates {dict(srs)}, channels {dict(chans)}, duration p10/p50/p90/max "
                      f"{durs[len(durs)//10]:.1f}/{durs[len(durs)//2]:.1f}/{durs[9*len(durs)//10]:.1f}/{durs[-1]:.1f} s, "
                      f"chars p50 {sorted(r['chars'] for r in kept)[len(kept)//2]}",
                  f"elapsed {time.time() - t0:.0f} s"]
    text = "\n".join(lines) + "\n"
    (out / "stats.md").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
