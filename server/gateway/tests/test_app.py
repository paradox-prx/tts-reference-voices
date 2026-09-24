from __future__ import annotations

import asyncio
import base64
import io
import logging
import struct

import pytest
import soundfile as sf

from conftest import Start, make_wav, raw_speech, wait_for, wait_ready
from tts_gateway import audio
from tts_gateway.backends.stub import StubBackend
from tts_gateway.config import Settings
from tts_gateway.textproc import max_new_tokens_for, pace_cap, voice_band

TEXT = "The quick brown fox jumps over the lazy dog."  # 9 words
WORDS = 9
SR = 24000


def pcm_seconds(spw: float, words: int = WORDS) -> float:
    return round(words * spw * SR) / SR


# ------------------------------------------------------------------------------------------------ auth + routes

async def test_auth(start: Start) -> None:
    async with start(api_key="k1, k2") as h:
        c = h.client
        body = {"input": TEXT, "voice": "alice"}
        r = await c.post("/v1/audio/speech", json=body, headers={"Authorization": ""})
        assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
        assert r.json()["error"]["code"] == "invalid_api_key"
        r = await c.post("/v1/audio/speech", json=body, headers={"Authorization": "Bearer nope"})
        assert r.status_code == 401
        assert (await c.post("/v1/audio/speech", json=body, headers={"Authorization": "Bearer k2"})).status_code == 200
        assert (await c.get("/v1/models", headers={"Authorization": "Basic k1"})).status_code == 401
        r = await c.get("/v1/models", headers={"Authorization": "Bearer k1"})
        assert r.status_code == 200 and r.json()["data"][0]["id"] == "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
        r = await c.get("/v1/audio/voices", headers={"Authorization": "Bearer k1"})
        assert [v["id"] for v in r.json()["data"]] == ["alice", "bilal"]
        assert r.json()["data"][1]["default_language"] == "Auto"
        # health, readiness and metrics need no key
        for path in ("/health", "/ready", "/metrics"):
            assert (await c.get(path, headers={"Authorization": ""})).status_code == 200


async def test_auth_disabled(start: Start) -> None:
    async with start(api_key=None, auth_disabled=True) as h:
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice"},
                                headers={"Authorization": ""})
        assert r.status_code == 200


async def test_unknown_route_uses_error_shape(start: Start) -> None:
    async with start() as h:
        r = await h.client.get("/v1/nope")
        assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


# ------------------------------------------------------------------------------------------------ validation

@pytest.mark.parametrize(("body", "status", "code"), [
    ({"input": TEXT, "voice": "nobody"}, 404, "voice_not_found"),
    ({"input": "   ", "voice": "alice"}, 400, "empty_input"),
    ({"input": "... !!", "voice": "alice"}, 400, "empty_input"),
    ({"input": "word " * 700, "voice": "alice"}, 413, "input_too_long"),
    ({"input": TEXT}, 400, "missing_voice"),
    ({"input": TEXT, "voice": "alice", "response_format": "mp3"}, 400, "invalid_request"),
    ({"input": TEXT, "voice": "alice", "instructions": "cheerful"}, 400, "invalid_request"),
    ({"input": TEXT, "voice": "alice", "retries": -1}, 400, "invalid_request"),
    ({"input": TEXT, "voice": "alice", "stream": True, "response_format": "flac"}, 400, "unsupported_parameter"),
    ({"input": TEXT, "voice": "alice", "stream": True, "speed": 1.2}, 400, "unsupported_parameter"),
    ({"input": TEXT, "voice": "alice", "stream": True, "stream_format": "sse"}, 400, "invalid_request"),
])
async def test_validation(start: Start, body: dict, status: int, code: str) -> None:
    async with start() as h:
        r = await h.client.post("/v1/audio/speech", json=body)
        assert r.status_code == status, r.text
        err = r.json()["error"]
        assert err["code"] == code and err["message"] and err["type"]
        assert h.stub.calls == 2  # the two warmups only


