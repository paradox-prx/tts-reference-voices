"""Dataset export: a zip streamed file by file (never the whole set in RAM), in a generic layout

    wavs/<speaker>/<id>.wav   metadata.csv   metadata.jsonl   rejected.csv   speakers/<speaker>.wav   speakers.csv
    job_config.json   README.md

plus small converters to other training formats (convert())."""
from __future__ import annotations

import csv
import io
import json
import time
import zipfile
from pathlib import Path
from typing import Iterable, Iterator

META_FIELDS = ["audio_path", "text", "speaker", "tags", "seed", "duration_s", "sample_rate", "qc_status", "wer"]
REJECT_FIELDS = ["id", "text", "speaker", "tags", "seed", "reason", "attempts"]


class _Sink(io.RawIOBase):
    def __init__(self):
        self.buf = bytearray()

    def writable(self) -> bool:
        return True

    def write(self, b) -> int:
        self.buf += b
        return len(b)

    def pop(self) -> bytes:
        out = bytes(self.buf)
        self.buf.clear()
        return out


def iter_zip(entries: Iterable[tuple[str, bytes | Path]], chunk: int = 1 << 20) -> Iterator[bytes]:
    """Zip entries (arcname, bytes or file path) as a byte stream. WAVs are stored, text deflated."""
    sink = _Sink()
    with zipfile.ZipFile(sink, "w", allowZip64=True) as zf:
        for name, src in entries:
            comp = zipfile.ZIP_STORED if name.endswith(".wav") else zipfile.ZIP_DEFLATED
            info = zipfile.ZipInfo(name, time.localtime()[:6])
            info.compress_type = comp
            with zf.open(info, "w", force_zip64=True) as dst:
                if isinstance(src, (bytes, bytearray)):
                    dst.write(src)
                else:
                    with open(src, "rb") as f:
                        while block := f.read(chunk):
                            dst.write(block)
                            if len(sink.buf) >= chunk:
                                yield sink.pop()
            yield sink.pop()
    yield sink.pop()


def metadata_csv(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=META_FIELDS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


def metadata_jsonl(rows: list[dict]) -> bytes:
    return "".join(json.dumps({k: r.get(k) for k in META_FIELDS}, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")


def rejected_csv(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=REJECT_FIELDS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


def speakers_csv(speakers: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["filename", "transcript"])
    for s in speakers:
        w.writerow([f"speakers/{s['tag']}.wav", s["transcript"]])
    return buf.getvalue().encode("utf-8")


def readme(job: dict, counts: dict, per_speaker: dict) -> bytes:
    cfg = job["config"]
    lines = [f"# {job['name']}", "", f"Generated {time.strftime('%Y-%m-%d %H:%M %Z')} by higgs-studio (Higgs Audio v3, "
             "bosonai/higgs-tts-3-4b). **All audio is AI-generated speech** cloned from the reference voices in "
             "speakers/.", "",
             f"- rows: {counts.get('total', 0)} total, {counts.get('done', 0)} kept, {counts.get('flagged', 0)} flagged "
             f"(rejected.csv), {counts.get('error', 0)} errors",
             f"- audio: {counts.get('seconds', 0) / 3600:.2f} h, {cfg['audio']['sample_rate']} Hz mono 16-bit WAV, "
             f"loudness {cfg['audio'].get('loudness_lufs')} LUFS",
             "- per speaker: " + ", ".join(f"{k} {v}" for k, v in per_speaker.items()),
             f"- sampling: {json.dumps(cfg['sampling'])}; seeds: {json.dumps(cfg['seeds'])}; takes per row: {cfg['takes']}",
             f"- tags: {json.dumps(cfg['tags'], ensure_ascii=False)}",
             f"- QC: {json.dumps(cfg['qc'])}", "",
             "Files: `metadata.csv` / `metadata.jsonl` (audio_path, text, speaker, tags, seed, duration_s, sample_rate, "
             "qc_status, wer; audio_path is relative to this folder), `rejected.csv`, `speakers/` + `speakers.csv` (the "
             "references and their transcripts), `job_config.json` (re-import it to repeat the run).", ""]
    return "\n".join(lines).encode("utf-8")


# ---- converters to other layouts (the Qwen3-TTS training format is not fixed yet) ----------------------------------

def to_pipe_csv(rows: list[dict]) -> bytes:
    """`audio_file|text|speaker_name` (the XTTS / qwen-train `derive` input format): drop it next to wavs/ and run
    `python -m qwen_train.derive --folder <unzipped> --csv-glob metadata_pipe.csv`."""
    out = ["audio_file|text|speaker_name"]
    for r in rows:
        out.append(f"{r['audio_path']}|{r['text'].replace('|', ' ').replace(chr(10), ' ')}|{r['speaker']}")
    return ("\n".join(out) + "\n").encode("utf-8")


CONVERTERS = {"pipe_csv": ("metadata_pipe.csv", to_pipe_csv)}


def convert(rows: list[dict], fmt: str) -> tuple[str, bytes]:
    if fmt not in CONVERTERS:
        raise ValueError(f"unknown format {fmt!r}; available: {', '.join(CONVERTERS)}")
    name, fn = CONVERTERS[fmt]
    return name, fn(rows)
