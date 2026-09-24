"""The engine interface every backend implements, and the typed errors the gateway maps to HTTP statuses."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..voices import Voice


@dataclass(frozen=True, kw_only=True)
class SynthesisRequest:
    text: str
    voice: Voice | None  # registered voice, or None for inline cloning (ref_audio + ref_text)
    language: str  # engine spelling: "English", "Auto", ...
    response_format: str = "pcm"  # the gateway always asks for PCM16 and encodes itself
    temperature: float | None = None  # None: the backend applies its own default
    top_k: int | None = None
    top_p: float | None = None
    repetition_penalty: float | None = None  # only when capabilities.per_request_repetition_penalty
    seed: int | None = None
    max_new_tokens: int | None = None  # codec frames (12.5/s for Qwen3-TTS)
    speed: float | None = None
    # Qwen3-TTS prompt layout: True puts the whole text in the prefill instead of feeding it one token per codec
    # frame (the Base default, False); None leaves it to the engine
    non_streaming_mode: bool | None = None
    ref_audio: bytes | None = None
    ref_text: str | None = None
    request_id: str


@dataclass(frozen=True)
class SynthesisResult:
    pcm: bytes  # PCM16 LE mono
    sample_rate: int
    engine_ms: float
    codec_frames: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Capabilities:
    streaming: bool = True
    per_request_repetition_penalty: bool = False
    voice_registry: bool = True  # voices are uploaded once (register_voice) and then referenced by id
    max_seconds_per_call: float | None = None  # per-call audio ceiling; the gateway splits text at sentences
    sample_rate: int = 24000  # of stream() chunks, needed for the WAV header before the first chunk


class TTSBackend(Protocol):
    name: str
    capabilities: Capabilities

    async def start(self) -> None: ...

    async def close(self) -> None: ...

    async def health(self) -> dict[str, Any]:  # {"ok": bool, ...}
        ...

    async def register_voice(self, voice: Voice) -> None:  # idempotent
        ...

    async def synthesize(self, req: SynthesisRequest) -> SynthesisResult: ...

    def stream(self, req: SynthesisRequest) -> AsyncGenerator[bytes, None]:
        """PCM16 chunks as they are generated (an async generator: aclose() must cancel the engine call)."""
        ...


class BackendError(Exception):
    """An engine call failed. `kind` labels the engine_errors_total metric."""

    kind = "error"
    retryable = False


class EngineUnavailable(BackendError):
    """Engine down or refusing connections (HTTP 503)."""

    kind = "unavailable"


class EngineTimeout(BackendError):
    """No answer within TTS_REQUEST_TIMEOUT_S (HTTP 504)."""

    kind = "timeout"


class EngineBadRequest(BackendError):
    """The engine rejected the request itself, e.g. an unsupported language (HTTP 400)."""

    kind = "bad_request"


class EngineFailure(BackendError):
    """The engine errored (HTTP 502 once retries are spent). retryable=True for failures a fresh take may fix,
    such as the codec limit being hit without EOS (a runaway) or a transient 5xx."""

    kind = "failure"

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable
