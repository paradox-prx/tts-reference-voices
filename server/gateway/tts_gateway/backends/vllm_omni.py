"""HTTP backend for the vLLM-Omni speech server (Qwen3-TTS Base): POST /v1/audio/speech plus the /v1/audio/voices
store. Fields, routes and behaviour follow the vllm-omni 0.28.0 source (docs/research/omni-source.md); file:line
references are to vllm_omni/entrypoints/openai/ in 0.28.0 unless marked otherwise."""

from __future__ import annotations

import asyncio
import base64
import logging
import re
import struct
import time
from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from .. import audio, logs
from ..config import Settings
from ..voices import Voice, VoiceRegistry
from .base import (
    BackendError,
    Capabilities,
    EngineBadRequest,
    EngineFailure,
    EngineTimeout,
    EngineUnavailable,
    SynthesisRequest,
    SynthesisResult,
)

SAMPLE_RATE = 24000  # Qwen3-TTS code2wav output
CONSENT_PREFIX = "tts-gateway:"  # marks the engine voices this gateway owns, and may delete once superseded
OUTPUT_TOKENS_HEADER = "X-VLLM-OMNI-OUTPUT-TOKENS"  # codec frames; non-streaming responses only (serving_speech.py:84)
INPUT_TOKENS_HEADER = "X-VLLM-OMNI-INPUT-TOKENS"
_MAX_WAV_HEADER = 4096
# Engine faults that 0.28 answers with HTTP 400, because vLLM's create_error_response defaults to BadRequest:
# serving_speech.py:3246 and :3255 raise ValueError, :3712 wraps any other exception.
_ENGINE_FAULTS_AS_400 = ("Speech generation failed", "No output generated from the model",
                         "TTS model did not produce audio output")
_AUDIO_MAGIC = ((b"RIFF", "audio/wav"), (b"fLaC", "audio/flac"), (b"OggS", "audio/ogg"), (b"ID3", "audio/mpeg"))


def engine_voice_name(voice: Voice) -> str:
    """Content-addressed: a new reference clip gets a new engine voice, and a restart finds the stored one."""
    return f"{voice.id}-{voice.ref_sha256[:10]}"


def _is_current(entry: dict[str, Any] | None, voice: Voice) -> bool:
    """A stored voice entry (GET /v1/audio/voices, api_server.py:1498-1512) matches the voice's transcript."""
    return entry is not None and str(entry.get("ref_text") or "").strip() == voice.ref_text


def _data_url(data: bytes) -> str:
    mime = next((m for magic, m in _AUDIO_MAGIC if data.startswith(magic)), "audio/wav")
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _message(response: httpx.Response) -> str:
    """Error text of an engine response: {"error": {"message"}} (OpenAI shape), {"error": "..."} (--api-key
    middleware), {"detail"} (FastAPI), or the raw body."""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            err = err.get("message")
        if text := err or body.get("detail"):
            return str(text)[:500]
    return response.text[:500] or f"HTTP {response.status_code}"


def _status_error(response: httpx.Response) -> BackendError:
    status, message = response.status_code, _message(response)
    if status in (401, 403):
        return EngineFailure(f"engine refused the gateway (HTTP {status}; check TTS_ENGINE_API_KEY): {message}")
    if status == 404:
        return EngineFailure(f"engine HTTP 404: {message}")
    if status == 503:
        return EngineUnavailable(f"engine unavailable: {message}")
    if status >= 500:  # includes the codec limit hit without EOS (serving_speech.py:3692-3701)
        return EngineFailure(f"engine HTTP {status}: {message}", retryable=True)
    if message.startswith(_ENGINE_FAULTS_AS_400):
        return EngineFailure(f"engine error: {message}", retryable=True)
    return EngineBadRequest(message)


def _transport_error(exc: httpx.TransportError, url: str) -> BackendError:
    detail = f"{type(exc).__name__}: {exc}"
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
        return EngineUnavailable(f"cannot connect to the engine at {url} ({detail})")
    if isinstance(exc, httpx.TimeoutException):
        return EngineTimeout(f"engine timed out ({detail})")
    # The engine dropped the connection mid-response. A raw stream that hits the codec limit ends this way
    # (the check runs after the last chunk, serving_speech.py:2306), and so does a crash.
    return EngineFailure(f"engine connection failed ({detail})", retryable=True)


