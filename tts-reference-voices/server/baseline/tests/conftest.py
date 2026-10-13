"""Fixtures: a synthetic voices dir, the app wired to FakeTTS, and an httpx client that runs the app's lifespan."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import io
import json
import sys
from pathlib import Path

import httpx
import numpy as np
import pytest
import soundfile as sf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import qwen_tts_server as srv  # noqa: E402
from fake_qwen_tts import FakeTTS  # noqa: E402


def wav_bytes(seconds: float, sr: int = 24000, amp: float = 0.3, freq: float = 200.0) -> bytes:
    t = np.arange(int(seconds * sr)) / sr
    buf = io.BytesIO()
    sf.write(buf, (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32), sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def data_url(data: bytes) -> str:
    return "data:audio/wav;base64," + base64.b64encode(data).decode()


def make_voice(root: Path, vid: str, lang: str, ref_s: float, clips: list[tuple[float, float]], sha: bool = True,
               text: str = "hello world this is the reference") -> None:
    folder = root / vid
    (folder / "references").mkdir(parents=True)
    ref = wav_bytes(ref_s)
    (folder / "references" / "qwen3-tts.wav").write_bytes(ref)
    entry = {"file": "qwen3-tts.wav", "text": text}
    if sha:
        entry["sha256"] = hashlib.sha256(ref).hexdigest()
    (folder / "references" / "references.json").write_text(json.dumps({"qwen3-tts": entry}), encoding="utf-8")
    (folder / "voice.json").write_text(json.dumps({"language": lang}), encoding="utf-8")
    names = []
    for i, (secs, amp) in enumerate(clips, 1):
        name = f"{vid}_{i:02d}.wav"
        (folder / name).write_bytes(wav_bytes(secs, sr=48000, amp=amp))
        names.append({"file": name, "text": "clip"})
    (folder / "clips.json").write_text(json.dumps({"clips": names}), encoding="utf-8")


@pytest.fixture
def voices_dir(tmp_path: Path) -> Path:
    root = tmp_path / "voices"
    make_voice(root, "alpha", "en", 3.0, [(1.5, 0.2), (2.0, 0.6)])
    make_voice(root, "beta", "ur", 2.0, [(1.2, 0.4)], sha=False, text="اردو حوالہ متن")
    return root


def make_args(voices_dir: Path, *extra: str, warmup: bool = False):
    return srv.build_parser().parse_args(["--device", "cpu", "--voices-dir", str(voices_dir),
                                          *([] if warmup else ["--no-warmup"]), *extra])


class Harness:
    def __init__(self, app, fake: FakeTTS, client: httpx.AsyncClient) -> None:
        self.app, self.fake, self.client = app, fake, client

    @property
    def st(self):
        return self.app.state.st

    async def speech(self, **body):
        body.setdefault("task_type", "Base")
        return await self.client.post("/v1/audio/speech", json=body)


@pytest.fixture
def make_harness(voices_dir):
    """async with make_harness(*cli_args, fake=FakeTTS(...)) as h: ..."""

    @contextlib.asynccontextmanager
    async def factory(*extra: str, fake: FakeTTS | None = None, loader=None, wait_ready: bool = True,
                      warmup: bool = False):
        fake = fake or FakeTTS()
        args = make_args(voices_dir, *extra, warmup=warmup)
        app = srv.create_app(args, loader=loader or (lambda a: (fake, {"model_path": "fake", "load_s": 0.0})))
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30) as client:
                h = Harness(app, fake, client)
                if wait_ready:
                    for _ in range(500):
                        r = await client.get("/health")
                        if r.status_code == 200 or h.st.error:
                            break
                        await asyncio.sleep(0.01)
                    assert h.st.ready, h.st.error
                yield h

    return factory
