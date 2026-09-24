"""HTTP API: health, voices, speech responses and labels, validation errors, voice upload, logs."""

from __future__ import annotations

import asyncio
import json
import logging
import threading

import numpy as np
import pytest

import engine as eng
from conftest import data_url, wav_bytes
from fake_qwen_tts import SPF, FakeTTS
from wavlabel import AI_LABEL, wav_comment, wav_pcm16


# ------------------------------------------------------------------------------------------------ health / startup

async def test_health_503_while_loading_then_200(make_harness):
    gate = threading.Event()
    fake = FakeTTS()

    def loader(args):
        gate.wait(10)
        return fake, {"model_path": "fake"}

    async with make_harness(loader=loader, wait_ready=False) as h:
        r = await h.client.get("/health")
        assert r.status_code == 503 and r.json() == {"status": "loading"}
        r = await h.speech(input="hi there", voice="alpha")
        assert r.status_code == 503 and r.json()["error"]["message"] == "model is not ready"
        gate.set()
        for _ in range(300):
            if (await h.client.get("/health")).status_code == 200:
                break
            await asyncio.sleep(0.01)
        r = await h.client.get("/health")
        assert r.status_code == 200 and r.json() == {"status": "healthy"}


async def test_startup_failure_is_unhealthy(make_harness):
    def loader(args):
        raise RuntimeError("no weights")

    async with make_harness(loader=loader, wait_ready=False) as h:
        for _ in range(300):
            if h.st.error:
                break
            await asyncio.sleep(0.01)
        r = await h.client.get("/health")
        assert r.status_code == 503 and r.json()["status"] == "unhealthy" and "no weights" in r.json()["error"]
        r = await h.speech(input="hi", voice="alpha")
        assert r.status_code == 503 and "startup failed" in r.json()["error"]["message"]


async def test_warmup_and_info(make_harness):
    fake = FakeTTS()
    async with make_harness(fake=fake, warmup=True) as h:
        info = (await h.client.get("/v1/baseline/info")).json()
    assert info["ready"] and info["startup"]["warmup"]["codec_frames"] == 3  # "Hello." = 1 word -> 3 frames
    assert fake.calls[0]["kwargs"]["max_new_tokens"] == 24
    assert {v["voice"] for v in info["startup"]["voices"]} == {"alpha", "beta"}
    assert info["engine"]["defaults"] == {"temperature": 0.9, "top_k": 50, "top_p": 1.0, "repetition_penalty": 1.05}
    assert info["versions"]["qwen-tts"] == "0.1.1"
    assert info["startup"]["languages"][0] == "Auto" and "English" in info["startup"]["languages"]


# ------------------------------------------------------------------------------------------------ speech

async def test_speech_wav_label_headers(make_harness):
    async with make_harness() as h:
        r = await h.client.post("/v1/audio/speech", headers={"X-Request-Id": "req-123"},
                                json={"input": "one two three four", "voice": "alpha", "task_type": "Base"})
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "audio/wav"
        assert r.headers["x-ai-generated"] == "true"
        assert r.headers["x-request-id"] == "req-123"
        assert r.headers["x-baseline-batch-size"] == "1"
        assert r.headers["x-baseline-codec-frames"] == "12"
        assert r.headers["x-baseline-finish-reason"] == "stop"
        assert r.headers["x-baseline-prompt-cache"] == "hit"          # repo voices are pinned at startup
        assert r.headers["x-baseline-text-tokens"] == "4"
        assert r.headers["x-baseline-max-new-tokens"] == "192"        # min(max(192, 12 x 4), 4096)
        assert float(r.headers["x-baseline-queue-ms"]) >= 0
        assert wav_comment(r.content) == AI_LABEL
        pcm, sr = wav_pcm16(r.content)
        assert sr == 24000 and len(pcm) == 12 * SPF * 2
        call = h.fake.calls[-1]
        assert call["languages"] == ["English"] and call["texts"] == ["one two three four"]
        assert call["non_streaming_mode"] is False
        assert call["kwargs"] == {"max_new_tokens": 192, "temperature": 0.9, "top_k": 50, "top_p": 1.0,
                                  "repetition_penalty": 1.05}


async def test_speech_pcm(make_harness):
    async with make_harness() as h:
        r = await h.speech(input="a b", voice="ALPHA", response_format="pcm")
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/pcm" and r.headers["x-ai-generated"] == "true"
        assert len(r.content) == 6 * SPF * 2
        assert np.abs(np.frombuffer(r.content, "<i2")).max() > 1000


