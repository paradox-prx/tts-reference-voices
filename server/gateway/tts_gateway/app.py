"""FastAPI app: OpenAI-compatible POST /v1/audio/speech in front of a TTS backend, plus voice, model, health,
readiness and metrics routes. Routes, headers and error shapes follow docs/DESIGN.md."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import io
import logging
import time
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable, Iterator
from contextlib import aclosing, asynccontextmanager, suppress
from dataclasses import dataclass, replace
from typing import Any, Literal

import soundfile as sf
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Message, Receive, Scope, Send

from . import __version__, audio, logs, quality
from .admission import Admission, QueueFull, QueueTimeout, Slot
from .backends import create_backend
from .backends.base import (
    BackendError,
    EngineBadRequest,
    EngineTimeout,
    EngineUnavailable,
    SynthesisRequest,
    TTSBackend,
)
from .config import Settings
from .logs import RequestLog
from .metrics import CONTENT_TYPE, Metrics
from .qc import QCClient
from .quality import Check
from .textproc import (
    PaceBand,
    count_letters,
    count_words,
    detect_lang,
    language_band,
    max_new_tokens_for,
    pace_cap,
    split_for_ceiling,
    voice_band,
)
from .voices import REF_SECONDS, Voice, VoiceRegistry, engine_language, load_pace, normalize_language

MAX_BODY_BYTES = 16 << 20  # JSON body: the input text plus, at most, an inline reference clip in base64
MAX_REF_AUDIO_BYTES = 10 << 20
OFFLOAD_BYTES = 1 << 20  # bodies to parse and PCM to encode above this size go to a worker thread
PART_GAP_S = 0.2  # silence between the parts of a request split for a backend's per-call ceiling
WARMUP_TEXT = {"en": "Hello, this is a short warmup.", "ur": "السلام علیکم، یہ ایک مختصر آزمائش ہے۔"}


class SpeechRequest(BaseModel):
    """OpenAI's speech request plus our extensions. Unknown fields are rejected, so a typo never silently falls back
    to a default (the engine ignores unknown fields)."""

    model_config = ConfigDict(extra="forbid")

    model: str | None = None  # accepted and ignored: one model per server
    input: str
    voice: str | None = Field(None, max_length=128)
    response_format: Literal["wav", "pcm", "flac", "mp3", "opus"] = "wav"
    speed: float | None = Field(None, ge=0.25, le=4.0)
    stream: bool = False
    stream_format: Literal["audio"] | None = None  # vLLM-Omni clients send it; only raw audio streams exist here
    task_type: Literal["Base"] | None = None  # vLLM-Omni clients send it; voice cloning is the only task
    language: str | None = Field(None, max_length=32)
    temperature: float | None = Field(None, gt=0, le=2)
    top_k: int | None = Field(None, ge=1, le=4096)
    top_p: float | None = Field(None, gt=0, le=1)
    repetition_penalty: float | None = Field(None, gt=0, le=2)
    seed: int | None = Field(None, ge=0, lt=2**31)
    max_new_tokens: int | None = Field(None, ge=1, le=4096)
    ref_audio: str | None = None
    ref_text: str | None = Field(None, max_length=4000)
    retries: int | None = Field(None, ge=0)


class APIError(Exception):
    """An error answered in OpenAI's shape. `detail` goes to the log only."""

    def __init__(self, status: int, code: str, message: str, headers: dict[str, str] | None = None,
                 detail: str | None = None) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.headers, self.detail = status, code, message, headers or {}, detail

    @property
    def type(self) -> str:
        if self.status >= 500:
            return "server_error"
        return {401: "authentication_error", 429: "rate_limit_error"}.get(self.status, "invalid_request_error")


def error_response(err: APIError, request_id: str | None = None) -> JSONResponse:
    headers = err.headers | ({"X-Request-Id": request_id} if request_id else {})
    return JSONResponse({"error": {"message": err.message, "type": err.type, "code": err.code}}, err.status, headers)


def engine_error(exc: BackendError) -> APIError:
    detail = f"{type(exc).__name__}: {exc}"
    if isinstance(exc, EngineUnavailable):
        return APIError(503, "engine_unavailable", "speech engine unavailable", {"Retry-After": "5"}, detail)
    if isinstance(exc, EngineTimeout):
        return APIError(504, "engine_timeout", "speech engine timed out", detail=detail)
    if isinstance(exc, EngineBadRequest):
        return APIError(400, "engine_rejected", f"speech engine rejected the request: {exc}", detail=detail)
    return APIError(502, "engine_error", "speech engine failed", detail=detail)


