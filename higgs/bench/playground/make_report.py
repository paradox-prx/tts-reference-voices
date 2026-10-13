#!/usr/bin/env python3
"""Turn a burst_load.py run folder into: requests.csv, summary.txt, percentiles_*.csv.

    python make_report.py <run-dir>
"""
from __future__ import annotations

import csv
import json
import statistics as st
import sys
from pathlib import Path

PCTS = (50, 90, 95, 99)
METRICS = (("lat", "latency_s"), ("ttfa", "ttfa_s"), ("rtf", "rtf"))


def pct(v: list[float], p: float):
    if not v:
        return None
    v = sorted(v)
    return v[min(len(v) - 1, round(p / 100 * (len(v) - 1)))]


def f(x, d=3):
    return "-" if x is None else f"{x:.{d}f}"


def bucket(x: int, width: int, lo: int) -> str:
    a = lo + (x - lo) // width * width
    return f"{a}-{a + width - 1}"


def stats_row(rows: list[dict]) -> dict:
    ok = [r for r in rows if r["ok"]]
    out = {"requests": len(rows), "ok": len(ok), "errors": len(rows) - len(ok),
           "audio_s_mean": st.mean(r["audio_s"] for r in ok) if ok else None}
    for key, name in METRICS:
        vals = [r[key] for r in ok if r.get(key) is not None]
        for p in PCTS:
            out[f"{name}_p{p}"] = pct(vals, p)
    return out


def write_table(path: Path, label: str, groups: dict[str, list[dict]]) -> list[dict]:
    rows = []
    for k in sorted(groups, key=lambda s: int(s.split("-")[0])):
        rows.append({label: k, **stats_row(groups[k])})
    allr = [r for g in groups.values() for r in g]
    rows.append({label: "ALL", **stats_row(allr)})
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
    return rows


def md_table(rows: list[dict], label: str) -> str:
    cols = [label, "requests", "errors", "audio_s_mean"] + [f"latency_s_p{p}" for p in PCTS] + \
           [f"ttfa_s_p{p}" for p in (50, 90, 99)] + ["rtf_p50", "rtf_p90"]
    lines = [" | ".join(cols), " | ".join("---" for _ in cols)]
    for r in rows:
        lines.append(" | ".join(str(r[c]) if c in (label, "requests", "errors") else f(r.get(c), 2 if c == "audio_s_mean" else 3)
                                for c in cols))
    return "\n".join(lines)


def main() -> None:
    d = Path(sys.argv[1])
    reqs = [json.loads(l) for l in (d / "requests.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in reqs:
        r["rtf"] = r["lat"] / r["audio_s"] if r.get("ok") and r.get("audio_s") else None
    with open(d / "requests.csv", "w", newline="", encoding="utf-8") as fh:
        cols = ["burst", "idx", "burst_size", "words", "ok", "lat", "ttfa", "audio_s", "rtf", "err"]
        w = csv.writer(fh)
        w.writerow(["burst", "idx", "burst_size", "words", "ok", "latency_s", "ttfa_s", "audio_s", "rtf", "error"])
        for r in reqs:
            w.writerow([f"{r[c]:.4f}" if isinstance(r.get(c), float) else ("" if r.get(c) is None else r[c]) for c in cols])

    by_words: dict[str, list] = {}
    by_burst: dict[str, list] = {}
    for r in reqs:
        by_words.setdefault(bucket(r["words"], 10, 10), []).append(r)
        by_burst.setdefault(bucket(r["burst_size"], 5, 5), []).append(r)
    ow = write_table(d / "percentiles_by_words.csv", "words", by_words)
    ob = write_table(d / "percentiles_by_burst_size.csv", "burst_size", by_burst)
    overall = stats_row(reqs)
    with open(d / "percentiles_overall.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", *[f"p{p}" for p in PCTS]])
        for key, name in METRICS:
            w.writerow([name, *[f"{overall[f'{name}_p{p}']:.4f}" if overall[f"{name}_p{p}"] is not None else "" for p in PCTS]])

    s = json.loads((d / "summary.json").read_text()) if (d / "summary.json").exists() else {}
    bursts = [json.loads(l) for l in (d / "bursts.jsonl").read_text().splitlines() if l.strip()] \
        if (d / "bursts.jsonl").exists() else []
    lines = [f"Higgs TTS burst load test: {d.name}", "=" * 60,
             f"bursts            {s.get('bursts', len(bursts))}   (size {s.get('burst_size')}, words {s.get('words')}, "
             f"stream={s.get('stream')}, seed={s.get('seed')})",
             f"requests          {s.get('requests', len(reqs))}   ok {s.get('ok')}   errors {s.get('errors')}",
             f"total wall        {f(s.get('total_wall_s'), 1)} s   mean burst wall {f(s.get('burst_wall_mean_s'), 1)} s",
             f"audio generated   {f(s.get('audio_s_total'), 1)} s   overall xRT {f(s.get('xrt_overall'), 2)}",
             f"latency p50/p90/p99  {f(s.get('lat_p50'))} / {f(s.get('lat_p90'))} / {f(s.get('lat_p99'))} s",
             f"TTFA p50/p90         {f(s.get('ttfa_p50'))} / {f(s.get('ttfa_p90'))} s"]
    if s.get("error_samples"):
        lines += ["", "error samples:", *[f"  - {e}" for e in s["error_samples"]]]
    lines += ["", "Percentiles by words per request (seconds; rtf = latency / audio)", md_table(ow, "words"),
              "", "Percentiles by burst size", md_table(ob, "burst_size")]
    if bursts:
        worst = sorted(bursts, key=lambda b: -(b.get("lat_p90") or 0))[:5]
        lines += ["", "Slowest 5 bursts by p90 latency",
                  *[f"  burst {b['burst']:3d} size {b['size']:2d} wall {b['wall_s']:.1f}s p90 {f(b['lat_p90'], 1)}s errors {b['errors']}"
                    for b in worst]]
    (d / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()