"""The real sidecar on CPU: Whisper large-v3 int8 + wavlm-base-plus-sv (the sidecar defaults), over HTTP, on the
reference clips. Slow (~1 min: model load + per-voice SIM references + a few ~10 s clips)."""
from __future__ import annotations

import base64
import json
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from tts_qc import paths
from tts_qc.app import create_app
from tts_qc.audio import read_wav
from tts_qc.config import Settings

pytestmark = [pytest.mark.slow,
              pytest.mark.skipif(not (paths.models_dir() / "faster-whisper-large-v3" / "model.bin").exists(),
                                 reason="eval models not downloaded (server/eval/fetch_models.py)")]


def clip(voice: str, name: str) -> tuple[np.ndarray, int, str]:
    clips = json.loads((paths.voices_dir() / voice / "clips.json").read_text(encoding="utf-8"))["clips"]
    entry = next(c for c in clips if c["file"] == name)
    pcm, sr = read_wav(paths.voices_dir() / voice / name)
    return pcm, sr, entry["text"]


def body(pcm: np.ndarray, sr: int, text: str, voice: str, lang: str, rid: str = "t") -> dict:
    return {"request_id": rid, "voice": voice, "lang": lang, "text": text, "sample_rate": sr,
            "pcm_b64": base64.b64encode(pcm.astype("<i2").tobytes()).decode()}


@pytest.fixture(scope="module")
def client():
    settings = Settings(device="cpu", workers=1, cpu_threads=8, sim_model="base")
    with TestClient(create_app(settings)) as c:
        deadline = time.time() + 600
        while c.get("/health").status_code != 200:
            assert time.time() < deadline, c.get("/health").json()
            time.sleep(0.5)
        yield c


def test_health_after_load(client) -> None:
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["asr"] and h["sim"] and h["device"] == "cpu"
    assert {"trump", "shehbaz"} <= set(h["voices"])


def test_real_urdu_clip_passes(client) -> None:
    """shehbaz_02 (10.2 s, held-out clip). pace is not judged: a human reference clip is not TTS output, and this
    speaker's address runs at ~0.16-0.18 s/letter vs 0.111 expected of Qwen, so the test sends only asr+sim+audio
    reasons that do not depend on pace (the pace ratio itself is still reported)."""
    pcm, sr, text = clip("shehbaz", "shehbaz_02.wav")
    timings = []
    for i in range(3):
        t0 = time.perf_counter()
        r = client.post("/v1/qc", json=body(pcm, sr, text, "shehbaz", "ur", f"lat{i}"))
        timings.append((time.perf_counter() - t0) * 1000)
        assert r.status_code == 200
    out = r.json()
    m = out["metrics"]
    print(f"\nCPU latency, 10.2 s Urdu clip, int8 ASR + base SIM: {[round(t) for t in timings]} ms; "
          f"server ms {out['ms']}")
    assert m["cer_nospace"] <= 0.05 and m["del_run"] == 0 and m["sim_prompt_base"] > 0.95
    assert m["sim_heldout_base"] > 0.95 and m["pace_ratio"] > 1.3  # a slow address vs Qwen pace 0.111 s/letter
    assert [x for x in out["reasons"] if not x.startswith("pace")] == []


def test_real_english_clip_passes_and_cross_speaker_fails_sim(client) -> None:
    pcm, sr, text = clip("trump", "trump_01.wav")
    out = client.post("/v1/qc", json=body(pcm, sr, text, "trump", "en")).json()
    assert out["pass"] is True, out["reasons"]
    assert out["metrics"]["wer"] <= 0.05 and out["metrics"]["sim_prompt_base"] > 0.97
    # an engine voice variant is judged against the repo voice's references
    avg = client.post("/v1/qc", json={**body(pcm, sr, text, "trump-avg", "en"), "checks": ["sim"]}).json()
    assert avg["pass"] is True and avg["metrics"]["sim_prompt_base"] == out["metrics"]["sim_prompt_base"]
    # the same English audio claimed as the Urdu voice: speaker similarity must reject it
    wrong = client.post("/v1/qc", json={**body(pcm, sr, text, "shehbaz", "en"), "checks": ["sim"]}).json()
    assert wrong["pass"] is False and wrong["reasons"] == ["sim<0.88"]
    assert wrong["metrics"]["sim_prompt_base"] < 0.85


def test_truncated_take_fails_on_text_checks(client) -> None:
    pcm, sr, text = clip("shehbaz", "shehbaz_02.wav")
    out = client.post("/v1/qc", json={**body(pcm[: int(len(pcm) * 0.6)], sr, text, "shehbaz", "ur"),
                                      "checks": ["asr"]}).json()
    assert out["pass"] is False
    assert "char_ratio<0.85" in out["reasons"]  # 40 % of the words missing


def test_padded_take_fails_on_audio_checks(client) -> None:
    pcm, sr, text = clip("trump", "trump_01.wav")
    padded = np.concatenate([np.zeros(int(1.5 * sr), np.int16), pcm, np.zeros(4 * sr, np.int16)])
    out = client.post("/v1/qc", json={**body(padded, sr, text, "trump", "en"), "checks": ["audio", "asr"]}).json()
    assert {"lead_sil>1", "trail_sil>1.5", "unaligned_tail>3"} <= set(out["reasons"])