class ClientDisconnected(Exception):
    """The client went away; the work done on its behalf was cancelled."""


@dataclass
class _Watch:
    armed: bool = True  # cleared once the response is complete: the server then reports a disconnect too
    fired: bool = False


@asynccontextmanager
async def cancel_on_disconnect(receive: Receive) -> AsyncIterator[_Watch]:
    """Cancel the current task when the client disconnects, and raise ClientDisconnected in its place, so queue
    slots and engine calls are released as soon as nobody is waiting for the audio."""
    task = asyncio.current_task()
    assert task is not None
    watch = _Watch()

    async def listen() -> None:
        while (await receive())["type"] != "http.disconnect":
            pass
        if watch.armed:
            watch.fired = True
            task.cancel()

    listener = asyncio.create_task(listen())
    try:
        yield watch
    except asyncio.CancelledError:
        if watch.fired and task.uncancel() == 0:
            raise ClientDisconnected from None
        raise
    finally:
        listener.cancel()


class AudioStream(StreamingResponse):
    """Streams audio chunks. A client disconnect cancels the body and with it the backend stream. on_close always
    runs, with the exception that ended the stream early (None when it completed). An engine error after the first
    byte leaves the response incomplete, so the server drops the connection and the client sees a failed transfer
    rather than a short but well-formed file."""

    def __init__(self, body: AsyncGenerator[bytes, None], on_close: Callable[[BaseException | None], Awaitable[None]],
                 **kwargs: Any) -> None:
        super().__init__(body, **kwargs)
        self._body, self._on_close = body, on_close

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        error: BaseException | None = None
        try:
            async with cancel_on_disconnect(receive) as watch:
                async def send_tracked(message: Message) -> None:
                    if message["type"] == "http.response.body" and not message.get("more_body", False):
                        watch.armed = False
                    await send(message)

                await self.stream_response(send_tracked)
        except (ClientDisconnected, BackendError) as exc:
            error = exc
        except BaseException as exc:
            error = exc
            raise
        finally:
            try:
                await self._body.aclose()
            finally:
                await self._on_close(error)


def decode_ref_audio(value: str) -> tuple[bytes, float]:
    """Inline reference audio (bytes, seconds): plain base64 or a data:audio/...;base64 URL. Never a URL: the engine
    would fetch http(s) URLs (SSRF) and read file:// paths (local file disclosure)."""
    payload = value
    if value[:5].lower() == "data:":
        header, sep, payload = value.partition(",")
        mime = header[5:].lower()
        if not sep or not mime.startswith("audio/") or not mime.endswith(";base64"):
            raise APIError(400, "invalid_ref_audio", "ref_audio data URL must be data:audio/<type>;base64,<data>")
    elif ":" in value:  # not in the base64 alphabet: a URL of some scheme
        raise APIError(400, "invalid_ref_audio",
                       "ref_audio must be base64 audio or a data:audio/...;base64 URL; URLs are not accepted")
    try:
        data = base64.b64decode("".join(payload.split()), validate=True)
    except (binascii.Error, ValueError):
        raise APIError(400, "invalid_ref_audio", "ref_audio is not valid base64") from None
    if len(data) > MAX_REF_AUDIO_BYTES:
        raise APIError(413, "ref_audio_too_large", f"ref_audio is over {MAX_REF_AUDIO_BYTES >> 20} MB")
    try:
        seconds = sf.info(io.BytesIO(data)).duration
    except sf.LibsndfileError:
        raise APIError(400, "invalid_ref_audio", "ref_audio is not a decodable audio file") from None
    if not REF_SECONDS[0] <= seconds <= REF_SECONDS[1]:
        raise APIError(400, "invalid_ref_audio",
                       f"ref_audio lasts {seconds:.1f} s; it must last {REF_SECONDS[0]:g}-{REF_SECONDS[1]:g} s")
    return data, seconds


async def read_body(request: Request) -> bytes:
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > MAX_BODY_BYTES:
        raise APIError(413, "request_too_large", f"request body is over {MAX_BODY_BYTES >> 20} MB")
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BODY_BYTES:
            raise APIError(413, "request_too_large", f"request body is over {MAX_BODY_BYTES >> 20} MB")
    return bytes(body)


