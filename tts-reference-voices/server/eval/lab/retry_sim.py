"""Offline retry-policy evaluation from K independent takes per prompt.

Input: one row per take: prompt, take, gate_pass (bool: passes the online gate, e.g. not suspect and CER<=x and SIM>=y),
bad (bool: the 'truth' label, ideally independent of the gate: human listen or a stricter/different ASR),
cost (seconds of GPU work or audio seconds generated for that take), score (lower is better; fallback pick).

Policy R = "up to R retries": try takes in order; stop at the first gate_pass; if all R+1 fail, ship the attempted take
with the best score. Expected values are exact over every ordered choice of R+1 distinct takes out of the K
(K!/(K-R-1)! orderings), so the arbitrary order the takes were generated in does not bias the estimate.
CIs: bootstrap over prompts (takes of one prompt are correlated: some prompts fail every time).
"""
from __future__ import annotations

import itertools
import random
from collections import defaultdict
from statistics import mean


def eval_prompt(takes: list[dict], R: int) -> dict:
    """Exact expectation over ordered (R+1)-subsets of this prompt's K takes."""
    k = len(takes)
    m = min(R + 1, k)
    bad = att = cost = 0.0
    n = 0
    for order in itertools.permutations(range(k), m):
        tried = []
        for i in order:
            tried.append(takes[i])
            if takes[i]["gate_pass"]:
                shipped = takes[i]
                break
        else:
            shipped = min(tried, key=lambda t: t["score"])
        bad += shipped["bad"]
        att += len(tried)
        cost += sum(t["cost"] for t in tried)
        n += 1
    first_cost = mean(t["cost"] for t in takes)
    return {"bad": bad / n, "attempts": att / n, "cost": cost / n, "cost_1": first_cost}


def eval_policy(rows: list[dict], R: int, n_boot: int = 1000, seed: int = 0) -> dict:
    by = defaultdict(list)
    for r in rows:
        by[r["prompt"]].append(r)
    per = {p: eval_prompt(t, R) for p, t in by.items()}

    def agg(keys):
        ps = [per[k] for k in keys]
        return (mean(p["bad"] for p in ps), mean(p["attempts"] for p in ps),
                sum(p["cost"] for p in ps) / sum(p["cost_1"] for p in ps) - 1)

    point = agg(list(per))
    rng, keys, boots = random.Random(seed), list(per), []
    for _ in range(n_boot):
        boots.append(agg([rng.choice(keys) for _ in keys]))
    ci = lambda j: (sorted(b[j] for b in boots)[int(0.025 * n_boot)], sorted(b[j] for b in boots)[int(0.975 * n_boot)])
    return {"R": R, "final_bad_rate": round(point[0], 4), "ci95": tuple(round(x, 4) for x in ci(0)),
            "mean_attempts": round(point[1], 3), "extra_compute": round(point[2], 3),
            "extra_compute_ci95": tuple(round(x, 3) for x in ci(2))}


def eval_best_of(rows: list[dict], N: int) -> dict:
    """Parallel alternative: always generate N takes, ship a passing one with the best score (else best score).
    Latency ~1 attempt (if capacity allows), compute N x. Exact over all N-subsets of each prompt's K takes."""
    by = defaultdict(list)
    for r in rows:
        by[r["prompt"]].append(r)
    bad = []
    for takes in by.values():
        combos = list(itertools.combinations(takes, min(N, len(takes))))
        tot = 0.0
        for c in combos:
            ok = [t for t in c if t["gate_pass"]]
            tot += min(ok or c, key=lambda t: t["score"])["bad"]
        bad.append(tot / len(combos))
    return {"best_of": N, "final_bad_rate": round(mean(bad), 4), "extra_compute": N - 1}


def gate_confusion(rows: list[dict]) -> dict:
    tp = sum(r["bad"] and not r["gate_pass"] for r in rows)
    fn = sum(r["bad"] and r["gate_pass"] for r in rows)
    fp = sum(not r["bad"] and not r["gate_pass"] for r in rows)
    tn = sum(not r["bad"] and r["gate_pass"] for r in rows)
    return {"take_bad_rate": round((tp + fn) / len(rows), 4), "gate_recall": round(tp / max(1, tp + fn), 3),
            "gate_precision": round(tp / max(1, tp + fp), 3), "false_reject_rate": round(fp / max(1, fp + tn), 3)}


if __name__ == "__main__":
    # Synthetic sanity check: 43 prompts x K=6 takes. Per-prompt failure probability is heterogeneous
    # (most prompts ~3%, a few 'hard' prompts with repeated syllables ~60%), overall ~10% like the Kaggle run.
    rng = random.Random(1)
    rows = []
    for p in range(43):
        pf = 0.6 if p < 4 else 0.03
        for t in range(6):
            bad = rng.random() < pf
            gate_pass = (not bad and rng.random() > 0.05) or (bad and rng.random() < 0.15)   # recall .85, 5% false rejects
            cost = (95.0 if bad and rng.random() < 0.5 else 30.0)                            # loops run to the token cap
            rows.append({"prompt": p, "take": t, "bad": bad, "gate_pass": gate_pass, "cost": cost,
                         "score": rng.random() + (1 if bad else 0)})
    print(gate_confusion(rows))
    f = sum(r["bad"] for r in rows) / len(rows)
    for R in range(0, 4):
        res = eval_policy(rows, R, n_boot=300)
        print(res, "| iid prediction (bad^(R+1), ignores gate errors):", round(f ** (R + 1), 4))
    for N in (2, 3):
        print(eval_best_of(rows, N))
