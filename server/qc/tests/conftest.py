"""Tests run on CPU only: the GPU belongs to the TTS engine (set TTS_QC_TEST_GPU=1 to leave CUDA visible).

    cd server/qc && ../eval/run.sh -m pytest -q tests                # everything (real-model tests take ~1-2 min)
    cd server/qc && ../eval/run.sh -m pytest -q tests -m 'not slow'  # decision logic, checks and API contract only
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

if os.environ.get("TTS_QC_TEST_GPU") != "1":
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def pytest_configure(config) -> None:
    config.addinivalue_line("markers", "slow: loads the real models on CPU (Whisper large-v3 int8, WavLM)")
