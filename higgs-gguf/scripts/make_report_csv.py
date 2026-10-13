#!/usr/bin/env python3
"""Build the showcase CSVs in report/ from the raw results (logs, takes.json, scores.jsonl, verify JSON).

    python3 scripts/make_report_csv.py

report/results_summary.csv       one row per condition (production safetensors, GGUF BF16, GGUF Q8_0)
report/results_load_tests.csv    one row per engine start attempt (stock x2, harness x2) with verdict and root cause
report/results_takes.csv         one row per generated take (78): latency, audio length, RTF, WER/CER, QC, sha match
report/results_tensors_q8_0.csv  one row per checkpoint tensor of the Q8_0 GGUF: GGUF name, type, quantisation error
"""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = ROOT / "report"
OUT.mkdir(exist_ok=True)
ANSI = re.compile(r"\x1b\[[0-9;]*m")

CONDS = {  # condition -> (takes dir, weights dir or None, load-test dir or None)
    "safetensors (production)": ("02_baseline_safetensors", None, None),
    "gguf_bf16": ("04_harness/bf16", "higgs-tts-3-4b-BF16", "04_harness/bf16"),
    "gguf_q8_0": ("04_harness/q8_0", "higgs-tts-3-4b-Q8_0", "04_harness/q8_0"),
}
SCORE_CASE = {"safetensors (production)": "safetensors", "gguf_bf16": "gguf_bf16", "gguf_q8_0": "gguf_q8_0"}


