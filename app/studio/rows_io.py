"""Dataset inputs: rows from CSV / JSON / JSONL (required: text; optional: id, speaker, tags, seed), speaker tags from
reference file names, and a speakers.csv (filename,transcript)."""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

csv.field_size_limit(10 ** 8)


def speaker_tag(name: str) -> str:
    """Speaker_1.wav -> speaker_1; 'Ali Khan' -> ali_khan."""
    stem = Path(name).stem if "." in name else name
    return re.sub(r"[^a-z0-9]+", "_", stem.strip().lower()).strip("_") or "speaker"


def safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value).strip()).strip("._") or "row"


@dataclass
class Row:
    index: int
    id: str
    text: str
    speaker: str | None = None
    tags: str = ""
    seed: int | None = None


class RowsError(ValueError):
    pass


def parse_rows(data: bytes | str, filename: str = "rows.csv") -> list[Row]:
    text = data.decode("utf-8-sig") if isinstance(data, (bytes, bytearray)) else data
    name = filename.lower()
    records: list[dict]
    if name.endswith(".jsonl") or (not name.endswith(".json") and text.lstrip().startswith("{")):
        records = [json.loads(l) for l in text.splitlines() if l.strip()]
    elif name.endswith(".json") or text.lstrip().startswith("["):
        obj = json.loads(text)
        records = obj["rows"] if isinstance(obj, dict) and "rows" in obj else obj
    else:
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",|\t;")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if not reader.fieldnames or "text" not in [f.strip().lower() for f in reader.fieldnames]:
            raise RowsError(f"CSV needs a 'text' column; found {reader.fieldnames}")
        records = [{(k or "").strip().lower(): v for k, v in r.items()} for r in reader]
    rows, seen = [], set()
    for i, r in enumerate(records):
        if not isinstance(r, dict):
            raise RowsError(f"row {i + 1} is not an object")
        t = str(r.get("text") or "").strip()
        if not t:
            continue
        rid = safe_id(r.get("id") or f"{len(rows) + 1:04d}")
        if rid in seen:
            rid = f"{rid}_{len(rows) + 1}"
        seen.add(rid)
        seed = r.get("seed")
        try:
            seed = int(seed) if seed not in (None, "") else None
        except (TypeError, ValueError):
            raise RowsError(f"row {i + 1}: seed {seed!r} is not an integer") from None
        spk = r.get("speaker")
        rows.append(Row(len(rows), rid, t, speaker_tag(str(spk)) if spk not in (None, "") else None,
                        str(r.get("tags") or "").strip(), seed))
    if not rows:
        raise RowsError("no rows with text")
    return rows


def parse_speakers_csv(data: bytes | str) -> dict[str, str]:
    """filename,transcript -> {speaker_tag: transcript}."""
    text = data.decode("utf-8-sig") if isinstance(data, (bytes, bytearray)) else data
    out = {}
    for r in csv.reader(io.StringIO(text)):
        if len(r) < 2 or (r[0].strip().lower() in ("filename", "file") and r[1].strip().lower() == "transcript"):
            continue
        out[speaker_tag(r[0])] = r[1].strip()
    return out
