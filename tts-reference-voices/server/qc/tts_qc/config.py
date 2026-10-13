"""Sidecar settings from the environment (prefix TTS_QC_). Threshold overrides use the same prefix with the field
names of policy.Thresholds (e.g. TTS_QC_CER_NOSPACE_UR=0.12, TTS_QC_SIM_LONG_BASE=0.9).

  TTS_QC_HOST / TTS_QC_PORT       bind address, default 127.0.0.1:8092
  TTS_QC_DEVICE                   cuda | cpu (default cuda); TTS_QC_DEVICE_INDEX (default 0)
  TTS_QC_ASR                      1/0: Whisper large-v3 checks (default 1)
  TTS_QC_SIM                      1/0: speaker similarity (default 1)
  TTS_QC_ASR_COMPUTE              float16 | int8_float16 | int8 (default float16 on cuda, int8 on cpu)
  TTS_QC_BEAM                     beam size (default 5)
  TTS_QC_WORKERS                  CTranslate2 workers sharing the weights (default 2)
  TTS_QC_CPU_THREADS              threads per CT2 worker / torch on CPU (default 8)
  TTS_QC_SIM_MODEL                base (wavlm-base-plus-sv, Kaggle scale, cheap; default) | large (WavLM-Large+ECAPA)
  TTS_QC_VOICES_DIR / TTS_QC_MODELS_DIR / TTS_QC_PACE_FILE   see paths.py
  TTS_QC_MAX_SECONDS              longest take accepted (default 300)
  TTS_QC_LOG_LEVEL / TTS_QC_TZ    default INFO / Asia/Karachi (log timestamps are local time with offset)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from . import paths
from .policy import GATE, Thresholds
from .sim import MODEL_DIRS

COMPUTE_TYPES = ("float16", "int8_float16", "int8", "int8_float32", "float32", "bfloat16", "int8_bfloat16")


def _bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off", ""):
        return False
    raise ValueError(f"not a boolean: {raw!r}")


@dataclass
class Settings:
    host: str = "127.0.0.1"
    port: int = 8092
    device: str = "cuda"
    device_index: int = 0
    asr: bool = True
    sim: bool = True
    asr_compute: str | None = None
    beam: int = 5
    workers: int = 2
    cpu_threads: int = 8
    sim_model: str = "base"
    voices_dir: Path = field(default_factory=paths.voices_dir)
    models_dir: Path = field(default_factory=paths.models_dir)
    pace_file: Path | None = field(default_factory=paths.pace_file)
    max_seconds: float = 300.0
    log_level: str = "INFO"
    tz: str = "Asia/Karachi"
    thresholds: Thresholds = GATE

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "Settings":
        env = os.environ if environ is None else environ
        get = lambda k, d=None: env.get(f"TTS_QC_{k}") or d   # noqa: E731
        s = cls(
            host=get("HOST", "127.0.0.1"), port=int(get("PORT", 8092)), device=get("DEVICE", "cuda").lower(),
            device_index=int(get("DEVICE_INDEX", 0)), asr=_bool(get("ASR", "1")), sim=_bool(get("SIM", "1")),
            asr_compute=get("ASR_COMPUTE"), beam=int(get("BEAM", 5)), workers=int(get("WORKERS", 2)),
            cpu_threads=int(get("CPU_THREADS", 8)), sim_model=get("SIM_MODEL", "base").lower(),
            voices_dir=paths.voices_dir(), models_dir=paths.models_dir(), pace_file=paths.pace_file(),
            max_seconds=float(get("MAX_SECONDS", 300)), log_level=get("LOG_LEVEL", "INFO"),
            tz=get("TZ", "Asia/Karachi"), thresholds=Thresholds.from_env(GATE, environ=env))
        s.validate()
        return s

    def validate(self) -> None:
        if self.device not in ("cuda", "cpu"):
            raise ValueError(f"TTS_QC_DEVICE must be cuda or cpu, not {self.device!r}")
        if self.sim_model not in MODEL_DIRS:
            raise ValueError(f"TTS_QC_SIM_MODEL must be one of {sorted(MODEL_DIRS)}, not {self.sim_model!r}")
        if self.asr_compute and self.asr_compute not in COMPUTE_TYPES:
            raise ValueError(f"TTS_QC_ASR_COMPUTE must be one of {COMPUTE_TYPES}, not {self.asr_compute!r}")
        if self.beam < 1 or self.workers < 1 or self.cpu_threads < 1 or self.max_seconds <= 0:
            raise ValueError("TTS_QC_BEAM / WORKERS / CPU_THREADS must be >= 1 and MAX_SECONDS > 0")

    def public(self) -> dict:
        return {"device": self.device, "asr": self.asr, "sim": self.sim, "sim_model": self.sim_model,
                "asr_compute": self.asr_compute or ("float16" if self.device == "cuda" else "int8"),
                "beam": self.beam, "workers": self.workers, "voices_dir": str(self.voices_dir),
                "models_dir": str(self.models_dir), "max_seconds": self.max_seconds}
