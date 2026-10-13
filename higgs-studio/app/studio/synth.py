"""Text -> one take: split into parts (<= max_part_s estimated speech, tags restated), generate the parts in parallel
through the shared queue, trim edge silence, QC each part (retry with a new seed), join with a gap, normalise."""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field

import numpy as np

from . import audio
from .engine import Engine, EngineError, Sampling, max_frames_for
from .scheduler import DEV, Scheduler
from .text import Part, plan_parts


@dataclass
class Ref:
    wav: bytes
    text: str
    s_per_letter: float


@dataclass
class QCConfig:
    duration: bool = True
    silence: bool = True
    clipping: bool = True
    pace_low: float = 0.55
    pace_high: float = 1.8
    max_gap_s: float = 2.5
    retries: int = 2            # extra attempts (new seed) for a part that fails QC or errors


@dataclass
class SynthRequest:
    text: str                   # text as sent (delivery tags already placed)
    ref: Ref
    sampling: Sampling = field(default_factory=Sampling)
    seed: int | None = None     # None: a random seed is drawn and reported
    max_part_s: float = 25.0
    gap_s: float = 0.3
    loudness_lufs: float | None = -20.0
    sample_rate: int = audio.SR
    qc: QCConfig = field(default_factory=QCConfig)
    priority: int = DEV
    exclusive: bool = False     # run each part alone on the engine (exact seed reproduction)


@dataclass
class PartResult:
    text: str
    est_s: float
    seconds: float
    seed: int
    attempts: int
    qc: dict
    ok: bool


@dataclass
class SynthResult:
    audio: np.ndarray           # at request.sample_rate
    sample_rate: int
    seed: int
    parts: list[PartResult]
    ok: bool
    reasons: list[str]

    @property
    def seconds(self) -> float:
        return len(self.audio) / self.sample_rate

    def summary(self) -> dict:
        return {"seed": self.seed, "seconds": round(self.seconds, 2), "ok": self.ok, "reasons": self.reasons,
                "parts": [p.__dict__ for p in self.parts]}


def part_seed(seed: int, part: int, attempt: int) -> int:
    return (seed + 1009 * part + 100003 * attempt) % (2 ** 31 - 1)


async def _gen_part(engine: Engine, sched: Scheduler, req: SynthRequest, part: Part, idx: int, seed: int,
                    on_event=None) -> tuple[np.ndarray, PartResult]:
    best: tuple[float, np.ndarray, PartResult] | None = None
    last_err = None
    for attempt in range(req.qc.retries + 1):
        s = part_seed(seed, idx, attempt)

        async def waiting(pos):
            if on_event:
                await on_event({"type": "queued", "part": idx, "position": pos})
        try:
            async with sched.slot(req.priority, req.exclusive, on_wait=waiting):
                if on_event:
                    await on_event({"type": "part_started", "part": idx, "attempt": attempt})
                wav = await engine.speech(part.text, req.ref.wav, req.ref.text, req.sampling, s,
                                          max_frames_for(part.est_s))
        except EngineError as e:
            last_err = e
            if not e.retryable:
                raise
            continue
        x, sr = audio.read_wav_bytes(wav)
        x = audio.trim_silence(audio.resample(x, sr, audio.SR))
        q = audio.measure(x, part.est_s, check_duration=req.qc.duration, check_silence=req.qc.silence,
                          check_clipping=req.qc.clipping, pace_band=(req.qc.pace_low, req.qc.pace_high),
                          max_gap_s=req.qc.max_gap_s)
        pr = PartResult(part.text, part.est_s, round(q.seconds, 2), s, attempt + 1, q.as_dict(), q.ok)
        score = (1.0 if q.ok else 0.0) - abs(np.log(max(q.pace_ratio, 1e-3)))
        if best is None or score > best[0]:
            best = (score, x, pr)
        if on_event:
            await on_event({"type": "part_done", "part": idx, "attempt": attempt, "ok": q.ok, "qc": q.as_dict()})
        if q.ok:
            break
    if best is None:
        raise last_err or EngineError("no audio")
    best[2].attempts = attempt + 1
    return best[1], best[2]


async def synthesize(engine: Engine, sched: Scheduler, req: SynthRequest, on_event=None) -> SynthResult:
    seed = req.seed if req.seed is not None else random.randrange(1, 2 ** 31 - 1)
    parts = plan_parts(req.text, req.max_part_s, req.ref.s_per_letter)
    if not parts:
        raise ValueError("empty text")
    if on_event:
        await on_event({"type": "planned", "parts": [{"text": p.text, "est_s": p.est_s} for p in parts], "seed": seed})
    results = await asyncio.gather(*[_gen_part(engine, sched, req, p, i, seed, on_event) for i, p in enumerate(parts)])
    y = audio.join([r[0] for r in results], req.gap_s)
    y = audio.normalize_loudness(y, audio.SR, req.loudness_lufs)
    if req.sample_rate != audio.SR:
        y = audio.resample(y, audio.SR, req.sample_rate)
    prs = [r[1] for r in results]
    reasons = [f"part {i + 1}: {r}" for i, p in enumerate(prs) for r in p.qc["reasons"]]
    return SynthResult(y, req.sample_rate, seed, prs, all(p.ok for p in prs), reasons)
