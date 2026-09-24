"""Gateway settings, read from the environment (prefix TTS_). See docs/DESIGN.md for the table."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

RETRY_REASONS = frozenset({"suspect", "engine_error"})

# comma-separated in the environment ("0.18,0.9"), so pydantic-settings must not JSON-decode them
Band = Annotated[tuple[float, float], NoDecode]
RetryOn = Annotated[frozenset[str], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TTS_", extra="ignore", env_parse_none_str="none")

    api_key: SecretStr | None = None  # one or more comma-separated bearer keys
    auth_disabled: bool = False
    backend: Literal["vllm_omni", "stub", "higgs_sglang"] = "vllm_omni"
    model: str = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"  # listed by /v1/models; the served engine model
    engine_url: str = "http://127.0.0.1:8091"
    engine_api_key: SecretStr | None = None
    voices_dir: Path = Path("/home/vector/tts-reference-voices/voices")
    voice_mode: Literal["registered", "inline"] = "registered"

    max_inflight: int = Field(32, ge=1)
    max_queue: int = Field(128, ge=0)
    queue_timeout_s: float = Field(60.0, gt=0)
    request_timeout_s: float = Field(300.0, gt=0)
    max_input_chars: int = Field(3000, ge=1)

    retry_max: int = Field(1, ge=0, le=5)
    retry_on: RetryOn = RETRY_REASONS
    length_cap: bool = True
    spw_en: Band = (0.18, 0.9)
    spw_ur: Band = (0.18, 1.1)
    default_temperature: float | None = 0.9  # applied by the backend when a request leaves it unset
    default_top_k: int | None = 50

    warmup: bool = True
    allow_inline_ref: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8090
    shutdown_grace_s: float = 30.0

    # stub backend (TTS_BACKEND=stub): deterministic fake engine for tests and gateway-overhead runs
    stub_spw: float = 0.35  # seconds of audio per word
    stub_base_latency_s: float = 0.0
    stub_latency_per_audio_s: float = 0.0
    stub_suspect_takes: int = 0  # the first N takes of every request come out suspect (too short)
    stub_fail_takes: int = 0  # the first N takes of every request fail with stub_fail_kind
    stub_fail_kind: Literal["unavailable", "timeout", "bad_request", "failure", "retryable"] = "retryable"
    stub_max_seconds_per_call: float | None = None
    stub_repetition_penalty: bool = False

    @field_validator("spw_en", "spw_ur", mode="before")
    @classmethod
    def _parse_band(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = tuple(float(x) for x in value.split(","))
        return value

    @field_validator("spw_en", "spw_ur")
    @classmethod
    def _check_band(cls, value: tuple[float, float]) -> tuple[float, float]:
        if not 0 < value[0] < value[1]:
            raise ValueError("band must be 'low,high' with 0 < low < high")
        return value

    @field_validator("retry_on", mode="before")
    @classmethod
    def _parse_retry_on(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = {x.strip() for x in value.split(",") if x.strip()}
        unknown = set(value) - RETRY_REASONS
        if unknown:
            raise ValueError(f"unknown retry reasons {sorted(unknown)}; allowed: {sorted(RETRY_REASONS)}")
        return frozenset(value)

    @model_validator(mode="after")
    def _require_key(self) -> Settings:
        if not self.auth_disabled and not self.api_keys:
            raise ValueError("TTS_API_KEY is required unless TTS_AUTH_DISABLED=1")
        return self

    @property
    def api_keys(self) -> list[str]:
        raw = self.api_key.get_secret_value() if self.api_key else ""
        return [k.strip() for k in raw.split(",") if k.strip()]