async def test_malformed_json(start: Start) -> None:
    async with start() as h:
        r = await h.client.post("/v1/audio/speech", content=b"{not json", headers={"Content-Type": "application/json"})
        assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_request"


async def test_body_too_large(start: Start) -> None:
    async with start() as h:
        r = await h.client.post("/v1/audio/speech", content=b"x" * (17 << 20))
        assert r.status_code == 413 and r.json()["error"]["code"] == "request_too_large"


async def test_vllm_omni_compat_fields_and_null_ref(start: Start) -> None:
    """bench_tts.py / vLLM-Omni clients send task_type and stream_format; nulls count as absent."""
    async with start() as h:
        body = {"input": TEXT, "voice": "alice", "task_type": "Base", "language": "English", "ref_audio": None,
                "ref_text": None, "stream": True, "stream_format": "audio"}
        assert (await h.client.post("/v1/audio/speech", json=body)).status_code == 200


# ------------------------------------------------------------------------------------------------ formats + headers

async def test_wav_output_labelled_and_headers(start: Start) -> None:
    async with start() as h:
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice"},
                                headers={"X-Request-Id": "abc-123"})
        assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
        assert audio.AI_LABEL.encode() in r.content[: r.content.index(b"data")]
        data, sr = sf.read(io.BytesIO(r.content), dtype="int16")
        assert sr == SR and len(data) / SR == pytest.approx(pcm_seconds(0.35))
        hd = r.headers
        assert hd["x-request-id"] == "abc-123" and hd["x-ai-generated"] == "true" and hd["x-tts-voice"] == "alice"
        assert float(hd["x-tts-audio-seconds"]) == pytest.approx(pcm_seconds(0.35), abs=1e-3)
        assert hd["x-tts-retries"] == "0" and hd["x-tts-suspect"] == "0"
        assert float(hd["x-tts-queue-ms"]) >= 0 and float(hd["x-tts-engine-ms"]) >= 0
        req = h.stub.requests[-1]
        assert req.language == "English" and req.response_format == "pcm" and req.request_id == "abc-123"
        band = voice_band(0.09, Settings(auth_disabled=True))  # conftest's pace for alice
        assert req.max_new_tokens == min(max_new_tokens_for(WORDS), pace_cap(band, WORDS, 35, 1.2)) == 111
        assert req.temperature is None and req.seed is None
        # an unusable client id is replaced
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice"},
                                headers={"X-Request-Id": "has spaces"})
        assert r.headers["x-request-id"] != "has spaces" and len(r.headers["x-request-id"]) == 32


async def test_pcm_and_flac_outputs(start: Start) -> None:
    async with start() as h:
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "bilal", "response_format": "pcm"})
        assert r.headers["content-type"] == "audio/pcm" and len(r.content) == 2 * round(WORDS * 0.35 * SR)
        assert h.stub.requests[-1].language == "Auto"
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "response_format": "flac"})
        assert r.headers["content-type"] == "audio/flac"
        with sf.SoundFile(io.BytesIO(r.content)) as f:
            assert f.format == "FLAC" and f.samplerate == SR and f.comment == audio.AI_LABEL
            assert f.frames == round(WORDS * 0.35 * SR)


async def test_request_overrides_reach_backend(start: Start) -> None:
    async with start(length_cap=False) as h:
        body = {"input": TEXT, "voice": "bilal", "language": "urdu", "temperature": 0.7, "top_k": 30, "top_p": 0.9,
                "seed": 7, "speed": 1.1}
        assert (await h.client.post("/v1/audio/speech", json=body)).status_code == 200
        req = h.stub.requests[-1]
        got = (req.language, req.temperature, req.top_k, req.top_p, req.seed, req.speed)
        assert got == ("Auto", 0.7, 30, 0.9, 7, 1.1)
        assert req.max_new_tokens is None  # length cap off
        await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "max_new_tokens": 500})
        assert h.stub.requests[-1].max_new_tokens == 500