async def test_language_defaults_and_urdu_maps_to_auto(make_harness, caplog):
    caplog.set_level(logging.WARNING, logger="qwen_tts_baseline")
    async with make_harness() as h:
        assert (await h.speech(input="x y", voice="beta")).status_code == 200            # ur voice -> Auto
        assert (await h.speech(input="x y", voice="beta", language="Urdu")).status_code == 200
        assert (await h.speech(input="x y", voice="beta", language="urdu")).status_code == 200
        assert (await h.speech(input="x y", voice="alpha", language="english")).status_code == 200
        assert (await h.speech(input="x y", voice="alpha", language="AUTO")).status_code == 200
        langs = [c["languages"][0] for c in h.fake.calls]
        assert langs == ["Auto", "Auto", "Auto", "English", "Auto"]
    mapped = [r for r in caplog.records if r.getMessage() == "language_mapped"]
    assert len(mapped) == 1  # logged once


async def test_inline_ref_audio(make_harness):
    async with make_harness() as h:
        ref = wav_bytes(2.5, sr=16000)
        r = await h.speech(input="p q r", ref_audio=data_url(ref), ref_text="the reference words", language="English")
        assert r.status_code == 200, r.text
        assert r.headers["x-baseline-prompt-cache"] == "miss"
        assert h.fake.prompt_calls[-1]["sr"] == 16000 and h.fake.prompt_calls[-1]["ref_text"] == "the reference words"
        # plain base64 (no data: prefix) is accepted too, and hits the cache (same audio bytes and transcript)
        r = await h.speech(input="p q r", ref_audio=data_url(ref).split(",", 1)[1], ref_text="the reference words")
        assert r.status_code == 200 and r.headers["x-baseline-prompt-cache"] == "hit"
        # x-vector-only inline needs no ref_text
        r = await h.speech(input="p q r", ref_audio=data_url(ref), x_vector_only_mode=True)
        assert r.status_code == 200 and h.fake.calls[-1]["items"][0].x_vector_only_mode is True


@pytest.mark.parametrize("body, status, needle", [
    ({"input": "hi", "voice": "alpha", "stream": True}, 400, "streaming not supported by the qwen-tts baseline"),
    ({"input": "   ", "voice": "alpha"}, 400, "Input text cannot be empty"),
    ({"voice": "alpha"}, 400, "input"),
    ({"input": "hi", "voice": "nobody"}, 400, "Unknown voice 'nobody'"),
    ({"input": "hi"}, 400, "requires 'ref_audio'"),
    ({"input": "hi", "voice": "alpha", "language": "Klingon"}, 400, "Invalid language 'Klingon'"),
    ({"input": "hi", "voice": "alpha", "response_format": "mp3"}, 400, "response_format 'mp3'"),
    ({"input": "hi", "voice": "alpha", "task_type": "CustomVoice"}, 400, "task_type 'CustomVoice'"),
    ({"input": "hi", "voice": "alpha", "max_new_tokens": 0}, 400, "at least 1"),
    ({"input": "hi", "voice": "alpha", "max_new_tokens": 4097}, 400, "cannot exceed 4096"),
    ({"input": "hi", "voice": "alpha", "speed": 1.5}, 400, "speed"),
    ({"input": "hi", "voice": "alpha", "word_timestamps": True}, 400, "word_timestamps"),
    ({"input": "hi", "speaker_embedding": [0.1] * 8}, 400, "speaker_embedding"),
    ({"input": "hi", "voice": "alpha", "extra_params": {"temperature": 0}}, 400, "temperature must be > 0"),
    ({"input": "hi", "voice": "alpha", "extra_params": {"top_k": 1.5}}, 400, "top_k must be a number (integer)"),
    ({"input": "hi", "voice": "alpha", "extra_params": {"top_p": 1.5}}, 400, "top_p must be in (0, 1]"),
    ({"input": "hi", "voice": "alpha", "extra_params": {"temperature": "hot"}}, 400, "temperature must be a number"),
    ({"input": "hi", "ref_audio": "https://example.com/a.wav", "ref_text": "x"}, 400, "'https:' URLs are not"),
    ({"input": "hi", "ref_audio": "file:///etc/passwd", "ref_text": "x"}, 400, "'file:' URLs are not supported"),
    ({"input": "hi", "ref_audio": "data:audio/wav,abc", "ref_text": "x"}, 400, "must be base64"),
    ({"input": "hi", "ref_audio": "!!!notbase64!!!", "ref_text": "x"}, 400, "not valid base64"),
    ({"input": "hi", "ref_audio": data_url(b"RIFFjunk"), "ref_text": "x"}, 400, "could not decode audio"),
    ({"input": "hi", "ref_audio": data_url(wav_bytes(0.5)), "ref_text": "x"}, 400, "too short"),
    ({"input": "hi", "ref_audio": data_url(wav_bytes(31.0, sr=8000)), "ref_text": "x"}, 400, "too long"),
    ({"input": "hi", "ref_audio": data_url(wav_bytes(2.0))}, 400, "requires non-empty 'ref_text'"),
    ({"input": "hi", "ref_audio": ["a", "b"], "ref_text": "x"}, 400, "ref_audio"),
])
async def test_validation_errors(make_harness, body, status, needle):
    async with make_harness() as h:
        body.setdefault("task_type", "Base")
        r = await h.client.post("/v1/audio/speech", json=body)
        assert r.status_code == status, r.text
        err = r.json()["error"]
        assert needle in err["message"], err
        assert err["code"] == status and err["type"] == "BadRequestError"
        assert "x-ai-generated" not in r.headers and r.headers["x-request-id"]
        assert h.fake.calls == []


