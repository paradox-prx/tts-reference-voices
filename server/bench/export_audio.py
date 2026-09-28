#!/usr/bin/env python3
"""Export the benchmark's audio for publication: one tar per phase of labelled FLAC files.

    venvs/gateway/bin/python bench/export_audio.py --out /path/to/tars [phase ...]   # default: every phase
    venvs/gateway/bin/python bench/export_audio.py --dir --out results 13_final_server  # FLACs beside the WAVs

Every take under results/<phase>/ (wav, mp3, raw pcm) becomes <phase>/<same path>.flac inside <out>/<phase>.tar,
with the AI-generated label in its Vorbis COMMENT and TITLE, next to AI_GENERATED_AUDIO.txt and AUDIO_MANIFEST.jsonl
(file, source, voice, text, and the takes left out with the reason). The numbers of every take stay in the phase's
requests.jsonl / takes_all.jsonl (published in git); the manifest's "source" is the path those files use.

Left out: takes whose text reads as a political statement or an official announcement (eval/pick_samples.py
POLITICAL: realistic misuse in a real head of government's voice), and takes whose text cannot be found (a few
smoke and knob checks with free-form side files: every text string of their folder must be non-political).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tarfile
import time
from pathlib import Path

import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
from pick_samples import LABEL, political  # noqa: E402

AUDIO = {".wav", ".mp3", ".pcm", ".flac", ".opus"}
NOTICE = ("AI-GENERATED AUDIO. Every audio file in this folder or archive is synthetic speech from Qwen3-TTS voice cloning that imitates "
          "real people (trump: Donald Trump; shehbaz: Shehbaz Sharif). None of it is a real recording and the speakers "
          "never said these words; the texts are fictional benchmark prompts. Each FLAC carries this label in its "
          "metadata. Do not present, cut or redistribute these clips as anything other than labelled AI-generated "
          "benchmark output.\n")


def json_strings(obj, keys=("text", "input")) -> list[str]:
    """Every string under a text-like key, at any depth."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and isinstance(v, str):
                out.append(v)
            else:
                out += json_strings(v, keys)
    elif isinstance(obj, list):
        for v in obj:
            out += json_strings(v, keys)
    return out


def load_json_any(f: Path) -> list:
    try:
        if f.suffix == ".jsonl":
            return [json.loads(line) for line in f.open() if line.strip()]
        return [json.loads(f.read_text())]
    except (ValueError, UnicodeDecodeError):
        return []


def texts_of(phase: Path) -> tuple[dict[str, dict], dict[Path, list[str]]]:
    """(resolved audio path -> request row, folder -> every text string of its json side files)."""
    rows, folder_texts = {}, {}
    for f in sorted(list(phase.rglob("*.jsonl")) + list(phase.rglob("*.json"))):
        docs = load_json_any(f)
        folder_texts.setdefault(f.parent, []).extend(s for d in docs for s in json_strings(d))
        for r in docs:
            if not isinstance(r, dict):
                continue
            if r.get("file") and isinstance(r.get("text"), str):
                p = Path(r["file"])
                for cand in (p if p.is_absolute() else f.parent / p, phase / p):
                    rows.setdefault(str(cand.resolve()), r)
            if isinstance(r.get("text"), str):
                # knob checks: one text, takes[].file next to the json; smoke takes: take_00.json beside take_00.wav,
                # or numbers.json beside the folder's only take
                for t in r.get("takes") or []:
                    if isinstance(t, dict) and t.get("file"):
                        rows.setdefault(str((f.parent / t["file"]).resolve()), {"text": r["text"], "voice": r.get("voice")})
                takes = [a for a in f.parent.iterdir() if a.suffix in AUDIO]
                for a in takes:
                    if a.stem == f.stem or len(takes) == 1:
                        rows.setdefault(str(a.resolve()), {"text": r["text"], "voice": r.get("voice")})
    return rows, folder_texts