async def test_request_log_line(start: Start, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="tts_gateway")
    async with start() as h:
        for rid, voice in (("log-1", "alice"), ("log-2", "ghost")):
            await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": voice}, headers={"X-Request-Id": rid})
    lines = {r.fields["request_id"]: r.fields for r in caplog.records if r.getMessage() == "request"}
    ok, missing = lines["log-1"], lines["log-2"]
    assert set(ok) == {"request_id", "voice", "lang", "chars", "words", "stream", "format", "status", "http_status",
                       "queue_ms", "engine_ms", "total_ms", "audio_s", "rtf", "retries", "suspect", "suspect_reason",
                       "pace_ratio", "qc", "qc_reasons", "qc_ms", "error"}
    assert ok["pace_ratio"] == pytest.approx(1.0, abs=0.01) and ok["qc"] is None
    assert (ok["voice"], ok["lang"], ok["words"], ok["status"], ok["http_status"]) == ("alice", "en", WORDS, "ok", 200)
    assert ok["audio_s"] == pytest.approx(pcm_seconds(0.35), abs=1e-3) and ok["rtf"] is not None
    assert (missing["voice"], missing["status"], missing["http_status"]) == ("ghost", "voice_not_found", 404)
    assert any(r.getMessage() == "startup" for r in caplog.records)
    assert any(r.getMessage() == "shutdown" for r in caplog.records)


# ------------------------------------------------------------------------------------------------ streaming

async def test_streaming_wav_and_pcm(start: Start) -> None:
    text = " ".join(["word"] * 20)  # 7 s of stub audio: 4 chunks of up to 2 s
    async with start() as h:
        r = await h.client.post("/v1/audio/speech", json={"input": text, "voice": "alice", "stream": True})
        assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
        assert r.headers["x-ai-generated"] == "true" and r.headers["x-tts-retries"] == "0"
        assert "x-tts-audio-seconds" not in r.headers  # not known up front
        header = audio.wav_header(SR)
        assert r.content.startswith(header)
        assert struct.unpack("<I", r.content[4:8])[0] == 0xFFFFFFFF
        pcm, sr = audio.wav_to_pcm(r.content)
        assert sr == SR and len(pcm) == len(r.content) - len(header) == 2 * round(20 * 0.35 * SR)
        r = await h.client.post("/v1/audio/speech",
                                json={"input": text, "voice": "alice", "stream": True, "response_format": "pcm"})
        assert r.headers["content-type"] == "audio/pcm" and len(r.content) == 2 * round(20 * 0.35 * SR)
        assert h.gw.admission.inflight == 0


async def test_split_for_per_call_ceiling(start: Start) -> None:
    text = "One two three. Four five six. Seven eight."
    async with start(stub=StubBackend(max_seconds_per_call=3.0)) as h:
        before = h.stub.calls
        r = await h.client.post("/v1/audio/speech", json={"input": text, "voice": "alice", "response_format": "pcm"})
        assert h.stub.calls - before == 3
        assert [q.text for q in list(h.stub.requests)[-3:]] == ["One two three.", "Four five six.", "Seven eight."]
        gap = 2 * round(0.2 * SR)
        assert len(r.content) == 2 * (2 * round(3 * 0.35 * SR) + round(2 * 0.35 * SR)) + 2 * gap
        r = await h.client.post("/v1/audio/speech",
                                json={"input": text, "voice": "alice", "response_format": "pcm", "stream": True})
        assert len(r.content) == 2 * (2 * round(3 * 0.35 * SR) + round(2 * 0.35 * SR)) + 2 * gap


# ------------------------------------------------------------------------------------------------ admission

