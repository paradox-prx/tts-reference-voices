"""Default locations, derived from this file's place in the repo checkout (<repo>/server/qc/tts_qc/paths.py).
Every one can be overridden from the environment, so nothing depends on where the checkout lives."""

from __future__ import annotations

import os
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = SERVER_DIR.parent


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else default


def voices_dir() -> Path:
    """voices/<id>/ folders (references/qwen3-tts.wav + references.json, voice.json, clips)."""
    return _env_path("TTS_QC_VOICES_DIR", REPO_DIR / "voices")


def models_dir() -> Path:
    """faster-whisper-large-v3/, wavlm-base-plus-sv/, beatrice/ (server/eval/fetch_models.py puts them here)."""
    return _env_path("TTS_QC_MODELS_DIR", SERVER_DIR / "models" / "eval")


def pace_file() -> Path:
    """Expected output pace per voice (seconds per letter); shared with the gateway and bench_tts.py."""
    return _env_path("TTS_QC_PACE_FILE", SERVER_DIR / "calibration" / "pace.json")


def benchmarks_dir() -> Path:
    """benchmarks/<voice>_<lang>.json: the 43 prompts per voice (used to name prompts in summaries)."""
    return _env_path("TTS_QC_BENCHMARKS_DIR", REPO_DIR / "benchmarks")
