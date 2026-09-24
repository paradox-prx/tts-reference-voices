"""VllmOmniBackend against the fake vLLM-Omni engine (tests/fake_vllm_omni.py) served on a real local port."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
import soundfile as sf

from conftest import API_KEY, make_wav, wait_for, wait_ready
from fake_vllm_omni import FakeEngine, bind, serve, streaming_wav_header, tone
from fake_vllm_omni import create_app as create_fake
from tts_gateway import audio
from tts_gateway.app import create_app
from tts_gateway.backends.base import (
    BackendError,
    EngineBadRequest,
    EngineFailure,
    EngineTimeout,
    EngineUnavailable,
    SynthesisRequest,
)
from tts_gateway.backends.vllm_omni import CONSENT_PREFIX, VllmOmniBackend, _PcmReader, engine_voice_name
from tts_gateway.config import Settings
from tts_gateway.voices import Voice, VoiceRegistry

TEXT = "The quick brown fox jumps over the lazy dog."  # 9 words: 3.15 s at the fake's 0.35 s/word = 39 frames
FRAME_BYTES = 2 * 1920
TEXT_BYTES = 39 * FRAME_BYTES
LONG_TEXT = " ".join(["word"] * 60)  # 262 frames: eleven streamed chunks


@dataclass
class Engine:
    fake: FakeEngine
    url: str

    @property
    def last(self) -> dict[str, Any]:
        return self.fake.calls[-1].payload


Make = Callable[..., VllmOmniBackend]


@pytest.fixture
async def engine() -> AsyncIterator[Engine]:
    fake = FakeEngine()
    async with serve(create_fake(fake)) as url:
        yield Engine(fake, url)


@pytest.fixture
async def make(engine: Engine, voices_dir: Path) -> AsyncIterator[Make]:
    """make(**settings) -> a backend for the fake engine; closed after the test."""
    backends: list[VllmOmniBackend] = []

    def _make(**settings: Any) -> VllmOmniBackend:
        s = Settings(**{"auth_disabled": True, "engine_url": engine.url, "voices_dir": voices_dir} | settings)
        backends.append(VllmOmniBackend(s, VoiceRegistry.load(s.voices_dir)))
        return backends[-1]

    yield _make
    for backend in backends:
        await backend.close()


def voice(voices_dir: Path, voice_id: str) -> Voice:
    found = VoiceRegistry.load(voices_dir).get(voice_id)
    assert found is not None
    return found


def speech(v: Voice | None, text: str = TEXT, **fields: Any) -> SynthesisRequest:
    fields.setdefault("language", v.language if v else "English")
    return SynthesisRequest(text=text, voice=v, request_id="t-1", **fields)


def rewrite_reference(voices_dir: Path, voice_id: str, *, text: str | None = None,
                      seconds: float | None = None) -> None:
    folder = voices_dir / voice_id / "references"
    refs = json.loads((folder / "references.json").read_text())
    entry = refs["qwen3-tts"]
    if seconds is not None:
        wav = make_wav(seconds)
        (folder / entry["file"]).write_bytes(wav)
        entry["sha256"] = hashlib.sha256(wav).hexdigest()
    if text is not None:
        entry["text"] = text
    (folder / "references.json").write_text(json.dumps(refs, ensure_ascii=False))


# ------------------------------------------------------------------------------------------------ the fake itself

async def test_fake_engine_mimics_the_engine(engine: Engine, voices_dir: Path) -> None:
    alice = voice(voices_dir, "alice")
    async with httpx.AsyncClient(base_url=engine.url) as c:
        base = {"input": TEXT, "task_type": "Base", "ref_audio": alice.data_url, "ref_text": alice.ref_text}
        r = await c.post("/v1/audio/speech", json=base | {"language": "Urdu"})
        assert r.status_code == 400 and "Invalid language 'Urdu'" in r.json()["error"]["message"]
        # top-level sampling fields are ignored silently; extra_params reach the talker
        r = await c.post("/v1/audio/speech", json=base | {"temperature": 0.1, "bogus": 1, "language": "english",
                                                          "extra_params": {"top_k": 7}})
        assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
        assert r.headers["x-vllm-omni-output-tokens"] == "39"
        assert engine.fake.calls[-1].sampling["temperature"] == 0.9
        assert engine.fake.calls[-1].sampling["top_k"] == 7
        # a raw wav stream starts with the 0xFFFFFFFF header; a pcm stream has none
        r = await c.post("/v1/audio/speech", json=base | {"stream": True, "stream_format": "audio"})
        assert r.content[:4] == b"RIFF" and r.content[40:44] == b"\xff\xff\xff\xff"
        assert len(r.content) == 44 + TEXT_BYTES
        r = await c.post("/v1/audio/speech", json=base | {"stream": True, "stream_format": "audio",
                                                          "response_format": "pcm"})
        assert len(r.content) == TEXT_BYTES
        r = await c.delete("/v1/audio/voices/nobody")
        assert r.status_code == 404 and r.json()["error"]["type"] == "NotFoundError"


# ------------------------------------------------------------------------------------------------ voice registration

async def test_registration_is_content_addressed_and_idempotent(engine: Engine, make: Make, voices_dir: Path) -> None:
    alice, bilal = voice(voices_dir, "alice"), voice(voices_dir, "bilal")
    name = engine_voice_name(alice)
    assert name == f"alice-{alice.ref_sha256[:10]}"
    backend = make()
    for v in (alice, bilal):
        await backend.register_voice(v)
    assert sorted(engine.fake.voices) == sorted([name, engine_voice_name(bilal)])
    stored = engine.fake.voices[name]
    assert stored["consent"] == CONSENT_PREFIX + "alice" and stored["ref_text"] == alice.ref_text
    assert engine.fake.uploads == 2
    await backend.register_voice(alice)  # again: found on the engine, nothing uploaded
    restarted = make()  # a gateway restart finds the stored voices
    for v in (alice, bilal):
        await restarted.register_voice(v)
    await restarted.synthesize(speech(alice))
    assert engine.fake.uploads == 2 and engine.fake.deletes == 0
    assert engine.last["voice"] == name and "ref_audio" not in engine.last and "ref_text" not in engine.last


async def test_reference_changes_replace_the_engine_voice(engine: Engine, make: Make, voices_dir: Path) -> None:
    old = voice(voices_dir, "alice")
    await make().register_voice(old)
    # a voice uploaded by someone else under a similar name is never touched
    async with httpx.AsyncClient(base_url=engine.url) as c:
        files = {"audio_sample": ("x.wav", make_wav(2.0), "audio/wav")}
        r = await c.post("/v1/audio/voices", files=files, data={"name": "alice-0123456789", "consent": "benchmark"})
        assert r.status_code == 200 and r.json()["success"] is True
    # new transcript, same clip: same name, re-uploaded
    rewrite_reference(voices_dir, "alice", text="A corrected transcript.")
    await make().register_voice(voice(voices_dir, "alice"))
    assert engine.fake.voices[engine_voice_name(old)]["ref_text"] == "A corrected transcript."
    assert (engine.fake.uploads, engine.fake.deletes) == (3, 1)
    # new clip: a new name; the superseded upload of ours is deleted
    rewrite_reference(voices_dir, "alice", seconds=3.0)
    new = voice(voices_dir, "alice")
    await make().register_voice(new)
    assert engine_voice_name(new) != engine_voice_name(old)
    assert sorted(engine.fake.voices) == sorted(["alice-0123456789", engine_voice_name(new)])


async def test_health_checks_engine_and_heals_lost_voices(engine: Engine, make: Make, voices_dir: Path) -> None:
    backend = make()
    health = await backend.health()  # first call: registers every voice
    assert health["ok"] and health["registered"] == ["alice", "bilal"]
    health = await backend.health()
    assert health["ok"] and "registered" not in health
    engine.fake.voices.pop(engine_voice_name(voice(voices_dir, "bilal")))  # e.g. a wiped SPEAKER_SAMPLES_DIR
    health = await backend.health()
    assert health["ok"] and health["registered"] == ["bilal"] and len(engine.fake.voices) == 2
    engine.fake.healthy = False
    health = await backend.health()
    assert not health["ok"] and "EngineUnavailable" in health["error"]
    assert (await make(voice_mode="inline").health())["ok"] is False
    engine.fake.healthy = True
    engine.fake.voices.clear()
    assert (await make(voice_mode="inline").health())["ok"]  # inline mode needs no stored voices
    assert not engine.fake.voices


async def test_request_reregisters_a_voice_the_engine_lost(engine: Engine, make: Make, voices_dir: Path) -> None:
    alice = voice(voices_dir, "alice")
    backend = make()
    await backend.register_voice(alice)
    engine.fake.voices.clear()
    result = await backend.synthesize(speech(alice))
    assert len(result.pcm) == TEXT_BYTES
    assert [c.outcome for c in engine.fake.calls] == ["rejected", "ok"] and engine.fake.uploads == 2


async def test_voice_is_registered_on_first_use(engine: Engine, make: Make, voices_dir: Path) -> None:
    alice = voice(voices_dir, "alice")
    backend = make()
    await asyncio.gather(*(backend.synthesize(speech(alice)) for _ in range(4)))
    assert engine.fake.uploads == 1 and [c.outcome for c in engine.fake.calls] == ["ok"] * 4


# ------------------------------------------------------------------------------------------------ payload

async def test_payload_defaults(engine: Engine, make: Make, voices_dir: Path) -> None:
    alice, bilal = voice(voices_dir, "alice"), voice(voices_dir, "bilal")
    backend = make()
    result = await backend.synthesize(speech(alice))
    assert engine.last == {"input": TEXT, "task_type": "Base", "language": "English", "response_format": "pcm",
                           "voice": engine_voice_name(alice), "extra_params": {"temperature": 0.9, "top_k": 50}}
    sampling = engine.fake.calls[-1].sampling
    assert sampling == {"temperature": 0.9, "top_k": 50, "top_p": 1.0, "repetition_penalty": 1.05, "seed": None,
                        "max_tokens": 192}
    assert result.sample_rate == 24000 and len(result.pcm) == TEXT_BYTES and result.codec_frames == 39
    assert result.meta["input_tokens"] > 0
    await backend.synthesize(speech(bilal, "یہ ایک آزمائش ہے"))
    assert engine.last["language"] == "Auto"
    # without gateway defaults the engine's own (deploy YAML) sampling applies
    await make(default_temperature=None, default_top_k=None).synthesize(speech(alice))
    assert "extra_params" not in engine.last


async def test_payload_overrides(engine: Engine, make: Make, voices_dir: Path) -> None:
    alice = voice(voices_dir, "alice")
    result = await make().synthesize(speech(alice, temperature=0.7, top_k=20, top_p=0.8, seed=7, max_new_tokens=300,
                                            speed=1.25))
    payload = engine.last
    assert payload["extra_params"] == {"temperature": 0.7, "top_k": 20, "top_p": 0.8}
    assert (payload["seed"], payload["max_new_tokens"], payload["speed"]) == (7, 300, 1.25)
    assert engine.fake.calls[-1].sampling == {"temperature": 0.7, "top_k": 20, "top_p": 0.8,
                                                   "repetition_penalty": 1.05, "seed": 7, "max_tokens": 300}
    assert len(result.pcm) == round(39 * 1920 / 1.25) * 2


async def test_repetition_penalty_needs_the_patched_engine(engine: Engine, make: Make, voices_dir: Path) -> None:
    alice = voice(voices_dir, "alice")
    stock = make()
    assert not stock.capabilities.per_request_repetition_penalty
    with pytest.raises(EngineBadRequest, match="TTS_ENGINE_PER_REQUEST_RP"):
        await stock.synthesize(speech(alice, repetition_penalty=1.2))
    assert not engine.fake.calls
    engine.fake.patched = True
    patched = make(engine_per_request_rp=True)
    assert patched.capabilities.per_request_repetition_penalty
    await patched.synthesize(speech(alice, repetition_penalty=1.2))
    assert engine.last["extra_params"] == {"temperature": 0.9, "top_k": 50, "repetition_penalty": 1.2}
    assert engine.fake.calls[-1].sampling["repetition_penalty"] == 1.2


async def test_inline_references(engine: Engine, make: Make, voices_dir: Path) -> None:
    alice = voice(voices_dir, "alice")
    await make(voice_mode="inline").synthesize(speech(alice))
    assert engine.last["ref_audio"] == alice.data_url and engine.last["ref_text"] == alice.ref_text
    assert "voice" not in engine.last and not engine.fake.voices
    clip = make_wav(1.5)
    await make().synthesize(speech(None, ref_audio=clip, ref_text="Inline transcript."))
    assert engine.last["ref_audio"] == "data:audio/wav;base64," + base64.b64encode(clip).decode()
    assert engine.last["ref_text"] == "Inline transcript." and not engine.fake.voices


# ------------------------------------------------------------------------------------------------ streaming

async def test_streaming(engine: Engine, make: Make, voices_dir: Path) -> None:
    alice = voice(voices_dir, "alice")
    engine.fake.chunk_delay_s = 0.05
    chunks = [c async for c in make().stream(speech(alice, LONG_TEXT, max_new_tokens=1000))]
    assert engine.last["stream"] is True and engine.last["stream_format"] == "audio"
    assert engine.last["response_format"] == "pcm" and engine.last["max_new_tokens"] == 1000
    assert "speed" not in engine.last
    assert len(chunks[0]) == FRAME_BYTES  # the first chunk holds one codec frame
    assert all(len(c) % 2 == 0 for c in chunks) and b"".join(chunks) == tone(262)
    assert engine.fake.calls[-1].outcome == "ok"
    with pytest.raises(EngineBadRequest, match="speed"):
        await anext(make().stream(speech(alice, speed=1.2)))


async def test_closing_a_stream_aborts_the_engine_request(engine: Engine, make: Make, voices_dir: Path) -> None:
    engine.fake.chunk_delay_s = 0.3
    stream = make().stream(speech(voice(voices_dir, "alice"), LONG_TEXT))
    assert len(await anext(stream)) == FRAME_BYTES
    await stream.aclose()
    await wait_for(lambda: engine.fake.calls[-1].outcome == "aborted", 3.0)


async def test_cancelling_a_request_aborts_the_engine_request(engine: Engine, make: Make, voices_dir: Path) -> None:
    engine.fake.fail("hang")
    task = asyncio.create_task(make().synthesize(speech(voice(voices_dir, "alice"))))
    await wait_for(lambda: bool(engine.fake.calls) and engine.fake.calls[-1].outcome == "running")
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await wait_for(lambda: engine.fake.calls[-1].outcome == "aborted", 3.0)


def test_pcm_reader_drops_a_wav_header_and_keeps_whole_samples() -> None:
    pcm = tone(3)
    for data in (streaming_wav_header() + pcm, pcm):
        reader, out, pos = _PcmReader(), [], 0
        for size in (1, 3, 7, 2, 40, 1, 999, 5, 10**6):  # splits inside the header and inside samples
            piece = reader.feed(data[pos:pos + size])
            assert len(piece) % 2 == 0
            out.append(piece)
            pos += size
        assert b"".join(out) == pcm and reader.pcm_bytes == len(pcm)
    wrong_rate = streaming_wav_header().replace((24000).to_bytes(4, "little"), (16000).to_bytes(4, "little"), 1)
    with pytest.raises(EngineFailure, match="16000 Hz"):
        _PcmReader().feed(wrong_rate + pcm)


# ------------------------------------------------------------------------------------------------ errors

@pytest.mark.parametrize(("failure", "error", "retryable"), [
    ("codec_limit", EngineFailure, True),  # HTTP 500 after the engine's own retry
    ("internal", EngineFailure, True),  # "Speech generation failed: ..." arrives as a 400
    ("server_error", EngineFailure, True),
    ("unavailable", EngineUnavailable, False),
    ("empty", EngineFailure, True),
])
async def test_engine_failures(engine: Engine, make: Make, voices_dir: Path, failure: str,
                               error: type[BackendError], retryable: bool) -> None:
    engine.fake.fail(failure)
    with pytest.raises(error) as caught:
        await make().synthesize(speech(voice(voices_dir, "alice")))
    assert type(caught.value) is error and caught.value.retryable is retryable


@pytest.mark.parametrize("failure", ["codec_limit", "internal", "unavailable", "empty"])
async def test_stream_failures_are_retryable(engine: Engine, make: Make, voices_dir: Path, failure: str) -> None:
    engine.fake.fail(failure)
    received = 0
    with pytest.raises(EngineFailure) as caught:
        async for chunk in make().stream(speech(voice(voices_dir, "alice"))):
            received += len(chunk)
    assert caught.value.retryable
    assert received == (TEXT_BYTES if failure == "codec_limit" else 0)  # a runaway fails after its audio


async def test_codec_budget_and_bad_requests(engine: Engine, make: Make, voices_dir: Path) -> None:
    alice = voice(voices_dir, "alice")
    backend = make()
    with pytest.raises(EngineFailure, match="codec EOS") as caught:  # a cap set by us: the engine does not retry
        await backend.synthesize(speech(alice, max_new_tokens=10))
    assert caught.value.retryable
    with pytest.raises(EngineFailure):
        async for _ in backend.stream(speech(alice, max_new_tokens=10)):
            pass
    with pytest.raises(EngineBadRequest, match="Invalid language 'Urdu'") as bad:
        await backend.synthesize(speech(alice, language="Urdu"))
    assert not bad.value.retryable


async def test_unreachable_slow_and_unauthorised_engine(engine: Engine, make: Make, voices_dir: Path) -> None:
    alice = voice(voices_dir, "alice")
    with bind() as sock:
        closed_port = sock.getsockname()[1]
    down = make(engine_url=f"http://127.0.0.1:{closed_port}", voice_mode="inline")
    with pytest.raises(EngineUnavailable):
        await down.synthesize(speech(alice))
    with pytest.raises(EngineUnavailable):
        await anext(down.stream(speech(alice)))
    assert not (await down.health())["ok"]
    engine.fake.fail("hang")
    with pytest.raises(EngineTimeout):
        await make(request_timeout_s=0.3).synthesize(speech(alice))
    await wait_for(lambda: engine.fake.calls[-1].outcome == "aborted", 3.0)
    engine.fake.api_key = "engine-key"
    health = await make().health()
    assert not health["ok"] and "TTS_ENGINE_API_KEY" in health["error"]
    with pytest.raises(EngineFailure) as caught:
        await make(voice_mode="inline").synthesize(speech(alice))
    assert not caught.value.retryable
    keyed = make(engine_api_key="engine-key")
    assert (await keyed.health())["ok"]
    assert len((await keyed.synthesize(speech(alice))).pcm) == TEXT_BYTES


def _raise(exc: Exception) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc
    return handler


def _wav(sample_rate: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, [0.0] * sample_rate, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


@pytest.mark.parametrize(("handler", "error", "match"), [
    (lambda r: httpx.Response(404, json={"detail": "Not Found"}), EngineFailure, "404: Not Found"),
    (lambda r: httpx.Response(401, json={"error": "Unauthorized"}), EngineFailure, "TTS_ENGINE_API_KEY"),
    (lambda r: httpx.Response(200, json={"ok": True}), EngineFailure, "not audio"),
    (lambda r: httpx.Response(422, text="plain text"), EngineBadRequest, "plain text"),
    (_raise(httpx.RemoteProtocolError("peer closed")), EngineFailure, "connection failed"),
    (_raise(httpx.ReadTimeout("slow")), EngineTimeout, "timed out"),
    (_raise(httpx.ConnectError("refused")), EngineUnavailable, "cannot connect"),
])
async def test_http_edge_cases(make: Make, voices_dir: Path, handler: Callable[[httpx.Request], httpx.Response],
                               error: type[BackendError], match: str) -> None:
    backend = make(voice_mode="inline")
    await backend.close()
    backend._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://engine")
    with pytest.raises(error, match=match):
        await backend.synthesize(speech(voice(voices_dir, "alice")))


async def test_a_wav_body_is_accepted(make: Make, voices_dir: Path) -> None:
    backend = make(voice_mode="inline")
    await backend.close()
    for rate in (24000, 16000):
        wav = _wav(rate)
        backend._client = httpx.AsyncClient(base_url="http://engine", transport=httpx.MockTransport(
            lambda r, wav=wav: httpx.Response(200, content=wav, headers={"content-type": "audio/wav"})))
        result = await backend.synthesize(speech(voice(voices_dir, "alice")))
        assert result.sample_rate == rate and result.pcm == bytes(2 * rate) and result.codec_frames is None
        await backend.close()


# ------------------------------------------------------------------------------------------------ gateway end to end

@asynccontextmanager
async def gateway(engine: Engine, voices_dir: Path, **settings: Any) -> AsyncIterator[httpx.AsyncClient]:
    s = Settings(api_key=API_KEY, backend="vllm_omni", engine_url=engine.url, voices_dir=voices_dir, **settings)
    app = create_app(s)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://gateway",
                                     headers={"Authorization": f"Bearer {API_KEY}"}) as client:
            await wait_ready(client, 10.0)
            yield client


async def test_gateway_over_the_engine(engine: Engine, voices_dir: Path) -> None:
    alice = voice(voices_dir, "alice")
    async with gateway(engine, voices_dir) as c:
        # bring-up registered both voices and warmed each one up
        assert sorted(engine.fake.voices) == sorted([engine_voice_name(alice),
                                                     engine_voice_name(voice(voices_dir, "bilal"))])
        assert [call.outcome for call in engine.fake.calls] == ["ok", "ok"]
        r = await c.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice"})
        assert r.status_code == 200, r.text
        assert r.headers["x-ai-generated"] == "true" and r.headers["x-tts-retries"] == "0"
        assert audio.AI_LABEL.encode() in r.content
        pcm, rate = audio.wav_to_pcm(r.content)
        assert rate == 24000 and pcm == tone(39)
        payload = engine.last
        assert payload["voice"] == engine_voice_name(alice) and payload["language"] == "English"
        assert payload["extra_params"] == {"temperature": 0.9, "top_k": 50}
        assert payload["max_new_tokens"] > 39 and "seed" not in payload  # the gateway's length cap, no seed
        r = await c.post("/v1/audio/speech", json={"input": "یہ ایک آزمائش ہے", "voice": "bilal",
                                                   "response_format": "pcm", "temperature": 0.6, "seed": 3})
        assert r.status_code == 200 and engine.last["language"] == "Auto"
        assert engine.last["extra_params"]["temperature"] == 0.6 and engine.last["seed"] == 3
        r = await c.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "stream": True})
        assert r.status_code == 200 and audio.wav_to_pcm(r.content) == (tone(39), 24000)
        assert engine.last["stream_format"] == "audio"


async def test_gateway_retries_and_rejections(engine: Engine, voices_dir: Path) -> None:
    async with gateway(engine, voices_dir) as c:
        engine.fake.fail("codec_limit")
        r = await c.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice"})
        assert r.status_code == 200 and r.headers["x-tts-retries"] == "1"
        engine.fake.fail("codec_limit", "codec_limit")
        r = await c.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice"})
        assert r.status_code == 502 and r.json()["error"]["code"] == "engine_error"
        r = await c.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "language": "Hindi"})
        assert r.status_code == 400 and r.json()["error"]["code"] == "engine_rejected"
        assert "Invalid language 'Hindi'" in r.json()["error"]["message"]
        r = await c.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "repetition_penalty": 1.1})
        assert r.status_code == 400 and r.json()["error"]["code"] == "unsupported_parameter"
    engine.fake.patched = True
    async with gateway(engine, voices_dir, engine_per_request_rp=True) as c:
        r = await c.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice", "repetition_penalty": 1.1})
        assert r.status_code == 200 and engine.fake.calls[-1].sampling["repetition_penalty"] == 1.1


async def test_gateway_readiness_follows_the_engine(engine: Engine, voices_dir: Path) -> None:
    async with gateway(engine, voices_dir, warmup=False) as c:
        engine.fake.healthy = False
        r = await c.get("/ready")
        assert r.status_code == 503 and "unhealthy" in r.json()["reason"]
        r = await c.post("/v1/audio/speech", json={"input": TEXT, "voice": "alice"})
        assert r.status_code == 200  # /health going red does not fail requests the engine still serves
        engine.fake.healthy = True
        engine.fake.voices.clear()  # the engine lost its voice store: the readiness check uploads them again
        assert (await c.get("/ready")).status_code == 200 and len(engine.fake.voices) == 2
