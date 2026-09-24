"""A small stand-in for the vLLM-Omni 0.28 speech server running Qwen3-TTS Base, for tests and gateway-only runs.

It mirrors what the gateway relies on in vllm_omni/entrypoints/openai (0.28.0): the /v1/audio/voices routes and their
response shapes (api_server.py:1468-1662, serving_speech.py upload_voice/delete_voice), and /v1/audio/speech parsing,
validation and output (protocol/audio.py, tts_adapters/qwen3_tts.py validate, serving_speech.py create_speech).
Unknown request fields are ignored; languages outside codec_language_id + Auto (e.g. 'Urdu') are a 400; extra_params
sets temperature/top_p/top_k (repetition_penalty only when `patched`, like engine/patches); raw streaming sends a
0xFFFFFFFF WAV header only for response_format=wav; non-streaming answers carry the X-VLLM-OMNI-* usage headers; a
client disconnect aborts the request. Audio is a quiet tone lasting `spw` seconds per word, in 1920-sample codec
frames (12.5 per second); a take longer than its codec budget fails like a runaway without EOS. Failures can be
injected into the next requests with FakeEngine.fail(). The audio it makes is synthetic, never speech.

    python tests/fake_vllm_omni.py --port 18091 [--api-key KEY] [--spw 0.35] [--chunk-delay 0.05] [--patched]
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import math
import random
import re
import socket
import struct
from collections import deque
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field, ValidationError
from starlette.types import ASGIApp, Receive, Scope, Send

SAMPLE_RATE = 24000
FRAME_SAMPLES = 1920  # one 12.5 Hz codec frame
INITIAL_CHUNK_FRAMES, CHUNK_FRAMES = 1, 25  # deploy/qwen3_tts.yaml connector settings
MAX_TOKENS = 4096
LANGUAGES = frozenset({"Auto", "Chinese", "English", "Japanese", "Korean", "German", "French", "Russian",
                       "Portuguese", "Spanish", "Italian"})  # tts_adapters/base.py DEFAULT_TTS_LANGUAGES
DEFAULT_SAMPLING = {"temperature": 0.9, "top_k": 50, "top_p": 1.0, "repetition_penalty": 1.05}  # stage-0 YAML
ALLOWED_MIME = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/ogg", "audio/aac", "audio/flac", "audio/webm",
                "audio/mp4"}
FAILURES = ("codec_limit", "internal", "server_error", "unavailable", "empty", "hang")


class SpeechBody(BaseModel):
    """The OpenAICreateSpeechRequest fields the fake reads; like the original, other fields are ignored."""

    input: str
    model: str | None = None
    voice: str | None = None
    response_format: Literal["wav", "pcm", "flac", "mp3", "opus"] = "wav"
    speed: float | None = Field(1.0, ge=0.25, le=4.0)
    stream: bool = False
    stream_format: Literal["sse", "audio"] | None = None
    task_type: Literal["CustomVoice", "VoiceDesign", "Base"] | None = None
    language: str | None = None
    ref_audio: str | None = None
    ref_text: str | None = None
    max_new_tokens: int | None = Field(None, ge=1)
    seed: int | None = None
    extra_params: dict[str, Any] | None = None


@dataclass
class Call:
    payload: dict[str, Any]  # the JSON body as received
    sampling: dict[str, Any] = field(default_factory=dict)  # effective stage-0 sampling parameters
    outcome: str = "rejected"  # rejected | running | ok | aborted | failed:<kind>


@dataclass
class FakeEngine:
    spw: float = 0.35  # seconds of audio per word
    chunk_delay_s: float = 0.0  # between streamed chunks
    latency_s: float = 0.0  # before a non-streaming answer
    api_key: str | None = None
    patched: bool = False  # per-request extra_params.repetition_penalty
    healthy: bool = True
    voices: dict[str, dict[str, Any]] = field(default_factory=dict)  # uploaded voices by lowercase name
    calls: list[Call] = field(default_factory=list)  # every /v1/audio/speech request
    uploads: int = 0
    deletes: int = 0
    _failures: deque[str] = field(default_factory=deque)
    _clock: int = 0

    def fail(self, *kinds: str) -> None:
        """The next len(kinds) accepted speech requests fail like this, in order (see FAILURES)."""
        unknown = set(kinds) - set(FAILURES)
        if unknown:
            raise ValueError(f"unknown failure kinds {sorted(unknown)}; known: {FAILURES}")
        self._failures.extend(kinds)

    def next_failure(self) -> str | None:
        return self._failures.popleft() if self._failures else None

    def timestamp(self) -> int:
        self._clock += 1
        return self._clock


def error(message: str, status: int = 400, err_type: str | None = None) -> JSONResponse:
    """vLLM's ErrorResponse shape."""
    err_type = err_type or ("BadRequestError" if status < 500 else "InternalServerError")
    return JSONResponse({"error": {"message": message, "type": err_type, "param": None, "code": status}}, status)