def voice_guess(rel: str, row: dict | None) -> str:
    v = ((row or {}).get("voice") or "").split("-")[0]
    if v:
        return v
    return next((x for x in ("trump", "shehbaz") if x in rel), "unknown")


def read_audio(f: Path):
    if f.suffix == ".pcm":
        return sf.read(f, dtype="int16", format="RAW", samplerate=24000, channels=1, subtype="PCM_16")
    return sf.read(f, dtype="int16")


def export_phase(phase: Path, out: Path, as_dir: bool = False) -> dict:
    rows, folder_texts = texts_of(phase)
    manifest, stats = [], {"included": 0, "political": 0, "no_text": 0, "unreadable": 0, "seconds": 0.0}
    tar_path = out / f"{phase.name}.tar"
    with (contextlib.nullcontext() if as_dir else tarfile.open(tar_path, "w")) as tar:
        def add(name: str, data: bytes) -> None:
            if as_dir:
                (out / phase.name / name).parent.mkdir(parents=True, exist_ok=True)
                (out / phase.name / name).write_bytes(data)
                return
            info = tarfile.TarInfo(f"{phase.name}/{name}")
            info.size, info.mtime = len(data), int(time.time())
            tar.addfile(info, io.BytesIO(data))

        add("AI_GENERATED_AUDIO.txt", NOTICE.encode())
        for f in sorted(p for p in phase.rglob("*") if p.suffix in AUDIO and p.is_file()):
            rel = str(f.relative_to(phase))
            row = rows.get(str(f.resolve()))
            entry = {"file": str(Path(rel).with_suffix(".flac")), "source": rel, "voice": voice_guess(rel, row),
                     "text": row.get("text") if row else None}
            if row is None:  # side-file check: every text string of this folder and its parent must be clean
                strings = folder_texts.get(f.parent, []) + folder_texts.get(f.parent.parent, [])
                if not strings:
                    stats["no_text"] += 1
                    manifest.append(entry | {"file": None, "left_out": "text not found"})
                    continue
                if any(political({"text": s}) for s in strings):
                    stats["political"] += 1
                    manifest.append(entry | {"file": None, "left_out": "political or official text in its folder"})
                    continue
                entry["text"] = "(smoke / knob check; texts in the side files of this folder)"
            elif political(row):
                stats["political"] += 1
                manifest.append(entry | {"file": None, "left_out": "political or official text"})
                continue
            try:
                x, sr = read_audio(f)
            except (sf.LibsndfileError, RuntimeError) as e:
                stats["unreadable"] += 1
                manifest.append(entry | {"file": None, "left_out": f"unreadable: {e}"})
                continue
            buf = io.BytesIO()
            with sf.SoundFile(buf, "w", samplerate=sr, channels=1, format="FLAC", subtype="PCM_16") as w:
                w.comment = LABEL
                w.title = f"AI-generated {entry['voice']} voice clone ({phase.name}/{Path(rel).parent})"
                w.write(x if x.ndim == 1 else x[:, 0])
            add(entry["file"], buf.getvalue())
            stats["included"] += 1
            stats["seconds"] += len(x) / sr
            manifest.append(entry)
        add("AUDIO_MANIFEST.jsonl", "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in manifest).encode())
    stats["seconds"] = round(stats["seconds"], 1)
    if not as_dir:
        stats["tar_mb"] = round(tar_path.stat().st_size / 1e6, 1)
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phases", nargs="*", help="phase folder names (default: every phase under --results)")
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--out", required=True, help="directory for <phase>.tar (or for <phase>/... with --dir)")
    ap.add_argument("--dir", action="store_true", help="write <out>/<phase>/<path>.flac files instead of a tar")
    a = ap.parse_args()
    results, out = Path(a.results), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    phases = a.phases or sorted(p.name for p in results.iterdir()
                                if p.is_dir() and not p.name.startswith("_samples"))
    summary = {}
    for name in phases:
        summary[name] = export_phase(results / name, out, a.dir)
        print(name, summary[name], flush=True)
    if not a.dir:
        (out / "export_summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