def write(name, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote report/{name} ({len(rows)} rows)")


def r(x, n=3):
    return None if x is None else round(x, n)


def mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


# --- scores, keyed by wav path
scores = {}
for line in (RES / "05_quality/scores.jsonl").read_text().splitlines():
    if line.strip():
        s = json.loads(line)
        scores[str(Path(s["file"]).resolve())] = s

# --- takes
base_sha = {}
for run in "ab":
    for t in json.loads((RES / f"02_baseline_safetensors/run_{run}/takes.json").read_text()):
        base_sha[(run, t["id"])] = t["sha256"]

takes = []
for cond, (d, _, _) in CONDS.items():
    for run in "ab":
        for t in json.loads((RES / d / f"run_{run}/takes.json").read_text()):
            wav = str((RES / d / f"run_{run}/{t['id']}.wav").resolve())
            s = scores.get(wav, {})
            takes.append({
                "condition": cond, "run": run, "take_id": t["id"], "phase": t["phase"],
                "lang": s.get("lang") or ("en" if "en_" in t["id"] else "ur"), "seed": t["seed"],
                "http_status": t["status"], "ok": t["ok"], "latency_s": t["latency_s"], "audio_s": t["audio_s"],
                "rtf": t["rtf"], "wer": s.get("wer"), "cer": s.get("cer"), "qc_gate_pass": s.get("gate_pass"),
                "qc_bad": s.get("bad"), "identical_to_production_take": t["sha256"] == base_sha.get((run, t["id"])),
                "text": re.sub(r"\s+", " ", t["text"]), "asr_text": s.get("asr_text"),
                "wav": str(Path(wav).relative_to(ROOT)), "sha256": t["sha256"]})
write("results_takes.csv", takes)

# --- load tests
load_rows = []
for case, yaml in (("stock_auto", "higgs_3090_32.yaml (production, load_format auto)"),
                   ("stock_gguf", "stock_load_format_gguf.yaml (load_format gguf)")):
    log = ANSI.sub("", (RES / f"03_stock_vllm_omni/{case}.log").read_text(errors="replace"))
    summ = ANSI.sub("", (RES / "03_stock_vllm_omni/summary.txt").read_text())
    m = re.search(rf"== {case}:.*?\n\s+(\S+) \(exit (\d+)\) after (\d+)s", summ)
    cause = re.findall(r"(RuntimeError: Cannot find any model weights[^\n]*|ValueError: Load format `\w+` is not supported)", log)
    load_rows.append({"attempt": case, "engine": "vLLM-Omni 0.28.0 stock (no harness)", "weights": "GGUF Q8_0",
                      "deploy": yaml, "verdict": m.group(1) if m else "?", "seconds": m.group(3) if m else None,
                      "tensors_loaded": 0, "weights_vram_gib": None, "stage0_gpu_mib": None, "stage1_gpu_mib": None,
                      "root_cause": (cause[0].split(" with `")[0] if cause else "")})
for cond in ("gguf_bf16", "gguf_q8_0"):
    d = RES / CONDS[cond][2]
    lt = ANSI.sub("", (d / "load.txt").read_text())
    log = ANSI.sub("", (d / "engine.log").read_text(errors="replace"))
    start = re.search(r"engine: (\w+) after (\d+)s", lt)
    vram = re.search(r"Model loading took ([\d.]+) GiB memory and ([\d.]+) seconds", lt)
    gpu = re.findall(r"gpu: \d+, VLLM::StageEngineCoreProc_stage(\d)_\S+, (\d+) MiB", lt)
    n = re.search(r"Talker: loaded (\d+) params", log)
    load_rows.append({"attempt": f"harness_{cond.split('_', 1)[1]}", "engine": "vLLM-Omni 0.28.0 + higgs_gguf harness",
                      "weights": f"GGUF {cond.split('_', 1)[1].upper()}", "deploy": "higgs_gguf_3090_32.yaml",
                      "verdict": "ACCEPTED (healthy)" if start and start.group(1) == "healthy" else "FAILED",
                      "seconds": start.group(2) if start else None,
                      "tensors_loaded": 929, "weights_vram_gib": vram.group(1) if vram else None,
                      "stage0_gpu_mib": dict(gpu).get("0"), "stage1_gpu_mib": dict(gpu).get("1"),
                      "root_cause": f"talker params loaded: {n.group(1) if n else '?'}; weight load {vram.group(2) if vram else '?'} s"})
write("results_load_tests.csv", load_rows)

# --- summary per condition
summary = []
for cond, (d, wdir, ldir) in CONDS.items():
    ts = [t for t in takes if t["condition"] == cond]
    seq = [t for t in ts if t["phase"] == "sequential"]
    sums = [json.loads((RES / d / f"run_{x}/summary.json").read_text()) for x in "ab"]
    sc = [scores[str((ROOT / t["wav"]).resolve())] for t in ts if str((ROOT / t["wav"]).resolve()) in scores]

    def cwer(rows):
        words = sum(len((x.get("ref_norm") or "").split()) for x in rows)
        return sum((x.get("sub") or 0) + (x.get("del") or 0) + (x.get("ins") or 0) for x in rows) / words if words else None

    size = (ROOT / "weights" / wdir / "model.gguf").stat().st_size if wdir else 8489763794
    lrow = next((x for x in load_rows if ldir and x["attempt"] == f"harness_{cond.split('_', 1)[1]}"), None)
    summary.append({
        "condition": cond,
        "weights_format": "safetensors (HF snapshot 239f63f)" if not wdir else f"GGUF {wdir.rsplit('-', 1)[1]}",
        "weights_size_gib": r(size / 2**30, 2),
        "tensor_check": "reference" if not wdir else ("929/929 bit-identical" if "BF16" in wdir
                                                       else "675 exact + 254 Q8_0, rel RMS err max 0.60%"),
        "engine_start_s": lrow["seconds"] if lrow else None,
        "weights_vram_gib": lrow["weights_vram_gib"] if lrow else "7.61 (same model)",
        "takes_ok": f"{sum(t['ok'] for t in ts)}/{len(ts)}",
        "seq_mean_latency_s": r(mean([t["latency_s"] for t in seq])),
        "seq_mean_rtf": r(mean([t["rtf"] for t in seq])),
        "burst8_wall_s_run_a": sums[0]["burst_wall_s"], "burst8_wall_s_run_b": sums[1]["burst_wall_s"],
        "seq_takes_identical_to_production": f"{sum(t['identical_to_production_take'] for t in seq)}/{len(seq)}",
        "wer_all": r(cwer(sc)), "wer_ur": r(cwer([x for x in sc if x["lang"] == "ur"])),
        "wer_en": r(cwer([x for x in sc if x["lang"] == "en"])),
        "mean_cer": r(mean([x.get("cer") for x in sc])),
        "takes_wer_gt_0.3": sum(1 for x in sc if (x.get("wer") or 0) > 0.3),
        "qc_bad_takes": sum(1 for x in sc if x.get("bad")),
        "mean_audio_s": r(mean([t["audio_s"] for t in ts]), 2),
        "max_audio_s": max(t["audio_s"] for t in ts)})
write("results_summary.csv", summary)

# --- tensors (Q8_0)
v = json.loads((RES / "01_verify/verify_Q8_0.json").read_text())
write("results_tensors_q8_0.csv", [{
    "checkpoint_name": t["name"], "gguf_name": t["gguf"], "stored_as_alias_of": t.get("alias_of") or "",
    "ggml_type": t["type"], "shape": "x".join(map(str, t["shape"])),
    "bit_exact": t.get("exact", False), "rel_rms_error": r(t.get("rel_rms"), 6), "max_abs_error": r(t.get("max_abs"), 6)}
    for t in v["tensors"]])