def tone(frames: int, speed: float = 1.0) -> bytes:
    n = round(frames * FRAME_SAMPLES / speed)
    t = np.arange(n) / SAMPLE_RATE
    return (0.2 * 32767 * np.sin(2 * np.pi * 220 * t)).astype("<i2").tobytes()


def streaming_wav_header() -> bytes:
    """serving_speech.py _create_wav_header: 44 bytes, sizes 0xFFFFFFFF."""
    return struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 0xFFFFFFFF, b"WAVE", b"fmt ", 16, 1, 1, SAMPLE_RATE,
                       2 * SAMPLE_RATE, 2, 16, b"data", 0xFFFFFFFF)


def codec_limit_message(budget: int) -> str:
    return (f"Qwen3-TTS Base did not emit codec EOS before its token budget ({budget}/{budget} codec tokens); "
            "the generated audio is incomplete.")


def validate(engine: FakeEngine, body: SpeechBody) -> str | None:
    """Qwen3TTSAdapter.validate plus the streaming checks of create_speech, for the Base model."""
    streaming = body.stream or body.stream_format is not None
    if streaming and body.response_format not in ("pcm", "wav"):
        return f"Streaming requires response_format='pcm' or 'wav'. Got response_format='{body.response_format}'."
    if streaming and body.stream_format != "audio":
        return "the fake engine streams raw audio only (stream_format='audio'); SSE is not implemented"
    if body.task_type is None and (body.ref_audio is not None or body.ref_text is not None):
        body.task_type = "Base"
    if body.voice is not None:
        body.voice = body.voice.lower()
    task_type = body.task_type or "CustomVoice"
    if not body.input.strip():
        return "Input text cannot be empty"
    if body.language is not None:
        body.language = body.language.title()
        if body.language not in LANGUAGES:
            return f"Invalid language '{body.language}'. Supported: {', '.join(sorted(LANGUAGES))}"
    if task_type == "CustomVoice":
        return ("This model does not support CustomVoice task (no speakers configured). Use task_type='Base' with "
                "ref_audio/ref_text for voice cloning, or use a CustomVoice model.")
    if task_type == "Base":
        if body.voice is None and body.ref_audio is None:
            return "Base task requires 'ref_audio' or 'speaker_embedding' for voice cloning"
        if body.voice is not None and body.voice not in engine.voices and body.ref_audio is None:
            return f"Base task with built-in speaker '{body.voice}' requires 'ref_audio' for voice cloning"
        if body.ref_audio is not None and not re.match(r"(?i)(https?|data|file):", body.ref_audio):
            return "ref_audio must be a URL (http/https), base64 data URL (data:...), or file URI (file://...)"
        if body.voice not in engine.voices and not (body.ref_text or "").strip():
            return ("Base task requires non-empty 'ref_text' (transcript of the reference audio) unless "
                    "'x_vector_only_mode' is enabled")
    elif body.ref_text is not None:
        return "'ref_text' is only valid for Base task"
    if body.max_new_tokens is not None and body.max_new_tokens > MAX_TOKENS:
        return f"max_new_tokens cannot exceed {MAX_TOKENS}"
    if streaming and body.speed not in (None, 1.0):
        return "Streaming is not supported with speed adjustment. Use a non-streaming request or remove the speed parameter."
    return None


