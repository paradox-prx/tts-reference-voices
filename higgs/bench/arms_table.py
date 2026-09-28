#!/usr/bin/env python3
"""One row per bench run of a results dir, grouped by arm (the bench --tag), for the A/B experiments: requests, errors,
pace-suspect takes, gateway retries, latency p50 / p90, time to first audio, x realtime, audio per take. Reads every
<run>/summary.json below the results dir; writes <results>/ARMS.md and ARMS.json.

    python higgs/bench/arms_table.py higgs/results/G_gateway
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SIZES = ("short", "medium", "long", "xlong", "xxlong", "prompts")


def fmt(v, d=2):
    return "-" if v in (None, "") else (f"{v:.{d}f}" if isinstance(v, float) else str(v))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", type=Path)
    args = ap.parse_args()
    rows = []
    for f in sorted(args.results.rglob("summary.json")):
        doc = json.loads(f.read_text())
        s = doc.get("summary") if isinstance(doc, dict) else None
        if isinstance(s, dict) and "voice" in s:
            rows.append(s)
    rows.sort(key=lambda s: (s.get("tag") or "", s["voice"], SIZES.index(s["size"]) if s["size"] in SIZES else 99,
                             bool(s.get("stream")), int(s["c"])))
    lines = [f"# Arms: {args.results.name}", "",
             "| arm | voice | size | c | stream | n | ok | err | suspect | retried | lat p50 / p90 s | TTFA p50 s | xRT | audio s/take | GPU MiB |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in rows:
        lines.append(f"| {s.get('tag') or '-'} | {s['voice']} | {s['size']} | {s['c']} | {'yes' if s.get('stream') else 'no'} | "
                     f"{s['n']} | {s['ok']} | {s['errors']} | {s['suspect']} | {s.get('retried', 0)} | "
                     f"{fmt(s['lat_p50'])} / {fmt(s['lat_p90'])} | {fmt(s.get('ttfa_p50'), 3)} | "
                     f"{fmt(s.get('x_realtime_p90wall'), 1)} | {fmt(s.get('audio_mean_s'), 1)} | {fmt(s.get('gpu_mem_peak_mib'), 0)} |")
    md = "\n".join(lines) + "\n"
    (args.results / "ARMS.md").write_text(md, encoding="utf-8")
    (args.results / "ARMS.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
