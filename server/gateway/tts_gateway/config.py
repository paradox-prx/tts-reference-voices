"""Gateway settings, read from the environment (prefix TTS_). See docs/DESIGN.md for the table."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

RETRY_REASONS = frozenset({"suspect", "engine_error", "qc"})
QC_CHECKS = frozenset({"asr", "sim", "audio"})
# the repo checkout this gateway lives in: <repo>/server/gateway/tts_gateway/config.py
REPO_ROOT = Path(__file__).resolve().parents[3]

# comma-separated in the environment ("0.18,0.9"), so pydantic-settings must not JSON-decode them
Band = Annotated[tuple[float, float], NoDecode]
NameSet = Annotated[frozenset[str], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TTS_", extra="ignore", env_parse_none_str="none")

    api_key: SecretStr | None = None  # one or more comma-separated bearer keys
    auth_disabled: bool = False
    backend: Literal["vllm_omni", "stub", "higgs_sglang"] = "vllm_omni"
    model: str = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"  # listed by /v1/models; the served engine model
    engine_url: str = "http://127.0.0.1:8091"
    engine_api_key: SecretStr | None = None
    # the engine runs with engine/patches rep_penalty applied, so extra_params.repetition_penalty reaches the talker
    engine_per_request_rp: bool = False
    voices_dir: Path = REPO_ROOT / "voices"
    # registered: upload each voice to the engine once, then send its name; inline: send the reference clip with
    # every request; precomputed: the engine loaded the voices at startup (custom_voice_dir, e.g. with an averaged
    # speaker embedding) under precomputed_voice_name, and the gateway only sends that name
    voice_mode: Literal["registered", "inline", "precomputed"] = "registered"
    precomputed_voice_name: str = "{id}-avg"

    max_inflight: int = Field(32, ge=1)
    max_queue: int = Field(128, ge=0)
    queue_timeout_s: float = Field(60.0, gt=0)
    request_timeout_s: float = Field(300.0, gt=0)
    max_input_chars: int = Field(3000, ge=1)

    retry_max: int = Field(1, ge=0, le=5)
    retry_on: NameSet = RETRY_REASONS
    length_cap: bool = True  # send max_new_tokens: min(words formula, pace cap), see textproc.pace_cap
    length_cap_headroom: float = Field(1.2, ge=1.0)  # pace cap = headroom x suspect band's upper edge x expected
    # a take is suspect when its seconds per letter fall outside this multiple of the voice's expected pace
    suspect_band: Band = (0.6, 1.8)
    # expected output pace per voice (s/letter): calibration file, then TTS_PACE="voice=0.088,..." overrides;
    # a voice in neither falls back to its reference clip's pace
    pace_file: Path | None = REPO_ROOT / "server" / "calibration" / "pace.json"
    pace: Annotated[dict[str, float], NoDecode] = {}
    # fallback seconds-per-word bands, for text whose language differs from the reference's
    spw_en: Band = (0.18, 0.9)
    spw_ur: Band = (0.18, 1.1)
    # text languages ("en", "ur") for which non_streaming_mode=true is sent unless the request sets it: the whole text
    # goes into the prefill instead of being fed one token per frame (see docs/EXPERIMENTS.md, X6)
    non_streaming_mode_langs: NameSet = frozenset()
    default_temperature: float | None = 0.9  # applied by the backend when a request leaves it unset
    default_top_k: int | None = 50

    # quality-check sidecar (server/qc): ASR / speaker-similarity / audio checks per non-streaming take
    qc_url: str | None = None  # e.g. http://127.0.0.1:8092; unset = off
    qc_checks: NameSet = QC_CHECKS
    qc_timeout_s: float = Field(30.0, gt=0)

    warmup: bool = True
    allow_inline_ref: bool = False
    log_level: str = "INFO"
    log_tz: str = "Asia/Karachi"  # timestamps in the JSON logs are local time in this zone, with the UTC offset
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

    @field_validator("suspect_band", "spw_en", "spw_ur", mode="before")
    @classmethod
    def _parse_band(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = tuple(float(x) for x in value.split(","))
        return value

    @field_validator("suspect_band", "spw_en", "spw_ur")
    @classmethod
    def _check_band(cls, value: tuple[float, float]) -> tuple[float, float]:
        if not 0 < value[0] < value[1]:
            raise ValueError("band must be 'low,high' with 0 < low < high")
        return value

    @field_validator("pace", mode="before")
    @classmethod
    def _parse_pace(cls, value: Any) -> Any:
        if isinstance(value, str):
            pairs = [item.split("=", 1) for item in value.split(",") if item.strip()]
            if any(len(pair) != 2 for pair in pairs):
                raise ValueError("pace must be 'voice=seconds_per_letter,...'")
            value = {k.strip().lower(): float(v) for k, v in pairs}
        if any(not v > 0 for v in value.values()):
            raise ValueError("every pace must be > 0")
        return value

    @field_validator("non_streaming_mode_langs", mode="before")
    @classmethod
    def _parse_langs(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = {x.strip().lower() for x in value.split(",") if x.strip()}
        return frozenset(value)

    @field_validator("retry_on", "qc_checks", mode="before")
    @classmethod
    def _parse_names(cls, value: Any, info: ValidationInfo) -> Any:
        if isinstance(value, str):
            value = {x.strip() for x in value.split(",") if x.strip()}
        allowed, what = (RETRY_REASONS, "retry reasons") if info.field_name == "retry_on" else (QC_CHECKS, "QC checks")
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"unknown {what} {sorted(unknown)}; allowed: {sorted(allowed)}")
        return frozenset(value)

    @field_validator("precomputed_voice_name")
    @classmethod
    def _check_voice_name(cls, value: str) -> str:
        try:
            value.format(id="x")
        except (KeyError, IndexError, ValueError) as exc:
            raise ValueError(f"must be a format string using only {{id}}: {exc}") from None
        return value

    @field_validator("log_tz")
    @classmethod
    def _check_tz(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f"unknown time zone {value!r}") from None
        return value

    @model_validator(mode="after")
    def _require_key(self) -> Settings:
        if not self.auth_disabled and not self.api_keys:
            raise ValueError("TTS_API_KEY is required unless TTS_AUTH_DISABLED=1")
        return self

    @property
    def api_keys(self) -> list[str]:
        raw = self.api_key.get_secret_value() if self.api_key else ""
        return [k.strip() for k in raw.split(",") if k.strip()]