def _int_header(response: httpx.Response, name: str) -> int | None:
    value = response.headers.get(name, "")
    return int(value) if value.isdigit() else None


def _wav_data_offset(head: bytes) -> int | None:
    """Where the PCM starts after the WAV header at the start of `head`; None while the header is incomplete."""
    pos = 12
    while pos + 8 <= len(head):
        chunk_id, size = head[pos:pos + 4], struct.unpack_from("<I", head, pos + 4)[0]
        if chunk_id == b"data":
            return pos + 8
        if chunk_id == b"fmt ":
            if pos + 24 > len(head):
                return None
            tag, channels, rate = struct.unpack_from("<HHI", head, pos + 8)
            bits = struct.unpack_from("<H", head, pos + 22)[0]
            if (tag, channels, rate, bits) != (1, 1, SAMPLE_RATE, 16):
                raise EngineFailure(f"engine streamed {rate} Hz, {channels} channel(s), {bits}-bit audio; "
                                    f"expected {SAMPLE_RATE} Hz mono PCM16")
        pos += 8 + size + (size & 1)
    if len(head) > _MAX_WAV_HEADER:
        raise EngineFailure("engine streamed a malformed WAV header")
    return None


class _PcmReader:
    """Whole PCM16 samples from the engine's raw byte stream. With response_format=pcm the stream has no header;
    one is sent only for wav (serving_speech.py:2268), so a leading WAV header is checked and dropped defensively."""

    def __init__(self) -> None:
        self._pending = b""
        self._header_checked = False
        self.pcm_bytes = 0

    def feed(self, data: bytes) -> bytes:
        buf = self._pending + data
        if not self._header_checked:
            if len(buf) < 12:
                self._pending = buf
                return b""
            if buf.startswith(b"RIFF") and buf[8:12] == b"WAVE":
                start = _wav_data_offset(buf)
                if start is None:
                    self._pending = buf
                    return b""
                buf = buf[start:]
            self._header_checked = True
        cut = len(buf) - len(buf) % audio.SAMPLE_WIDTH
        self._pending = buf[cut:]
        self.pcm_bytes += cut
        return buf[:cut]