async def test_queue_full_429(start: Start) -> None:
    async with start(stub=StubBackend(base_latency_s=0.3), max_inflight=1, max_queue=1) as h:
        body = {"input": TEXT, "voice": "alice"}
        results = await asyncio.gather(*(h.client.post("/v1/audio/speech", json=body) for _ in range(3)))
        assert sorted(r.status_code for r in results) == [200, 200, 429]
        rejected = next(r for r in results if r.status_code == 429)
        assert int(rejected.headers["retry-after"]) >= 1 and rejected.json()["error"]["type"] == "rate_limit_error"
        assert rejected.json()["error"]["code"] == "queue_full" and rejected.headers["x-request-id"]
        assert h.gw.admission.inflight == 0 and h.gw.admission.waiting == 0


async def test_queue_timeout_503(start: Start) -> None:
    async with start(stub=StubBackend(base_latency_s=0.4), max_inflight=1, max_queue=4, queue_timeout_s=0.1) as h:
        body = {"input": TEXT, "voice": "alice"}
        results = await asyncio.gather(*(h.client.post("/v1/audio/speech", json=body) for _ in range(2)))
        assert sorted(r.status_code for r in results) == [200, 503]
        timed_out = next(r for r in results if r.status_code == 503)
        assert timed_out.json()["error"]["code"] == "queue_timeout" and "retry-after" in timed_out.headers


async def test_slots_released_when_client_task_cancelled(start: Start) -> None:
    async with start(stub=StubBackend(base_latency_s=5.0), max_inflight=1, max_queue=2, warmup=False) as h:
        adm = h.gw.admission
        body = {"input": TEXT, "voice": "alice"}
        running = asyncio.create_task(h.client.post("/v1/audio/speech", json=body))
        await wait_for(lambda: adm.inflight == 1)
        queued = asyncio.create_task(h.client.post("/v1/audio/speech", json=body))
        await wait_for(lambda: adm.waiting == 1)
        for task in (queued, running):
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert adm.inflight == 0 and adm.waiting == 0
        assert 'tts_requests_total{status="cancelled",voice="alice"} 2.0' in (await h.client.get("/metrics")).text


async def test_disconnect_cancels_non_streaming_request(start: Start) -> None:
    async with start(stub=StubBackend(base_latency_s=5.0), warmup=False) as h:
        gone = asyncio.Event()
        call = asyncio.create_task(raw_speech(h.app, {"input": TEXT, "voice": "alice"}, gone))
        await wait_for(lambda: h.gw.admission.inflight == 1)
        gone.set()
        async with asyncio.timeout(1):  # far sooner than the 5 s engine call
            messages = await call
        assert messages[0]["status"] == 499
        assert h.gw.admission.inflight == 0


async def test_disconnect_mid_stream_closes_backend_stream(start: Start) -> None:
    stub = StubBackend(latency_per_audio_s=0.2)  # 0.4 s per 2 s chunk
    async with start(stub=stub, warmup=False) as h:
        gone, first_audio = asyncio.Event(), asyncio.Event()
        payload = {"input": " ".join(["word"] * 40), "voice": "alice", "stream": True}
        call = asyncio.create_task(raw_speech(h.app, payload, gone, first_audio))
        await asyncio.wait_for(first_audio.wait(), 2)
        assert h.gw.admission.inflight == 1
        gone.set()
        async with asyncio.timeout(1):
            messages = await call
        assert messages[0]["status"] == 200
        assert not any(m["type"] == "http.response.body" and not m.get("more_body") for m in messages)
        assert stub.closed_early == 1 and h.gw.admission.inflight == 0


# ------------------------------------------------------------------------------------------------ retries

async def test_retry_on_suspect_picks_good_take(start: Start) -> None:
    async with start(stub=StubBackend(suspect_takes=1), retry_max=1) as h:
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "response_format": "pcm"})
        assert r.headers["x-tts-retries"] == "1" and r.headers["x-tts-suspect"] == "0"
        assert len(r.content) == 2 * round(WORDS * 0.35 * SR)  # the second, good take
        metrics = (await h.client.get("/metrics")).text
        assert 'tts_retries_total{reason="too_short"} 1.0' in metrics
        assert 'tts_suspect_total{reason="too_short",voice="alice"} 1.0' in metrics


