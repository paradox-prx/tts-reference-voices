"""Offline tooling without models: stats, retry simulation, score_run's verdicts / summary / --rejudge.

    cd server && eval/run.sh -m pytest -q eval/tests
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
EVAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL))
sys.path.insert(0, str(EVAL.parent / "qc"))

import retry_sim  # noqa: E402
import score_run  # noqa: E402
import takes  # noqa: E402
from stats import rate, wilson  # noqa: E402


def test_wilson_matches_the_research_example() -> None:
    lo, hi = wilson(5, 46)                     # the Kaggle Urdu failure rate (eval-tooling.md finding 29): 4.7-23 %
    assert (round(lo, 3), round(hi, 3)) == (0.047, 0.23)
    assert wilson(0, 0) is None and rate(0, 10)["ci95"][0] == 0.0


def take(prompt: int, t: int, gate_pass: bool, bad: bool, cost: float = 30.0, pace: float = 1.0) -> dict:
    return {"file": f"{prompt}_{t}", "take": t, "gate_pass": gate_pass, "bad": bad, "cost": cost,
            "gate_reasons": [] if gate_pass else ["cer_nospace>0.15"], "pace_ratio": pace}


def test_retry_exact_expectation_small_case() -> None:
    # one prompt, K=2: take A fails the gate and is bad, take B passes and is good
    takes = [take(0, 0, False, True), take(0, 1, True, False)]
    r0, r1 = retry_sim.eval_retry(takes, 0), retry_sim.eval_retry(takes, 1)
    assert r0["bad"] == 0.5 and r0["attempts"] == 1.0          # no retry: half the time we ship A
    assert r1["bad"] == 0.0 and r1["attempts"] == 1.5          # A first -> retry to B; B first -> stop
    assert retry_sim.eval_best_of(takes, 2)["bad"] == 0.0


def test_fallback_prefers_qc_failures_over_pace_failures() -> None:
    a = take(0, 0, False, True, pace=2.5) | {"gate_reasons": ["pace>1.8"]}
    b = take(0, 1, False, False, pace=1.1)
    assert retry_sim.eval_retry([a, b], 1)["bad"] == 0.0         # both fail: ship b (QC-only failure) every time


def test_policy_table_and_cli(tmp_path: Path) -> None:
    rows = []
    for p in range(10):
        for t in range(4):
            bad = p < 2 and t < 3                                   # two hard prompts
            rows.append({"run": "rp110", "voice": "shehbaz", "prompt_id": f"p{p}", "take": t, "seed": None,
                         "file": f"a/{p}_{t}.wav",
                         "gate_pass": not bad, "gate_reasons": [] if not bad else ["long_word>2.5"], "bad": bad,
                         "audio_s": 60.0 if bad else 30.0, "pace_ratio": 1.0})
    (tmp_path / "scores.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    labels = tmp_path / "labels.jsonl"
    labels.write_text(json.dumps({"file": "a/9_3.wav", "bad": True}) + "\n")
    subprocess.run([sys.executable, str(EVAL / "retry_sim.py"), str(tmp_path), "--boot", "200",
                    "--labels", str(labels)], check=True, capture_output=True)
    res = json.loads((tmp_path / "retry_sim.json").read_text())
    t = res["settings"]["rp110 [shehbaz]"]
    r = {x["R"]: x for x in t["retry"]}
    assert t["n_prompts"] == 10 and t["takes_per_prompt"] == [4] and "human labels for 1" in res["bad_source"]
    assert r[0]["final_bad_rate"] == pytest.approx((2 * 0.75 + 0.25) / 10)
    assert r[3]["final_bad_rate"] == pytest.approx(0.025)        # hard prompts always reach their good take
    assert r[1]["extra_compute"] > 0 and r[0]["extra_compute"] == 0
    assert (tmp_path / "retry_sim.md").read_text().startswith("# Retry-policy simulation")


def test_score_run_rejudge_and_summary(tmp_path: Path) -> None:
    base = {"voice": "shehbaz", "lang": "ur", "text": "x", "duration_s": 10.0, "speech_ratio": 0.9, "lead_sil_s": 0.1,
            "trail_sil_s": 0.1, "max_internal_sil_s": 0.5, "pace_ratio": 1.0, "wer": 0.2, "cer": 0.05,
            "cer_nospace": 0.05, "char_ratio": 1.0, "del_run": 0, "ins_run": 0, "repeat_excess": 0, "token_run": 1,
            "char_runs": 0, "ref_norm": "a b c d e", "hyp_norm": "a b c d e", "sim_speech_s": 9.0,
            "sim_prompt_base": 0.97, "sim_prompt_large": 0.8, "gate_pass": True, "gate_reasons": [], "bad": False,
            "bad_reasons": []}
    rows = [base | {"run": "r", "prompt_id": f"p{i}", "take": 0, "file": f"f{i}.wav", "cer_nospace": c,
                    "hyp_norm": "a b c d e" if c < 0.1 else "a b"}
            for i, c in enumerate([0.02, 0.05, 0.12, 0.30])]
    (tmp_path / "requests.jsonl").write_text("")
    (tmp_path / "scores.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    thresholds = tmp_path / "t.json"
    thresholds.write_text(json.dumps({"gate": {"cer_nospace_ur": 0.2}}))
    subprocess.run([sys.executable, str(EVAL / "score_run.py"), str(tmp_path), "--rejudge", "--thresholds",
                    str(thresholds)], check=True, capture_output=True)
    scored = [json.loads(x) for x in (tmp_path / "scores.jsonl").read_text().splitlines()]
    assert [r["gate_pass"] for r in scored] == [True, True, True, False]      # gate at 0.2 (overridden)
    assert [r["bad"] for r in scored] == [False, False, True, True]           # bad at 0.10 (default)
    s = json.loads((tmp_path / "scores_summary.json").read_text())
    g = s["runs"]["r [shehbaz]"]
    assert g["gate_fail"]["k"] == 1 and g["bad"]["k"] == 2 and g["bad_first_take"]["n"] == 4
    assert g["gate_vs_bad"] == {"recall": 0.5, "precision": 1.0, "false_reject_rate": 0.0}
    assert g["corpus"]["wer"] == pytest.approx(6 / 20)
    assert s["thresholds"]["gate"]["cer_nospace_ur"] == 0.2 and s["rejudged"] is True
    assert (tmp_path / "scores_summary.md").exists()


def test_grouping_keys_ignore_seeds_and_map_engine_voices() -> None:
    row = {"run": "P5_rp110_k6", "voice": "trump", "engine_voice": "trump-avg", "prompt_id": "07_x", "text_idx": 3,
           "take": 2, "seed": None, "file": "a.wav", "text": "Hello."}
    assert takes.prompt_key(row) == "trump/07_x"
    assert takes.setting_key(row) == "P5_rp110_k6 [trump-avg]"
    assert takes.setting_key(row | {"engine_voice": None}) == "P5_rp110_k6 [trump]"
    assert takes.prompt_key({"voice": "shehbaz-3f9a0c1b2d", "text_idx": 3}) == "shehbaz/text3"
    key = takes.prompt_key
    assert key({"voice": "shehbaz-prompt", "text": "x"}) == key({"voice": "shehbaz", "text": "x"})
    assert key({"voice": "trump", "seed": 1, "text": "x"}) == key({"voice": "trump", "seed": 2, "text": "x"})


def test_combine_pairs_settings_by_prompt(tmp_path: Path) -> None:
    for rp, hard in (("rp105", 3), ("rp115", 1)):          # rp115 fixes two of the three hard prompts
        d = tmp_path / rp
        d.mkdir()
        rows = [{"run": f"P5_{rp}_k3", "voice": "shehbaz", "engine_voice": "shehbaz-avg", "prompt_id": f"p{p}",
                 "take": t, "seed": None, "file": f"{rp}/{p}_{t}.wav", "gate_pass": not (p < hard and t < 2),
                 "gate_reasons": [], "bad": p < hard and t < 2, "audio_s": 30.0, "pace_ratio": 1.0}
                for p in range(8) for t in range(3)]
        (d / "scores.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    out = tmp_path / "combined"
    subprocess.run([sys.executable, str(EVAL / "retry_sim.py"), str(tmp_path / "rp105"), str(tmp_path / "rp115"),
                    "--combine", str(out), "--baseline", "rp105", "--boot", "200"], check=True, capture_output=True)
    res = json.loads((out / "retry_sim.json").read_text())
    assert res["baseline"] == "P5_rp105_k3 [shehbaz-avg]" and len(res["settings"]) == 2
    r0 = next(p for p in res["paired"] if p["R"] == 0)
    assert r0["n_prompts"] == 8 and r0["bad_baseline"] == pytest.approx(3 * 2 / 3 / 8)
    assert r0["diff"] == pytest.approx(-2 * 2 / 3 / 8, abs=1e-3)
    assert "Paired by prompt" in (out / "retry_sim.md").read_text()


def test_run_discovery(tmp_path: Path) -> None:
    (tmp_path / "P2" / "x").mkdir(parents=True)
    (tmp_path / "P2" / "x" / "requests.jsonl").write_text("")
    assert score_run.find_run_dirs([str(tmp_path)]) == [tmp_path / "P2" / "x"]
