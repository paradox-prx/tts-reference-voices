"""Backend factory. Engine-specific modules are imported lazily, so the stub needs none of their dependencies."""

from __future__ import annotations

from ..config import Settings
from ..voices import VoiceRegistry
from .base import (
    BackendError,
    Capabilities,
    EngineBadRequest,
    EngineFailure,
    EngineTimeout,
    EngineUnavailable,
    SynthesisRequest,
    SynthesisResult,
    TTSBackend,
)

__all__ = [
    "BackendError", "Capabilities", "EngineBadRequest", "EngineFailure", "EngineTimeout", "EngineUnavailable",
    "SynthesisRequest", "SynthesisResult", "TTSBackend", "create_backend",
]


def create_backend(settings: Settings, voices: VoiceRegistry) -> TTSBackend:
    match settings.backend:
        case "stub":
            from .stub import StubBackend

            return StubBackend.from_settings(settings)
        case "vllm_omni":
            from .vllm_omni import VllmOmniBackend

            return VllmOmniBackend(settings, voices)
        case "higgs_sglang":
            from .higgs_sglang import HiggsSglangBackend

            return HiggsSglangBackend(settings, voices)
    raise ValueError(f"unknown backend {settings.backend!r}")
