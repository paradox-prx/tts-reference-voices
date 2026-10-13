"""Tests for engine/precompute_voices.py: the averaging recipe and the manifest (pure numpy, gateway venv), plus the
engine's own loaders on the written directory (engine venv, CPU, skipped when it or the output is missing).

Run: venvs/gateway/bin/python -m pytest engine/tests
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ENGINE = Path(__file__).resolve().parents[1]
SERVER = ENGINE.parent
OUT_DIR = SERVER / "state" / "custom_voices"


@pytest.fixture(scope="module")
def pv():
    spec = importlib.util.spec_from_file_location("precompute_voices", ENGINE / "precompute_voices.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["precompute_voices"] = module
    spec.loader.exec_module(module)
    return module


def test_average_is_the_mean_direction_at_the_mean_norm(pv) -> None:
    rng = np.random.default_rng(0)
    base = rng.normal(size=2048)
    clips = np.stack([base * s + rng.normal(scale=0.3, size=2048) for s in (0.9, 1.0, 1.1, 1.2)])
    averaged, stats = pv.average_embedding(clips)
    norms = np.linalg.norm(clips, axis=1)
    assert averaged.dtype == np.float32 and averaged.shape == (2048,)
    assert np.isclose(np.linalg.norm(averaged), norms.mean(), rtol=1e-5)
    assert pv.cosine(averaged, clips.mean(axis=0)) > 1 - 1e-6
    assert stats["mean_vector_norm"] < norms.mean()  # averaging shrinks the norm; the rescale restores it
    assert len(stats["cos_to_mean"]) == 4 and min(stats["cos_to_mean"]) > 0.9
    single, _ = pv.average_embedding(clips[:1])
    assert np.allclose(single, clips[0], rtol=1e-5)
    for bad in (np.zeros((2, 8)), np.ones(8), np.empty((0, 8)), np.array([[np.nan, 1.0]])):
        with pytest.raises(ValueError):
            pv.average_embedding(bad)


def test_voice_clips_and_reference(pv, tmp_path: Path) -> None:
    voice = tmp_path / "v1"
    (voice / "references").mkdir(parents=True)
    for name in ("v1_02.wav", "v1_01.wav"):
        (voice / name).write_bytes(b"RIFF")
    ref = voice / "references" / "qwen3-tts.wav"
    ref.write_bytes(b"reference audio")
    digest = hashlib.sha256(b"reference audio").hexdigest()
    (voice / "references" / "references.json").write_text(json.dumps(
        {"qwen3-tts": {"file": "qwen3-tts.wav", "text": " Hello there. ", "sha256": digest}}))
    got = pv.load_reference(voice)
    assert got == {"path": ref, "text": "Hello there.", "sha256": digest}
    assert pv.voice_clips(voice, ref) == [voice / "v1_01.wav", voice / "v1_02.wav", ref]
    (voice / "references" / "references.json").write_text(json.dumps(
        {"qwen3-tts": {"file": "qwen3-tts.wav", "text": "Hello", "sha256": "0" * 64}}))
    with pytest.raises(SystemExit, match="does not match"):
        pv.load_reference(voice)
    assert pv.profile_names("Trump") == ("trump-avg", "trump-prompt")


def test_manifest_merge_keeps_other_voices(pv) -> None:
    entry = pv.manifest_entry("a-avg", "a-avg.safetensors", "text", 291, 2048, "A")
    assert entry == {"name": "a-avg", "file": "a-avg.safetensors", "mode": "icl", "embedding_dim": 2048,
                     "ref_code_length": 291, "ref_text": "text", "speaker_description": "A"}
    old = {"schema_version": 1, "model_type": "qwen3_tts", "voices": {"b-avg": {"name": "b-avg"}}}
    merged = pv.merge_manifest(old, "Qwen/X", 2048, {"a-avg": entry})
    assert list(merged["voices"]) == ["a-avg", "b-avg"] and merged["hidden_size"] == 2048
    foreign = pv.merge_manifest({"model_type": "voxcpm2", "voices": {"c": {}}}, "Qwen/X", 2048, {"a-avg": entry})
    assert list(foreign["voices"]) == ["a-avg"] and foreign["model_type"] == "qwen3_tts"


def test_written_voices_load_with_the_engine_loaders() -> None:
    """The engine's API-side and talker-side loaders accept state/custom_voices (written by precompute_voices.py)."""
    python = SERVER / "venvs" / "engine" / "bin" / "python"
    if not python.exists() or not (OUT_DIR / "custom_voice_manifest.json").exists():
        pytest.skip("no venvs/engine or no state/custom_voices yet (run engine/precompute_voices.py)")
    manifest = json.loads((OUT_DIR / "custom_voice_manifest.json").read_text())
    ids = sorted({name.rsplit("-", 1)[0] for name in manifest["voices"]})
    args = [str(python), str(ENGINE / "precompute_voices.py"), "--verify-only", "--out-dir", str(OUT_DIR)]
    for voice_id in ids:
        args += ["--voice", voice_id]
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    r = subprocess.run(["nice", *args], capture_output=True, text=True, timeout=600, env=env)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-3000:]
    assert f"verify: {2 * len(ids)} profile(s) load" in r.stdout
    for voice_id in ids:
        stats = json.loads((OUT_DIR / f"{voice_id}-embeddings.json").read_text())
        assert abs(stats["avg_norm"] - stats["mean_clip_norm"]) < 1e-3
        assert len(stats["clips"]) >= 2 and stats["clips"][-1]["file"] == "references/qwen3-tts.wav"