async def test_non_json_body(make_harness):
    async with make_harness() as h:
        r = await h.client.post("/v1/audio/speech", content=b"not json", headers={"content-type": "application/json"})
        assert r.status_code == 400 and "JSON" in r.json()["error"]["message"]
        r = await h.client.post("/v1/audio/speech", json=[1, 2])
        assert r.status_code == 400


async def test_unknown_fields_ignored_and_logged_once(make_harness, caplog):
    caplog.set_level(logging.WARNING, logger="qwen_tts_baseline")
    async with make_harness() as h:
        for _ in range(3):
            r = await h.speech(input="a b", voice="alpha", temperature=0.1, sample_rate=8000, model="whatever",
                               extra_params={"foo": 1})
            assert r.status_code == 200
        # top-level temperature is ignored (vLLM-Omni drops it too): the defaults were used
        assert h.fake.calls[-1]["kwargs"]["temperature"] == 0.9
    unknown = sorted(r.fields["field"] for r in caplog.records if r.getMessage() == "unknown_field_ignored")
    assert unknown == ["sample_rate", "temperature"]
    assert [r.fields["field"] for r in caplog.records if r.getMessage() == "extra_param_ignored"] == ["foo"]
    assert [r.fields["field"] for r in caplog.records if r.getMessage() == "field_ignored"] == ["model"]


async def test_extra_params_and_non_streaming_mode_pass_through(make_harness):
    async with make_harness() as h:
        r = await h.speech(input="a b", voice="alpha", non_streaming_mode=True,
                           extra_params={"temperature": 0.7, "top_k": 30, "top_p": 0.8, "repetition_penalty": 1.2})
        assert r.status_code == 200
        call = h.fake.calls[-1]
        assert call["non_streaming_mode"] is True
        assert call["kwargs"] == {"max_new_tokens": 192, "temperature": 0.7, "top_k": 30, "top_p": 0.8,
                                  "repetition_penalty": 1.2}


async def test_request_log_line(make_harness, caplog):
    caplog.set_level(logging.INFO, logger="qwen_tts_baseline")
    async with make_harness() as h:
        await h.speech(input="a b c", voice="alpha")
        await h.speech(input="", voice="alpha")
    reqs = [r for r in caplog.records if r.getMessage() == "request"]
    assert len(reqs) == 2
    ok, bad = reqs[0].fields, reqs[1].fields
    assert ok["http_status"] == 200 and ok["codec_frames"] == 9 and ok["batch_size"] == 1 and ok["voice"] == "alpha"
    assert ok["audio_s"] == round(9 * SPF / 24000, 3) and ok["rtf"] > 0 and ok["lang"] == "English"
    assert bad["http_status"] == 400 and bad["status"] == "error"
    import qwen_tts_server as srv

    line = json.loads(srv.JsonFormatter().format(reqs[0]))
    assert line["event"] == "request" and line["ts"].endswith("+05:00")


# ------------------------------------------------------------------------------------------------ voices

async def test_list_voices(make_harness):
    async with make_harness() as h:
        r = await h.client.get("/v1/audio/voices")
        assert r.json() == {"voices": ["alpha", "beta"], "uploaded_voices": []}


