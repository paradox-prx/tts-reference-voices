"""Client for the quality-check sidecar (server/qc, `python -m tts_qc`): ASR (Whisper large-v3), speaker similarity
(WavLM) and audio checks on one take. POST /v1/qc {request_id, voice, lang, text, sample_rate, pcm_b64, checks} ->
{pass, reasons, metrics, ms}. The check is advisory: when the sidecar is down or slow the take is kept (fail open),
and the error is counted, so a QC outage never takes the speech service down with it."""

from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import Settings

OFFLOAD_BYTES = 1 << 20  # PCM above this is base64-encoded in a worker thread


@dataclass(frozen=True)
class QCResult:
    status: str  # "pass", "fail" or "error" (sidecar unreachable, timed out or answered with an error)
    reasons: tuple[str, ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)
    ms: float = 0.0
    error: str | None = None

    @property
    def failed(self) -> bool:
        return self.status == "fail"


class QCClient:
    def __init__(self, settings: Settings) -> None:
        assert settings.qc_url
        self.url, self.checks = settings.qc_url, sorted(settings.qc_checks)
        self._client = httpx.AsyncClient(base_url=settings.qc_url, trust_env=False,
                                         timeout=httpx.Timeout(settings.qc_timeout_s, connect=2.0),
                                         limits=httpx.Limits(max_connections=settings.max_inflight + 4))

    async def close(self) -> None:
        await self._client.aclose()

    async def health(self) -> dict[str, Any]:
        try:
            response = await self._client.get("/health", timeout=3.0)
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            return {"ok": response.status_code == 200, "url": self.url} | (body if isinstance(body, dict) else {})
        except (httpx.HTTPError, ValueError) as exc:
            return {"ok": False, "url": self.url, "error": f"{type(exc).__name__}: {exc}"}

    async def check(self, *, request_id: str, voice: str | None, lang: str, text: str, pcm: bytes,
                    sample_rate: int) -> QCResult:
        """One take. Speaker similarity needs a known voice, so inline takes (voice None) skip it."""
        checks = [c for c in self.checks if voice or c != "sim"]
        if len(pcm) > OFFLOAD_BYTES:
            pcm_b64 = await asyncio.to_thread(lambda: base64.b64encode(pcm).decode())
        else:
            pcm_b64 = base64.b64encode(pcm).decode()
        body = {"request_id": request_id, "voice": voice or "", "lang": lang, "text": text,
                "sample_rate": sample_rate, "pcm_b64": pcm_b64, "checks": checks}
        start = time.perf_counter()
        try:
            response = await self._client.post("/v1/qc", json=body)
            ms = (time.perf_counter() - start) * 1000
            if response.status_code != 200:
                return QCResult("error", ms=ms, error=f"HTTP {response.status_code}: {response.text[:300]}")
            answer = response.json()
            passed = answer["pass"]
            if not isinstance(passed, bool):
                raise ValueError(f"'pass' is {passed!r}")
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            return QCResult("error", ms=(time.perf_counter() - start) * 1000, error=f"{type(exc).__name__}: {exc}")
        return QCResult("pass" if passed else "fail", tuple(str(r) for r in answer.get("reasons") or ()),
                        answer.get("metrics") or {}, ms)
