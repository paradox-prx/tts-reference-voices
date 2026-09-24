from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pytest
import soundfile as sf
from fastapi import FastAPI

from tts_gateway.app import Gateway, create_app
from tts_gateway.backends.stub import StubBackend
from tts_gateway.config import Settings

API_KEY = "test-key"


def make_wav(seconds: float, sample_rate: int = 24000) -> bytes:
    t = np.arange(round(seconds * sample_rate)) / sample_rate
    buf = io.BytesIO()
    sf.write(buf, (0.2 * np.sin(2 * np.pi * 150 * t)).astype(np.float32), sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def write_voice(root: Path, voice_id: str, lang: str, text: str, seconds: float = 2.0,
                sha256: str | None = None) -> Path:
    folder = root / voice_id
    (folder / "references").mkdir(parents=True)
    wav = make_wav(seconds)
    (folder / "references" / "qwen3-tts.wav").write_bytes(wav)
    (folder / "voice.json").write_text(json.dumps({"label": voice_id.title(), "language": lang}))
    refs = {"qwen3-tts": {"file": "qwen3-tts.wav", "text": text, "sha256": sha256 or hashlib.sha256(wav).hexdigest()}}
    (folder / "references" / "references.json").write_text(json.dumps(refs, ensure_ascii=False))
    return folder


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("TTS_"):
            monkeypatch.delenv(key)


@pytest.fixture
def voices_dir(tmp_path: Path) -> Path:
    root = tmp_path / "voices"
    write_voice(root, "alice", "en", "This is a reference sentence for the test voice.")
    write_voice(root, "bilal", "ur", "یہ آزمائشی آواز کا حوالہ ہے۔")
    return root


@dataclass
class Harness:
    client: httpx.AsyncClient
    app: FastAPI
    stub: StubBackend

    @property
    def gw(self) -> Gateway:
        return self.app.state.gateway


async def wait_ready(client: httpx.AsyncClient, timeout_s: float = 5.0) -> None:
    async with asyncio.timeout(timeout_s):
        while (await client.get("/ready")).status_code != 200:
            await asyncio.sleep(0.02)


async def wait_for(predicate: Callable[[], bool], timeout_s: float = 5.0) -> None:
    async with asyncio.timeout(timeout_s):
        while not predicate():
            await asyncio.sleep(0.005)


Start = Callable[..., AbstractAsyncContextManager[Harness]]


@pytest.fixture
def start(voices_dir: Path) -> Start:
    """start(stub=StubBackend(...), ready=True, **settings) -> running app + authenticated client."""

    @asynccontextmanager
    async def _start(*, stub: StubBackend | None = None, ready: bool = True, **settings: Any) -> AsyncIterator[Harness]:
        settings.setdefault("api_key", API_KEY)
        stub = stub or StubBackend()
        app = create_app(Settings(voices_dir=voices_dir, **settings), backend=stub)
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test",
                                         headers={"Authorization": f"Bearer {API_KEY}"}) as client:
                if ready:
                    await wait_ready(client)
                yield Harness(client, app, stub)

    return _start


async def raw_speech(app: FastAPI, payload: dict[str, Any], disconnect: asyncio.Event,
                     on_body: asyncio.Event | None = None) -> list[dict[str, Any]]:
    """Call the ASGI app directly, so the test controls when the client disconnects."""
    body = json.dumps(payload).encode()
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"}, "http_version": "1.1", "method": "POST",
        "scheme": "http", "path": "/v1/audio/speech", "raw_path": b"/v1/audio/speech", "query_string": b"",
        "root_path": "", "client": ("127.0.0.1", 50000), "server": ("test", 80),
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
                    (b"authorization", f"Bearer {API_KEY}".encode())],
    }
    delivered = False
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        await disconnect.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)
        if on_body and message["type"] == "http.response.body" and message.get("body"):
            on_body.set()

    await app(scope, receive, send)
    return messages
