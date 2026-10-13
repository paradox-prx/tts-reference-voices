#!/usr/bin/env python3
"""Summarise results/05_quality/scores.jsonl (score_run.py manifest mode output) per condition and language:
corpus WER, mean per-take WER/CER, QC `bad` count, takes with WER > 0.3, mean duration. Writes summary.json + summary.md next to it.

    python3 scripts/summarise_quality.py [results/05_quality]
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

d = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "results" / "05_quality")
rows = [json.loads(line) for line in (d / "scores.jsonl").read_text().splitlines() if line.strip()]
groups = defaultdict(list)
for r in rows:
    for lang in (r["lang"], "all"):
        groups[(r["case"], lang)].append(r)


def corpus_wer(rs):
    words = sum(len((r.get("ref_norm") or "").split()) for r in rs)
    return sum((r.get("sub") or 0) + (r.get("del") or 0) + (r.get("ins") or 0) for r in rs) / words if words else None


def mean(rs, k):
    v = [r[k] for r in rs if r.get(k) is not None]
    return sum(v) / len(v) if v else None


out = {}
lines = ["| condition | lang | takes | corpus WER | mean CER | mean WER | takes WER>0.3 | `bad` (QC) | mean audio s |",
         "|---|---|---|---|---|---|---|---|---|"]
for (case, lang), rs in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    s = {"takes": len(rs),
         "corpus_wer": corpus_wer(rs),
         "mean_cer": mean(rs, "cer"),
         "mean_wer": mean(rs, "wer"),
         "wer_gt_0.3": sum(1 for r in rs if (r.get("wer") or 0) > 0.3),
         "bad": sum(1 for r in rs if r.get("bad")),
         "mean_duration_s": sum(r.get("duration_s") or 0 for r in rs) / len(rs)}
    out[f"{case}/{lang}"] = s
    f = lambda x: "-" if x is None else f"{x:.3f}"  # noqa: E731
    lines.append(f"| {case} | {lang} | {s['takes']} | {f(s['corpus_wer'])} | {f(s['mean_cer'])} | "
                 f"{f(s['mean_wer'])} | {s['wer_gt_0.3']} | {s['bad']} | {s['mean_duration_s']:.2f} |")
(d / "summary.json").write_text(json.dumps(out, indent=1) + "\n")
(d / "summary.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
