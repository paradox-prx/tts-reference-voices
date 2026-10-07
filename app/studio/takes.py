"""Customer takes: one generation (1 of up to 3 variations) with live events, optional live PCM streaming of the first
part while the rest generates, and the finished WAV on disk."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path

import numpy as np

from . import audio
from .engine import Engine, EngineError, max_frames_for
from .scheduler import CUSTOMER, Busy, Scheduler
from .synth import SynthRequest, _gen_part, synthesize
from .text import plan_parts


class Take:
    def __init__(self, seed: int, stream: bool, meta: dict, out_dir: Path):
        self.id = uuid.uuid4().hex[:12]
        self.seed, self.stream, self.meta = seed, stream, meta
        self.events: list[dict] = []
        self.pcm = bytearray()          # live s16le 24 kHz (streaming takes)
        self.pcm_done = False
        self.state = "queued"           # queued | running | done | error
        self.error = ""
        self.created = time.time()
        self.path = out_dir / f"{self.id}.wav"
        self.result: dict = {}
        self._cond = asyncio.Condition()

    async def emit(self, ev: dict) -> None:
        ev = {"t": round(time.time() - self.created, 3)} | ev
        async with self._cond:
            self.events.append(ev)
            self._cond.notify_all()

    async def push_pcm(self, chunk: bytes) -> None:
        async with self._cond:
            self.pcm += chunk
            self._cond.notify_all()

    async def finish_pcm(self) -> None:
        async with self._cond:
            self.pcm_done = True
            self._cond.notify_all()

    async def wait_change(self, timeout: float = 15.0) -> None:
        async with self._cond:
            try:
                await asyncio.wait_for(self._cond.wait(), timeout)
            except asyncio.TimeoutError:
                pass

    def info(self) -> dict:
        return {"id": self.id, "seed": self.seed, "state": self.state, "error": self.error, "stream": self.stream,
                "result": self.result, "wav_url": f"/api/studio/takes/{self.id}.wav" if self.state == "done" else None}


async def run_take(take: Take, engine: Engine, sched: Scheduler, req: SynthRequest) -> None:
    take.state = "running"
    try:
        if take.stream:
            res_audio, summary = await _run_streaming(take, engine, sched, req)
        else:
            res = await synthesize(engine, sched, req, on_event=take.emit)
            res_audio, summary = res.audio, res.summary()
        take.path.write_bytes(audio.wav_bytes(res_audio, req.sample_rate))
        take.result = summary | {"peaks": audio.peaks(res_audio, 600)}
        take.state = "done"
        await take.emit({"type": "done", "result": take.result})
    except Busy as e:
        take.state, take.error = "error", str(e)
        await take.emit({"type": "error", "error": take.error, "busy": True})
    except (EngineError, ValueError) as e:
        take.state, take.error = "error", str(e)
        await take.emit({"type": "error", "error": take.error})
    except Exception as e:  # noqa: BLE001
        take.state, take.error = "error", f"{e.__class__.__name__}: {e}"
        await take.emit({"type": "error", "error": take.error})
    finally:
        await take.finish_pcm()


async def _run_streaming(take: Take, engine: Engine, sched: Scheduler, req: SynthRequest):
    """Part 1 is streamed from the engine as it is generated; the other parts are generated in parallel (with QC and
    retries) and appended to the live stream in order. The streamed part cannot be retried: its audio is already
    playing. The saved WAV is the same parts, edge-trimmed, joined and loudness-normalised."""
    parts = plan_parts(req.text, req.max_part_s, req.ref.s_per_letter)
    if not parts:
        raise ValueError("empty text")
    seed = take.seed
    await take.emit({"type": "planned", "parts": [{"text": p.text, "est_s": p.est_s} for p in parts], "seed": seed})
    rest = [asyncio.create_task(_gen_part(engine, sched, req, p, i, seed, take.emit))
            for i, p in enumerate(parts) if i > 0]
    first = bytearray()

    async def waiting(pos):
        await take.emit({"type": "queued", "part": 0, "position": pos})
    try:
        async with sched.slot(CUSTOMER, req.exclusive, on_wait=waiting):
            await take.emit({"type": "part_started", "part": 0, "attempt": 0, "streaming": True})
            async for chunk in engine.speech_stream(parts[0].text, req.ref.wav, req.ref.text, req.sampling, seed,
                                                    max_frames_for(parts[0].est_s)):
                first += chunk
                await take.push_pcm(chunk)
        x0 = np.frombuffer(bytes(first), dtype="<i2").astype(np.float32) / 32768.0
        x0t = audio.trim_silence(x0)
        q = audio.measure(x0t, parts[0].est_s)
        await take.emit({"type": "part_done", "part": 0, "attempt": 0, "ok": q.ok, "qc": q.as_dict()})
        pieces, prs = [x0t], [{"text": parts[0].text, "est_s": parts[0].est_s, "seconds": round(q.seconds, 2),
                               "seed": seed, "attempts": 1, "qc": q.as_dict(), "ok": q.ok}]
        gap = np.zeros(int(req.gap_s * audio.SR), dtype=np.float32)
        for t in rest:
            x, pr = await t
            await take.push_pcm((np.clip(np.concatenate([gap, x]), -1, 1) * 32767).astype("<i2").tobytes())
            pieces.append(x)
            prs.append(pr.__dict__)
    except BaseException:
        for t in rest:
            t.cancel()
        raise
    y = audio.normalize_loudness(audio.join(pieces, req.gap_s), audio.SR, req.loudness_lufs)
    reasons = [f"part {i + 1}: {r}" for i, p in enumerate(prs) for r in p["qc"]["reasons"]]
    return y, {"seed": seed, "seconds": round(len(y) / audio.SR, 2), "ok": all(p["ok"] for p in prs),
               "reasons": reasons, "parts": prs}


class TakeStore:
    def __init__(self, out_dir: Path, ttl_h: float = 24.0):
        self.dir = out_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_h * 3600
        self.takes: dict[str, Take] = {}

    def add(self, take: Take) -> None:
        self.takes[take.id] = take
        self.gc()

    def get(self, tid: str) -> Take | None:
        return self.takes.get(tid)

    def gc(self) -> None:
        now = time.time()
        for tid, t in list(self.takes.items()):
            if now - t.created > self.ttl:
                t.path.unlink(missing_ok=True)
                del self.takes[tid]
        for p in self.dir.glob("*.wav"):
            if now - p.stat().st_mtime > self.ttl:
                p.unlink(missing_ok=True)
