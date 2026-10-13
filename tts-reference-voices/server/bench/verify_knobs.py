#!/usr/bin/env python3
"""Check that request knobs really change what the server does, before a benchmark phase relies on them (vLLM-Omni
silently ignores unknown or misplaced fields, so a knob that "works" may be doing nothing).

    venvs/gateway/bin/python bench/verify_knobs.py --url http://127.0.0.1:8091 --out results/X/knobs --spec SPEC

SPEC is a JSON object (or a path to one):
  name      label; results go to <out>/<name>/ (knobs.json + one AI-labelled WAV per take)
  voice     voice id (default trump). Requests are bench_tts.py's inline requests for that voice (ref_audio data: URL,
            ref_text, language English/Auto, task_type Base, wav), unless `base` changes them
  text      text to synthesise (default: the voice's first 'medium' pool text, ~7 s)
  base      fields merged into every request; null removes a field; extra_params merges key by key. The base
            request itself must succeed (200 with audio)
  fails     {label: fields}: each must be refused (HTTP status >= 400): an out-of-range value that only a server
            which reads the field can reject (extra_params.repetition_penalty=-1 on the patched engine,
            extra_params.temperature=-1, language=Urdu, max_new_tokens far below the text's length)
  succeeds  {label: fields}: each must be accepted with audio (e.g. a field the server ignores, or a custom voice)
  listed    [names]: GET /v1/audio/voices must list each (vLLM-Omni voices[] / uploaded_voices[].name; gateway
            data[].id)
  headers   {header: [allowed values]}: the base response must carry one of them (e.g. x-tts-qc: [pass, fail])
  differs   {label: fields}: an optional statistic, never a gate: compares the audio with `base` at the same `seed`.
            Only meaningful on a server whose seeded output reproduces: vLLM-Omni 0.28 with CUDA graphs does NOT
            reproduce a seed even sequentially at c=1 (docs/EXPERIMENTS.md E04)
  seed      seed of every request (default: none)

With `differs`, the base request is sent twice; verdicts are 'changed', 'no_change' (identical audio) or
'inconclusive' (the two base takes already differ), reported in knobs.json only. Requests run one at a time. Exit 0 when nothing failed, 1 otherwise, 2 on a
bad spec; --lenient always exits 0 (CPU stand-in engines). The API key comes from $TTS_API_KEY.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BENCH = REPO / "bench" / "bench_tts.py"
SPEC_KEYS = {"name", "voice", "text", "seed", "base", "differs", "fails", "succeeds", "listed", "headers", "via"}


def load_bench():
    spec = importlib.util.spec_from_file_location("bench_tts", BENCH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bench_tts"] = mod               # dataclasses resolve string annotations through sys.modules
    spec.loader.exec_module(mod)
    return mod


def merge(payload: dict, fields: dict) -> dict:
    out = dict(payload)
    for k, v in fields.items():
        if v is None:
            out.pop(k, None)
        elif k == "extra_params" and isinstance(v, dict):
            extra = {**(out.get("extra_params") or {}), **v}
            out["extra_params"] = {ek: ev for ek, ev in extra.items() if ev is not None}
        else:
            out[k] = v
    return out


async def take(bench, client, url: str, payload: dict, label: str, folder: Path, auth: dict | None) -> dict:
    res = await bench.one_request(client, url, payload, 300.0, "wav", auth)
    row = {"label": label, "status": res["status"], "error": res["error"], "latency_s": round(res["latency"], 3),
           "request": bench.request_fields(payload),
           "headers": {h: v for h, v in res["headers"].items() if h.startswith("x-")}}
    if not res["error"]:
        try:
            pcm, sr, ch, width = bench.wav_pcm(res["data"])
        except ValueError as exc:
            row["error"] = f"bad audio: {exc}"
            return row
        row.update(audio_s=round(len(pcm) / (sr * ch * width), 3), pcm_sha256=hashlib.sha256(pcm).hexdigest(),
                   file=f"{label}.wav")
        (folder / f"{label}.wav").write_bytes(bench.labelled_wav(pcm, sr, ch, width))
    return row


async def verify(spec: dict, url: str, out: Path, voices_dir: Path | None) -> dict:
    bench = load_bench()
    import httpx
    voice = bench.Voice(spec.get("voice", "trump"), voices_dir or REPO / "voices")
    text = spec.get("text")
    if not text:
        pools = json.loads((REPO / "bench" / "pools" / f"{voice.lang}.json").read_text(encoding="utf-8"))
        text = pools["medium"][0].strip()
    base = {"input": text, "task_type": "Base", "response_format": "wav",
            "language": "English" if voice.lang == "en" else "Auto", "ref_audio": voice.ref_b64,
            "ref_text": voice.ref_text, **({"seed": int(spec["seed"])} if spec.get("seed") is not None else {})}
    base = merge(base, spec.get("base") or {})
    folder = out / spec["name"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "AI_GENERATED_AUDIO.txt").write_text(bench.AI_LABEL + "\n", encoding="utf-8")
    key = os.environ.get("TTS_API_KEY")
    auth = {"Authorization": f"Bearer {key}"} if key else None
    endpoint = url.rstrip("/") + "/v1/audio/speech"
    rows, problems = [], []
    async with httpx.AsyncClient(trust_env=False) as client:
        if spec.get("listed"):
            r = await client.get(url.rstrip("/") + "/v1/audio/voices", headers=auth, timeout=30.0)
            listing = r.json() if r.status_code == 200 else {}
            names = {str(x.get("id") or x.get("name") if isinstance(x, dict) else x).lower()
                     for key in ("data", "voices", "uploaded_voices") for x in (listing.get(key) or [])}
            missing = [n for n in spec["listed"] if n.lower() not in names]
            rows.append({"label": "listed", "status": r.status_code, "error": None, "listed": sorted(names),
                         "verdict": "listed" if not missing else f"missing {missing}"})
            if missing:
                problems.append(f"GET /v1/audio/voices does not list {missing}")
        a = await take(bench, client, endpoint, base, "base_a", folder, auth)
        rows.append(a)
        if a["error"]:
            problems.append(f"base request failed: {a['error']}")
        b = await take(bench, client, endpoint, base, "base_b", folder, auth) if spec.get("differs") else {}
        if b:
            rows.append(b)
        deterministic = bool(a.get("pcm_sha256")) and a.get("pcm_sha256") == b.get("pcm_sha256")
        for header, allowed in (spec.get("headers") or {}).items():
            got = a["headers"].get(header.lower())
            ok = got in [str(x) for x in allowed]
            a.setdefault("header_checks", {})[header] = {"got": got, "allowed": allowed, "ok": ok}
            if not ok:
                problems.append(f"header {header}={got!r}, expected one of {allowed}")
        for label, fields in (spec.get("differs") or {}).items():
            row = await take(bench, client, endpoint, merge(base, fields), f"differs_{label}", folder, auth)
            if row["error"]:
                row["verdict"] = "error"
                problems.append(f"{label}: request failed: {row['error']}")
            elif row["pcm_sha256"] in (a.get("pcm_sha256"), b.get("pcm_sha256")):
                row["verdict"] = "no_change"          # reported, not a gate: see the `differs` note above
            else:
                row["verdict"] = "changed" if deterministic else "inconclusive"
            rows.append(row)
        for label, fields in (spec.get("fails") or {}).items():
            row = await take(bench, client, endpoint, merge(base, fields), f"fails_{label}", folder, auth)
            row["verdict"] = "refused" if (row["status"] or 0) >= 400 else "accepted"
            if row["verdict"] == "accepted":
                problems.append(f"{label}: HTTP {row['status']} for {fields}; the server did not reject it, so it "
                                "probably never reads the field")
            rows.append(row)
        for label, fields in (spec.get("succeeds") or {}).items():
            row = await take(bench, client, endpoint, merge(base, fields), f"succeeds_{label}", folder, auth)
            row["verdict"] = "accepted" if not row["error"] and row.get("pcm_sha256") else "failed"
            if row["verdict"] == "failed":
                problems.append(f"{label}: {row['error'] or 'no audio'} for {fields}")
            rows.append(row)
    report = {"name": spec["name"], "url": url, "voice": voice.id, "text": text, "seed": base.get("seed"),
              "spec": spec, "deterministic_base": deterministic, "takes": rows, "problems": problems,
              "ok": not problems}
    (folder / "knobs.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="server base URL (engine or gateway)")
    ap.add_argument("--spec", required=True, help="JSON object, or a path to a JSON file")
    ap.add_argument("--out", type=Path, required=True, help="results folder; the check writes <out>/<name>/")
    ap.add_argument("--voices-dir", type=Path, default=None, help="voice folders (default <repo>/voices)")
    ap.add_argument("--lenient", action="store_true", help="report problems but exit 0")
    args = ap.parse_args()
    try:
        raw = args.spec if args.spec.lstrip().startswith("{") else Path(args.spec).read_text(encoding="utf-8")
        spec = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"bad --spec: {exc}", file=sys.stderr)
        return 2
    if not isinstance(spec, dict) or not spec.get("name") or set(spec) - SPEC_KEYS:
        print(f"bad --spec: needs a name; allowed keys {sorted(SPEC_KEYS)}", file=sys.stderr)
        return 2
    report = asyncio.run(verify(spec, args.url, args.out, args.voices_dir))
    for row in report["takes"]:
        print(f"  {row['label']}: HTTP {row['status']} {row.get('audio_s', '-')} s {str(row.get('verdict', ''))[:120]}"
              + (f" {row['error'][:120]}" if row.get("error") else ""))
    print(f"knob check {report['name']}: "
          + (f"deterministic base={report['deterministic_base']}; " if spec.get("differs") else "")
          + ("OK" if report["ok"] else "PROBLEMS: " + "; ".join(report["problems"])))
    return 0 if report["ok"] or args.lenient else 1


if __name__ == "__main__":
    sys.exit(main())