class VllmOmniBackend:
    """Registered mode (default) uploads each voice once under a content-addressed name and sends `voice`; inline
    mode sends the reference clip as a data URL with every request. Either way, per-request inline cloning
    (SynthesisRequest.voice None) sends ref_audio + ref_text."""

    name = "vllm_omni"

    def __init__(self, settings: Settings, voices: VoiceRegistry) -> None:
        self.capabilities = Capabilities(streaming=True, per_request_repetition_penalty=settings.engine_per_request_rp,
                                         voice_registry=True, sample_rate=SAMPLE_RATE)
        self._settings, self._voices = settings, voices
        self._registered_mode = settings.voice_mode == "registered"
        key = settings.engine_api_key
        pool = settings.max_inflight + 8  # speech calls plus health checks, voice uploads and warmups
        self._client = httpx.AsyncClient(
            base_url=settings.engine_url, trust_env=False,  # never through a proxy
            headers={"Authorization": f"Bearer {key.get_secret_value()}"} if key else None,
            timeout=httpx.Timeout(settings.request_timeout_s, connect=5.0),
            limits=httpx.Limits(max_connections=pool, max_keepalive_connections=pool))
        self._confirmed: set[str] = set()  # engine voice names known to be stored with the current transcript
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def start(self) -> None:
        """Nothing to open up front: the gateway polls health() until the engine is up."""

    async def close(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------------------------------ engine calls

    async def _call(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """One small engine request; transport failures and non-2xx answers raise BackendError."""
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TransportError as exc:
            raise _transport_error(exc, self._settings.engine_url) from exc
        if not response.is_success:
            raise _status_error(response)
        return response

    async def _json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = await self._call(method, path, **kwargs)
        try:
            body = response.json()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            raise EngineFailure(f"engine {method} {path}: expected a JSON object, got {response.text[:200]!r}")
        return body

    async def health(self) -> dict[str, Any]:
        """Engine /health and, in registered mode, every voice stored on the engine. A voice the engine lost (a wiped
        SPEAKER_SAMPLES_DIR, a manual DELETE) is uploaded again here, so readiness heals itself."""
        info: dict[str, Any] = {"ok": False, "backend": self.name, "engine": self._settings.engine_url}
        try:
            await self._call("GET", "/health", timeout=5.0)  # 200 {"status": "healthy"} or 503 (api_server.py:1783)
            if self._registered_mode:
                stored = await self._stored_voices()
                lost = [v for v in self._voices if not _is_current(stored.get(engine_voice_name(v)), v)]
                for voice in lost:
                    self._confirmed.discard(engine_voice_name(voice))
                    await self._voice_name(voice)
                if lost:
                    info["registered"] = [v.id for v in lost]
        except BackendError as exc:
            return info | {"error": f"{type(exc).__name__}: {exc}"}
        return info | {"ok": True}

    # ------------------------------------------------------------------------------------------ voices

    async def _stored_voices(self) -> dict[str, dict[str, Any]]:
        """The engine's uploaded voices by lowercase name (api_server.py:1468-1515)."""
        body = await self._json("GET", "/v1/audio/voices")
        return {str(v.get("name", "")).lower(): v for v in body.get("uploaded_voices") or [] if isinstance(v, dict)}

    async def register_voice(self, voice: Voice) -> None:
        """Idempotent: checks the engine's store first and uploads only when the voice is missing or stale."""
        async with self._locks[voice.id]:
            await self._register(voice)

    async def _voice_name(self, voice: Voice) -> str:
        name = engine_voice_name(voice)
        if name not in self._confirmed:
            async with self._locks[voice.id]:
                if name not in self._confirmed:  # another request may have registered it meanwhile
                    await self._register(voice)
        return name

    async def _register(self, voice: Voice) -> None:
        name, consent = engine_voice_name(voice), CONSENT_PREFIX + voice.id
        stored = await self._stored_voices()
        entry = stored.get(name)
        if not _is_current(entry, voice):
            if entry is not None:  # same clip, new transcript; delete first, as 0.30 may refuse overwrites
                await self._call("DELETE", f"/v1/audio/voices/{name}")
            mime = voice.data_url[5:voice.data_url.index(";")]
            # multipart fields per api_server.py:1519-1536; the engine keeps ref_text for ICL (serving_speech.py:997)
            body = await self._json(
                "POST", "/v1/audio/voices", timeout=60.0,
                files={"audio_sample": (voice.ref_path.name, voice.ref_audio, mime)},
                data={"name": name, "consent": consent, "ref_text": voice.ref_text})
            if body.get("success") is not True:
                raise EngineFailure(f"engine did not store voice {name!r}: {body}")
            logs.event("engine_voice_uploaded", voice=voice.id, engine_voice=name, replaced=entry is not None)
        superseded = re.compile(rf"{re.escape(voice.id)}-[0-9a-f]{{10}}")
        for old, old_entry in stored.items():
            if old != name and superseded.fullmatch(old) and old_entry.get("consent") == consent:
                try:
                    await self._call("DELETE", f"/v1/audio/voices/{old}")
                    logs.event("engine_voice_deleted", voice=voice.id, engine_voice=old, reason="superseded")
                except BackendError as exc:
                    logs.event("engine_voice_delete_failed", logging.WARNING, voice=voice.id, engine_voice=old,
                               error=str(exc))
        self._confirmed.add(name)

    # ------------------------------------------------------------------------------------------ speech

    async def _payload(self, req: SynthesisRequest, *, stream: bool) -> dict[str, Any]:
        """The /v1/audio/speech body (protocol/audio.py:57-205). The engine ignores unknown fields silently, so only
        fields it reads are sent."""
        s = self._settings
        payload: dict[str, Any] = {"input": req.text, "task_type": "Base", "language": req.language,
                                   "response_format": "pcm"}
        if req.voice is None:
            if not req.ref_audio or not req.ref_text:
                raise EngineBadRequest("inline cloning needs ref_audio and ref_text")
            payload |= {"ref_audio": _data_url(req.ref_audio), "ref_text": req.ref_text}
        elif self._registered_mode:
            payload["voice"] = await self._voice_name(req.voice)  # ref_text comes from the stored voice
        else:
            payload |= {"ref_audio": req.voice.data_url, "ref_text": req.voice.ref_text}
        # Per-request sampling reaches the talker (codebook 0) only through extra_params (serving_speech.py:3089);
        # top-level temperature/top_k/top_p would be dropped silently.
        extra = {"temperature": s.default_temperature if req.temperature is None else req.temperature,
                 "top_k": s.default_top_k if req.top_k is None else req.top_k, "top_p": req.top_p}
        if req.repetition_penalty is not None:
            if not self.capabilities.per_request_repetition_penalty:
                raise EngineBadRequest("repetition_penalty needs the patched engine (TTS_ENGINE_PER_REQUEST_RP=1)")
            extra["repetition_penalty"] = req.repetition_penalty
        if extra := {k: v for k, v in extra.items() if v is not None}:
            payload["extra_params"] = extra
        if req.max_new_tokens is not None:  # also turns off the engine's own retry-once (serving_speech.py:3621)
            payload["max_new_tokens"] = req.max_new_tokens
        if req.seed is not None:  # 0.28 then runs the code predictor row by row in a batch: never by default
            payload["seed"] = req.seed
        if stream:
            if req.speed is not None:
                raise EngineBadRequest("speed is not supported when streaming")  # serving_speech.py:3499
            payload |= {"stream": True, "stream_format": "audio"}
        elif req.speed is not None:
            payload["speed"] = req.speed
        return payload

    async def _open(self, req: SynthesisRequest, *, stream: bool, reregister: bool = True) -> httpx.Response:
        """POST /v1/audio/speech; returns the 200 response with its body unread, for the caller to aclose(). Closing
        it early drops the connection, which aborts the engine request: non-streaming through with_cancellation
        (api_server.py:1345), streaming by cancelling the response generator."""
        payload = await self._payload(req, stream=stream)
        request = self._client.build_request("POST", "/v1/audio/speech", json=payload,
                                             headers={"X-Request-Id": req.request_id})
        try:
            response = await self._client.send(request, stream=True)
        except httpx.TransportError as exc:
            raise _transport_error(exc, self._settings.engine_url) from exc
        content_type = response.headers.get("content-type", "")
        if response.status_code == 200 and content_type.startswith("audio/"):
            return response
        try:
            if response.status_code != 200:
                await response.aread()  # the error message
        except httpx.TransportError as exc:
            raise _transport_error(exc, self._settings.engine_url) from exc
        finally:
            await response.aclose()
        if response.status_code == 200:
            raise EngineFailure(f"engine answered {content_type or 'without a content type'}, not audio")
        error = _status_error(response)
        name = payload.get("voice")
        if reregister and name and isinstance(error, EngineBadRequest) and f"'{name}'" in str(error):
            # The engine no longer has the voice (tts_adapters/qwen3_tts.py:128,142, serving_speech.py:993): upload
            # it again and retry once.
            logs.event("engine_voice_lost", logging.WARNING, engine_voice=name, error=str(error))
            self._confirmed.discard(name)
            return await self._open(req, stream=stream, reregister=False)
        raise error

    async def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
        start = time.perf_counter()
        response = await self._open(req, stream=False)
        try:
            body = await response.aread()
        except httpx.TransportError as exc:
            raise _transport_error(exc, self._settings.engine_url) from exc
        finally:
            await response.aclose()
        pcm, sample_rate = body, SAMPLE_RATE
        if body.startswith(b"RIFF"):  # PCM was asked for; accept a WAV all the same
            try:
                pcm, sample_rate = audio.wav_to_pcm(body)
            except ValueError as exc:
                raise EngineFailure(f"engine sent an unreadable WAV: {exc}") from None
        pcm = pcm[:len(pcm) - len(pcm) % audio.SAMPLE_WIDTH]
        if not pcm:
            raise EngineFailure("engine returned no audio", retryable=True)
        return SynthesisResult(pcm=pcm, sample_rate=sample_rate, engine_ms=(time.perf_counter() - start) * 1000,
                               codec_frames=_int_header(response, OUTPUT_TOKENS_HEADER),
                               meta={"input_tokens": _int_header(response, INPUT_TOKENS_HEADER)})

    async def stream(self, req: SynthesisRequest) -> AsyncGenerator[bytes, None]:
        """PCM16 chunks as the engine decodes them (the first after one codec frame, then every 25 frames)."""
        response = await self._open(req, stream=True)
        reader = _PcmReader()
        try:
            async for data in response.aiter_bytes():
                if pcm := reader.feed(data):
                    yield pcm
        except httpx.TransportError as exc:
            raise _transport_error(exc, self._settings.engine_url) from exc
        finally:
            await response.aclose()
        if not reader.pcm_bytes:
            raise EngineFailure("engine streamed no audio", retryable=True)
