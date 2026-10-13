"""Deterministic fake engine: a 200 Hz tone lasting `spw` seconds per word. For tests and for measuring the gateway's
own overhead. Takes are counted per request id, so failures and suspect takes can be injected into the first N
takes of every request (the retry path)."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict, deque
from collections.abc import AsyncGenerator
from typing import Any

import numpy as np

from ..config import Settings
from ..textproc import count_words
from ..voices import Voice
from .base import (
    BackendError,
    Capabilities,
    EngineBadRequest,
    EngineFailure,
    EngineTimeout,
    EngineUnavailable,
    SynthesisRequest,
    SynthesisResult,
)

_TONE_HZ = 200  # divides 24000 and 16000, so one period tiles exactly
_SUSPECT_SPW = (0.05, 0.10, 0.15)  # too short for any band; later takes get closer to it
_TRACKED_REQUESTS = 4096


def _failure(kind: str) -> BackendError:
    match kind:
        case "unavailable":
            return EngineUnavailable("stub: engine unavailable")
        case "timeout":
            return EngineTimeout("stub: engine timed out")
        case "bad_request":
            return EngineBadRequest("stub: engine rejected the request")
        case "failure":
            return EngineFailure("stub: engine failed", retryable=False)
        case _:
            return EngineFailure("stub: codec limit reached without EOS", retryable=True)


class StubBackend:
    name = "stub"

    def __init__(self, *, sample_rate: int = 24000, spw: float = 0.35, base_latency_s: float = 0.0,
                 latency_per_audio_s: float = 0.0, suspect_takes: int = 0, fail_takes: int = 0,
                 fail_kind: str = "retryable", chunk_s: float = 2.0, max_seconds_per_call: float | None = None,
                 repetition_penalty: bool = False) -> None:
        self.capabilities = Capabilities(streaming=True, per_request_repetition_penalty=repetition_penalty,
                                         voice_registry=True, max_seconds_per_call=max_seconds_per_call,
                                         sample_rate=sample_rate)
        self.sample_rate, self.spw, self.chunk_s = sample_rate, spw, chunk_s
        self.base_latency_s, self.latency_per_audio_s = base_latency_s, latency_per_audio_s
        self.suspect_takes, self.fail_takes, self.fail_kind = suspect_takes, fail_takes, fail_kind
        self.healthy = False
        self.registered: set[str] = set()
        self.calls = 0
        self.closed_early = 0  # streams closed before their last chunk (client gone)
        self.requests: deque[SynthesisRequest] = deque(maxlen=64)  # the latest calls, for tests
        self._takes: OrderedDict[str, int] = OrderedDict()
        period = np.sin(2 * np.pi * _TONE_HZ * np.arange(sample_rate // _TONE_HZ) / sample_rate)
        self._period = (0.3 * 32767 * period).astype("<i2")

    @classmethod
    def from_settings(cls, s: Settings) -> StubBackend:
        return cls(spw=s.stub_spw, base_latency_s=s.stub_base_latency_s, latency_per_audio_s=s.stub_latency_per_audio_s,
                   suspect_takes=s.stub_suspect_takes, fail_takes=s.stub_fail_takes, fail_kind=s.stub_fail_kind,
                   max_seconds_per_call=s.stub_max_seconds_per_call, repetition_penalty=s.stub_repetition_penalty)

    async def start(self) -> None:
        self.healthy = True

    async def close(self) -> None:
        self.healthy = False

    async def health(self) -> dict[str, Any]:
        return {"ok": self.healthy, "backend": self.name}

    async def register_voice(self, voice: Voice) -> None:
        self.registered.add(voice.id)

    def _next_take(self, req: SynthesisRequest) -> tuple[int, float]:
        """(take index for this request id, seconds of audio it will have); raises injected failures."""
        self.calls += 1
        self.requests.append(req)
        take = self._takes.pop(req.request_id, 0)
        self._takes[req.request_id] = take + 1
        if len(self._takes) > _TRACKED_REQUESTS:
            self._takes.popitem(last=False)
        if take < self.fail_takes:
            raise _failure(self.fail_kind)
        spw = _SUSPECT_SPW[min(take, len(_SUSPECT_SPW) - 1)] if take < self.suspect_takes else self.spw
        return take, max(1, count_words(req.text)) * spw

    def _pcm(self, seconds: float) -> bytes:
        n = round(seconds * self.sample_rate)
        return np.resize(self._period, n).tobytes()

    async def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
        start = time.perf_counter()
        take, seconds = self._next_take(req)
        await asyncio.sleep(self.base_latency_s + self.latency_per_audio_s * seconds)
        return SynthesisResult(pcm=self._pcm(seconds), sample_rate=self.sample_rate,
                               engine_ms=(time.perf_counter() - start) * 1000,
                               codec_frames=round(seconds * 12.5), meta={"take": take})

    async def stream(self, req: SynthesisRequest) -> AsyncGenerator[bytes, None]:
        _, seconds = self._next_take(req)
        pcm = self._pcm(seconds)
        step = 2 * round(self.chunk_s * self.sample_rate)
        finished = False
        try:
            await asyncio.sleep(self.base_latency_s)
            for i in range(0, len(pcm), step):
                chunk = pcm[i:i + step]
                await asyncio.sleep(self.latency_per_audio_s * len(chunk) / (2 * self.sample_rate))
                yield chunk
            finished = True
        finally:
            if not finished:
                self.closed_early += 1