async def test_upload_use_delete_voice(make_harness):
    async with make_harness() as h:
        files = {"audio_sample": ("mine.wav", wav_bytes(2.0, sr=22050), "audio/wav")}
        r = await h.client.post("/v1/audio/voices", files=files,
                                data={"name": "Bench-Alpha", "consent": "benchmark", "ref_text": "my words"})
        assert r.status_code == 200, r.text
        v = r.json()["voice"]
        assert r.json()["success"] is True and v["name"] == "Bench-Alpha" and v["ref_text"] == "my words"
        assert v["mode"] == "icl" and v["sample_rate"] == 22050
        listing = (await h.client.get("/v1/audio/voices")).json()
        assert "Bench-Alpha" in listing["voices"]
        assert listing["uploaded_voices"][0]["name"] == "Bench-Alpha"
        assert listing["uploaded_voices"][0]["ref_text"] == "my words"
        r = await h.speech(input="a b", voice="bench-alpha")          # case-insensitive, like vLLM-Omni
        assert r.status_code == 200 and r.headers["x-baseline-prompt-cache"] == "miss"
        assert h.fake.calls[-1]["languages"] == ["Auto"]
        r = await h.speech(input="a b", voice="Bench-Alpha")
        assert r.headers["x-baseline-prompt-cache"] == "hit"
        # re-upload overwrites (vLLM-Omni evicts the old one)
        r = await h.client.post("/v1/audio/voices", files={"audio_sample": ("x.wav", wav_bytes(3.0), "audio/wav")},
                                data={"name": "bench-alpha", "consent": "c2"})
        assert r.status_code == 200 and r.json()["voice"]["mode"] == "x_vector_only"
        assert len((await h.client.get("/v1/audio/voices")).json()["uploaded_voices"]) == 1
        r = await h.client.delete("/v1/audio/voices/BENCH-ALPHA")
        assert r.status_code == 200 and r.json()["success"] is True
        r = await h.client.delete("/v1/audio/voices/bench-alpha")
        assert r.status_code == 404 and r.json()["error"]["type"] == "NotFoundError"
        r = await h.speech(input="a b", voice="bench-alpha")
        assert r.status_code == 400


@pytest.mark.parametrize("files, data, needle", [
    ({"audio_sample": ("a.wav", wav_bytes(2.0), "audio/wav")}, {"name": "x"}, "consent"),
    ({"audio_sample": ("a.wav", wav_bytes(2.0), "audio/wav")}, {"consent": "c"}, "name"),
    (None, {"name": "x", "consent": "c"}, "Either 'audio_sample' or 'speaker_embedding'"),
    (None, {"name": "x", "consent": "c", "speaker_embedding": "[0.1]"}, "speaker_embedding uploads"),
    ({"audio_sample": ("a.wav", wav_bytes(0.4), "audio/wav")}, {"name": "x", "consent": "c"}, "too short"),
    ({"audio_sample": ("a.wav", wav_bytes(2.0), "audio/wav")}, {"name": "a/b", "consent": "c"}, "Invalid voice name"),
    ({"audio_sample": ("a.wav", wav_bytes(2.0), "audio/wav")}, {"name": "Alpha", "consent": "c"}, "built-in"),
    ({"audio_sample": ("a.wav", b"\0" * (10 * 1024 * 1024 + 1), "audio/wav")}, {"name": "x", "consent": "c"},
     "exceeds maximum limit of 10MB"),
])
async def test_upload_errors(make_harness, files, data, needle):
    async with make_harness() as h:
        r = await h.client.post("/v1/audio/voices", files=files or {"dummy": ("d", b"", "text/plain")}, data=data)
        assert r.status_code == 400, r.text
        assert needle in r.json()["error"]["message"]


async def test_voice_and_ref_audio_voice_wins(make_harness):
    async with make_harness() as h:
        r = await h.speech(input="a b", voice="alpha", ref_audio=data_url(wav_bytes(2.0)), ref_text="zz")
        assert r.status_code == 200 and r.headers["x-baseline-prompt-cache"] == "hit"
        assert h.fake.calls[-1]["items"][0].ref_text == "hello world this is the reference"


async def test_voice_x_vector_only_mode(make_harness):
    async with make_harness() as h:
        r = await h.speech(input="a b", voice="alpha", x_vector_only_mode=True)
        assert r.status_code == 200 and r.headers["x-baseline-prompt-cache"] == "miss"
        item = h.fake.calls[-1]["items"][0]
        assert item.x_vector_only_mode is True and item.ref_code is None


async def test_model_called_from_one_worker_thread(make_harness):
    fake = FakeTTS(delay=0.01)
    async with make_harness("--max-batch", "2", fake=fake) as h:
        rs = await asyncio.gather(*(h.speech(input=f"w {i}", voice="alpha") for i in range(6)))
        assert all(r.status_code == 200 for r in rs)
    assert len(fake.threads) == 1 and threading.get_ident() not in fake.threads


def test_engine_reference_parsing():
    assert eng.decode_ref_audio_string(data_url(b"abc")) == b"abc"
    assert eng.decode_ref_audio_string("  YWJj\n ") == b"abc"
    with pytest.raises(ValueError, match="'http:' URLs"):
        eng.decode_ref_audio_string("http://x/y.wav")
    with pytest.raises(ValueError, match="'c:' URLs"):
        eng.decode_ref_audio_string("C:\\voices\\a.wav")
