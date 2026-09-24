#!/usr/bin/env python3
"""Collect every phase under results/ into one place. Missing, unfinished or empty phases are reported, never fatal.

    venvs/gateway/bin/python bench/collect.py [--results DIR] [--plan bench/plan.py]

Writes (next to the phase folders):
  ALL_summary.csv / ALL_summary.json   one row per bench run of every phase: the run's numbers (bench_tts.py
                                       summary), its folder, the phase's engine / gateway / QC config and versions
                                       (phase.json), GPU memory minus the phase's idle baseline, and quality scores
                                       when eval/score_run.py has scored it
  INDEX.md                             every phase and run: folder path, config, knob checks, headline numbers
  REPORT_tables.md                     tables ready for REPORT.md: per phase, pivots by concurrency, quality
Inputs: <phase>/summary.json (bench_tts.py; summary.csv for older runs), <phase>/phase.json (run_plan.py), and
eval/score_run.py's scores_summary.json in <phase>/<run>/ or <phase>/ (keyed by run). Folders starting with _ or .
are skipped (results/_attic holds replaced partial phases).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AI_NOTE = "All audio under these folders is AI-generated (Qwen3-TTS voice clones): never publish it."
RUN_KEYS = ["run", "tag", "voice", "size", "c", "n", "texts", "takes", "seed", "stream", "voice_mode", "ok", "errors",
            "error_kinds", "suspect", "suspect_short", "suspect_long", "dup_audio", "retried", "retries_total",
            "gw_suspect", "qc_pass", "qc_fail", "qc_error", "wall_s", "lat_mean", "lat_p50", "lat_p90", "lat_p95",
            "lat_p99", "lat_max", "ttfa_mean", "ttfa_p50", "ttfa_p90", "ttfa_p99", "audio_s", "audio_mean_s",
            "throughput_x_realtime", "x_realtime_p90wall", "t90_s", "stragglers", "req_per_s", "rtf_mean", "rtf_p50", "rtf_p90", "pace_ratio_p10", "pace_ratio_p50",
            "pace_ratio_p90", "gpu_mem_first_mib", "gpu_mem_peak_mib", "gpu_util_mean", "language", "max_new_tokens",
            "params", "extra_params", "started", "url"]
PHASE_KEYS = ["phase", "phase_status", "folder", "via", "engine", "engine_kind", "variant", "venv", "yaml_sha256",
              "gateway", "qc", "gpu_baseline_mib", "gpu_engine_idle_mib", "gpu_engine_peak_mib", "engine_builtin_retries",
              "engine_preemptions", "vllm", "vllm_omni", "torch", "transformers", "qwen_tts", "stub"]
QUALITY_KEYS = ["q_takes", "q_prompts", "q_wer_mean", "q_cer_mean", "q_cer_nospace_mean", "q_corpus_wer",
                "q_corpus_cer_nospace", "q_sim_prompt_large", "q_sim_heldout_large", "q_sim_prompt_base",
                "q_pace_ratio", "q_gate_fail_rate", "q_bad_rate", "q_bad_first_take_rate", "q_bad_among_gate_pass_rate"]
COLUMNS = PHASE_KEYS[:2] + RUN_KEYS + PHASE_KEYS[2:] + QUALITY_KEYS


def natural(name: str) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def plan_phases(plan: Path) -> list:
    """Phases in plan order ([] when the plan cannot be loaded)."""
    sys.path.insert(0, str(HERE))
    try:
        from run_plan import load_plan
        return load_plan(plan)[0]
    except Exception as exc:                          # noqa: BLE001 - ordering is a nicety
        print(f"(plan not loaded: {exc}; phases sorted by name)", file=sys.stderr)
        return []


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def read_summary(d: Path) -> list[dict]:
    data = read_json(d / "summary.json")
    if data and isinstance(data.get("runs"), list):
        return data["runs"]
    if (d / "summary.csv").exists():
        try:
            with open(d / "summary.csv", newline="", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            print(f"(skipping {d / 'summary.csv'}: {exc})", file=sys.stderr)
    return []


def read_runs(d: Path) -> list[tuple[str, dict]]:
    """(sub-folder, run summary) of a phase folder: its own bench summary, or, when it has none (hand-made
    experiment folders such as 03_ab_async_chunk/<arm>/), the summaries one level down."""
    runs = read_summary(d)
    if runs:
        return [("", r) for r in runs]
    return [(sub.name, r) for sub in sorted(p for p in d.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))
            for r in read_summary(sub)]


def num(v):
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        f = float(v)
        return int(f) if f.is_integer() and "." not in str(v) else f
    except (TypeError, ValueError):
        return v


def quality_of(scores: dict | None, run: str) -> dict:
    """The q_* columns of one run from an eval/score_run.py scores_summary.json."""
    g = ((scores or {}).get("runs") or {}).get(run)
    if not g:
        return {}
    st, co = g.get("stats") or {}, g.get("corpus") or {}

    def mean(k):
        return (st.get(k) or {}).get("mean")

    def rate(k):
        return (g.get(k) or {}).get("rate")
    return {"q_takes": g.get("n_takes"), "q_prompts": g.get("n_prompts"), "q_wer_mean": mean("wer"),
            "q_cer_mean": mean("cer"), "q_cer_nospace_mean": mean("cer_nospace"), "q_corpus_wer": co.get("wer"),
            "q_corpus_cer_nospace": co.get("cer_nospace"), "q_sim_prompt_large": mean("sim_prompt_large"),
            "q_sim_heldout_large": mean("sim_heldout_large"), "q_sim_prompt_base": mean("sim_prompt_base"),
            "q_pace_ratio": mean("pace_ratio"), "q_gate_fail_rate": rate("gate_fail"), "q_bad_rate": rate("bad"),
            "q_bad_first_take_rate": rate("bad_first_take"), "q_bad_among_gate_pass_rate": rate("bad_among_gate_pass")}


def phase_info(rec: dict | None) -> dict:
    rec = rec or {}
    eng, gpu, ver = rec.get("engine") or {}, rec.get("gpu") or {}, rec.get("versions") or {}
    pk = {}
    for venv in ("engine", "engine30", "qwentts"):
        pk.update({k: v for k, v in ((ver.get(venv) or {}).get("packages") or {}).items() if v})
    base = gpu.get("baseline_mib")
    idle = gpu.get("engine_ready_mib")
    found = eng.get("log_findings") or {}
    return {"engine": eng.get("describe") or eng.get("kind"), "engine_kind": eng.get("kind"),
            "variant": eng.get("variant"), "venv": eng.get("venv"), "yaml_sha256": (eng.get("yaml_sha256") or "")[:16],
            "gpu_baseline_mib": base, "gpu_engine_idle_mib": idle - base if idle is not None and base is not None else None,
            "engine_builtin_retries": found.get("builtin_retries"), "engine_preemptions": found.get("preemption"),
            "vllm": pk.get("vllm"), "vllm_omni": pk.get("vllm-omni"), "torch": pk.get("torch"),
            "transformers": pk.get("transformers"), "qwen_tts": pk.get("qwen-tts"), "stub": rec.get("stub")}


def phase_state(d: Path, rec: dict | None) -> str:
    if (d / "DONE").exists():
        return "DONE"
    return (rec or {}).get("status") or "no phase.json"


def collect(results: Path, order: list[str]) -> tuple[list[dict], dict[str, dict]]:
    dirs = {d.name: d for d in results.glob("*") if d.is_dir() and not d.name.startswith(("_", "."))}
    names = [n for n in order if n in dirs] + sorted((n for n in dirs if n not in order), key=natural)
    rows, phases = [], {}
    for name in names:
        d = dirs[name]
        rec = read_json(d / "phase.json")
        info = phase_info(rec)
        status = phase_state(d, rec)
        phase_scores = read_json(d / "scores_summary.json")
        pairs = read_runs(d)
        runs = [r for _, r in pairs]
        phases[name] = {"dir": d, "rec": rec, "status": status, "runs": runs, "info": info}
        for subdir, r in pairs:
            where = d / subdir if subdir else d
            meta = r.get("meta") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta) if meta else {}
                except json.JSONDecodeError:
                    meta = {}
            folder = r.get("folder") or r.get("run")
            prefix = f"{name}/{subdir}/" if subdir else f"{name}/"
            row = {"phase": name, "phase_status": status, **{k: num(r.get(k)) for k in RUN_KEYS},
                   "folder": prefix + str(folder) if (where / str(folder)).is_dir() else prefix.rstrip("/"), **info,
                   "via": meta.get("via"), "gateway": meta.get("gateway") or "", "qc": meta.get("qc")}
            for k in ("run", "tag", "voice", "size", "voice_mode", "error_kinds", "language", "max_new_tokens",
                      "params", "extra_params", "started", "url"):
                row[k] = r.get(k) if r.get(k) not in (None, "") else ""
            row["stream"] = str(r.get("stream")) in ("True", "true", "1")
            if subdir:
                row["run"] = f"{subdir}/{row['run']}"
            peak, base = num(r.get("gpu_mem_peak_mib")), info["gpu_baseline_mib"]
            row["gpu_engine_peak_mib"] = peak - base if isinstance(peak, (int, float)) and base is not None else None
            run_scores = read_json(where / str(folder) / "scores_summary.json")
            row.update(quality_of(run_scores, r.get("run")) or quality_of(read_json(where / "scores_summary.json"),
                                                                          r.get("run")) or quality_of(phase_scores, r.get("run")))
            rows.append(row)
    return rows, phases


# ------------------------------------------------------------------------------------------------ markdown

def fmt(v, nd: int = 3) -> str:
    if v in (None, ""):
        return "–"
    if isinstance(v, bool):
        return "y" if v else ""
    if isinstance(v, float):
        return f"{v:.{nd}f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:.0f}"
    return str(v)


def triple(r: dict, prefix: str) -> str:
    vals = [r.get(f"{prefix}_{p}") for p in ("p50", "p90", "p99")]
    return "–" if all(v is None for v in vals) else " / ".join(fmt(v, 2) for v in vals)


def table(header: list[str], lines: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(x) + " |" for x in lines]


def config_label(r: dict) -> str:
    parts = [r.get("engine") or ""]
    if r.get("via") == "gateway":
        parts.append("gateway " + (r.get("gateway") or "{}") + (" + QC" if r.get("qc") == "true" else ""))
    return "; ".join(p for p in parts if p)


def run_line(r: dict, link: bool) -> list[str]:
    name = f"[{r['run']}]({r['folder']}/)" if link and r.get("folder") else str(r.get("run"))
    susp = fmt(r.get("suspect")) + (f" ({fmt(r.get('suspect_short'))}s/{fmt(r.get('suspect_long'))}l)"
                                     if r.get("suspect") else "")
    gpu = fmt(r.get("gpu_mem_peak_mib")) + (f" ({fmt(r.get('gpu_engine_peak_mib'))})"
                                            if r.get("gpu_engine_peak_mib") is not None else "")
    return [name, fmt(r.get("voice")), fmt(r.get("size")), fmt(r.get("c")), fmt(r.get("n")),
            "y" if r.get("stream") else "", fmt(r.get("voice_mode")), fmt(r.get("errors")), susp,
            triple(r, "lat"), triple(r, "ttfa"), fmt(r.get("audio_mean_s"), 2), fmt(r.get("throughput_x_realtime"), 2),
            fmt(r.get("x_realtime_p90wall"), 2), fmt(r.get("stragglers")), fmt(r.get("rtf_p50")),
            fmt(r.get("req_per_s"), 2), gpu]


RUN_HEADER = ["run", "voice", "size", "c", "n", "stream", "voice mode", "errors", "suspects", "latency p50/p90/p99 s",
              "TTFA p50/p90/p99 s", "audio s/req", "x realtime", "x realtime p90-wall", "stragglers", "RTF p50", "req/s",
              "GPU peak MiB (engine)"]


def quality_lines(rows: list[dict], link: bool) -> list[str]:
    q = [r for r in rows if r.get("q_takes")]
    if not q:
        return []
    header = ["phase", "run", "voice", "takes", "WER mean", "CER-ns mean", "corpus WER", "SIM-L prompt",
              "SIM-L heldout", "SIM-B prompt", "gate fail", "bad", "bad (take 0)", "bad among gate-pass"]
    lines = [[r["phase"], f"[{r['run']}]({r['folder']}/)" if link and r.get("folder") else r["run"], fmt(r["voice"]),
              fmt(r["q_takes"]), fmt(r.get("q_wer_mean")), fmt(r.get("q_cer_nospace_mean")),
              fmt(r.get("q_corpus_wer")), fmt(r.get("q_sim_prompt_large")), fmt(r.get("q_sim_heldout_large")),
              fmt(r.get("q_sim_prompt_base")), fmt(r.get("q_gate_fail_rate")), fmt(r.get("q_bad_rate")),
              fmt(r.get("q_bad_first_take_rate")), fmt(r.get("q_bad_among_gate_pass_rate"))] for r in q]
    return table(header, lines)


def pivots(rows: list[dict]) -> list[str]:
    """Per phase: metric x concurrency tables for run series that share voice/size/stream/mode/tag."""
    out = []
    series: dict[tuple, dict[int, dict]] = {}
    for r in rows:
        if isinstance(r.get("c"), int):
            key = (r.get("tag") or "", r.get("voice"), r.get("size"), bool(r.get("stream")), r.get("voice_mode"))
            series.setdefault(key, {})[r["c"]] = r
    multi = {k: v for k, v in series.items() if len(v) > 1}
    if not multi:
        return out
    cs = sorted({c for v in multi.values() for c in v})
    metrics = [("throughput_x_realtime", "aggregate x realtime"),
               ("x_realtime_p90wall", "x realtime over the first 90% of finished requests (straggler-robust)"),
               ("req_per_s", "req/s"), ("lat_p50", "latency p50 s"),
               ("lat_p90", "latency p90 s"), ("rtf_p50", "per-request RTF p50")]
    if any(k[3] for k in multi):
        metrics += [("ttfa_p50", "TTFA p50 s"), ("ttfa_p90", "TTFA p90 s")]
    metrics += [("gpu_engine_peak_mib", "engine GPU MiB (peak - idle baseline)")]
    for key, label in metrics:
        lines = []
        for (tag, voice, size, stream, mode), by_c in sorted(multi.items(), key=lambda kv: [str(x) for x in kv[0]]):
            if key.startswith("ttfa") and not stream:
                continue
            name = " ".join(x for x in (tag, voice, size, "stream" if stream else "", mode if mode != "inline" else "")
                            if x)
            nd = 3 if key.startswith("rtf") else 2
            lines.append([name] + [fmt(by_c[c].get(key), nd) if c in by_c else "" for c in cs])
        if lines:
            out += [f"**{label}** by concurrency", ""] + table(["series"] + [f"c={c}" for c in cs], lines) + [""]
    return out


def write_outputs(results: Path, rows: list[dict], phases: dict[str, dict], pending: list[str]) -> None:
    with open(results / "ALL_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore", restval="")
        w.writeheader()
        w.writerows(rows)
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    (results / "ALL_summary.json").write_text(json.dumps(
        {"generated": now, "results": str(results), "columns": COLUMNS, "pending_phases": pending,
         "phases": {n: {"status": p["status"], "folder": n, "runs": len(p["runs"]),
                        "error": (p["rec"] or {}).get("error"), **p["info"]} for n, p in phases.items()},
         "runs": rows}, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    idx = [f"# Benchmark results index", "", f"Generated {now} by `server/bench/collect.py` from `{results}`.",
           f"**{AI_NOTE}**", "",
           "Each phase folder holds `phase.json` (config, versions, host, git, engine YAML, GPU baseline/release, "
           "commands and exit codes), `commands.sh`, `summary.{csv,md,json}` and `requests.jsonl` (every run), "
           "`logs/`, `snapshots/` (nvidia-smi and /metrics around every bench command), `versions/` (every package "
           "of every venv used), `knobs/` (knob verification takes) and one folder per run with its `audio/`, "
           "`requests.jsonl` and `summary.json`.", "", "## Phases", ""]
    lines = []
    for name, p in phases.items():
        rec, runs = p["rec"] or {}, p["runs"]
        audio_h = sum(float(num(r.get("audio_s")) or 0) for r in runs) / 3600
        gpu = rec.get("gpu") or {}
        eng = p["info"]["engine"] or "–"
        gw = rec.get("gateway") or {}
        gw_label = "off" if not gw.get("enabled") else json.dumps(gw.get("overrides") or {}) + (
            " + QC" if (rec.get("spec") or {}).get("qc") else "")
        lines.append([f"[{name}]({name}/)", p["status"] + (" (stub)" if rec.get("stub") else ""), str(len(runs)),
                      fmt(sum(int(num(r.get("n")) or 0) for r in runs)),
                      fmt(sum(int(num(r.get("errors")) or 0) for r in runs)),
                      fmt(sum(int(num(r.get("suspect")) or 0) for r in runs)),
                      fmt(p["info"]["engine_builtin_retries"]), fmt(p["info"]["engine_preemptions"]), f"{audio_h:.2f}",
                      fmt(round((rec.get("duration_s") or 0) / 60, 1)), eng, gw_label,
                      f"{fmt(gpu.get('baseline_mib'))} / {fmt(p['info']['gpu_engine_idle_mib'])}"])
    idx += table(["phase", "status", "runs", "requests", "errors", "suspects", "engine built-in retries",
                  "preemption lines", "audio h", "minutes", "engine", "gateway",
                  "GPU MiB: idle baseline / engine at rest (above baseline)"], lines)
    if pending:
        idx += ["", "Not run yet: " + ", ".join(pending)]
    report = [f"# Tables for REPORT.md", "", f"Generated {now} from `{results}` by `server/bench/collect.py`. "
              "Latency and TTFA in seconds (p50 / p90 / p99); TTFA is the first audio byte past the WAV header "
              "(streaming runs only); x realtime = audio seconds per wall second over the run (aggregate); x realtime "
              "p90-wall = audio finished by the time 90% of the requests had finished over that time (one runaway "
              "cannot dominate it); stragglers = requests slower than 3x the run's median latency; RTF = "
              "latency / audio seconds per request; GPU peak is nvidia-smi memory.used of the benchmark GPU during "
              "the run, in brackets minus the idle baseline before the engine started (desktop and other tenants). "
              "Suspects: takes whose pace is outside 0.6-1.8x the voice's expected s/letter (s = too short, l = too "
              "long).", ""]
    for name, p in phases.items():
        rec = p["rec"] or {}
        prow = [r for r in rows if r["phase"] == name]
        idx += ["", f"## {name}: {p['status']}" + (" (CPU stub run: numbers are not real)" if rec.get("stub") else ""), ""]
        if rec.get("note"):
            idx.append(rec["note"] + "  ")
        info = p["info"]
        if rec:
            eng = rec.get("engine") or {}
            gw = rec.get("gateway") or {}
            idx.append(f"- engine: {info['engine'] or '–'}" + (f", YAML sha256 {info['yaml_sha256']}" if info["yaml_sha256"]
                                                             else "") + (f", reused from {eng['reused_from']}"
                                                                         if eng.get("reused_from") else ""))
            vers = ", ".join(f"{k} {info[k]}" for k in ("vllm", "vllm_omni", "torch", "transformers", "qwen_tts")
                             if info.get(k))
            if vers:
                idx.append(f"- versions: {vers} (all packages: `{name}/versions/`)")
            idx.append("- gateway: " + ("off" if not gw.get("enabled") else json.dumps(gw.get("overrides") or {}))
                       + ("; QC sidecar on" if (rec.get("spec") or {}).get("qc") else ""))
            found = eng.get("log_findings") or {}
            if found:
                idx.append(f"- engine log: built-in runaway retries {found.get('builtin_retries')}, preemption lines "
                           f"{found.get('preemption')}, error lines {found.get('errors')}"
                           + (f"; KV: {found['kv_cache'][-1]}" if found.get("kv_cache") else ""))
            g = rec.get("gpu") or {}
            idx.append(f"- GPU {g.get('index')}: baseline {fmt(g.get('baseline_mib'))} MiB, engine idle "
                       f"{fmt(g.get('engine_ready_mib'))} MiB, released after: {g.get('released', '–')}"
                       + (f"; kept for the next phase" if g.get("engine_kept_for_next_phase") else ""))
            for k in rec.get("knob_checks") or []:
                idx.append(f"- knob check `{k['name']}` ({k['via']}): {'OK' if k.get('ok') else 'NOT verified'} "
                           f"{k.get('verdicts')}" + (" (not enforced: stub)" if not k.get("enforced", True) else "")
                           + (f" problems: {k['problems']}" if k.get("problems") else ""))
            codes = [str(b.get("exit_code")) for b in rec.get("bench") or []]
            idx.append(f"- bench commands: {len(codes)} (exit codes {', '.join(codes) or '–'}); `{name}/commands.sh`"
                       + (f"; duration {fmt(round((rec.get('duration_s') or 0) / 60, 1))} min" if rec.get("duration_s")
                          else ""))
            if rec.get("error"):
                idx.append(f"- **error:** {rec['error']}")
        if prow:
            idx += [""] + table(RUN_HEADER, [run_line(r, True) for r in prow])
            report += [f"## {name}", "", f"Config: {config_label(prow[0])}", ""]
            report += table(RUN_HEADER, [run_line(r, False) for r in prow]) + [""]
            report += pivots(prow)
        else:
            idx.append("\nno bench_tts.py runs here" + (" (see the folder's own files)" if any(
                p["dir"].glob("*.json")) or any(p["dir"].iterdir()) else ""))
    q = quality_lines(rows, True)
    if q:
        idx += ["", "## Quality (eval/score_run.py)", ""] + q
        report += ["## Quality", "", "Rates are fractions of takes (see scores_summary.md in each phase for 95 % "
                   "Wilson intervals).", ""] + quality_lines(rows, False) + [""]
    (results / "INDEX.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    (results / "REPORT_tables.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=HERE.parent / "results")
    ap.add_argument("--plan", type=Path, default=HERE / "plan.py")
    args = ap.parse_args()
    if not args.results.is_dir():
        print(f"no results folder {args.results}")
        return 0
    plan = plan_phases(args.plan)
    order = [p.name for p in plan]
    rows, phases = collect(args.results, order)
    pending = [p.name + (" (optional)" if p.optional else "") for p in plan if p.name not in phases]
    for name, p in phases.items():
        err = (p["rec"] or {}).get("error")
        print(f"{name:26} {p['status']:12} {len(p['runs']):4} runs" + (f"  error: {err}" if err else ""))
    if pending:
        print(f"not run yet: {', '.join(pending)}")
    write_outputs(args.results, rows, phases, pending)
    print(f"{len(rows)} runs from {len(phases)} phases -> {args.results / 'ALL_summary.csv'}, ALL_summary.json, "
          f"INDEX.md, REPORT_tables.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
