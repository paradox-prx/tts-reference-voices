"""Assign dataset rows to speakers: uniform random, balanced (equal counts +-1) or weighted (% per speaker). Rows that
name a speaker (pinned) keep it in every mode. The assignment is a pure function of (rows, speakers, mode, weights,
seed), so a run can be repeated exactly."""
from __future__ import annotations

import random
from collections import Counter


class DistributionError(ValueError):
    pass


def assign(pinned: list[str | None], speakers: list[str], mode: str = "balanced", weights: dict[str, float] | None = None,
           seed: int = 0) -> list[str]:
    """pinned[i] is the speaker row i is pinned to, or None. Returns a speaker per row."""
    if not speakers:
        raise DistributionError("no speakers")
    unknown = sorted({p for p in pinned if p is not None and p not in speakers})
    if unknown:
        raise DistributionError(f"rows pinned to unknown speakers: {', '.join(unknown)}")
    rng = random.Random(seed)
    out: list[str | None] = list(pinned)
    free = [i for i, p in enumerate(pinned) if p is None]
    if mode == "uniform":
        for i in free:
            out[i] = rng.choice(speakers)
        return out  # type: ignore[return-value]
    counts = Counter(p for p in pinned if p is not None)
    n = len(pinned)
    if mode == "balanced":
        target = {s: n // len(speakers) for s in speakers}
        extra = list(speakers)
        rng.shuffle(extra)
        for s in extra[: n % len(speakers)]:
            target[s] += 1
    elif mode == "weighted":
        w = {s: float((weights or {}).get(s, 0.0)) for s in speakers}
        if any(v < 0 for v in w.values()) or sum(w.values()) <= 0:
            raise DistributionError("weights must be >= 0 and not all zero")
        tot = sum(w.values())
        raw = {s: n * w[s] / tot for s in speakers}
        target = {s: int(raw[s]) for s in speakers}
        rest = n - sum(target.values())
        for s in sorted(speakers, key=lambda s: (-(raw[s] - target[s]), rng.random()))[:rest]:  # largest remainder
            target[s] += 1
    else:
        raise DistributionError(f"unknown mode {mode!r} (uniform, balanced, weighted)")
    # pinned rows already count towards their speaker; fill the rest towards the targets
    need = {s: max(0, target[s] - counts[s]) for s in speakers}
    pool = [s for s in speakers for _ in range(need[s])]
    # pinned rows can overshoot a target, then there are fewer free slots than free rows: fill by remaining deficit
    while len(pool) < len(free):
        pool.append(min(speakers, key=lambda s: (counts[s] + pool.count(s) - target[s], rng.random())))
    rng.shuffle(pool)
    order = list(free)
    rng.shuffle(order)
    for i, s in zip(order, pool):
        out[i] = s
    return out  # type: ignore[return-value]


def preview(assigned: list[str], speakers: list[str]) -> dict[str, int]:
    c = Counter(assigned)
    return {s: c.get(s, 0) for s in speakers}
