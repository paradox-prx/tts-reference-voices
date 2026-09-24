"""The QC sidecar path (retries on a failed QC verdict, fail-open on sidecar errors), voice-relative pace, the
/v1/voices route and local-time log timestamps."""

from __future__ import annotations

import base64
import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest

from conftest import Start, make_wav
from tts_gateway import logs
from tts_gateway.backends.stub import StubBackend
from tts_gateway.qc import QCClient

TEXT = "The quick brown fox jumps over the lazy dog."  # 9 words, 35 letters
SR = 24000


class FakeQC:
    """Answers POST /v1/qc from a list of verdicts (the last one repeats); records every call."""

    def __init__(self, verdicts: list[bool | str] | None = None) -> None:
        self.verdicts = verdicts or [True]
        self.calls: list[dict[str, Any]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok", "asr": True, "sim": True, "device": "cpu"})
        body = json.loads(request.content)
        self.calls.append(body)
        verdict = self.verdicts[min(len(self.calls), len(self.verdicts)) - 1]
        if verdict == "down":
            raise httpx.ConnectError("sidecar down")
        if verdict == "500":
            return httpx.Response(500, text="boom")
        reasons = [] if verdict else ["cer_nospace>0.15", "del_run>=4"]
        return httpx.Response(200, json={"pass": verdict, "reasons": reasons, "metrics": {"cer_nospace": 0.3},
                                         "ms": {"total": 12.0}})


def install(h: Any, fake: FakeQC) -> None:
    qc = h.gw.qc
    assert isinstance(qc, QCClient)
    qc._client = httpx.AsyncClient(base_url="http://qc", transport=httpx.MockTransport(fake.handler))


Speak = Callable[..., Any]


async def speak(h: Any, **extra: Any) -> httpx.Response:
    return await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "response_format": "pcm"}
                               | extra)


async def test_qc_pass_keeps_the_first_take(start: Start) -> None:
    fake = FakeQC([True])
    async with start(qc_url="http://qc", retry_max=2) as h:
        install(h, fake)
        r = await speak(h)
        assert r.status_code == 200 and r.headers["x-tts-qc"] == "pass" and r.headers["x-tts-retries"] == "0"
        assert "x-tts-qc-reasons" not in r.headers and r.headers["x-tts-suspect"] == "0"
        call = fake.calls[0]
        assert (call["voice"], call["lang"], call["text"], call["sample_rate"]) == ("alice", "en", TEXT, SR)
        assert sorted(call["checks"]) == ["asr", "audio", "sim"]
        assert len(base64.b64decode(call["pcm_b64"])) == len(r.content)
        metrics = (await h.client.get("/metrics")).text
        assert 'tts_qc_results_total{status="pass",voice="alice"} 1.0' in metrics


async def test_qc_failure_is_retried_with_a_fresh_take(start: Start) -> None:
    fake = FakeQC([False, True])
    async with start(qc_url="http://qc", retry_max=2) as h:
        install(h, fake)
        r = await speak(h)
        assert r.headers["x-tts-retries"] == "1" and r.headers["x-tts-qc"] == "pass" and r.headers["x-tts-suspect"] == "0"
        assert len(fake.calls) == 2 and h.stub.calls == 2 + 2  # 2 warmups, 2 takes
        assert [q.seed for q in list(h.stub.requests)[-2:]] == [None, None]  # fresh sampling, no seed
        metrics = (await h.client.get("/metrics")).text
        assert 'tts_retries_total{reason="qc"} 1.0' in metrics
        assert 'tts_suspect_total{reason="qc",voice="alice"} 1.0' in metrics
        assert 'tts_qc_reasons_total{reason="cer_nospace"} 1.0' in metrics


async def test_qc_failing_every_take_returns_the_best_one_flagged(start: Start,
                                                                    caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="tts_gateway")
    fake = FakeQC([False])
    async with start(qc_url="http://qc", retry_max=1) as h:
        install(h, fake)
        r = await speak(h, **{"retries": 1})
        assert r.status_code == 200 and r.headers["x-tts-retries"] == "1"
        assert (r.headers["x-tts-suspect"], r.headers["x-tts-suspect-reason"], r.headers["x-tts-qc"]) == ("1", "qc",
                                                                                                         "fail")
        assert r.headers["x-tts-qc-reasons"] == "cer_nospace>0.15,del_run>=4"
    line = next(r.fields for r in caplog.records if r.getMessage() == "request")
    assert (line["status"], line["suspect_reason"], line["qc"]) == ("suspect", "qc", "fail")
    assert line["qc_ms"] is not None and line["qc_reasons"] == ["cer_nospace>0.15", "del_run>=4"]


