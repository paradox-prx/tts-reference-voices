"""The HTTP contract (server/gateway/tts_gateway/qc.py is written against it), with a fake scorer."""
from __future__ import annotations

import base64
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from tts_qc.app import create_app
from tts_qc.config import Settings

SR = 24_000


def pcm_b64(seconds: float = 1.0) -> str:
    t = np.arange(int(seconds * SR)) / SR
    return base64.b64encode((0.3 * 32767 * np.sin(2 * np.pi * 220 * t)).astype("<i2").tobytes()).decode()


class FakeScorer:
    """Stands in for scorer.Scorer: returns canned metrics and records calls."""

    def __init__(self, metrics: dict | None = None, ready: bool = True, load_delay: float = 0.0) -> None:
        self.voices = {"trump": SimpleNamespace(id="trump"), "shehbaz": SimpleNamespace(id="shehbaz")}
        self.asr, self.embedders = object(), {"base": object()}
        self.metrics = metrics or {}
        self.calls: list[dict] = []
        self.load_delay, self.load_s = load_delay, {}
        self._ready = threading.Event()
        if ready:
            self._ready.set()

    @property
    def ready(self) -> bool:
        return self._ready.is_set()

    def load(self) -> "FakeScorer":
        time.sleep(self.load_delay)
        self._ready.set()
        return self

    def score(self, pcm, sr, text, lang, voice, checks, pace=True):
        self.calls.append({"n": len(pcm), "sr": sr, "text": text, "lang": lang, "voice": voice,
                           "checks": sorted(checks)})
        m = {"duration_s": len(pcm) / sr, "speech_ratio": 0.9, "lead_sil_s": 0.0, "trail_sil_s": 0.0,
             "max_internal_sil_s": 0.2, "pace_ratio": 1.0, "asr_text": "hello", "ref_norm": "x", "hyp_norm": "x",
             "wer": 0.0, "cer": 0.0, "cer_nospace": 0.0, "char_ratio": 1.0, "del_run": 0, "ins_run": 0,
             "repeat_excess": 0, "token_run": 1, "char_runs": 0, "sim_speech_s": 1.0, "sim_prompt_base": 0.97,
             "clip_frac": np.float64(0.0)}
        m.update(self.metrics)
        return m, {"audio": 1.0, "asr": 2.0, "sim": 3.0, "total": 6.0}


def client(scorer: FakeScorer, **settings) -> TestClient:
    return TestClient(create_app(Settings(device="cpu", **settings), scorer))


def body(**changes) -> dict:
    return {"request_id": "r1", "voice": "trump", "lang": "en", "text": "Hello there.", "sample_rate": SR,
            "pcm_b64": pcm_b64(), "checks": ["asr", "sim", "audio"], **changes}


def test_health_is_503_while_loading_then_200() -> None:
    scorer = FakeScorer(ready=False, load_delay=0.5)
    with client(scorer) as c:
        r = c.get("/health")
        assert r.status_code == 503 and r.json()["status"] == "loading"
        assert c.post("/v1/qc", json=body()).status_code == 503
        for _ in range(50):
            if c.get("/health").status_code == 200:
                break
            time.sleep(0.05)
        h = c.get("/health").json()
        assert h["status"] == "ok" and h["asr"] is True and h["sim"] is True and h["device"] == "cpu"


def test_health_reports_load_failure() -> None:
    scorer = FakeScorer(ready=False)
    scorer.load = lambda: (_ for _ in ()).throw(RuntimeError("no model"))
    with client(scorer) as c:
        time.sleep(0.2)
        r = c.get("/health")
        assert r.status_code == 503 and r.json()["status"] == "error" and "no model" in r.json()["error"]


def test_pass_response_shape() -> None:
    scorer = FakeScorer()
    with client(scorer) as c:
        r = c.post("/v1/qc", json=body())
    assert r.status_code == 200
    out = r.json()
    assert set(out) == {"pass", "reasons", "metrics", "ms"}
    assert out["pass"] is True and out["reasons"] == []
    assert out["metrics"]["asr_text"] == "hello" and "ref_norm" not in out["metrics"]
    assert out["metrics"]["checks"] == ["asr", "audio", "sim"] and out["metrics"]["clip_frac"] == 0.0
    assert set(out["ms"]) == {"asr", "sim", "audio", "total"}
    assert scorer.calls[0] | {"n": 0} == {"n": 0, "sr": SR, "text": "Hello there.", "lang": "en", "voice": "trump",
                                          "checks": ["asr", "audio", "sim"]}


def test_fail_response_carries_reason_codes() -> None:
    with client(FakeScorer({"cer_nospace": 0.4, "del_run": 9, "trail_sil_s": 3.0, "sim_prompt_base": 0.5,
                            "sim_speech_s": 8.0})) as c:
        out = c.post("/v1/qc", json=body(voice="shehbaz", lang="ur")).json()
    assert out["pass"] is False
    assert out["reasons"] == ["trail_sil>1.5", "cer_nospace>0.35", "del_run>=8", "sim<0.88"]


