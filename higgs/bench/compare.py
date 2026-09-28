#!/usr/bin/env python3
"""Side-by-side tables: Higgs TTS 3 runs (bench_tts.py summary.json files under a results dir) against the Qwen3-TTS
benchmark's engine-direct rows (server/results/ALL_summary.json: P2_matrix non-streaming, P3_stream streaming), per
voice, by text size and concurrency.

    python higgs/bench/compare.py higgs/results/B0_baseline_<ts> [--qwen server/results/ALL_summary.json]
                                  [--out higgs/results/B0_baseline_<ts>/COMPARE.md] [--json ...]

Columns: n = requests, lat = total latency p50 / p90 (s), TTFA = time to first audio p50 / p90 (s, streaming runs),
xRT = audio seconds finished per wall second while 90 % of the requests were in flight (x_realtime_p90wall), RTF =
per-request compute / audio (p50), audio = mean seconds per take, err / susp = errors and pace-suspect takes,
GPU = peak MiB on the card (desktop included). Qwen rows carry the gateway's length cap (max_new_tokens auto);
Higgs rows carry no cap unless the run's params say so.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SIZES = ("short", "medium", "long", "xlong", "xxlong", "prompts")
COLS = ("n", "lat_p50", "lat_p90", "lat_p99", "ttfa_p50", "ttfa_p90", "x_realtime_p90wall", "throughput_x_realtime",
        "rtf_p50", "audio_mean_s", "errors", "suspect", "gpu_mem_peak_mib", "pace_ratio_p50", "wall_s")


def higgs_rows(results: Path) -> list[dict]:
    rows = []
    for f in sorted(results.rglob("summary.json")):
        try:
            doc = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        s = doc.get("summary") if isinstance(doc, dict) else None
        if not isinstance(s, dict) or "voice" not in s:
            continue
        s = dict(s)
        s["folder"] = str(f.parent.relative_to(results))
        s["engine"] = "higgs"
        rows.append(s)
    return rows


def qwen_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    doc = json.loads(path.read_text())
    out = []
    for r in doc.get("runs", []):
        if r.get("phase") == "P2_matrix" and not r.get("stream"):
            pass
        elif r.get("phase") == "P3_stream" and r.get("stream"):
            pass
        else:
            continue
        r = dict(r)
        r["engine"] = "qwen"
        out.append(r)
    return out


def fmt(v, digits=2):
    if v is None or v == "":
        return "-"
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return str(v)


def cell(r: dict | None, stream: bool) -> str:
    if r is None:
        return " - | - | - | - | - | - | - | - "
    lat = f"{fmt(r.get('lat_p50'))} / {fmt(r.get('lat_p90'))}"
    ttfa = f"{fmt(r.get('ttfa_p50'), 3)} / {fmt(r.get('ttfa_p90'), 3)}" if stream else "-"
    return (f" {fmt(r.get('n'), 0)} | {lat} | {ttfa} | {fmt(r.get('x_realtime_p90wall'), 1)} | "
            f"{fmt(r.get('rtf_p50'), 3)} | {fmt(r.get('audio_mean_s'), 1)} | "
            f"{fmt(r.get('errors'), 0)}/{fmt(r.get('suspect'), 0)} | {fmt(r.get('gpu_mem_peak_mib'), 0)} ")


def table(voice: str, stream: bool, higgs: list[dict], qwen: list[dict]) -> str:
    hd = {(r["size"], int(r["c"])): r for r in higgs if r["voice"] == voice and bool(r.get("stream")) == stream}
    qd = {(r["size"], int(r["c"])): r for r in qwen if r["voice"] == voice and bool(r.get("stream")) == stream}
    keys = sorted(set(hd) | set(qd), key=lambda k: (SIZES.index(k[0]) if k[0] in SIZES else 99, k[1]))
    if not keys:
        return ""
    head = "n | lat p50 / p90 s | TTFA p50 / p90 s | xRT | RTF p50 | audio s | err/susp | GPU MiB"
    lines = [f"### {voice}, {'streaming' if stream else 'non-streaming'}", "",
             f"| size | c | Higgs TTS 3: {head} | Qwen3-TTS: {head} |",
             "|---|---|" + "---|" * 8 + "---|" * 8]
    for size, c in keys:
        lines.append(f"| {size} | {c} |{cell(hd.get((size, c)), stream)}|{cell(qd.get((size, c)), stream)}|")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", type=Path, help="Higgs results dir (bench_tts.py run folders below it)")
    ap.add_argument("--qwen", type=Path, default=Path(__file__).resolve().parents[2] / "server/results/ALL_summary.json")
    ap.add_argument("--out", type=Path, default=None, help="markdown file (default <results>/COMPARE.md)")
    ap.add_argument("--json", type=Path, default=None, help="joined rows as JSON (default <results>/COMPARE.json)")
    args = ap.parse_args()
    higgs, qwen = higgs_rows(args.results), qwen_rows(args.qwen)
    voices = sorted({r["voice"] for r in higgs} | ({r["voice"] for r in qwen} if higgs else set()))
    parts = [f"# Higgs TTS 3 vs Qwen3-TTS, engine direct ({args.results.name})", "",
             f"Higgs: {len(higgs)} runs under `{args.results}`. Qwen: `{args.qwen}` (P2_matrix, P3_stream). "
             "Same voices, texts, reference clips (`references/qwen3-tts.wav`) and tool; one RTX 3090. "
             "Qwen rows: max_new_tokens auto (the gateway's cap); Higgs rows: the engine's cap unless noted.", ""]
    for voice in voices:
        for stream in (False, True):
            t = table(voice, stream, higgs, qwen)
            if t:
                parts.append(t)
    md = "\n".join(parts)
    out = args.out or args.results / "COMPARE.md"
    out.write_text(md, encoding="utf-8")
    (args.json or args.results / "COMPARE.json").write_text(json.dumps(
        {"higgs": [{k: r.get(k) for k in ("voice", "size", "c", "stream", "folder", "run", "params", "extra_params",
                                            "max_new_tokens", *COLS)} for r in higgs],
         "qwen": [{k: r.get(k) for k in ("voice", "size", "c", "stream", "phase", "folder", *COLS)} for r in qwen]},
        indent=1, ensure_ascii=False), encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
