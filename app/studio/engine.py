"""Client for the Higgs engine (vLLM-Omni /v1/audio/speech). No language field: Higgs reads the language from the text
and the reference. The reference goes inline (data URL) with its exact transcript; the engine's prefix cache makes a
repeated reference cheap."""
from __future__ import annotations

import base64
import math
from dataclasses import dataclass

import httpx

from .settings import settings

FPS = 25            # Higgs codec frames per second
MAX_FRAMES = 2048   # the engine's own cap (82 s)


class EngineError(RuntimeError):
    def __init__(self, msg: str, retryable: bool = True):
        super().__init__(msg)
        self.retryable = retryable


@dataclass
class Sampling:
    temperature: float = 0.8
    top_k: int = 50
    top_p: float = 1.0

    def as_extra(self) -> dict:
        return {"temperature": float(self.temperature), "top_k": int(self.top_k), "top_p": float(self.top_p)}


def max_frames_for(expected_s: float) -> int:
    """Length cap from the text: 2x the estimate + 4 s, so a runaway take stops early instead of at 82 s."""
    return int(min(MAX_FRAMES, math.ceil(FPS * (2.0 * expected_s + 4.0))))


class Engine:
    def __init__(self, url: str | None = None, api_key: str | None = None, timeout: float | None = None):
        self.url = (url or settings.engine_url).rstrip("/")
        headers = {"Authorization": f"Bearer {api_key or settings.engine_api_key}"} if (api_key or settings.engine_api_key) else {}
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(timeout or settings.request_timeout_s, connect=10.0),
                                        headers=headers, limits=httpx.Limits(max_connections=64))

    async def close(self) -> None:
        await self.client.aclose()

    async def health(self) -> bool:
        try:
            r = await self.client.get(f"{self.url}/health", timeout=3.0)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    def _body(self, text: str, ref_wav: bytes, ref_text: str, sampling: Sampling, seed: int | None,
              max_frames: int | None, stream: bool) -> dict:
        body = {"input": text, "ref_audio": "data:audio/wav;base64," + base64.b64encode(ref_wav).decode(),
                "ref_text": ref_text, "response_format": "pcm" if stream else "wav",
                "extra_params": sampling.as_extra()}
        if seed is not None:
            body["seed"] = int(seed)
        if max_frames:
            body["max_new_tokens"] = int(max_frames)
        if stream:
            body |= {"stream": True, "stream_format": "audio"}
        return body

    async def speech(self, text: str, ref_wav: bytes, ref_text: str, sampling: Sampling, seed: int | None = None,
                     max_frames: int | None = None) -> bytes:
        try:
            r = await self.client.post(f"{self.url}/v1/audio/speech",
                                       json=self._body(text, ref_wav, ref_text, sampling, seed, max_frames, False))
        except httpx.HTTPError as e:
            raise EngineError(f"engine unreachable: {e.__class__.__name__}: {e}") from e
        if r.status_code != 200:
            raise EngineError(f"engine HTTP {r.status_code}: {r.text[:300]}", retryable=r.status_code >= 500)
        return r.content

    async def speech_stream(self, text: str, ref_wav: bytes, ref_text: str, sampling: Sampling,
                            seed: int | None = None, max_frames: int | None = None):
        """Async iterator of raw PCM s16le 24 kHz mono chunks."""
        body = self._body(text, ref_wav, ref_text, sampling, seed, max_frames, True)
        try:
            async with self.client.stream("POST", f"{self.url}/v1/audio/speech", json=body) as r:
                if r.status_code != 200:
                    raise EngineError(f"engine HTTP {r.status_code}: {(await r.aread())[:300]!r}",
                                      retryable=r.status_code >= 500)
                carry = b""
                async for chunk in r.aiter_bytes():
                    chunk = carry + chunk
                    cut = len(chunk) - (len(chunk) % 2)
                    carry = chunk[cut:]
                    if cut:
                        yield chunk[:cut]
        except httpx.HTTPError as e:
            raise EngineError(f"engine stream failed: {e.__class__.__name__}: {e}") from e
