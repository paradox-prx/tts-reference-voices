#!/usr/bin/env python3
"""Tabulate the T (streaming start latency) phases: per phase, size and concurrency: TTFA, gapless playback start,
streams that would stall, throughput. Markdown to stdout (and results/T_summary.md with --write).

    venvs/gateway/bin/python bench/ttfa_table.py [--write]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--write", action="store_true", help="also write results/T_summary.md")
    a = ap.parse_args()
    rows = []
    for f in sorted(Path(a.results).glob("T[0-9]*/*/summary.json")):
        s = json.loads(f.read_text())["summary"]
        rows.append((f.parts[-3], s))
    lines = ["| phase | size | c | TTFA p50 / p90 s | gapless start p50 / p90 s | would stall | x realtime | errors |",
             "|---|---|---|---|---|---|---|---|"]
    for phase, s in sorted(rows, key=lambda r: (r[1]["size"], r[1]["c"], r[0])):
        lines.append(f"| {phase} | {s['size']} | {s['c']} | {s['ttfa_p50']} / {s['ttfa_p90']} | "
                     f"{s.get('play_start_p50')} / {s.get('play_start_p90')} | {s.get('stalled')}/{s['ok']} | "
                     f"{s['throughput_x_realtime']} | {s['errors']} |")
    text = "\n".join(lines) + "\n"
    print(text)
    if a.write:
        (Path(a.results) / "T_summary.md").write_text(text)


if __name__ == "__main__":
    main()
