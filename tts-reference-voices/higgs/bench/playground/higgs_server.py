#!/usr/bin/env python3
"""FastAPI gateway for Higgs TTS 3 (vLLM-Omni engine), configured like baseline.sh / quality_runs.sh.

Mirrors the bench setup: engine on :8095, requests carry NO task_type / language / max_new_tokens / seed
(Higgs clones from ref_audio + ref_text and detects the language), 25 Hz codec, wav output.
Sampling defaults (temperature 0.8 / top_k 50) live in the engine's deploy YAML; override per request
(e.g. temperature=1.0, top_p=0.95 for the Q2 arm).

    # engine already running on :8095
    python higgs_server.py --ref-audio references/qwen3-tts.wav --ref-text-file references/qwen3-tts.txt

    # let this script start the engine too (you supply the command, see HIGGS_ENGINE_CMD)
    HIGGS_ENGINE_CMD="vllm serve bosonai/higgs-tts-3-4b --omni --port 8095 ..." \
        python higgs_server.py --launch-engine --ref-audio ... --ref-text-file ...

Endpoints: GET /health, POST /tts {"text": "...", "stream": false, "temperature": null, "top_p": null, "top_k": null}
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
import os
import shlex
import subprocess
import time
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

ENGINE_URL = os.environ.get("HIGGS_URL", "http://127.0.0.1:8095")
MODEL = os.environ.get("HIGGS_MODEL", "bosonai/higgs-tts-3-4b")
DEPLOY = os.environ.get("HIGGS_DEPLOY", "mem080_seqs32.yaml")  # quality_runs.sh default; baseline used base.yaml
MAX_INFLIGHT = int(os.environ.get("HIGGS_MAX_INFLIGHT", "32"))  # matches max_num_seqs=32 in the deploy name
SPEECH_PATH = os.environ.get("HIGGS_SPEECH_PATH", "/v1/audio/speech")

state: dict = {}


class TTSRequest(BaseModel):
    text: str
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None


def build_payload(req: TTSRequest) -> dict:
    p = {
        "model": MODEL,
        "input": req.text,
        "ref_audio": state["ref_audio"],
        "ref_text": state["ref_text"],
        "response_format": "wav",
        "stream": req.stream,
    }
    for k in ("temperature", "top_p", "top_k"):
        v = getattr(req, k)
        if v is not None:
            p[k] = v
    return p


async def wait_engine(timeout: float = 900.0) -> None:
    t0 = time.time()
    async with httpx.AsyncClient() as c:
        while time.time() - t0 < timeout:
            with contextlib.suppress(httpx.HTTPError):
                if (await c.get(f"{ENGINE_URL}/health", timeout=3)).status_code == 200:
                    return
            await asyncio.sleep(3)
    raise RuntimeError(f"engine at {ENGINE_URL} not healthy after {timeout:.0f}s")


async def discover_speech_path() -> None:
    """Log the engine's routes; if the configured speech path is not one of them, try to find the right one."""
    try:
        r = await state["client"].get("/openapi.json", timeout=10)
        paths = [p for p, ops in r.json().get("paths", {}).items() if "post" in ops]
    except Exception as e:  # noqa: BLE001
        print(f"[gateway] could not read {ENGINE_URL}/openapi.json ({e}); using {SPEECH_PATH}", flush=True)
        return
    print(f"[gateway] engine POST routes: {paths}", flush=True)
    if SPEECH_PATH in paths:
        return
    cands = [p for p in paths if any(k in p for k in ("speech", "tts", "audio", "synth"))]
    if len(cands) == 1:
        state["speech_path"] = cands[0]
        print(f"[gateway] WARNING {SPEECH_PATH} not found on the engine, using {cands[0]}", flush=True)
    else:
        print(f"[gateway] WARNING {SPEECH_PATH} not found on the engine and no unique candidate {cands}; "
              f"set HIGGS_SPEECH_PATH", flush=True)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    proc = None
    if state["launch_engine"]:
        cmd = os.environ.get("HIGGS_ENGINE_CMD")
        if not cmd:
            raise SystemExit("--launch-engine needs HIGGS_ENGINE_CMD (the vllm-omni serve command for the engine)")
        proc = subprocess.Popen(shlex.split(cmd))
    await wait_engine()
    state["client"] = httpx.AsyncClient(base_url=ENGINE_URL, timeout=httpx.Timeout(300.0, connect=10.0),
                                        limits=httpx.Limits(max_connections=256))
    state["sem"] = asyncio.Semaphore(MAX_INFLIGHT)
    state["speech_path"] = SPEECH_PATH
    await discover_speech_path()
    try:
        yield
    finally:
        await state["client"].aclose()
        if proc:
            proc.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                proc.wait(30)


