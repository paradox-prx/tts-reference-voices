#!/usr/bin/env python3
"""Wait until a vLLM-Omni Qwen3-TTS engine is up and actually synthesises: poll GET /health, then run one short Base
voice-clone request and check that WAV audio comes back.

  wait_ready.py [URL] [--timeout 1200] [--voice NAME] [--ref-voice trump]

URL defaults to http://127.0.0.1:$TTS_ENGINE_PORT (8091).

The request uses the registered engine voice --voice when GET /v1/audio/voices lists it, otherwise the reference of
--ref-voice from the voices directory inline (data: URL + ref_text). No seed and no max_new_tokens, like production
traffic. The generated audio is only checked, never written anywhere. The API key comes from $TTS_ENGINE_API_KEY
(or $VLLM_API_KEY). Stdlib only. Exit 0 = ready, 1 = not ready before the deadline, 2 = configuration or request
error that waiting cannot fix.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VOICES_DIR = Path("/home/vector/tts-reference-voices/voices")
LANGUAGES = {"en": "English"}  # vLLM-Omni has no "Urdu"; everything else goes as "Auto"
TEXT = "The engine is ready to speak."


class NotReady(Exception):
    """Transient: keep waiting."""


class Fatal(Exception):
    """Waiting will not help."""


def request(url: str, key: str | None, body: dict | None = None, timeout: float = 10.0) -> tuple[int, dict, bytes]:
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()
    except (urllib.error.URLError, OSError) as exc:  # refused, reset, timeout
        raise NotReady(str(getattr(exc, "reason", exc))) from exc


def language(voices_dir: Path, voice_id: str) -> str:
    try:
        code = json.loads((voices_dir / voice_id / "voice.json").read_text()).get("language", "")
    except (OSError, ValueError):
        code = ""
    return LANGUAGES.get(code, "Auto")


def inline_reference(voices_dir: Path, voice_id: str) -> dict:
    """ref_audio (data: URL) + ref_text + language for a voice-server/v1 folder, sha256-verified."""
    folder = voices_dir / voice_id
    try:
        ref = json.loads((folder / "references" / "references.json").read_text())["qwen3-tts"]
        audio = (folder / "references" / ref["file"]).read_bytes()
    except (OSError, KeyError, ValueError) as exc:
        raise Fatal(f"voice {voice_id!r} in {voices_dir}: {exc}") from exc
    if hashlib.sha256(audio).hexdigest() != ref["sha256"]:
        raise Fatal(f"voice {voice_id!r}: reference audio does not match its sha256")
    return {"ref_audio": "data:audio/wav;base64," + base64.b64encode(audio).decode(), "ref_text": ref["text"],
            "language": language(voices_dir, voice_id)}


def registered(url: str, key: str | None, voice: str) -> bool:
    status, _, body = request(f"{url}/v1/audio/voices", key)
    if status != 200:
        raise Fatal(f"GET /v1/audio/voices -> {status}: {body[:200]!r}")
    listing = json.loads(body)
    names = {str(v.get("name", v) if isinstance(v, dict) else v).lower()
             for v in (listing.get("voices") or []) + (listing.get("uploaded_voices") or [])}
    return voice.lower() in names


def wav_seconds(data: bytes) -> float:
    """Duration of a PCM WAV; tolerates the streaming header's 0xFFFFFFFF sizes."""
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise Fatal(f"response is not a WAV file: {data[:16]!r}")
    pos, rate, block, frames = 12, 0, 0, 0.0
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if cid == b"fmt ":
            _, _, rate, _, block = struct.unpack("<HHIIH", data[pos + 8:pos + 22])
        elif cid == b"data":
            pcm = data[pos + 8:] if size == 0xFFFFFFFF else data[pos + 8:pos + 8 + size]
            if not any(pcm):
                raise Fatal("the WAV data is all silence")
            frames = len(pcm) / block if block else 0.0
            break
        pos += 8 + size + (size & 1)
    if not rate or not frames:
        raise Fatal("the WAV has no fmt or data chunk")
    return frames / rate


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?", default=f"http://127.0.0.1:{os.environ.get('TTS_ENGINE_PORT') or 8091}",
                    help="engine base URL (default %(default)s)")
    ap.add_argument("--timeout", type=float, default=1200.0, help="overall deadline in seconds (default %(default)s)")
    ap.add_argument("--voice", help="registered engine voice to use when the engine lists it")
    ap.add_argument("--ref-voice", default="trump", help="voice folder for the inline fallback (default %(default)s)")
    ap.add_argument("--voices-dir", type=Path, default=VOICES_DIR, help="voice-server/v1 folders (default %(default)s)")
    ap.add_argument("--text", default=TEXT, help="text to synthesise")
    a = ap.parse_args()
    url = a.url.rstrip("/")
    key = os.environ.get("TTS_ENGINE_API_KEY") or os.environ.get("VLLM_API_KEY") or None
    start = time.monotonic()
    deadline = start + a.timeout
    last = "no attempt yet"
    try:
        while True:
            try:
                status, _, body = request(f"{url}/health", key, timeout=5)
                if status != 200:
                    raise NotReady(f"/health -> {status}")
                health_s = time.monotonic() - start
                if a.voice and registered(url, key, a.voice):
                    fields = {"voice": a.voice, "language": language(a.voices_dir, a.voice)}
                    used = f"registered:{a.voice}"
                else:
                    fields, used = inline_reference(a.voices_dir, a.ref_voice), f"inline:{a.ref_voice}"
                payload = {"input": a.text, "task_type": "Base", "response_format": "wav", **fields}
                t0 = time.monotonic()
                status, headers, audio = request(f"{url}/v1/audio/speech", key, payload,
                                                 timeout=max(30.0, deadline - t0))
                if status in (502, 503, 504):
                    raise NotReady(f"speech -> {status}: {audio[:200]!r}")
                if status != 200:
                    raise Fatal(f"speech -> {status}: {audio[:300]!r}")
                seconds, took = wav_seconds(audio), time.monotonic() - t0
                print(f"ready: /health after {health_s:.0f} s; {seconds:.2f} s of audio in {took:.2f} s"
                      f" ({used}, {headers.get('X-VLLM-OMNI-OUTPUT-TOKENS', '?')} codec frames)")
                return 0
            except NotReady as exc:
                last = str(exc)
            if time.monotonic() + 2 > deadline:
                print(f"not ready after {a.timeout:.0f} s: {last}", file=sys.stderr)
                return 1
            time.sleep(2)
    except Fatal as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
