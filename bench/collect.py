#!/usr/bin/env python3
"""Merge every results/<phase>/summary.csv into results/ALL_summary.csv (with a leading `phase` column) and print a
compact markdown table per phase. Phases that are missing, unfinished or empty are reported, never fatal.

    venvs/gateway/bin/python bench/collect.py [--results DIR] [--plan bench/plan.py]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COLUMNS = [("tag", "tag"), ("voice", "voice"), ("size", "size"), ("c", "c"), ("n", "n"), ("stream", "stream"),
           ("ok", "ok"), ("errors", "err"), ("suspect", "susp"), ("retried", "retried"), ("lat_p50", "lat p50"),
           ("lat_p90", "lat p90"), ("lat_p99", "lat p99"), ("ttfa_p50", "TTFA p50"), ("ttfa_p90", "TTFA p90"),
           ("throughput_x_realtime", "x RT"), ("req_per_s", "req/s"), ("gpu_mem_peak_mib", "GPU MiB")]


def natural(name: str) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def plan_order(plan: Path) -> list[str]:
    """Phase names in plan order, or [] when the plan cannot be loaded."""
    sys.path.insert(0, str(HERE))
    try:
        from run_plan import load_plan
        return [p.name for p in load_plan(plan)]
    except Exception as exc:                          # noqa: BLE001 - ordering is a nicety
        print(f"(plan not loaded: {exc}; phases sorted by name)", file=sys.stderr)
        return []


def read_summary(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        print(f"(skipping {path}: {exc})", file=sys.stderr)
        return []


def phase_state(d: Path) -> str:
    try:
        rec = json.loads((d / "phase.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "DONE" if (d / "DONE").exists() else "no phase.json"
    state = "DONE" if (d / "DONE").exists() else rec.get("status", "?")
    secs = rec.get("duration_s") or 0
    extra = [f"{secs / 60:.0f} min" if secs >= 60 else f"{secs:.0f} s",
             f"engine {rec['engine'].get('variant') or rec['engine'].get('kind', '')}" if rec.get("engine") else "",
             f"error: {rec['error']}" if rec.get("error") else ""]
    return ", ".join([state, *filter(None, extra)])


def cell(phase: str, key: str, value: str | None) -> str:
    if key == "tag":
        value = (value or "").removeprefix(phase).lstrip("_")
    elif key == "stream":
        value = "y" if value == "True" else ""
    return value if value not in (None, "") else "–"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=HERE.parent / "results")
    ap.add_argument("--plan", type=Path, default=HERE / "plan.py")
    args = ap.parse_args()

    dirs = {d.name: d for d in args.results.glob("*") if d.is_dir() and not d.name.startswith(("_", "."))}
    order = plan_order(args.plan)
    names = [n for n in order if n in dirs] + sorted((n for n in dirs if n not in order), key=natural)
    rows, fields = [], ["phase"]
    for name in names:
        summary = read_summary(dirs[name] / "summary.csv")
        print(f"\n### {name} ({phase_state(dirs[name])})\n")
        if not summary:
            print("no summary.csv rows")
            continue
        print("| " + " | ".join(h for _, h in COLUMNS) + " |\n|" + "---|" * len(COLUMNS))
        for r in summary:
            print("| " + " | ".join(cell(name, k, r.get(k)) for k, _ in COLUMNS) + " |")
            rows.append({"phase": name, **r})
            fields += [k for k in r if k not in fields]
    if missing := [n for n in order if n not in dirs]:
        print(f"\nnot run yet: {', '.join(missing)}")
    if not rows:
        print(f"\nno results under {args.results}")
        return 0
    out = args.results / "ALL_summary.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, restval="")
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} runs from {len({r['phase'] for r in rows})} phases -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
