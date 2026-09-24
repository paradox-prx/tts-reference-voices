"""Quality guardrail for non-streaming requests: flag suspect takes by seconds-per-word, retry them (and retryable
engine failures), keep the best take. See "Retry and quality policy" in docs/DESIGN.md."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace

from .audio import duration_s
from .backends.base import BackendError, EngineTimeout, SynthesisRequest, SynthesisResult, TTSBackend
from .metrics import Metrics
from .textproc import SpwBand


@dataclass(frozen=True)
class Take:
    result: SynthesisResult
    audio_s: float
    spw: float
    reason: str | None  # None, "too_short" or "too_long"

    @property
    def suspect(self) -> bool:
        return self.reason is not None


@dataclass(frozen=True)
class Outcome:
    take: Take  # the best take
    attempts: int  # engine calls made, failed ones included

    @property
    def retries(self) -> int:
        return self.attempts - 1


def assess(result: SynthesisResult, words: int, band: SpwBand | None) -> Take:
    audio_s = duration_s(len(result.pcm), result.sample_rate)
    spw = audio_s / max(1, words)
    return Take(result, audio_s, spw, band.reason(spw) if band else None)


def best(takes: list[Take], band: SpwBand | None) -> Take:
    """A take inside the band if any, else the one whose seconds-per-word is closest to the band's centre."""
    return min(takes, key=lambda t: (t.suspect, band.distance(t.spw) if band else 0.0))


async def synthesize(backend: TTSBackend, req: SynthesisRequest, *, words: int, band: SpwBand | None,
                     retries: int, retry_on: frozenset[str], timeout_s: float, metrics: Metrics,
                     voice: str) -> Outcome:
    """Up to 1 + retries takes. Raises the last BackendError only when no take produced audio."""
    takes: list[Take] = []
    error: BackendError | None = None
    attempt = 0
    for attempt in range(retries + 1):
        if attempt and req.seed is not None:
            req = replace(req, seed=req.seed + 1)  # a seeded request would repeat the same take
        try:
            async with asyncio.timeout(timeout_s):
                result = await backend.synthesize(req)
        except (BackendError, TimeoutError) as exc:
            error = exc if isinstance(exc, BackendError) else EngineTimeout(f"no audio within {timeout_s:g} s")
            metrics.engine_errors.labels(error.kind).inc()
            if not (error.retryable and "engine_error" in retry_on) or attempt == retries:
                break
            metrics.retries.labels("engine_error").inc()
            continue
        take = assess(result, words, band)
        takes.append(take)
        if take.reason is None:
            break
        metrics.suspect.labels(voice).inc()
        if "suspect" not in retry_on or attempt == retries:
            break
        metrics.retries.labels(take.reason).inc()
    if not takes:
        assert error is not None
        raise error
    return Outcome(best(takes, band), attempt + 1)