async def parse_speech(raw: bytes) -> SpeechRequest:
    try:
        if len(raw) > OFFLOAD_BYTES:
            return await asyncio.to_thread(SpeechRequest.model_validate_json, raw)
        return SpeechRequest.model_validate_json(raw)
    except ValidationError as exc:
        problems = [f"{'.'.join(str(p) for p in e['loc']) or 'body'}: {e['msg']}" for e in exc.errors()[:5]]
        raise APIError(400, "invalid_request", "; ".join(problems)) from None


@dataclass(frozen=True)
class Plan:
    """A validated speech request, ready for the engine."""

    base: SynthesisRequest
    parts: list[str]  # the text, split only for a backend with a per-call ceiling
    band: PaceBand | None
    lang: str  # the text's language: "en", "ur" or "und"
    fmt: str
    stream: bool
    retries: int
    voice_label: str  # voice id, or "inline"
    length_cap: bool

    def check(self, text: str, qc: QCClient | None) -> Check:
        voice = self.base.voice.id if self.base.voice else None
        return Check(count_words(text), count_letters(text), self.band, self.lang, voice, qc)


class Gateway:
    def __init__(self, settings: Settings, voices: VoiceRegistry, backend: TTSBackend) -> None:
        self.settings, self.voices, self.backend = settings, voices, backend
        self.qc = QCClient(settings) if settings.qc_url else None
        self.metrics = Metrics()
        self.admission = Admission(settings.max_inflight, settings.max_queue, settings.queue_timeout_s)
        self.metrics.track(self.admission)
        self.ready = False
        self.not_ready_reason = "starting"
        self._keys = [hashlib.sha256(k.encode()).digest() for k in settings.api_keys]
        self._bringup: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------------------------------ lifecycle

    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncIterator[None]:
        s = self.settings
        logs.event("startup", version=__version__, backend=self.backend.name, voices=[v.id for v in self.voices],
                   invalid_voices=self.voices.errors, voice_mode=s.voice_mode, max_inflight=s.max_inflight,
                   max_queue=s.max_queue, retry_max=s.retry_max, retry_on=sorted(s.retry_on), length_cap=s.length_cap,
                   suspect_band=s.suspect_band, pace={v.id: [round(v.pace, 4), v.pace_source] for v in self.voices},
                   qc=s.qc_url and {"url": s.qc_url, "checks": sorted(s.qc_checks)}, warmup=s.warmup,
                   inline_ref=s.allow_inline_ref, auth="disabled" if s.auth_disabled else f"{len(self._keys)} key(s)")
        await self.backend.start()
        self._bringup = asyncio.create_task(self._bring_up())
        try:
            yield
        finally:
            self.ready, self.not_ready_reason = False, "shutting down"
            self._bringup.cancel()
            with suppress(asyncio.CancelledError):
                await self._bringup
            await self.backend.close()
            if self.qc:
                await self.qc.close()
            logs.event("shutdown", inflight=self.admission.inflight)

    async def _bring_up(self) -> None:
        """Wait for a healthy engine, register every voice, warm each one up; only then is the gateway ready."""
        register = self.settings.voice_mode == "registered" and self.backend.capabilities.voice_registry
        pending = list(self.voices) if register else []
        cold = list(self.voices) if self.settings.warmup else []
        delay = 1.0
        while True:
            try:
                async with asyncio.timeout(10):
                    health = await self.backend.health()
                if not health.get("ok"):
                    raise RuntimeError(f"engine not healthy: {health}")
                while pending:
                    await self.backend.register_voice(pending[0])
                    logs.event("voice_registered", voice=pending.pop(0).id)
                while cold:
                    await self._warm(cold[0])
                    cold.pop(0)
                self.ready = True
                logs.event("ready", backend=self.backend.name, voices=[v.id for v in self.voices])
                return
            except Exception as exc:  # noqa: BLE001 - keep trying until the engine comes up
                self.not_ready_reason = f"{type(exc).__name__}: {exc}"
                logs.event("bringup_retry", logging.WARNING, error=self.not_ready_reason, retry_in_s=delay)
                await asyncio.sleep(delay)
                delay = min(2 * delay, 30.0)

    async def _warm(self, voice: Voice) -> None:
        text = WARMUP_TEXT.get(voice.lang, WARMUP_TEXT["en"])
        cap = max_new_tokens_for(count_words(text)) if self.settings.length_cap else None
        req = SynthesisRequest(text=text, voice=voice, language=voice.language, max_new_tokens=cap,
                               request_id=f"warmup-{voice.id}")
        start = time.perf_counter()
        async with asyncio.timeout(self.settings.request_timeout_s):
            result = await self.backend.synthesize(req)
        logs.event("warmup", voice=voice.id, ms=round((time.perf_counter() - start) * 1000, 1),
                   audio_s=round(audio.duration_s(len(result.pcm), result.sample_rate), 3))

    # ------------------------------------------------------------------------------------------ plain routes

    def require_auth(self, request: Request) -> None:
        if self.settings.auth_disabled:
            return
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        digest = hashlib.sha256(token.strip().encode()).digest()
        matched = False
        for key in self._keys:  # every key is compared, in constant time
            matched |= hmac.compare_digest(digest, key)
        if scheme.lower() != "bearer" or not matched:
            raise APIError(401, "invalid_api_key", "missing or invalid API key (Authorization: Bearer <key>)",
                           {"WWW-Authenticate": "Bearer"})

    async def readiness(self) -> JSONResponse:
        if not self.ready:
            return JSONResponse({"ready": False, "reason": self.not_ready_reason}, 503)
        try:
            async with asyncio.timeout(5):
                health = await self.backend.health()
        except Exception as exc:  # noqa: BLE001 - any failure means not ready
            health = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        if not health.get("ok"):
            return JSONResponse({"ready": False, "reason": f"engine unhealthy: {health}"}, 503)
        body = {"ready": True, "backend": self.backend.name, "voices": [v.id for v in self.voices],
                "inflight": self.admission.inflight, "queued": self.admission.waiting}
        if self.qc:  # advisory: takes are kept when the sidecar is down, so it never makes the gateway unready
            body["qc"] = await self.qc.health()
        return JSONResponse(body)

    # ------------------------------------------------------------------------------------------ speech

    async def speech(self, request: Request) -> Response:
        log = RequestLog(request_id=logs.request_id(request.headers.get("x-request-id")))
        label, streaming = "-", False
        try:
            self.require_auth(request)
            body = await parse_speech(await read_body(request))
            plan = await self.plan(body, log)
            label = plan.voice_label
            if not self.ready:
                raise APIError(503, "not_ready", f"not ready: {self.not_ready_reason}", {"Retry-After": "5"})
            async with cancel_on_disconnect(request.receive):
                if plan.stream:
                    response = await self.start_stream(plan, log)
                    streaming = True  # the stream's on_close finishes the log
                    return response
                return await self.respond(plan, log)
        except APIError as err:
            log.fail(err.code, err.status, err.detail or err.message)
            return error_response(err, log.request_id)
        except ClientDisconnected:
            log.fail("cancelled", 499, "client disconnected")
            return Response(status_code=499)
        except asyncio.CancelledError:
            log.fail("cancelled", 499, "cancelled")
            raise
        except Exception as exc:
            logs.event("internal_error", logging.ERROR, exc_info=exc, request_id=log.request_id)
            log.fail("internal_error", 500, f"{type(exc).__name__}: {exc}")
            return error_response(APIError(500, "internal_error", "internal error"), log.request_id)
        finally:
            if not streaming:
                self.finish(log, label)

    async def plan(self, body: SpeechRequest, log: RequestLog) -> Plan:
        """Validate a request against the settings, the voices and the backend's capabilities."""
        s, caps = self.settings, self.backend.capabilities
        text = body.input.strip()
        log.chars, log.stream, log.format = len(text), body.stream, body.response_format
        log.voice = body.voice[:64] if body.voice else "inline" if body.ref_audio else None
        if not text:
            raise APIError(400, "empty_input", "input is empty")
        if len(text) > s.max_input_chars:
            raise APIError(413, "input_too_long", f"input has {len(text)} characters; the limit is {s.max_input_chars}")
        log.words = count_words(text)
        if not log.words:
            raise APIError(400, "empty_input", "input has no words")
        if body.stream:
            if not caps.streaming:
                raise APIError(400, "unsupported_parameter", f"the {self.backend.name} backend cannot stream")
            if body.response_format not in ("wav", "pcm"):
                raise APIError(400, "unsupported_parameter", "streaming supports response_format wav or pcm")
            if body.speed is not None:
                raise APIError(400, "unsupported_parameter", "speed is not supported when streaming")
        if body.repetition_penalty is not None and not caps.per_request_repetition_penalty:
            raise APIError(400, "unsupported_parameter",
                           f"repetition_penalty cannot be set per request on the {self.backend.name} backend")
        voice, ref_audio, ref_text, ref_seconds = await self._voice(body)
        label = voice.id if voice else "inline"
        lang = detect_lang(text)
        log.voice, log.lang = label, lang
        # The pace band is voice-relative only when the text is in the reference's language: a pace measured on
        # English letters says nothing about Urdu ones. Otherwise fall back to the language's seconds-per-word band.
        if voice is not None and lang == voice.lang:
            band: PaceBand | None = voice_band(voice.pace, s)
        elif voice is None and ref_text and lang == detect_lang(ref_text):
            band = voice_band(ref_seconds / max(1, count_letters(ref_text)), s)
        else:
            band = language_band(lang, s)
        if body.language:
            language = normalize_language(body.language)
        else:  # the voice's language (English for trump, Auto for shehbaz); inline: the text's
            language = voice.language if voice else engine_language(lang)
        parts = [text]
        if caps.max_seconds_per_call:  # a conservative words-per-part estimate from the language's centre pace
            est = language_band(lang, s) or language_band("en", s)
            assert est is not None
            parts = split_for_ceiling(text, max(1, int(caps.max_seconds_per_call / (1.5 * est.expected))))
        retries = 0 if body.stream else min(s.retry_max, s.retry_max if body.retries is None else body.retries)
        base = SynthesisRequest(text=text, voice=voice, language=language, temperature=body.temperature,
                                top_k=body.top_k, top_p=body.top_p, repetition_penalty=body.repetition_penalty,
                                seed=body.seed, max_new_tokens=body.max_new_tokens, speed=body.speed,
                                ref_audio=ref_audio, ref_text=ref_text, request_id=log.request_id)
        return Plan(base, parts, band, lang, body.response_format, body.stream, retries, label,
                    length_cap=s.length_cap and band is not None)

    async def _voice(self, body: SpeechRequest) -> tuple[Voice | None, bytes | None, str | None, float]:
        if body.ref_audio is not None or body.ref_text is not None:
            if not self.settings.allow_inline_ref:
                raise APIError(400, "inline_ref_disabled",
                               "inline cloning (ref_audio, ref_text) is disabled on this server; use a voice")
            if body.voice is not None:
                raise APIError(400, "invalid_request", "send either voice or ref_audio + ref_text, not both")
            if not body.ref_audio or not (body.ref_text or "").strip():
                raise APIError(400, "invalid_request", "inline cloning needs ref_audio and a non-empty ref_text")
            ref_audio, seconds = await asyncio.to_thread(decode_ref_audio, body.ref_audio)
            return None, ref_audio, (body.ref_text or "").strip(), seconds
        if not body.voice:
            raise APIError(400, "missing_voice", "voice is required")
        voice = self.voices.get(body.voice)
        if voice is None:
            raise APIError(404, "voice_not_found", f"voice {body.voice[:64]!r} not found; see GET /v1/voices")
        return voice, None, None, voice.ref_seconds

    def _part_requests(self, plan: Plan) -> Iterator[tuple[Check, SynthesisRequest]]:
        """(what to check, engine request) per part, each with its own length cap."""
        for i, text in enumerate(plan.parts):
            check = plan.check(text, self.qc)
            cap = plan.base.max_new_tokens or (self._length_cap(check) if plan.length_cap else None)
            rid = plan.base.request_id if len(plan.parts) == 1 else f"{plan.base.request_id}.{i + 1}"
            yield check, replace(plan.base, text=text, max_new_tokens=cap, request_id=rid)

    def _length_cap(self, check: Check) -> int:
        """The NOTES words formula, tightened to the voice's expected pace when there is a band."""
        cap = max_new_tokens_for(check.words)
        if check.band is not None:
            cap = min(cap, pace_cap(check.band, check.words, check.letters, self.settings.length_cap_headroom))
        return cap

    async def _acquire(self, log: RequestLog) -> Slot:
        try:
            slot = await self.admission.acquire()
        except QueueFull as exc:
            raise APIError(429, "queue_full", "server busy: request queue is full",
                           {"Retry-After": str(exc.retry_after_s)}) from None
        except QueueTimeout as exc:
            raise APIError(503, "queue_timeout", f"server busy: {exc}",
                           {"Retry-After": str(self.admission.retry_after_s())}) from None
        log.queue_ms = slot.waited_s * 1000
        self.metrics.queue_wait.observe(slot.waited_s)
        return slot

    def _headers(self, plan: Plan, log: RequestLog) -> dict[str, str]:
        return {"X-Request-Id": log.request_id, "X-AI-Generated": "true", "X-TTS-Voice": plan.voice_label,
                "X-TTS-Retries": str(log.retries), "X-TTS-Queue-Ms": f"{log.queue_ms or 0:.0f}",
                "X-TTS-Sample-Rate": str(self.backend.capabilities.sample_rate)}

    async def respond(self, plan: Plan, log: RequestLog) -> Response:
        """Non-streaming: every part through the retry policy, within one slot."""
        slot = await self._acquire(log)
        pcm: list[bytes] = []
        sample_rate = self.backend.capabilities.sample_rate
        start = time.perf_counter()
        try:
            for check, req in self._part_requests(plan):
                outcome = await quality.synthesize(
                    self.backend, req, check=check, retries=plan.retries, retry_on=self.settings.retry_on,
                    timeout_s=self.settings.request_timeout_s, metrics=self.metrics, voice=plan.voice_label)
                log.retries += outcome.retries
                log.take(outcome.take, outcome.qc_ms)
                sample_rate = outcome.take.result.sample_rate
                if pcm:
                    pcm.append(audio.silence(PART_GAP_S, sample_rate))
                pcm.append(outcome.take.result.pcm)
        except BackendError as exc:
            raise engine_error(exc) from exc
        finally:
            slot.release()
            log.engine_ms = (time.perf_counter() - start) * 1000  # every take, failed ones included
        joined = b"".join(pcm)
        log.audio_s = audio.duration_s(len(joined), sample_rate)
        if log.suspect:
            log.status = "suspect"
        if plan.fmt in ("flac", "mp3", "opus") or (plan.fmt == "wav" and len(joined) > OFFLOAD_BYTES):
            data = await asyncio.to_thread(audio.encode, joined, sample_rate, plan.fmt)
        else:
            data = audio.encode(joined, sample_rate, plan.fmt)
        headers = self._headers(plan, log) | {
            "X-TTS-Sample-Rate": str(sample_rate), "X-TTS-Audio-Seconds": f"{log.audio_s:.3f}",
            "X-TTS-Suspect": str(int(log.suspect)), "X-TTS-Engine-Ms": f"{log.engine_ms:.0f}",
            "X-TTS-QC": log.qc or "off"}
        if log.suspect_reason:
            headers["X-TTS-Suspect-Reason"] = log.suspect_reason
        if log.pace_ratio is not None:
            headers["X-TTS-Pace-Ratio"] = f"{log.pace_ratio:.3f}"
        if log.qc_reasons:
            headers["X-TTS-QC-Reasons"] = ",".join(log.qc_reasons)[:512]
        return Response(data, media_type=audio.MEDIA_TYPES[plan.fmt], headers=headers)

    async def start_stream(self, plan: Plan, log: RequestLog) -> Response:
        """Streaming: hold a slot for the whole stream. Errors before the first chunk still get an HTTP status."""
        slot = await self._acquire(log)
        chunks = self._stream_parts(plan, log)
        try:
            first = await anext(chunks)
        except BaseException as exc:
            slot.release()
            await chunks.aclose()
            if isinstance(exc, BackendError):
                raise engine_error(exc) from exc
            if isinstance(exc, StopAsyncIteration):
                raise APIError(502, "engine_error", "speech engine returned no audio") from None
            raise
        header = audio.wav_header(self.backend.capabilities.sample_rate) if plan.fmt == "wav" else b""

        async def body() -> AsyncGenerator[bytes, None]:
            yield header + first
            async for chunk in chunks:
                yield chunk

        async def on_close(error: BaseException | None) -> None:
            try:
                await chunks.aclose()
            finally:
                slot.release()
                self._close_stream(plan, log, error)

        return AudioStream(body(), on_close, media_type=audio.MEDIA_TYPES[plan.fmt], headers=self._headers(plan, log))

    async def _stream_parts(self, plan: Plan, log: RequestLog) -> AsyncGenerator[bytes, None]:
        sample_rate = self.backend.capabilities.sample_rate
        timeout = self.settings.request_timeout_s
        for i, (_, req) in enumerate(self._part_requests(plan)):
            if i:
                yield audio.silence(PART_GAP_S, sample_rate)
            start = time.perf_counter()
            try:
                async with aclosing(self.backend.stream(req)) as stream:
                    while True:
                        try:
                            async with asyncio.timeout(timeout):
                                chunk = await anext(stream)
                        except StopAsyncIteration:
                            break
                        except TimeoutError:
                            raise EngineTimeout(f"no audio for {timeout:g} s") from None
                        log.audio_s = (log.audio_s or 0.0) + audio.duration_s(len(chunk), sample_rate)
                        yield chunk
            except BackendError as exc:
                self.metrics.engine_errors.labels(exc.kind).inc()
                raise
            finally:
                log.engine_ms += (time.perf_counter() - start) * 1000

    def _close_stream(self, plan: Plan, log: RequestLog, error: BaseException | None) -> None:
        """Log a finished stream. It could not be retried, but a suspect one is still flagged and counted."""
        if error is None:
            if plan.band:
                log.pace_ratio = plan.band.ratio(log.audio_s or 0.0, log.words or 0, count_letters(plan.base.text))
                if reason := plan.band.reason(log.pace_ratio):
                    log.suspect, log.status, log.suspect_reason = True, "suspect", reason
                    self.metrics.suspect.labels(plan.voice_label, reason).inc()
        elif isinstance(error, BackendError):
            api = engine_error(error)
            log.fail(api.code, 200, f"after the first byte: {api.detail}")  # the client already has a 200
        elif isinstance(error, (ClientDisconnected, asyncio.CancelledError)):
            log.fail("cancelled", 499, "client disconnected mid-stream")
        else:
            log.fail("internal_error", 500, f"{type(error).__name__}: {error}")
        self.finish(log, plan.voice_label)

    def finish(self, log: RequestLog, voice_label: str) -> None:
        log.emit()
        self.metrics.requests.labels(log.status, voice_label).inc()
        self.metrics.request_seconds.observe((log.total_ms or 0.0) / 1000)
        if log.audio_s and log.http_status == 200:
            self.metrics.audio_seconds.labels(voice_label).inc(log.audio_s)