def sampling_for(engine: FakeEngine, body: SpeechBody, words: int) -> dict[str, Any]:
    """Stage-0 SamplingParams after extra_params (serving_speech.py:3079-3095) and the codec budget."""
    sampling: dict[str, Any] = dict(DEFAULT_SAMPLING, seed=body.seed)
    extra = body.extra_params or {}
    for name in ("temperature", "top_p", "top_k"):
        if (value := extra.get(name)) is not None:
            sampling[name] = value
    if engine.patched and (penalty := extra.get("repetition_penalty")) is not None:
        if isinstance(penalty, bool) or not isinstance(penalty, (int, float)) or not 0 < penalty < math.inf:
            raise ValueError("extra_params.repetition_penalty must be a finite number > 0")
        sampling["repetition_penalty"] = float(penalty)
    # tts_adapters/qwen3_tts.py: min(max(192, 12 x text tokens), 4096) unless the request sets max_new_tokens
    sampling["max_tokens"] = body.max_new_tokens or min(max(192, 12 * words), MAX_TOKENS)
    return sampling


async def until_disconnect(request: Request, work: Awaitable[Response], call: Call) -> Response:
    """vLLM's with_cancellation: a client disconnect cancels the handler (and so aborts the engine request)."""
    task = asyncio.ensure_future(work)

    async def disconnected() -> None:
        while (await request.receive())["type"] != "http.disconnect":
            pass

    listener = asyncio.ensure_future(disconnected())
    try:
        await asyncio.wait({task, listener}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        listener.cancel()
    if task.done():
        return task.result()
    task.cancel()
    call.outcome = "aborted"
    return Response(status_code=499)


class ApiKeyAuth:
    """Pure ASGI, like vLLM's AuthenticationMiddleware: /v1 routes need the bearer key; /health does not."""

    def __init__(self, app: ASGIApp, engine: FakeEngine) -> None:
        self.app, self.engine = app, engine

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        key = self.engine.api_key
        if key and scope["type"] == "http" and scope["path"].startswith("/v1") and \
                dict(scope["headers"]).get(b"authorization") != f"Bearer {key}".encode():
            await JSONResponse({"error": "Unauthorized"}, 401)(scope, receive, send)
            return
        await self.app(scope, receive, send)


def create_app(engine: FakeEngine) -> FastAPI:
    app = FastAPI(title="fake vllm-omni", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine = engine
    app.add_middleware(ApiKeyAuth, engine=engine)

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error(str(exc.errors()[:3]))

    @app.get("/health")
    async def health() -> JSONResponse:
        if engine.healthy:
            return JSONResponse({"status": "healthy"})
        return JSONResponse({"status": "unhealthy"}, 503)

    @app.get("/v1/audio/voices")
    async def list_voices() -> dict[str, Any]:
        uploaded = []
        for info in engine.voices.values():
            entry = {k: info[k] for k in ("name", "consent", "created_at", "file_size", "mime_type")}
            entry |= {"embedding_source": "audio", "embedding_dim": None}
            if info.get("ref_text"):
                entry["ref_text"] = info["ref_text"]
            uploaded.append(entry)
        return {"voices": sorted(set(engine.voices) | {"default"}), "uploaded_voices": uploaded}

    @app.post("/v1/audio/voices")
    async def upload_voice(audio_sample: UploadFile | None = File(None), speaker_embedding: str | None = Form(None),
                           consent: str = Form(...), name: str = Form(...), ref_text: str | None = Form(None),
                           speaker_description: str | None = Form(None)) -> JSONResponse:
        if speaker_embedding is not None:
            return error("the fake engine does not implement speaker_embedding uploads")
        if audio_sample is None:
            return error("Either 'audio_sample' or 'speaker_embedding' must be provided")
        name = name.strip()
        if not name or name in (".", "..") or any(c in name for c in "/\\\x00"):
            return error(f"Invalid voice name {name!r}: must be non-empty, no path separators or NUL")
        content = await audio_sample.read()
        if len(content) > 10 * 1024 * 1024:
            return error(f"File size exceeds maximum limit of 10MB. Got {len(content)} bytes.")
        mime = audio_sample.content_type or "audio/wav"
        if mime == "application/octet-stream":
            mime = "audio/wav"
        if mime not in ALLOWED_MIME:
            return error(f"Unsupported MIME type: {mime}. Allowed: {ALLOWED_MIME}")
        try:
            info = sf.info(io.BytesIO(content))
        except sf.LibsndfileError as exc:
            return error(f"Could not decode audio file: {exc}")
        if not 1.0 <= info.duration <= 30.0:
            return error(f"Reference audio lasts {info.duration:.1f}s; 1-30 s supported")
        if name.lower() not in engine.voices and len(engine.voices) >= 1000:
            return error("Uploaded voice limit reached (1000).")
        ref_text = (ref_text or "").strip() or None
        voice = {"name": name, "consent": consent, "created_at": engine.timestamp(), "mime_type": mime,
                 "file_size": len(content), "ref_text": ref_text, "seconds": info.duration}
        engine.voices[name.lower()] = voice  # the default policy overwrites an upload of the same name
        engine.uploads += 1
        result = {k: voice[k] for k in ("name", "consent", "created_at", "mime_type", "file_size")}
        if ref_text:
            result["ref_text"] = ref_text
        return JSONResponse({"success": True, "voice": result})

    @app.delete("/v1/audio/voices/{name}")
    async def delete_voice(name: str) -> JSONResponse:
        if engine.voices.pop(name.lower(), None) is None:
            return error(f"Voice '{name}' not found", 404, "NotFoundError")
        engine.deletes += 1
        return JSONResponse({"success": True, "message": f"Voice '{name}' deleted successfully"})

    @app.post("/v1/audio/speech")
    async def speech(request: Request) -> Response:
        raw = await request.body()
        try:
            payload = SpeechBody.model_validate_json(raw)
        except ValidationError as exc:
            return error(str(exc.errors()[:3]))
        call = Call(payload=json.loads(raw))
        engine.calls.append(call)
        if problem := validate(engine, payload):
            return error(problem)
        words = max(1, len(re.findall(r"\w+", payload.input)))
        try:
            call.sampling = sampling_for(engine, payload, words)
        except ValueError as exc:
            return error(str(exc))
        call.outcome = "running"
        failure = engine.next_failure()
        frames = max(1, round(words * engine.spw * 12.5))
        budget = call.sampling["max_tokens"]
        runaway = failure == "codec_limit" or frames > budget
        if payload.stream_format == "audio":
            return StreamingResponse(stream(engine, call, payload, failure, min(frames, budget), runaway),
                                     media_type=f"audio/{payload.response_format}")
        return await until_disconnect(request, answer(engine, call, payload, failure, frames, runaway), call)

    return app


async def answer(engine: FakeEngine, call: Call, body: SpeechBody, failure: str | None, frames: int,
                 runaway: bool) -> Response:
    """A non-streaming answer. The engine retries a runaway once itself, unless seed or max_new_tokens is set; the
    fake's takes are deterministic, so that retry fails the same way."""
    if failure == "hang":
        await asyncio.sleep(3600)
    await asyncio.sleep(engine.latency_s)
    if failure is not None or runaway:
        call.outcome = f"failed:{failure or 'codec_limit'}"
    match failure:
        case "internal":  # any unexpected exception: create_error_response defaults to 400
            return error("Speech generation failed: RuntimeError: CUDA error: an illegal memory access")
        case "server_error":
            return error("EngineGenerateError: stage 0 failed", 500)
        case "unavailable":
            return error("engine is dead", 503, "ServiceUnavailableError")
        case "empty":
            return Response(b"", media_type=f"audio/{body.response_format}")
    if runaway:
        return error(codec_limit_message(call.sampling["max_tokens"]), 500, "server_error")
    pcm = tone(frames, body.speed or 1.0)
    if body.response_format == "wav":
        buf = io.BytesIO()
        sf.write(buf, np.frombuffer(pcm, "<i2"), SAMPLE_RATE, format="WAV", subtype="PCM_16")
        data = buf.getvalue()
    elif body.response_format == "pcm":
        data = pcm
    else:
        return error(f"the fake engine does not encode {body.response_format}")
    text_tokens = len(body.input.split())
    audio_tokens = round(engine.voices.get(body.voice or "", {}).get("seconds", 0.0) * 12.5)
    headers = {"X-VLLM-OMNI-INPUT-TOKENS": str(text_tokens + audio_tokens), "X-VLLM-OMNI-OUTPUT-TOKENS": str(frames),
               "X-VLLM-OMNI-TOTAL-TOKENS": str(text_tokens + audio_tokens + frames),
               "X-VLLM-OMNI-INPUT-TEXT-TOKENS": str(text_tokens), "X-VLLM-OMNI-INPUT-AUDIO-TOKENS": str(audio_tokens)}
    call.outcome = "ok"
    return Response(data, media_type=f"audio/{body.response_format}", headers=headers)


async def stream(engine: FakeEngine, call: Call, body: SpeechBody, failure: str | None, frames: int,
                 runaway: bool) -> AsyncIterator[bytes]:
    """Raw audio: the first chunk after one frame, then every 25; a failure after the first byte just ends the
    connection early (serving_speech.py _generate_audio_chunks re-raises)."""
    try:
        if failure == "hang":
            await asyncio.sleep(3600)
        if failure in ("internal", "server_error", "unavailable"):
            raise RuntimeError(f"injected {failure}")
        spans, start = [], 0
        while failure != "empty" and start < frames:
            end = min(frames, start + (INITIAL_CHUNK_FRAMES if not spans else CHUNK_FRAMES))
            spans.append((start, end))
            start = end
        pcm = tone(frames)
        for i, (start, end) in enumerate(spans):
            if i:
                await asyncio.sleep(engine.chunk_delay_s)
            head = streaming_wav_header() if i == 0 and body.response_format == "wav" else b""
            yield head + pcm[start * 2 * FRAME_SAMPLES:end * 2 * FRAME_SAMPLES]
        if runaway:
            raise RuntimeError(codec_limit_message(call.sampling["max_tokens"]))
        call.outcome = "ok"
    except (asyncio.CancelledError, GeneratorExit):
        call.outcome = "aborted"
        raise
    except Exception:
        call.outcome = f"failed:{failure or 'codec_limit'}"
        raise


def bind(host: str = "127.0.0.1", ports: range = range(18000, 19000)) -> socket.socket:
    """A listening-ready socket on a free port of `ports`, tried from a random start."""
    offset = random.randrange(len(ports))
    for i in range(len(ports)):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, ports[(offset + i) % len(ports)]))
            return sock
        except OSError:
            sock.close()
    raise RuntimeError(f"no free port in {ports}")