async def test_retries_exhausted_return_best_suspect_take(start: Start) -> None:
    async with start(stub=StubBackend(suspect_takes=10), retry_max=2) as h:
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "response_format": "pcm"})
        assert r.status_code == 200
        assert r.headers["x-tts-retries"] == "2" and r.headers["x-tts-suspect"] == "1"
        assert len(r.content) == 2 * round(WORDS * 0.15 * SR)  # 0.15 s/word is the closest of 0.05, 0.10, 0.15
        # per-request override, clamped to TTS_RETRY_MAX
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "retries": 0})
        assert r.headers["x-tts-retries"] == "0" and r.headers["x-tts-suspect"] == "1"
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "retries": 9})
        assert r.headers["x-tts-retries"] == "2"


async def test_seeded_retry_changes_seed(start: Start) -> None:
    async with start(stub=StubBackend(suspect_takes=1), retry_max=1) as h:
        await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "seed": 5})
        assert [q.seed for q in list(h.stub.requests)[-2:]] == [5, 6]


async def test_retry_on_suspect_can_be_disabled(start: Start) -> None:
    async with start(stub=StubBackend(suspect_takes=1), retry_max=1, retry_on="engine_error") as h:
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice"})
        assert r.headers["x-tts-retries"] == "0" and r.headers["x-tts-suspect"] == "1"


@pytest.mark.parametrize(("kind", "retry_max", "status", "code", "retries"), [
    ("unavailable", 1, 503, "engine_unavailable", None),
    ("timeout", 1, 504, "engine_timeout", None),
    ("failure", 1, 502, "engine_error", None),
    ("bad_request", 1, 400, "engine_rejected", None),
    ("retryable", 0, 502, "engine_error", None),
    ("retryable", 1, 200, None, "1"),
])
async def test_engine_error_mapping(start: Start, kind: str, retry_max: int, status: int, code: str | None,
                                    retries: str | None) -> None:
    async with start(stub=StubBackend(fail_takes=1, fail_kind=kind), retry_max=retry_max, warmup=False) as h:
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice"})
        assert r.status_code == status
        if code:
            assert r.json()["error"]["code"] == code
        else:
            assert r.headers["x-tts-retries"] == retries
        metrics = (await h.client.get("/metrics")).text
        assert f'tts_engine_errors_total{{kind="{"failure" if kind == "retryable" else kind}"}} 1.0' in metrics
        assert h.gw.admission.inflight == 0


async def test_engine_timeout_enforced_by_gateway(start: Start) -> None:
    async with start(stub=StubBackend(base_latency_s=2.0), request_timeout_s=0.1, warmup=False) as h:
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice"})
        assert r.status_code == 504


async def test_stream_error_before_first_byte(start: Start) -> None:
    async with start(stub=StubBackend(fail_takes=1, fail_kind="unavailable"), warmup=False) as h:
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "stream": True})
        assert r.status_code == 503 and h.gw.admission.inflight == 0


# ------------------------------------------------------------------------------------------------ readiness + metrics

async def test_ready_only_after_registration_and_warmup(start: Start) -> None:
    async with start(stub=StubBackend(base_latency_s=0.3), ready=False) as h:
        r = await h.client.get("/ready")
        assert r.status_code == 503 and r.json()["ready"] is False
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice"})
        assert r.status_code == 503 and r.json()["error"]["code"] == "not_ready"
        await wait_ready(h.client)
        assert h.stub.registered == {"alice", "bilal"}
        assert {q.request_id for q in h.stub.requests} == {"warmup-alice", "warmup-bilal"}
        h.stub.healthy = False  # engine died
        assert (await h.client.get("/ready")).status_code == 503


