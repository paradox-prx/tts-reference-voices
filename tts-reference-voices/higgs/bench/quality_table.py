#!/usr/bin/env python3
"""Quality per voice and text size from server/eval/score_run.py's scores.jsonl files under a results dir: takes,
mean WER / CER-nospace, speaker similarity (WavLM-Large vs the prompt clip; base-plus-sv), pace ratio, gate-fail and
`bad` rates with 95 % Wilson intervals, the leading failure reasons. Writes <results>/QUALITY.md and QUALITY.json.

    python higgs/bench/quality_table.py higgs/results/B0_baseline_flash_attn [--by voice,size,stream]
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean

SIZES = ("short", "medium", "long", "xlong", "xxlong", "prompts")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return (math.nan, math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, c - h, c + h)


def load(results: Path) -> list[dict]:
    rows = []
    for f in sorted(results.rglob("scores.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                r["_run"] = f.parent.name
                rows.append(r)
    return rows


def group_key(r: dict, by: list[str]) -> tuple:
    def is_stream(r):  # scores.jsonl rows carry the bench run name, which says stream / nonstream
        return "_stream_" in str(r.get("run") or r.get("_run") or "") or bool(r.get("stream"))
    return tuple(("stream" if is_stream(r) else "nonstream") if k == "stream" else r.get(k) for k in by)


def summarise(rows: list[dict]) -> dict:
    def m(key):
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        return mean(vals) if vals else math.nan
    n = len(rows)
    gate = sum(1 for r in rows if r.get("gate_pass") is False)
    bad = sum(1 for r in rows if r.get("bad"))
    reasons = Counter()
    for r in rows:
        for x in r.get("bad_reasons") or []:
            reasons[str(x).split(">")[0].split("<")[0].strip()] += 1
    return {"takes": n, "audio_s": sum(r.get("audio_s") or 0 for r in rows), "wer": m("wer"),
            "cer_nospace": m("cer_nospace"), "sim_large": m("sim_prompt_large"), "sim_base": m("sim_prompt_base"),
            "pace_ratio": m("pace_ratio"), "gate_fail": wilson(gate, n), "bad": wilson(bad, n),
            "top_reasons": reasons.most_common(4)}


def fmt_rate(t):
    p, lo, hi = t
    return "-" if math.isnan(p) else f"{p:.1%} [{lo:.0%}, {hi:.0%}]"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", type=Path)
    ap.add_argument("--by", default="voice,size,stream")
    args = ap.parse_args()
    by = args.by.split(",")
    rows = load(args.results)
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(group_key(r, by), []).append(r)
    order = sorted(groups, key=lambda k: tuple((SIZES.index(x) if x in SIZES else str(x)) for x in k))
    out = {"results": str(args.results), "by": by, "groups": []}
    lines = [f"# Quality: {args.results.name}", "",
             "Stock Whisper large-v3 (language forced) WER / CER-nospace against the input text; SIM = cosine speaker "
             "similarity to the voice's reference clip (WavLM-Large seed-tts-eval scale / wavlm-base-plus-sv); pace = "
             "seconds per letter over the voice's calibrated pace; gate fail = the production QC verdict (pace + ASR + "
             "SIM + audio detectors), bad = the stricter offline label; rates with 95 % Wilson CIs "
             "(server/eval/score_run.py, thresholds in server/qc/tts_qc/policy.py).", "",
             f"| {' | '.join(by)} | takes | audio h | WER | CER-ns | SIM-L | SIM-B | pace | gate fail | bad | bad reasons |",
             "|" + "---|" * (len(by) + 10)]
    for k in order:
        s = summarise(groups[k])
        out["groups"].append({"key": dict(zip(by, k)), **s})
        reasons = ", ".join(f"{r} {c}" for r, c in s["top_reasons"]) or "-"
        lines.append(f"| {' | '.join(str(x) for x in k)} | {s['takes']} | {s['audio_s'] / 3600:.2f} | {s['wer']:.3f} | "
                     f"{s['cer_nospace']:.3f} | {s['sim_large']:.3f} | {s['sim_base']:.3f} | {s['pace_ratio']:.2f} | "
                     f"{fmt_rate(s['gate_fail'])} | {fmt_rate(s['bad'])} | {reasons} |")
    s = summarise(rows)
    out["all"] = s
    lines.append(f"| ALL | {'| ' * (len(by) - 1)}{s['takes']} | {s['audio_s'] / 3600:.2f} | {s['wer']:.3f} | "
                 f"{s['cer_nospace']:.3f} | {s['sim_large']:.3f} | {s['sim_base']:.3f} | {s['pace_ratio']:.2f} | "
                 f"{fmt_rate(s['gate_fail'])} | {fmt_rate(s['bad'])} | "
                 f"{', '.join(f'{r} {c}' for r, c in s['top_reasons'])} |")
    md = "\n".join(lines) + "\n"
    (args.results / "QUALITY.md").write_text(md, encoding="utf-8")
    (args.results / "QUALITY.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
