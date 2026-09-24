"""Quality guardrail for non-streaming requests: flag suspect takes by pace (seconds per letter against the voice's
expected pace) and, when the QC sidecar is configured, by its ASR / speaker-similarity / audio checks; retry them (and
retryable engine failures) with fresh sampling, and keep the best take. See "Retry and quality policy" in
docs/DESIGN.md."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace

from .audio import duration_s
from .backends.base import BackendError, EngineTimeout, SynthesisRequest, SynthesisResult, TTSBackend
from .metrics import Metrics
from .qc import QCClient, QCResult
from .textproc import PaceBand

_PACE_REASONS = ("too_short", "too_long")


@dataclass(frozen=True)
class Take:
    result: SynthesisResult
    audio_s: float
    ratio: float | None  # observed pace / expected pace (1.0 = as expected); None without a band
    reason: str | None  # None, "too_short", "too_long" (pace band) or "qc" (the sidecar failed it)
    qc: QCResult | None = None

    @property
    def suspect(self) -> bool:
        return self.reason is not None

    @property
    def rank(self) -> int:
        """0 clean, 1 failed only the QC checks, 2 outside the pace band (a loop, padding or a large skip)."""
        return 0 if self.reason is None else 1 if self.reason == "qc" else 2


@dataclass(frozen=True)
class Outcome:
    take: Take  # the best take
    attempts: int  # engine calls made, failed ones included
    qc_ms: float = 0.0  # QC sidecar time over all takes

    @property
    def retries(self) -> int:
        return self.attempts - 1


@dataclass(frozen=True)
class Check:
    """What to check a take against: the pace band and, optionally, the QC sidecar."""

    words: int
    letters: int
    band: PaceBand | None
    lang: str  # the text's language ("en", "ur", "und"), for the ASR check
    voice: str | None  # repo voice id for speaker similarity; None for inline references
    qc: QCClient | None = None


def assess(result: SynthesisResult, check: Check) -> Take:
    audio_s = duration_s(len(result.pcm), result.sample_rate)
    if check.band is None:
        return Take(result, audio_s, None, None)
    ratio = check.band.ratio(audio_s, check.words, check.letters)
    return Take(result, audio_s, ratio, check.band.reason(ratio))


def best(takes: list[Take]) -> Take:
    """The first clean take if any; else the least bad: QC-only failures before pace failures, then the take whose
    pace is closest to the expected one."""
    return min(takes, key=lambda t: (t.rank, PaceBand.distance(t.ratio) if t.ratio is not None else 0.0))


async def _qc(take: Take, req: SynthesisRequest, check: Check, metrics: Metrics, voice: str) -> Take:
    assert check.qc is not None
    result = await check.qc.check(request_id=req.request_id, voice=check.voice, lang=check.lang, text=req.text,
                                  pcm=take.result.pcm, sample_rate=take.result.sample_rate)
    metrics.qc_seconds.observe(result.ms / 1000)
    metrics.qc_results.labels(result.status, voice).inc()
    for reason in result.reasons:
        metrics.qc_reasons.labels(reason.split(">")[0].split("<")[0].strip()[:40]).inc()
    return replace(take, qc=result, reason="qc" if result.failed else take.reason)


async def synthesize(backend: TTSBackend, req: SynthesisRequest, *, check: Check, retries: int,
                     retry_on: frozenset[str], timeout_s: float, metrics: Metrics, voice: str) -> Outcome:
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
        take = assess(result, check)
        if take.reason is None and check.qc is not None:
            take = await _qc(take, req, check, metrics, voice)
        takes.append(take)
        if take.reason is None:
            break
        metrics.suspect.labels(voice, take.reason).inc()
        if ("qc" if take.reason == "qc" else "suspect") not in retry_on or attempt == retries:
            break
        metrics.retries.labels(take.reason).inc()
    if not takes:
        assert error is not None
        raise error
    return Outcome(best(takes), attempt + 1, sum(t.qc.ms for t in takes if t.qc))