app = FastAPI(title="Higgs TTS 3 gateway", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"ok": True, "engine": ENGINE_URL, "model": MODEL, "deploy": DEPLOY, "max_inflight": MAX_INFLIGHT}


@app.post("/tts")
async def tts(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(400, "empty text")
    payload = build_payload(req)
    client: httpx.AsyncClient = state["client"]
    if not req.stream:
        async with state["sem"]:
            r = await client.post(state["speech_path"], json=payload)
        if r.status_code != 200:
            print(f"engine {r.status_code} on {state['speech_path']}: {r.text[:500]}", flush=True)
            raise HTTPException(r.status_code, r.text[:500])
        return Response(r.content, media_type="audio/wav")

    async def gen():
        async with state["sem"]:
            async with client.stream("POST", state["speech_path"], json=payload) as r:
                if r.status_code != 200:
                    raise HTTPException(r.status_code, (await r.aread()).decode()[:500])
                async for chunk in r.aiter_bytes():
                    yield chunk

    return StreamingResponse(gen(), media_type="audio/wav")


TEXT_FIELDS = ("ref_text", "text", "transcript", "transcription", "prompt_text")


def ref_text_from_json(path: Path, key: str) -> str:
    """Look up a transcript in references.json. Accepts {key: "text"}, {key: {"text": ...}}, a nested
    {"references": {...}} wrapper, or a list of entries carrying key/name/id/file/audio."""
    import json

    doc = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(doc, dict):
        for wrap in ("references", "refs", "voices"):
            if isinstance(doc.get(wrap), (dict, list)):
                doc = doc[wrap]
                break

    def stem(s: str) -> str:
        return Path(str(s)).stem

    entry, avail = None, []
    if isinstance(doc, dict):
        avail = list(doc)
        for k in (key, f"{key}.wav"):
            if k in doc:
                entry = doc[k]
                break
        else:
            entry = next((v for k, v in doc.items() if stem(k) == key), None)
    elif isinstance(doc, list):
        for it in doc:
            if not isinstance(it, dict):
                continue
            ids = [it.get(f) for f in ("key", "name", "id", "file", "audio", "path") if it.get(f)]
            avail += [stem(i) for i in ids[:1]]
            if any(stem(i) == key for i in ids):
                entry = it
                break
    if entry is None:
        raise SystemExit(f"ref key '{key}' not found in {path}; available: {avail}")
    if isinstance(entry, str):
        return entry.strip()
    if isinstance(entry, dict):
        for f in TEXT_FIELDS:
            if isinstance(entry.get(f), str) and entry[f].strip():
                return entry[f].strip()
    raise SystemExit(f"no transcript field ({'/'.join(TEXT_FIELDS)}) in the entry for '{key}': {entry!r}"[:400])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref-audio", type=Path, required=True, help="reference clip (the bench's qwen3-tts.wav)")
    ap.add_argument("--ref-json", type=Path, help="references.json holding the transcripts of the reference clips")
    ap.add_argument("--ref-key", help="key in references.json (default: the --ref-audio file stem)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--ref-text", help="transcript of the reference clip")
    g.add_argument("--ref-text-file", type=Path)
    ap.add_argument("--launch-engine", action="store_true")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    state["ref_audio"] = "data:audio/wav;base64," + base64.b64encode(a.ref_audio.read_bytes()).decode()
    if a.ref_text:
        state["ref_text"] = a.ref_text
    elif a.ref_text_file:
        state["ref_text"] = a.ref_text_file.read_text(encoding="utf-8").strip()
    elif a.ref_json:
        state["ref_text"] = ref_text_from_json(a.ref_json, a.ref_key or a.ref_audio.stem)
    else:
        ap.error("give one of --ref-json, --ref-text, --ref-text-file")
    print(f"reference: {a.ref_audio.name} | transcript ({len(state['ref_text'])} chars): {state['ref_text'][:80]}...")
    state["launch_engine"] = a.launch_engine
    uvicorn.run(app, host=a.host, port=a.port, log_level="info")


if __name__ == "__main__":
    main()