def create_app(settings: Settings | None = None, *, voices: VoiceRegistry | None = None,
               backend: TTSBackend | None = None) -> FastAPI:
    settings = settings or Settings()
    if voices is None:
        voices = VoiceRegistry.load(settings.voices_dir, load_pace(settings.pace_file, settings.pace))
    if not len(voices) and not settings.allow_inline_ref:
        raise RuntimeError(f"no valid voices under {settings.voices_dir} and inline cloning is disabled")
    gw = Gateway(settings, voices, backend or create_backend(settings, voices))
    app = FastAPI(title="qwen3-tts-server", version=__version__, lifespan=gw.lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.gateway = gw
    auth = [Depends(gw.require_auth)]

    @app.post("/v1/audio/speech")
    async def speech(request: Request) -> Response:
        return await gw.speech(request)

    @app.get("/v1/voices", dependencies=auth)
    @app.get("/v1/audio/voices", dependencies=auth)
    async def list_voices() -> dict[str, Any]:
        return {"object": "list", "data": [
            {"id": v.id, "object": "voice", "label": v.label, "language": v.lang, "default_language": v.language,
             "ref_seconds": v.ref_seconds} for v in gw.voices]}

    @app.get("/v1/models", dependencies=auth)
    async def list_models() -> dict[str, Any]:
        return {"object": "list",
                "data": [{"id": settings.model, "object": "model", "created": 0, "owned_by": "qwen3-tts-server"}]}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> JSONResponse:
        return await gw.readiness()

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(gw.metrics.render(), media_type=CONTENT_TYPE)

    @app.exception_handler(APIError)
    async def api_error(request: Request, exc: APIError) -> JSONResponse:
        return error_response(exc)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return error_response(APIError(exc.status_code, code, str(exc.detail), dict(exc.headers or {})))

    return app
