#!/usr/bin/env python3
"""Failure tiers per take and per run, runaways included, for REPORT.md and the retry study.

    eval/run.sh eval/failure_classes.py results/P5_urdu_rp105 results/X6_nsm_long_urdu ...

score_run.py scores only takes that produced audio. A runaway (no EOS before the length cap: HTTP 500, no audio) is
the worst failure there is, so this script puts those requests back: it reads each phase's requests.jsonl (every
request) and scores.jsonl (every scored take) and writes, next to them:

  failure_classes.json   per bench run (and ALL): takes, runaways, severe / moderate / clean counts and rates with
                         95 % Wilson intervals, the reasons, and corpus means over the clean + moderate takes
  takes_all.jsonl        scores.jsonl rows plus one row per runaway (gate_pass false, bad true, cost = the audio the
                         engine generated before the cap), with `bad` set to the SEVERE label, for retry_sim.py

Tiers (thresholds chosen for audibility, calibrated on the takes themselves: docs/EXPERIMENTS.md, quality):
  severe    the take is unusable: runaway; pace outside 0.6-1.8x the voice's expected s/letter; a skipped passage
            (longest run of reference words with nothing heard >= 12 words Urdu / 5 English, or char ratio < 0.80);
            garbled (CER-nospace > 0.45 Urdu, WER > 0.30 English); a loop Whisper swallowed (one voiced 'word' over
            2.5 s) or a voiced gap over 3 s; an unaligned tail over 3 s; the wrong speaker (SIM-large < 0.5 on >= 5 s)
  moderate  audible but local: a skipped phrase (6-11 words Urdu, 3-4 English), char ratio 0.80-0.88 or 1.12-1.20,
            repetition beyond the text (repeat_excess >= 6 Urdu / 5 English), CER-nospace 0.35-0.45
  clean     neither (for Urdu this still includes accent-level recognition errors)
English caveat: the benchmark prompts contain onomatopoeia ("haha", "achoo") that Whisper spells differently
("ha ha", "a chew"), which the repeat detectors count; the English moderate tier over-counts."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def wilson(k: int, n: int) -> list[float]:
    if n == 0:
        return [0.0, 1.0]
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def tier(r: dict) -> tuple[str, list[str]]:
    ur = r.get("lang") == "ur"
    sev, mod = [], []
    g = lambda k, d=0.0: r.get(k) if isinstance(r.get(k), (int, float)) else d  # noqa: E731
    pace = g("pace_ratio", 1.0)
    if pace < 0.6 or pace > 1.8:
        sev.append("pace")
    dr = g("del_run")
    if dr >= (12 if ur else 5):
        sev.append("skip")
    elif dr >= (6 if ur else 3):
        mod.append("skip_phrase")
    cr = g("char_ratio", 1.0)
    if cr < 0.80:
        sev.append("char_ratio<0.8")
    elif cr < 0.88 or cr > 1.12:
        (sev if cr > 1.20 else mod).append("char_ratio")
    if ur:
        c = g("cer_nospace")
        if c > 0.45:
            sev.append("garbled")
        elif c > 0.35:
            mod.append("cer_nospace")
    elif g("wer") > 0.30:
        sev.append("garbled")
    if g("max_word_s") > 2.5 and g("max_word_voiced") > 0.8:
        sev.append("loop_long_word")
    if g("max_gap_s") > 3.0 and g("max_gap_voiced") > 0.5:
        sev.append("voiced_gap")
    if g("unaligned_tail_s") > 3.0:
        sev.append("unaligned_tail")
    if g("sim_speech_s") >= 5 and 0 < g("sim_prompt_large", 1.0) < 0.5:
        sev.append("wrong_speaker")
    if g("repeat_excess") >= (6 if ur else 5):
        mod.append("repeat")
    if sev:
        return "severe", sev
    return ("moderate", mod) if mod else ("clean", [])


def run_key(row: dict) -> str:
    return f'{row.get("run")} [{row.get("voice")}]'


def analyse(phase: Path) -> dict:
    reqs = [json.loads(line) for line in (phase / "requests.jsonl").open()]
    scored = {}
    if (phase / "scores.jsonl").exists():
        for line in (phase / "scores.jsonl").open():
            s = json.loads(line)
            scored[s.get("file")] = s
    groups: dict[str, list[dict]] = defaultdict(list)
    takes_all = []
    for q in reqs:
        key = run_key(q)
        if q.get("status") == 200:
            s = scored.get(q.get("file"))
            if s is None:
                continue  # not scored (yet)
            t, why = tier(s)
            groups[key].append({"tier": t, "why": why, "s": s})
            takes_all.append(s | {"bad": t == "severe", "tier": t, "tier_reasons": why, "moderate": t == "moderate"})
        else:  # no audio: a runaway (engine: "did not emit codec EOS before its token budget"; gateway: 502) or
            # any other failed request; for a client every one of them is an unusable result
            err = q.get("error") or ""
            why = "runaway" if ("token budget" in err or "EOS" in err or "502" in err) else "error"
            groups[key].append({"tier": "severe", "why": [why], "s": None})
            cap = q.get("max_new_tokens") or 0
            takes_all.append({k: q.get(k) for k in ("run", "voice", "lang", "size", "c", "idx", "text_idx", "take",
                                                     "prompt_id", "engine_voice", "text", "file", "voice_mode")}
                             | {"gate_pass": False, "gate_reasons": [why], "bad": True, "tier": "severe",
                                "tier_reasons": [why], "audio_s": cap / 12.5, "duration_s": cap / 12.5,
                                "runaway": why == "runaway"})
    out = {"phase": phase.name, "runs": {}}
    everything = [t for ts in groups.values() for t in ts]
    for key, ts in [*sorted(groups.items()), ("ALL", everything)]:
        n = len(ts)
        cnt = Counter(t["tier"] for t in ts)
        runaways = sum(1 for t in ts if t["s"] is None)  # no audio: runaways and other failed requests
        ok = [t["s"] for t in ts if t["s"] is not None and t["tier"] != "severe"]
        mean = lambda k: round(sum(x.get(k) or 0 for x in ok) / len(ok), 4) if ok else None  # noqa: E731
        out["runs"][key] = {
            "n": n, "runaways": runaways,
            **{f"{tier_}": {"k": cnt[tier_], "rate": round(cnt[tier_] / n, 4) if n else None,
                            "ci95": wilson(cnt[tier_], n)} for tier_ in ("severe", "moderate", "clean")},
            "severe_or_moderate": {"k": cnt["severe"] + cnt["moderate"],
                                   "rate": round((cnt["severe"] + cnt["moderate"]) / n, 4) if n else None,
                                   "ci95": wilson(cnt["severe"] + cnt["moderate"], n)},
            "reasons": dict(Counter(w for t in ts for w in t["why"]).most_common()),
            "non_severe_means": {k: mean(k) for k in ("wer", "cer_nospace", "sim_prompt_large", "sim_prompt_base",
                                                      "sim_heldout_large")},
        }
    (phase / "failure_classes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    with (phase / "takes_all.jsonl").open("w") as f:
        for row in takes_all:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phases", nargs="+")
    for p in ap.parse_args().phases:
        out = analyse(Path(p))
        for key, r in out["runs"].items():
            print(f'{out["phase"][:22]:22s} {key[:62]:62s} n={r["n"]:4d} runaway={r["runaways"]:3d} '
                  f'severe={r["severe"]["rate"]:.3f} [{r["severe"]["ci95"][0]:.2f}-{r["severe"]["ci95"][1]:.2f}] '
                  f'moderate={r["moderate"]["rate"]:.3f} clean={r["clean"]["rate"]:.3f}')


if __name__ == "__main__":
    main()
