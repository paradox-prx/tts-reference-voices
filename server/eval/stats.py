"""Small statistics helpers shared by score_run.py and retry_sim.py (stdlib only)."""
from __future__ import annotations

import math
import random
from statistics import mean, median
from typing import Callable, Sequence

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float] | None:
    """95 % Wilson score interval for a proportion k/n (None when n = 0)."""
    if n <= 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": wilson(k, n)}


def bootstrap(keys: Sequence, stat: Callable[[list], float], n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    """Percentile 95 % CI of stat() over resamples (with replacement) of `keys` (clusters, e.g. prompts)."""
    rng, keys = random.Random(seed), list(keys)
    vals = sorted(stat([rng.choice(keys) for _ in keys]) for _ in range(n_boot))
    return round(vals[int(0.025 * n_boot)], 4), round(vals[min(n_boot - 1, int(0.975 * n_boot))], 4)


def describe(values: Sequence[float | None]) -> dict | None:
    xs = sorted(float(v) for v in values if v is not None and not (isinstance(v, float) and math.isnan(v)))
    if not xs:
        return None
    q = lambda p: xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]   # noqa: E731
    return {"n": len(xs), "mean": round(mean(xs), 4), "median": round(median(xs), 4), "p10": round(q(0.1), 4),
            "p90": round(q(0.9), 4), "min": round(xs[0], 4), "max": round(xs[-1], 4)}