def test_checks_subset_default_and_inline_voice() -> None:
    scorer = FakeScorer({"wer": 0.9})
    with client(scorer) as c:
        assert c.post("/v1/qc", json=body(checks=["audio"])).json()["pass"] is True     # ASR not asked: ignored
        assert c.post("/v1/qc", json={k: v for k, v in body().items() if k != "checks"}).json()["pass"] is False
        out = c.post("/v1/qc", json=body(voice="", checks=["asr", "sim"])).json()          # inline: no SIM
        und = c.post("/v1/qc", json=body(lang="und")).json()                               # no ASR for 'und'
    assert [call["checks"] for call in scorer.calls] == [["audio"], ["asr", "audio", "sim"], ["asr"], ["audio", "sim"]]
    assert scorer.calls[2]["voice"] is None and out["metrics"]["checks"] == ["asr"]
    assert und["pass"] is True and und["metrics"]["checks"] == ["audio", "sim"]


def test_disabled_models_are_not_run() -> None:
    scorer = FakeScorer()
    scorer.asr, scorer.embedders = None, {}
    with client(scorer, asr=False, sim=False) as c:
        assert c.get("/health").json() | {"voices": None, "version": None, "sim_model": None} == {
            "status": "ok", "asr": False, "sim": False, "device": "cpu", "voices": None, "version": None,
            "sim_model": None}
        c.post("/v1/qc", json=body())
    assert scorer.calls[0]["checks"] == ["audio"]


def test_unknown_voice_is_404_and_engine_variants_map_to_repo_voices() -> None:
    scorer = FakeScorer()
    with client(scorer) as c:
        r = c.post("/v1/qc", json=body(voice="nobody"))
        assert r.status_code == 404 and r.json()["error"] == "unknown_voice"
        assert c.post("/v1/qc", json=body(voice="nobody-avg")).status_code == 404
        for name in ("trump-avg", "shehbaz-prompt", "trump-3f9a0c1b2d"):
            assert c.post("/v1/qc", json=body(voice=name)).status_code == 200, name
    assert [call["voice"] for call in scorer.calls] == ["trump-avg", "shehbaz-prompt", "trump-3f9a0c1b2d"]


@pytest.mark.parametrize("changes", [
    {"lang": "fr"}, {"sample_rate": 0}, {"sample_rate": "x"}, {"pcm_b64": "%%%"}, {"pcm_b64": ""},
    {"pcm_b64": base64.b64encode(b"\x01\x02\x03").decode()}, {"checks": ["asr", "nope"]}, {"text": None},
    {"pcm_b64": pcm_b64(3.0), "sample_rate": 4000},   # 18 s of samples at 4 kHz > max_seconds=10
])
def test_bad_input_is_400(changes: dict) -> None:
    with client(FakeScorer(), max_seconds=10) as c:
        r = c.post("/v1/qc", json=body(**changes))
    assert r.status_code == 400, r.text


def test_missing_fields_and_bad_json_are_400() -> None:
    with client(FakeScorer()) as c:
        assert c.post("/v1/qc", json={"voice": "trump"}).status_code == 400
        assert c.post("/v1/qc", content=b"{not json", headers={"content-type": "application/json"}).status_code == 400


def test_the_gateway_client_parses_the_answer() -> None:
    """The fields tts_gateway.qc.QCClient.check reads: pass (must be a bool), reasons, metrics."""
    with client(FakeScorer({"wer": 0.5})) as c:
        answer = c.post("/v1/qc", json=body()).json()
    assert isinstance(answer["pass"], bool) and answer["pass"] is False
    assert all(isinstance(r, str) for r in answer["reasons"]) and isinstance(answer["metrics"], dict)


def test_settings_from_env() -> None:
    s = Settings.from_env({"TTS_QC_DEVICE": "cpu", "TTS_QC_PORT": "9000", "TTS_QC_ASR": "0",
                           "TTS_QC_SIM_MODEL": "large", "TTS_QC_ASR_COMPUTE": "int8", "TTS_QC_WORKERS": "3",
                           "TTS_QC_CER_NOSPACE_UR": "0.2"})
    assert (s.device, s.port, s.asr, s.sim, s.sim_model, s.asr_compute, s.workers) == (
        "cpu", 9000, False, True, "large", "int8", 3)
    assert s.thresholds.cer_nospace_ur == 0.2
    for bad in ({"TTS_QC_DEVICE": "tpu"}, {"TTS_QC_SIM_MODEL": "huge"}, {"TTS_QC_ASR_COMPUTE": "int4"},
                {"TTS_QC_ASR": "maybe"}, {"TTS_QC_WORKERS": "0"}):
        with pytest.raises(ValueError):
            Settings.from_env(bad)