async def test_bringup_waits_for_engine(start: Start) -> None:
    stub = StubBackend()

    async def sick() -> dict:
        return {"ok": False}

    stub.health = sick  # type: ignore[method-assign]
    async with start(stub=stub, ready=False, warmup=False) as h:
        await asyncio.sleep(0.1)
        r = await h.client.get("/ready")
        assert r.status_code == 503 and "not healthy" in r.json()["reason"]
        del stub.health  # healthy again; the next bring-up attempt (after 1 s) succeeds
        await wait_ready(h.client, timeout_s=3)


async def test_metrics_exposed(start: Start) -> None:
    async with start() as h:
        await h.client.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice"})
        r = await h.client.get("/metrics")
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
        text = r.text
        assert 'tts_requests_total{status="ok",voice="alice"} 1.0' in text
        assert f'tts_audio_seconds_total{{voice="alice"}} {pcm_seconds(0.35)}' in text
        for name in ("tts_request_seconds_bucket", "tts_queue_wait_seconds_count", "tts_inflight 0.0",
                     "tts_queue_depth 0.0", "# TYPE tts_retries_total counter", "# TYPE tts_suspect_total counter",
                     "# TYPE tts_engine_errors_total counter"):
            assert name in text, name


# ------------------------------------------------------------------------------------------------ inline + capabilities

async def test_inline_ref_disabled_by_default(start: Start) -> None:
    async with start() as h:
        data_url = "data:audio/wav;base64," + base64.b64encode(make_wav(2.0)).decode()
        r = await h.client.post("/v1/audio/speech", json={"input": TEXT, "ref_audio": data_url, "ref_text": "Hi."})
        assert r.status_code == 400 and r.json()["error"]["code"] == "inline_ref_disabled"


async def test_inline_ref_accepts_base64_only(start: Start) -> None:
    wav = make_wav(2.0)
    b64 = base64.b64encode(wav).decode()
    async with start(allow_inline_ref=True) as h:
        async def post(ref_audio: str, **extra: object):
            body = {"input": TEXT, "ref_audio": ref_audio, "ref_text": "Reference words.", **extra}
            return await h.client.post("/v1/audio/speech", json=body)

        for url in ("http://169.254.169.254/latest/a.wav", "https://example.com/a.wav", "file:///etc/passwd",
                    "data:text/plain;base64," + b64, "data:audio/wav," + b64):
            r = await post(url)
            assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_ref_audio", url
        assert (await post("not base64 at all!")).status_code == 400
        assert (await post(base64.b64encode(b"RIFF junk").decode())).status_code == 400
        assert (await post(base64.b64encode(make_wav(0.5)).decode())).status_code == 400  # too short
        r = await post(base64.b64encode(bytes(11 << 20)).decode())
        assert r.status_code == 413 and r.json()["error"]["code"] == "ref_audio_too_large"
        assert (await post("data:audio/wav;base64," + b64, voice="alice")).status_code == 400

        r = await post("data:audio/wav;base64," + b64)
        assert r.status_code == 200 and r.headers["x-tts-voice"] == "inline"
        req = h.stub.requests[-1]
        assert req.voice is None and req.ref_audio == wav and req.ref_text == "Reference words."
        assert req.language == "English"
        r = await post(b64)
        assert r.status_code == 200


async def test_repetition_penalty_needs_capability(start: Start) -> None:
    body = {"input": TEXT, "voice": "alice", "repetition_penalty": 1.1}
    async with start() as h:
        r = await h.client.post("/v1/audio/speech", json=body)
        assert r.status_code == 400 and "repetition_penalty" in r.json()["error"]["message"]
    async with start(stub=StubBackend(repetition_penalty=True)) as h:
        assert (await h.client.post("/v1/audio/speech", json=body)).status_code == 200
        assert h.stub.requests[-1].repetition_penalty == 1.1