async def test_qc_retry_can_be_turned_off(start: Start) -> None:
    fake = FakeQC([False])
    async with start(qc_url="http://qc", retry_max=2, retry_on="suspect,engine_error") as h:
        install(h, fake)
        r = await speak(h)
        assert r.headers["x-tts-retries"] == "0" and r.headers["x-tts-qc"] == "fail" and len(fake.calls) == 1


@pytest.mark.parametrize("failure", ["down", "500"])
async def test_qc_errors_fail_open(start: Start, failure: str) -> None:
    fake = FakeQC([failure])
    async with start(qc_url="http://qc", retry_max=2) as h:
        install(h, fake)
        r = await speak(h)
        assert r.status_code == 200 and r.headers["x-tts-qc"] == "error" and r.headers["x-tts-retries"] == "0"
        assert r.headers["x-tts-suspect"] == "0"
        metrics = (await h.client.get("/metrics")).text
        assert 'tts_qc_results_total{status="error",voice="alice"} 1.0' in metrics


async def test_pace_failures_skip_qc(start: Start) -> None:
    fake = FakeQC([True])
    async with start(stub=StubBackend(suspect_takes=1), qc_url="http://qc", retry_max=1) as h:
        install(h, fake)
        r = await speak(h)
        assert r.headers["x-tts-retries"] == "1" and r.headers["x-tts-qc"] == "pass"
        assert len(fake.calls) == 1  # only the second take (inside the pace band) went to the sidecar


async def test_streams_are_not_qc_checked(start: Start) -> None:
    fake = FakeQC([False])
    async with start(qc_url="http://qc") as h:
        install(h, fake)
        r = await speak(h, stream=True)
        assert r.status_code == 200 and "x-tts-qc" not in r.headers and not fake.calls


async def test_inline_takes_skip_speaker_similarity_and_use_the_clip_pace(start: Start) -> None:
    fake = FakeQC([True])
    ref = base64.b64encode(make_wav(3.15)).decode()  # 3.15 s / 35 letters = 0.09 s/letter, as the stub speaks
    async with start(qc_url="http://qc", allow_inline_ref=True) as h:
        install(h, fake)
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "ref_audio": ref, "ref_text": TEXT})
        assert r.status_code == 200 and r.headers["x-tts-voice"] == "inline"
        assert float(r.headers["x-tts-pace-ratio"]) == pytest.approx(1.0, abs=0.01)
        assert sorted(fake.calls[0]["checks"]) == ["asr", "audio"] and fake.calls[0]["voice"] == ""


async def test_ready_reports_the_sidecar_without_depending_on_it(start: Start) -> None:
    async with start(qc_url="http://qc") as h:
        install(h, FakeQC())
        body = (await h.client.get("/ready")).json()
        assert body["ready"] and body["qc"]["ok"] and body["qc"]["asr"]
        h.gw.qc._client = httpx.AsyncClient(base_url="http://qc", transport=httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(httpx.ConnectError("down"))))
        r = await h.client.get("/ready")
        assert r.status_code == 200 and not r.json()["qc"]["ok"]


async def test_text_in_another_language_uses_the_language_band(start: Start) -> None:
    async with start() as h:  # bilal is an Urdu voice; English text is judged by the English s/word band
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "bilal"})
        assert r.headers["x-tts-suspect"] == "0" and h.stub.requests[-1].language == "Auto"
        assert float(r.headers["x-tts-pace-ratio"]) == pytest.approx(0.35 / (0.18 * 0.9) ** 0.5, abs=0.01)


async def test_v1_voices_route(start: Start) -> None:
    async with start() as h:
        a, b = await h.client.get("/v1/voices"), await h.client.get("/v1/audio/voices")
        assert a.status_code == 200 and a.json() == b.json()
        assert [v["id"] for v in a.json()["data"]] == ["alice", "bilal"]
        assert (await h.client.get("/v1/voices", headers={"Authorization": "Bearer nope"})).status_code == 401


def test_log_timestamps_are_local_time_with_offset(monkeypatch: pytest.MonkeyPatch) -> None:
    record = logging.LogRecord("tts_gateway", logging.INFO, __file__, 1, "event", None, None)
    record.fields = {}
    stamp = datetime.fromisoformat(json.loads(logs.JsonFormatter().format(record))["ts"])  # the default zone
    assert stamp.utcoffset() is not None and stamp.utcoffset().total_seconds() == 5 * 3600  # Asia/Karachi
    monkeypatch.setattr(logs, "_tz", ZoneInfo("UTC"))
    stamp = datetime.fromisoformat(json.loads(logs.JsonFormatter().format(record))["ts"])
    assert stamp.utcoffset().total_seconds() == 0
