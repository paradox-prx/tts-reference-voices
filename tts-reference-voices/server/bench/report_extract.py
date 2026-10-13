#!/usr/bin/env python3
"""Curated markdown tables for REPORT.md from results/ALL_summary.json (bench/collect.py) and the eval scores.

    venvs/gateway/bin/python bench/report_extract.py [--results results] > results/REPORT_curated.md

Every number in REPORT.md's performance tables comes from here, so the report can be regenerated after a re-run.
Throughput is `x_realtime_p90wall` (audio finished by the time 90% of a run's requests had finished, per wall second)
unless a table says otherwise: one runaway straggler cannot dominate it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(results: Path) -> list[dict]:
    data = json.loads((results / "ALL_summary.json").read_text())
    return data["runs"] if isinstance(data, dict) else data


def f(x, nd=2):
    if x is None:
        return "–"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def pick(rows, phase, **kw):
    out = [r for r in rows if r["phase"] == phase and all(r.get(k) == v for k, v in kw.items())]
    return out


def lat(r):
    return f"{f(r.get('lat_p50'))} / {f(r.get('lat_p90'))} / {f(r.get('lat_p99'))}"


def ttfa(r):
    return f"{f(r.get('ttfa_p50'), 3)} / {f(r.get('ttfa_p90'), 3)} / {f(r.get('ttfa_p99'), 3)}"


def table(head: list[str], body: list[list]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in body]
    return "\n".join(lines)


def matrix(rows) -> str:
    """P2 (+P2_high_c): per voice and size, by concurrency."""
    out = []
    for voice in ("trump", "shehbaz"):
        body = []
        for size in ("short", "medium", "long", "xlong", "xxlong"):
            for c in (1, 2, 4, 8, 16, 32, 48, 64):
                rs = pick(rows, "P2_matrix", voice=voice, size=size, c=c) or pick(rows, "P2_high_c", voice=voice,
                                                                                    size=size, c=c)
                for r in rs:
                    body.append([size, c, r["n"], r.get("errors"), f(r.get("audio_mean_s"), 1), lat(r),
                                 f(r.get("x_realtime_p90wall"), 1), f(r.get("throughput_x_realtime"), 1),
                                 f(r.get("req_per_s")), f(r.get("rtf_p50")), r.get("gpu_mem_peak_mib")])
        out.append(f"**{voice}** (non-streaming, engine direct, gateway cap)\n\n" + table(
            ["size", "c", "n", "errors", "audio s/req", "latency p50/p90/p99 s", "x realtime (p90 wall)",
             "x realtime (wall)", "req/s", "RTF p50", "GPU MiB"], body))
    return "\n\n".join(out)


def stream(rows) -> str:
    body = []
    for voice in ("trump", "shehbaz"):
        for size in ("short", "xlong", "xxlong"):
            for r in pick(rows, "P3_stream", voice=voice, size=size):
                body.append([voice, size, r["c"], r["n"], r.get("errors"), ttfa(r), lat(r),
                             f(r.get("x_realtime_p90wall"), 1)])
    return table(["voice", "size", "c", "n", "errors", "TTFA p50/p90/p99 s", "total p50/p90/p99 s",
                  "x realtime (p90 wall)"], body)


def cache(rows) -> str:
    body = []
    for r in pick(rows, "P4_voice_cache"):
        body.append([r["voice"], r.get("voice_mode"), "yes" if r.get("stream") else "", r["c"], r["n"], lat(r),
                     ttfa(r) if r.get("stream") else "–", f(r.get("x_realtime_p90wall"), 1)])
    return table(["voice", "reference", "stream", "c", "n", "latency p50/p90/p99 s", "TTFA p50/p90/p99 s",
                  "x realtime"], body)


def baseline(rows) -> str:
    body = []
    for voice in ("trump", "shehbaz"):
        for size in ("short", "xlong", "xxlong"):
            for c in (1, 2, 4, 8, 16):
                b = pick(rows, "P9_baseline_b8", voice=voice, size=size, c=c)
                o = pick(rows, "P2_matrix", voice=voice, size=size, c=c)
                if not b and not o:
                    continue
                b, o = (b or [{}])[0], (o or [{}])[0]
                body.append([voice, size, c, f(b.get("rtf_p50")), f(o.get("rtf_p50")), lat(b) if b else "–",
                             lat(o) if o else "–", f(b.get("x_realtime_p90wall"), 1), f(o.get("x_realtime_p90wall"), 1),
                             f"{b.get('errors')}/{b.get('n')}" if b else "–", f"{o.get('errors')}/{o.get('n')}" if o else "–"])
    return table(["voice", "size", "c", "RTF p50 qwen-tts", "RTF p50 vLLM-Omni", "latency qwen-tts p50/p90/p99",
                  "latency vLLM-Omni p50/p90/p99", "x realtime qwen-tts", "x realtime vLLM-Omni",
                  "errors qwen-tts", "errors vLLM-Omni"], body)


def simple(rows, phase, extra=()) -> str:
    body = []
    for r in pick(rows, phase):
        body.append([r["run"], r["c"], r["n"], r.get("errors"), f"{r.get('suspect_short', 0)}/{r.get('suspect_long', 0)}",
                     f(r.get("pace_ratio_p50")), lat(r), f(r.get("x_realtime_p90wall"), 1),
                     *[f(r.get(k)) for k in extra]])
    return table(["run", "c", "n", "errors", "too short/too long", "pace ratio p50", "latency p50/p90/p99 s",
                  "x realtime", *extra], body)


def quality(results: Path) -> str:
    """Per run: from each phase's scores_summary.json (eval/score_run.py)."""
    body = []
    for phase_dir in sorted(p for p in results.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        sp = phase_dir / "scores_summary.json"
        if not sp.exists():
            continue
        summary = json.loads(sp.read_text())
        runs = summary.get("runs") or summary.get("by_run") or {}
        items = runs.items() if isinstance(runs, dict) else [(r.get("run"), r) for r in runs]
        for run, s in items:
            if run in (None, "ALL"):
                continue
            g = s.get
            body.append([phase_dir.name, run, g("n"), f(g("wer_mean"), 3), f(g("cer_nospace_mean"), 3),
                         f(g("sim_prompt_large_mean"), 3), f(g("sim_prompt_base_mean"), 3),
                         f(g("gate_fail_rate"), 3), f(g("bad_rate"), 3)])
    return table(["phase", "run", "takes", "WER", "CER-nospace", "SIM-large", "SIM-base", "gate fail", "bad"], body)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default=str(ROOT / "results"))
    results = Path(ap.parse_args().results)
    rows = load(results)
    parts = [
        ("P2 matrix (+ P2_high_c)", matrix(rows)),
        ("P3 streaming", stream(rows)),
        ("P4 voice-prompt cache", cache(rows)),
        ("P9 qwen-tts baseline vs vLLM-Omni (P2)", baseline(rows)),
        ("P6 Auralis pools", simple(rows, "P6_auralis")),
        ("P7 gateway", simple(rows, "P7_gateway", ("retries_total",))),
        ("X4 length cap", simple(rows, "X4_length_cap", ("engine_builtin_retries",))),
        ("X6 non_streaming_mode, long texts", simple(rows, "X6_nsm_long_urdu")),
        ("X7 sentence splitting", simple(rows, "X7_split_off") + "\n\n" + simple(rows, "X7_split_60")),
        ("P8 quality phases (load view)", "\n\n".join(simple(rows, p, ("retries_total", "qc_pass", "qc_fail", "qc_error"))
                                                      for p in ("P8_quality_raw", "P8_quality_guard",
                                                                "P8_quality_guard_fast"))),
        ("Quality (eval/score_run.py)", quality(results)),
    ]
    for title, body in parts:
        print(f"## {title}\n\n{body}\n")


if __name__ == "__main__":
    main()