@asynccontextmanager
async def serve(app: FastAPI, host: str = "127.0.0.1") -> AsyncIterator[str]:
    """Run `app` with uvicorn on a free port in 18000-18999 inside the current event loop; yields its base URL."""
    sock = bind(host)
    server = uvicorn.Server(uvicorn.Config(app, lifespan="off", log_level="warning", timeout_graceful_shutdown=1))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        while not server.started:
            if task.done():
                await task
                raise RuntimeError("fake engine did not start")
            await asyncio.sleep(0.01)
        yield f"http://{host}:{sock.getsockname()[1]}"
    finally:
        server.should_exit = True
        await task
        sock.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=18091)
    ap.add_argument("--api-key")
    ap.add_argument("--spw", type=float, default=0.35, help="seconds of audio per word")
    ap.add_argument("--chunk-delay", type=float, default=0.0, help="seconds between streamed chunks")
    ap.add_argument("--latency", type=float, default=0.0, help="seconds before a non-streaming answer")
    ap.add_argument("--patched", action="store_true", help="accept extra_params.repetition_penalty")
    a = ap.parse_args()
    engine = FakeEngine(spw=a.spw, chunk_delay_s=a.chunk_delay, latency_s=a.latency, api_key=a.api_key,
                        patched=a.patched)
    uvicorn.run(create_app(engine), host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
