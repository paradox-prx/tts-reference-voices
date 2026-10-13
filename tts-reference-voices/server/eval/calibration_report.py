#!/usr/bin/env python3
"""Compare this stack's calibration with the eval research's recorded numbers and check the synthetic failures.

    eval/run.sh eval/calibration_report.py      # reads eval/calibration/*, writes eval/calibration/summary_<tag>.json

Inputs (eval/calibration/): refs_<tag>.scores.jsonl and synth_<tag>.scores.jsonl (score_run.py --manifest ...),
sim_calibration_<device>.json (sim_eval.py). Research records: eval/lab/asr_refs_int8_v2.jsonl and
eval/lab/asr_synth.jsonl (CPU int8, 2026-09-24; synthetic clips spliced independently, so their durations differ by
a few tens of ms from make_synth.py's). Output: per-clip metric pairs (ours vs research), the Urdu corpus error rates,
real-clip ranges of the audio / timing detectors (the margins the thresholds rest on), and for each synthetic case
the gate reasons expected, obtained and missing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "qc"))
sys.path.insert(0, str(HERE))

from score_run import corpus, read_jsonl  # noqa: E402

CAL = HERE / "calibration"
PAIRS = [("wer", "wer"), ("cer", "cer"), ("cer_nospace", "cer_nospace"), ("char_ratio", "t_char_ratio"),
         ("max_internal_sil_s", "a_max_internal_sil_s"), ("trail_sil_s", "a_trail_sil_s"),
         ("speech_ratio", "a_speech_ratio"), ("max_word_s", "w_max_word_dur_s"),
         ("max_word_voiced", "w_max_word_voiced"),
         ("unaligned_tail_s", "unaligned_tail_s"), ("seg_max_cr", "seg_max_cr"), ("del_run", "t_longest_del_run"),
         ("ins_run", "t_longest_ins_run"), ("repeat_excess", "t_repeat_excess"), ("duration_s", "a_duration_s")]
RANGE_KEYS = ("max_internal_sil_s", "lead_sil_s", "trail_sil_s", "speech_ratio", "max_word_s", "unaligned_tail_s",
              "seg_max_cr", "char_ratio", "del_run", "ins_run", "repeat_excess", "lid_ur", "sim_prompt_large",
              "sim_prompt_base", "sim_heldout_large", "sim_heldout_base")


def by_name(rows: list[dict], key: str = "file") -> dict[str, dict]:
    return {Path(r[key]).name if key == "file" else r[key]: r for r in rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default="cpu_int8", help="suffix of the score files (refs_<tag>.scores.jsonl)")
    ap.add_argument("--sim", default=str(CAL / "sim_calibration_cpu.json"))
    args = ap.parse_args()
    refs = read_jsonl(CAL / f"refs_{args.tag}.scores.jsonl")
    synth = read_jsonl(CAL / f"synth_{args.tag}.scores.jsonl")
    lab_refs = by_name(read_jsonl(HERE / "lab" / "asr_refs_int8_v2.jsonl"))
    lab_synth = by_name(read_jsonl(HERE / "lab" / "asr_synth.jsonl"), "case")
    out: dict = {"tag": args.tag, "about": __doc__.split("\n\n")[0]}

    # ---------------------------------------------------------------- real clips
    clips = {}
    for r in refs:
        name = f"{r['voice']}/{Path(r['file']).name}"
        lab = lab_refs.get(Path(r["file"]).name) if Path(r["file"]).name != "qwen3-tts.wav" else next(
            (x for x in read_jsonl(HERE / "lab" / "asr_refs_int8_v2.jsonl")
             if x["file"].endswith(f"{r['voice']}/references/qwen3-tts.wav")), None)
        clips[name] = {k: {"ours": r.get(k), "research": lab.get(lk) if lab else None} for k, lk in PAIRS}
        clips[name].update({"asr_text": r.get("asr_text"), "gate_reasons": r["gate_reasons"],
                            "bad_reasons": r["bad_reasons"], "lid_ur": r.get("lid_ur"),
                            "sim_prompt_large": r.get("sim_prompt_large"), "sim_prompt_base": r.get("sim_prompt_base")})
    out["real_clips"] = clips
    sh8 = [r for r in refs if r["voice"] == "shehbaz" and "references" not in r["file"]]
    lab8 = [lab_refs[Path(r["file"]).name] for r in sh8 if Path(r["file"]).name in lab_refs]
    out["urdu_corpus_8_clips"] = {"ours": corpus(sh8), "research": {**corpus(lab8), "reported": {
        "wer": 0.131, "cer": 0.035, "cer_nospace": 0.038, "per_clip_wer": [0, 0.286],
        "per_clip_cer_nospace": [0, 0.086]}}}
    rng = {}
    for k in RANGE_KEYS:
        vals = [r[k] for r in refs if r.get(k) is not None and not (k.startswith("sim_") and "references" in r["file"])]
        if vals:
            rng[k] = [min(vals), max(vals)]
    out["real_clip_ranges"] = rng
    out["real_clips_gate_pass"] = f"{sum(r['gate_pass'] for r in refs)}/{len(refs)}"
    out["real_clips_bad"] = {f"{r['voice']}/{Path(r['file']).name}": r["bad_reasons"] for r in refs if r["bad"]}

    # ---------------------------------------------------------------- synthetic failures
    cases = {}
    for r in synth:
        fam = {x.split(">")[0].split("<")[0] for x in r["gate_reasons"]}
        exp = r.get("expect", [])
        lab = lab_synth.get(r["case"], {})
        cases[r["case"]] = {"expected": exp, "gate_reasons": r["gate_reasons"], "bad_reasons": r["bad_reasons"],
                            "missing": [e for e in exp if e not in fam], "detected": not r["gate_pass"],
                            **{k: {"ours": r.get(k), "research": lab.get(lk)} for k, lk in PAIRS},
                            "asr_text": r.get("asr_text")}
    out["synthetic"] = cases
    out["synthetic_detected"] = f"{sum(c['detected'] for c in cases.values())}/{len(cases)}"
    out["synthetic_all_expected_reasons"] = f"{sum(not c['missing'] for c in cases.values())}/{len(cases)}"

    # ---------------------------------------------------------------- SIM
    sim_path = Path(args.sim)
    if sim_path.exists():
        sim = json.loads(sim_path.read_text())
        out["sim"] = {m: {"summary": r["summary"],
                          "shehbaz_prompt_vs_heldout_centroid": r["shehbaz_prompt_vs_heldout_centroid"],
                          "trump_half1_vs_half2": r["trump_half1_vs_half2"],
                          "short_crop_shehbaz02_vs_prompt": r["short_crop_shehbaz02_vs_prompt"],
                          "x_realtime": r["x_realtime"], "research": r["research"]}
                      for m, r in sim["models"].items()}
    path = CAL / f"summary_{args.tag}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("urdu_corpus_8_clips", "real_clip_ranges", "real_clips_gate_pass",
                                          "real_clips_bad", "synthetic_detected", "synthetic_all_expected_reasons")},
                     ensure_ascii=False, indent=1))
    for case, c in cases.items():
        print(f"{case:20} gate={','.join(c['gate_reasons']) or 'PASS'}  missing={c['missing']}")
    print(f"-> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
