#!/usr/bin/env python3
"""Benchmark a Qwen3-TTS voice-clone server (vLLM-Omni's OpenAI-compatible /v1/audio/speech, our gateway, the plain
qwen-tts baseline, or anything that speaks the same request shape) under concurrency, across text lengths, with
streaming latency.

    python bench/bench_tts.py --voice shehbaz --size short -n 32 -c 8
    python bench/bench_tts.py --voice trump --size medium --sweep 1,2,4,8,16,32
    python bench/bench_tts.py --voice shehbaz --stream --size long --sweep 1,4,8
    python bench/bench_tts.py --voice trump --matrix                  # every pool size x the default sweep
    python bench/bench_tts.py --voice shehbaz --size prompts --takes 6 -c 16   # 6 takes per benchmark prompt
    python bench/bench_tts.py --voice shehbaz --size prompts --extra-param repetition_penalty=1.15   # patched engine
    python bench/bench_tts.py --voice shehbaz --size xlong --param non_streaming_mode=true --max-new-tokens auto
    python bench/bench_tts.py --voice trump shehbaz --voice-mode server --url http://127.0.0.1:8090   # our gateway
    python bench/bench_tts.py --voice shehbaz --voice-mode server --voice-name '{voice}-avg'   # engine custom voice
    python bench/bench_tts.py --voice trump --voice-mode nocache --size short -c 8   # reference caches defeated
    python bench/bench_tts.py --voice trump shehbaz --mix --size medium -n 16 -c 16   # both voices in one batch
    python bench/bench_tts.py --voice shehbaz --pools bench/pools/auralis_ur.json --size short medium long -n 20 -c 20

Sizes (texts from bench/pools/<lang>.json; speech at the calibrated pace, en / ur):
  short    one sentence, ~3 s                                        the user's "short (1 sentence)"
  medium   20-45 words, ~7-8 s
  long     55-70 words, ~17-18 s
  xlong    one full benchmark prompt, ~37 s / ~28 s                  the user's "medium (~30 s)"
  xxlong   two consecutive benchmark prompts joined, ~73 s / ~56 s   the user's "long (~60 s)"
  prompts  the 43 prompts of benchmarks/<set>.json (plain_text) in benchmark order, with their ids in every row
           (the same texts as xlong; -n defaults to all of them); trump -> trump_en.json, shehbaz ->
           shehbaz_ur.json, or --prompts-file (e.g. benchmarks/shehbaz_ur_expressive.json)

Voice modes (--voice-mode):
  inline   ref_audio (data: URL of voices/<id>/references/qwen3-tts.wav) + ref_text in every request (default)
  upload   POST /v1/audio/voices once per voice, then voice=<name> (a voice registered with the engine)
  server   voice=<name> only: a voice the server already knows (our gateway's voice ids, engine custom voices)
  nocache  like inline, but each request's reference WAV differs from every other in one bit, so the server's
           reference caches miss on every request: the "voice-prompt cache off" arm (see --voice-mode help)

Engine-direct request fields: --language (English | Auto | none), --param K=V (any top-level field, JSON value,
e.g. non_streaming_mode=true), --extra-param K=V (merged into extra_params: temperature, top_k, top_p, and
repetition_penalty on an engine with engine/patches applied), --max-new-tokens auto|words|N (auto = the gateway's
length cap: min(words / 2.5 x 12.5 x 2.4 + 60, the voice's pace cap) codec frames; unset = the engine's own cap and
its built-in retry).

Per request: total latency, time to first audio (--stream), audio seconds (from the returned bytes), RTF, pace
(seconds per letter and per word), token counts from x-vllm-omni-* headers, all x-* response headers, the request
fields sent (minus text and reference audio), a hash of the PCM, and a `suspect` flag with its reason when the pace
is far off the voice's expected pace (too_short: skipped or cut-off text; too_long: a loop, filler or padding). Per
run: latency and TTFA percentiles, wall time, throughput (audio seconds per wall second; and x_realtime_p90wall, the
audio finished by the time 90% of the requests had finished over that time, which one runaway cannot dominate, with
`stragglers` = requests slower than 3x the median latency), req/s, per-request RTF, error / suspect / duplicate-audio
/ retry / QC counts, pace-ratio percentiles, peak GPU memory and mean utilisation.

A run never repeats a string while the pool is large enough, and each run continues where the previous one stopped,
so numbers reflect real generation work rather than cache hits. Voices come from voices/<id>/: the Qwen reference
(references/qwen3-tts.wav) and its transcript (references.json).

Outputs (--out, default results/<timestamp>/), one folder per run, named for it
(<tag>_<voice>_<size>_c<c>_n<n>[_k<takes>][_s<seed>]_<stream|nonstream>_<voice mode>):
  <run>/audio/*.wav          every generated take (unless --no-audio), AI-labelled
  <run>/requests.jsonl       that run's requests; `file` is relative to <run>/ (while the run is in progress, and
                             after an interrupted run: requests.partial.jsonl, in completion order)
  <run>/summary.json         that run's numbers + the full config of the invocation that made it
  requests.jsonl             every request of every run in --out; `file` is relative to --out
  summary.csv / .md / .json  one row per run (the json also keeps every invocation's config)
Saved audio is rewritten as a clean RIFF file (streamed headers carry bogus sizes) with a LIST/INFO comment marking it
AI-generated; results/ is gitignored and must not be published. Reusing --out appends runs. `--estimate` prints the
runs, request counts and expected audio seconds as JSON without sending anything.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import secrets
import signal
import statistics
import struct
import subprocess
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

try:
    import httpx
except ImportError:                                           # --estimate needs no network
    httpx = None

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

REPO = Path(os.environ.get("TTS_REPO_ROOT") or Path(__file__).resolve().parents[1])
POOL_SIZES = ("short", "medium", "long", "xlong", "xxlong")
SIZES = (*POOL_SIZES, "prompts")
DEFAULT_SWEEP = (1, 2, 4, 8, 16, 32)
PROMPT_SETS = {"trump": "trump_en.json", "shehbaz": "shehbaz_ur.json"}   # --size prompts, unless --prompts-file
DEFAULT_PACE_FILE = REPO / "server" / "calibration" / "pace.json"
SUSPECT_BAND = "0.6,1.8"
TIMEOUT = {"short": 120.0, "medium": 180.0, "long": 300.0, "xlong": 420.0, "xxlong": 600.0, "prompts": 420.0}
VOICE_MODES = ("inline", "upload", "server", "nocache")
DEFAULT_VOICE_NAME = {"upload": "bench-{voice}", "server": "{voice}"}
CODEC_HZ = 12.5                                               # Qwen3-TTS-12Hz codec frames per second of audio
MIN_NEW_TOKENS, MAX_NEW_TOKENS = 96, 4096                     # the gateway's length-cap clamp (textproc.py)
AI_LABEL = "AI-generated speech (Qwen3-TTS voice clone benchmark). Not a real recording of the speaker. Do not publish."
_HAS_WORD = re.compile(r"[^\W_]")


def now_label() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def count_letters(text: str) -> int:
    """Letters and digits in any script (str.isalnum); spaces, punctuation and combining marks don't count. The same
    definition as the gateway's, so bench and gateway pace numbers compare."""
    return sum(1 for ch in text if ch.isalnum())


def count_words(text: str) -> int:
    """Whitespace-separated tokens with a letter or digit (the gateway's count_words)."""
    return sum(1 for token in text.split() if _HAS_WORD.search(token))


def words_cap(words: int) -> int:
    """The NOTES.md codec-frame budget: 2.5 words/s, 2.4x headroom, +60 frames, clamped to 96..4096 (the gateway's
    textproc.max_new_tokens_for)."""
    return max(MIN_NEW_TOKENS, min(MAX_NEW_TOKENS, math.ceil(words / 2.5 * CODEC_HZ * 2.4 + 60)))


def pace_cap(letters: int, s_per_letter: float, band_hi: float, headroom: float) -> int:
    """headroom x the suspect band's upper edge x the expected duration, + 2 s, in codec frames, clamped to 96..4096
    (the gateway's textproc.pace_cap): a take longer than the band's edge is suspect anyway."""
    frames = math.ceil(CODEC_HZ * (headroom * band_hi * s_per_letter * max(1, letters) + 2.0))
    return max(MIN_NEW_TOKENS, min(MAX_NEW_TOKENS, frames))


def length_cap(args, voice, text: str) -> int | None:
    """max_new_tokens for --max-new-tokens: auto = what the gateway sends (TTS_LENGTH_CAP=1): min(words cap, pace cap
    from the voice's expected pace); words = the words cap alone; N = fixed; None = unset (the engine's own cap)."""
    if args.max_new_tokens == "auto":
        return min(words_cap(count_words(text)), pace_cap(count_letters(text), voice.pace, args.band[1], args.cap_headroom))
    if args.max_new_tokens == "words":
        return words_cap(count_words(text))
    return args.max_new_tokens


# ------------------------------------------------------------------------------------------------ audio

def wav_layout(data: bytes) -> tuple[int, int, int, int, int] | None:
    """(offset of the first PCM byte, PCM byte count, sample rate, channels, sample width) of a WAV payload, tolerant
    of streamed size fields (0 / 0xFFFFFFFF: the data runs to the end). None while the header is incomplete."""
    if len(data) < 12:
        return None
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("not a WAV payload")
    pos, sr, ch, width = 12, None, None, None
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        body = pos + 8
        if cid == b"fmt ":
            if len(data) < body + 16:
                return None
            ch, sr = struct.unpack("<HI", data[body + 2:body + 8])
            width = struct.unpack("<H", data[body + 14:body + 16])[0] // 8
        elif cid == b"data":
            if not (sr and ch and width):
                raise ValueError("WAV data chunk before fmt chunk")
            end = len(data) if size in (0, 0xFFFFFFFF) or body + size > len(data) else body + size
            return body, end - body, sr, ch, width
        pos = body + size + (size & 1)
    return None


def wav_pcm(data: bytes) -> tuple[bytes, int, int, int]:
    """(pcm bytes, sample rate, channels, sample width) of a complete WAV payload."""
    layout = wav_layout(data)
    if layout is None:
        raise ValueError("no data chunk in WAV payload")
    off, n, sr, ch, width = layout
    pcm = data[off:off + n]
    return pcm[:len(pcm) - len(pcm) % (ch * width)], sr, ch, width


def labelled_wav(pcm: bytes, sr: int, ch: int = 1, width: int = 2, comment: str = AI_LABEL) -> bytes:
    """A clean RIFF/WAVE file with a LIST/INFO chunk (ICMT comment, ISFT software) ahead of the data chunk."""
    def sub(cid: bytes, text: str) -> bytes:
        b = text.encode("utf-8") + b"\0"
        b += b"\0" * (len(b) & 1)
        return cid + struct.pack("<I", len(b)) + b
    info = b"INFO" + sub(b"ICMT", comment) + sub(b"ISFT", "tts-reference-voices/bench/bench_tts.py")
    fmt = struct.pack("<HHIIHH", 1, ch, sr, sr * ch * width, ch * width, width * 8)
    body = (b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"LIST" + struct.pack("<I", len(info)) + info
            + b"data" + struct.pack("<I", len(pcm)) + pcm + b"\0" * (len(pcm) & 1))
    return b"RIFF" + struct.pack("<I", len(body)) + body


# ------------------------------------------------------------------------------------------------ GPU sampling

class GpuMonitor:
    """nvidia-smi every 500 ms on the selected GPUs; per run: peak memory (MiB, summed over those GPUs, including any
    other tenant's memory on them, e.g. the desktop) and mean utilisation. nvidia-smi runs in our process group, so
    whoever stops bench by group (run_plan.py) stops it too."""

    def __init__(self, gpus: str | None = None) -> None:
        self.samples: list[tuple[float, float]] = []
        self.proc, self.pending = None, {}
        cmd = ["nvidia-smi", "--query-gpu=index,memory.used,utilization.gpu", "--format=csv,noheader,nounits", "-lms", "500"]
        if gpus:
            cmd.insert(1, f"--id={gpus}")
        self.n_gpus = len(gpus.split(",")) if gpus else None
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        except FileNotFoundError:
            return
        self.lock = threading.Lock()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        # one line per GPU per tick; a tick is complete when a GPU index repeats
        for line in self.proc.stdout:
            try:
                idx, mem, util = (float(x) for x in line.strip().split(","))
            except ValueError:
                continue
            if idx in self.pending or (self.n_gpus and len(self.pending) == self.n_gpus):
                tick, self.pending = self.pending, {}
                with self.lock:
                    self.samples.append((sum(m for m, _ in tick.values()), statistics.mean(u for _, u in tick.values())))
            self.pending[idx] = (mem, util)

    def mark(self) -> int:
        return len(self.samples) if self.proc else 0

    def since(self, mark: int) -> dict:
        empty = {"gpu_mem_first_mib": None, "gpu_mem_peak_mib": None, "gpu_util_mean": None}
        if not self.proc:
            return empty
        with self.lock:
            s = self.samples[mark:]
        if not s:
            return empty
        return {"gpu_mem_first_mib": round(s[0][0]), "gpu_mem_peak_mib": round(max(m for m, _ in s)),
                "gpu_util_mean": round(statistics.mean(u for _, u in s), 1)}

    def stop(self) -> None:
        if self.proc:
            self.proc.terminate()


# ------------------------------------------------------------------------------------------------ voices and texts

class Voice:
    def __init__(self, voice_id: str, voices_dir: Path) -> None:
        folder = voices_dir / voice_id
        refs = json.loads((folder / "references" / "references.json").read_text(encoding="utf-8"))["qwen3-tts"]
        meta = json.loads((folder / "voice.json").read_text(encoding="utf-8"))
        self.id, self.lang = voice_id, meta.get("language", "en")
        self.ref_path = folder / "references" / refs["file"]
        self.ref_text = refs["text"]
        self.ref_bytes = self.ref_path.read_bytes()
        self.ref_b64 = "data:audio/wav;base64," + base64.b64encode(self.ref_bytes).decode()
        off, n, sr, ch, width = wav_layout(self.ref_bytes) or (0, 0, 0, 0, 0)
        if not n:
            raise ValueError(f"{self.ref_path}: no PCM data")
        self.ref_seconds = n / (sr * ch * width)
        self.ref_letters = count_letters(self.ref_text)
        self.ref_pace = self.ref_seconds / max(1, self.ref_letters)     # seconds per letter of the reference clip
        self.pace, self.pace_source = self.ref_pace, "reference"       # replaced by resolve_paces()
        self.engine_name: str | None = None                            # voice=<name> in upload / server mode
        self._pcm_off, self._width, self._samples = off, width, n // width
        self._nonce = secrets.randbelow(1 << 30)                        # new per process: see nocache_ref()

    def nocache_ref(self, k: int) -> str:
        """The reference as a data: URL that differs from every other request's: one PCM sample in the middle half of
        the clip has its least significant bit flipped (-90 dBFS, inaudible; the WAV stays valid). The sample index
        comes from a per-request counter k (unique for the first half-clip-length requests, ~280k) plus a random
        per-process start, so two bench processes don't replay each other's clips either."""
        data = bytearray(self.ref_bytes)
        span = max(1, self._samples // 2)
        idx = self._samples // 4 + (self._nonce + k) % span
        data[self._pcm_off + idx * self._width] ^= 1                    # little-endian: the first byte holds the LSB
        return "data:audio/wav;base64," + base64.b64encode(bytes(data)).decode()


def load_pace_file(path: Path | None) -> dict[str, float]:
    """{voice: s_per_letter} from {"<voice>": {"s_per_letter": x, ...} | x}; keys starting with _ are comments."""
    if path is None:
        return {}
    if not path.exists():
        print(f"note: pace file {path} not found; every voice uses its reference clip's pace")
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        x = v.get("s_per_letter") if isinstance(v, dict) else v
        if isinstance(x, (int, float)) and x > 0:
            out[k] = float(x)
    return out


def resolve_paces(voices: list[Voice], args) -> None:
    """Expected seconds per letter per voice: --pace override, else the pace file, else the reference clip."""
    file_paces = load_pace_file(args.pace_file)
    for v in voices:
        if v.id in args.pace:
            v.pace, v.pace_source = args.pace[v.id], "override"
        elif v.id in file_paces:
            v.pace, v.pace_source = file_paces[v.id], "file"
        else:
            v.pace, v.pace_source = v.ref_pace, "reference"


def prompt_texts(args, voice: Voice) -> tuple[list[tuple[str, str | None]], Path]:
    """The benchmark prompts (plain_text, id) for --size prompts."""
    path = args.prompts_file
    if path is None:
        name = PROMPT_SETS.get(voice.id)
        if name is None:
            found = sorted(REPO.glob(f"benchmarks/{voice.id}_*.json"), key=lambda p: (len(p.name), p.name))
            if not found:
                raise SystemExit(f"no benchmarks/{voice.id}_*.json for --size prompts; pass --prompts-file")
            path = found[0]
        else:
            path = REPO / "benchmarks" / name
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("voice") not in (None, voice.id):
        print(f"  note: {path.name} was written for voice {data.get('voice')!r}, used here for {voice.id!r}")
    return [(s["plain_text"].strip(), s.get("id")) for s in data["samples"]], path


def texts_for(args, voice: Voice, size: str) -> tuple[list[tuple[str, str | None]], str]:
    """(texts with prompt ids, source name) of a size for a voice; [] when the pools file lacks the size."""
    if size == "prompts":
        texts, path = prompt_texts(args, voice)
        return texts, path.name
    pool_file = args.pools or REPO / "bench" / "pools" / f"{voice.lang}.json"
    pools = json.loads(pool_file.read_text(encoding="utf-8"))
    return [(t.strip(), None) for t in pools.get(size) or []], pool_file.name


def warm_text(args, voice: Voice, w: int) -> str:
    for size in ("short", *POOL_SIZES[1:]):
        texts, _ = texts_for(args, voice, size)
        if texts:
            return texts[-1 - w % len(texts)][0]
    return "Hello."


# ------------------------------------------------------------------------------------------------ requests

def build_payload(args, voice: Voice, text: str, seed: int | None = None) -> tuple[dict, int | None]:
    """(JSON body, nocache counter or None). Field order: base fields, voice/reference, stream, --param, then
    --extra-param merged into extra_params, --max-new-tokens and the seed."""
    p = {"input": text, "task_type": "Base", "response_format": args.format}
    lang = args.language or ("English" if voice.lang == "en" else "Auto")
    if lang.lower() != "none":
        p["language"] = lang
    k = None
    if args.voice_mode in ("upload", "server"):
        p["voice"] = voice.engine_name
    elif args.voice_mode == "nocache":
        k = args.ref_counter
        args.ref_counter += 1
        p["ref_audio"], p["ref_text"] = voice.nocache_ref(k), voice.ref_text
    else:
        p["ref_audio"], p["ref_text"] = voice.ref_b64, voice.ref_text
    if args.stream:
        p["stream"], p["stream_format"] = True, "audio"
    p.update(args.params)
    if args.extra:
        base = p.get("extra_params") if isinstance(p.get("extra_params"), dict) else {}
        p["extra_params"] = {**base, **args.extra}
    if (cap := length_cap(args, voice, text)) is not None:
        p["max_new_tokens"] = cap
    if seed is not None:
        p["seed"] = seed
    for key in [key for key, v in p.items() if v is None]:          # --param k=null removes a field
        del p[key]
    return p, k


def request_fields(payload: dict) -> dict:
    """What a row records of its request: every field but the text and the reference audio/transcript."""
    return {k: v for k, v in payload.items() if k not in ("input", "ref_audio", "ref_text")}


async def one_request(client, url: str, payload: dict, timeout: float, fmt: str = "wav",
                      headers: dict | None = None) -> dict:
    """ttfb = first response byte; ttfa = first byte of audio samples (past the WAV header, if any). `timeout` is a
    deadline for the whole request, not only between bytes: a stream that trickles forever still ends."""
    t0 = time.perf_counter()
    st = {"ttfb": None, "ttfa": None, "status": None, "headers": {}, "error": None}
    chunks: list[bytes] = []

    async def fetch() -> None:
        got = 0
        async with client.stream("POST", url, json=payload, timeout=timeout, headers=headers) as r:
            st["status"], st["headers"] = r.status_code, dict(r.headers)
            if r.status_code != 200:
                body = (await r.aread()).decode("utf-8", "replace")
                st["error"] = f"HTTP {r.status_code}: {body[:200]}"
                return
            async for chunk in r.aiter_bytes():
                if not chunk:
                    continue
                now = time.perf_counter() - t0
                chunks.append(chunk)
                got += len(chunk)
                if st["ttfb"] is None:
                    st["ttfb"] = now
                if st["ttfa"] is None:
                    if fmt != "wav":
                        st["ttfa"] = now
                        continue
                    try:
                        layout = wav_layout((b"".join(chunks) if len(chunks) > 1 else chunk)[:8192])
                    except ValueError:                        # not a WAV after all: count the first byte
                        st["ttfa"] = now
                        continue
                    if layout is not None and got > layout[0]:
                        st["ttfa"] = now

    try:
        await asyncio.wait_for(fetch(), timeout)
    except asyncio.TimeoutError:
        st["error"] = f"TimeoutError: no complete response within {timeout:.0f} s"
    except Exception as exc:                                  # noqa: BLE001 - every failure is a result
        st["error"] = f"{type(exc).__name__}: {exc}"
    return {"latency": time.perf_counter() - t0, "ttfb": st["ttfb"], "ttfa": st["ttfa"], "status": st["status"],
            "error": st["error"], "data": b"".join(chunks), "headers": st["headers"]}


async def register_voice(client, args, voice: Voice) -> None:
    files = {"audio_sample": (voice.ref_path.name, voice.ref_bytes, "audio/wav")}
    data = {"name": voice.engine_name, "ref_text": voice.ref_text, "consent": args.consent}
    r = await client.post(args.url.rstrip("/") + "/v1/audio/voices", files=files, data=data, timeout=120.0,
                          headers=args.auth)
    print(f"voice upload {voice.engine_name!r}: HTTP {r.status_code} {r.text[:160]}")
    r.raise_for_status()


async def check_server_voice(client, args, voice: Voice) -> None:
    """--voice-mode server: warn early when GET /v1/audio/voices does not list the voice (gateway: data[].id; vLLM-Omni:
    voices[] and uploaded_voices[].name). Only a warning: some servers resolve names they don't list."""
    try:
        r = await client.get(args.url.rstrip("/") + "/v1/audio/voices", timeout=30.0, headers=args.auth)
        listing = r.json() if r.status_code == 200 else None
    except Exception as exc:                                  # noqa: BLE001
        print(f"  note: GET /v1/audio/voices failed ({type(exc).__name__}: {exc}); not checking {voice.engine_name!r}")
        return
    if not isinstance(listing, dict):
        print(f"  note: GET /v1/audio/voices -> HTTP {r.status_code}; not checking {voice.engine_name!r}")
        return
    names = set()
    for key in ("data", "voices", "uploaded_voices", "custom_voices"):
        for item in listing.get(key) or []:
            if isinstance(item, dict):
                names.update(str(item.get(f)).lower() for f in ("id", "name") if item.get(f))
            else:
                names.add(str(item).lower())
    known = voice.engine_name.lower() in names
    print(f"  server voice {voice.engine_name!r}: {'listed' if known else 'NOT listed'} by GET /v1/audio/voices"
          + ("" if known else f" (it lists {sorted(names)[:12]})"))


# ------------------------------------------------------------------------------------------------ runs

def pct(xs: list[float], p: float):
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))], 3)


@dataclass
class Lane:
    """One voice's share of a run: its texts and where the next run continues in them."""
    voice: Voice
    texts: list[tuple[str, str | None]]
    cursor: int = 0


def suspect_of(secs: float, letters: int, voice: Voice, band: tuple[float, float]) -> tuple[float | None, str | None]:
    """(pace ratio, suspect reason). The pace ratio is the take's seconds per letter over the voice's expected
    seconds per letter (1.0 = on pace). Below band[0] the take is too_short (skipped or cut-off text, or no audio at
    all), above band[1] too_long (a loop, filler or padding). Duration alone cannot see a 15-25% truncation, a
    swapped word or a loop that happens to fit the length: the ASR and audio detectors catch those, offline
    (server/eval) and online (the gateway's QC sidecar). This flag is only the cheap first screen."""
    if not letters:
        return None, None
    ratio = secs / letters / voice.pace
    return round(ratio, 3), "too_short" if ratio < band[0] else "too_long" if ratio > band[1] else None


def mode_label(args) -> str:
    """The voice mode in run names; upload/server with a non-default --voice-name add its fixed part (server-avg)."""
    if args.voice_mode not in DEFAULT_VOICE_NAME or args.voice_name == DEFAULT_VOICE_NAME[args.voice_mode]:
        return args.voice_mode
    extra = re.sub(r"[^A-Za-z0-9.]+", "-", args.voice_name.replace("{voice}", "")).strip("-")
    return f"{args.voice_mode}-{extra}" if extra else args.voice_mode


def run_name(args, lanes: list[Lane], size: str, n: int, c: int, taken: set[str], out_dir: Path) -> str:
    parts = [args.tag] if args.tag else []
    parts += ["+".join(lane.voice.id for lane in lanes), size, f"c{c}", f"n{n}"]
    if args.takes > 1:
        parts.append(f"k{args.takes}")
    if args.seed is not None:
        parts.append(f"s{args.seed}")
    parts += ["stream" if args.stream else "nonstream", mode_label(args)]
    base = re.sub(r"[^A-Za-z0-9._+=-]+", "-", "_".join(parts))
    name, i = base, 1
    while name in taken or (out_dir / name).exists():             # never overwrite an earlier run's folder
        i += 1
        name = f"{base}_r{i}"
    return name


def error_kind(msg: str) -> str:
    m = re.match(r"(HTTP \d+|[A-Za-z]+Error|bad audio)", msg or "")
    return m.group(1) if m else "other"


async def run_one(client, args, lanes: list[Lane], size: str, n: int, c: int, gpu, out_dir: Path,
                  taken: set[str], cfg: dict) -> dict:
    """n distinct texts per voice (continuing at each lane's cursor), each sent --takes times; with several lanes
    (--mix) the voices alternate, so their requests share the batch. c requests in flight."""
    for lane in lanes:
        if n > len(lane.texts):
            print(f"  note: {n} requests > {len(lane.texts)} {size} texts for {lane.voice.id}, so some repeat")
    jobs = [(li, i, k) for i in range(n) for li in range(len(lanes)) for k in range(args.takes)]
    url = args.url.rstrip("/") + "/v1/audio/speech"
    run = run_name(args, lanes, size, n, c, taken, out_dir)
    taken.add(run)
    run_dir = out_dir / run
    audio_dir = run_dir / "audio"
    run_dir.mkdir(parents=True)
    if not args.no_audio:
        audio_dir.mkdir()
        (run_dir / "AI_GENERATED_AUDIO.txt").write_text(AI_LABEL + "\n", encoding="utf-8")
    timeout = args.timeout or TIMEOUT[size] * max(1.0, c / 16)
    sem, rows = asyncio.Semaphore(c), []
    partial = open(run_dir / "requests.partial.jsonl", "a", encoding="utf-8")   # survives a killed run

    async def guarded(li: int, i: int, k: int) -> None:
        lane = lanes[li]
        voice = lane.voice
        text_idx = (lane.cursor + i) % len(lane.texts)
        text, prompt_id = lane.texts[text_idx]
        seed = None if args.seed is None else args.seed + (lane.cursor + i) * 100 + k
        async with sem:
            payload, nonce = build_payload(args, voice, text, seed)
            started = time.time()
            res = await one_request(client, url, payload, timeout, args.format, args.auth)
        words, letters = count_words(text), count_letters(text)
        headers = res["headers"]
        row = {"run": run, "tag": args.tag, "voice": voice.id, "lang": voice.lang, "size": size, "c": c,
               "idx": i, "text_idx": text_idx, "take": k, "seed": seed, "prompt_id": prompt_id,
               "voice_mode": args.voice_mode, "engine_voice": voice.engine_name, "ref_nonce": nonce,
               "words": words, "letters": letters, "chars": len(text), "max_new_tokens": payload.get("max_new_tokens"),
               "t_start": round(started, 3), "latency": round(res["latency"], 3),
               "ttfb": round(res["ttfb"], 3) if res["ttfb"] is not None and args.stream else None,
               "ttfa": round(res["ttfa"], 3) if res["ttfa"] is not None and args.stream else None,
               "status": res["status"], "error": res["error"], "bytes": len(res["data"]),
               "out_tokens": headers.get("x-vllm-omni-output-tokens"),
               "resp_headers": {h: v for h, v in headers.items() if h.startswith("x-")},
               "request": request_fields(payload), "params": args.params, "text": text}
        if not res["error"]:
            try:
                if args.format == "wav":
                    pcm, sr, ch, width = wav_pcm(res["data"])
                elif args.format == "pcm":
                    pcm, sr, ch, width = res["data"], args.pcm_rate, 1, 2
                else:
                    pcm = None
                secs = len(pcm) / (sr * ch * width) if pcm is not None else float("nan")
            except ValueError as exc:
                row["error"], secs, pcm = f"bad audio: {exc}", 0.0, None
            row["audio_s"] = round(secs, 3)
            row["rtf"] = round(res["latency"] / secs, 3) if secs else None
            row["s_per_word"] = round(secs / words, 3) if secs and words else None
            row["s_per_letter"] = round(secs / letters, 4) if secs and letters else None
            row["pace"], row["pace_source"] = round(voice.pace, 4), voice.pace_source
            if pcm is not None:
                row["pace_ratio"], row["suspect_reason"] = suspect_of(secs, letters, voice, args.band)
                row["pcm_sha256"] = hashlib.sha256(pcm).hexdigest()
            else:                                            # flac/mp3/opus: no duration without a decoder
                row["pace_ratio"], row["suspect_reason"] = None, None
            row["suspect"] = row["suspect_reason"] is not None
            if not args.no_audio and pcm is not None:
                name = (f"{voice.id}_" if len(lanes) > 1 else "") + f"{row['idx']:03d}{f'_t{k}' if args.takes > 1 else ''}.wav"
                (audio_dir / name).write_bytes(labelled_wav(pcm, sr, ch, width))
                row["file"] = f"audio/{name}"                     # relative to the run folder
        rows.append(row)
        partial.write(json.dumps(row, ensure_ascii=False) + "\n")
        partial.flush()

    mark = gpu.mark()
    started = iso()
    run_t0 = time.time()
    t0 = time.perf_counter()
    try:
        await asyncio.gather(*[guarded(li, i, k) for li, i, k in jobs])
    finally:
        partial.close()
    wall = time.perf_counter() - t0
    for lane in lanes:
        lane.cursor += n

    ok = [r for r in rows if not r["error"]]
    lat = [r["latency"] for r in ok]
    ttfa = [r["ttfa"] for r in ok if r["ttfa"] is not None]
    audio = sum(r.get("audio_s") or 0 for r in ok)
    hdr = [r["resp_headers"] for r in rows]
    retries = [int(h.get("x-tts-retries", 0) or 0) for h in hdr]
    qc = Counter(h.get("x-tts-qc") for h in hdr if h.get("x-tts-qc"))
    ratios = [r["pace_ratio"] for r in ok if r.get("pace_ratio") is not None]
    hashes = [r["pcm_sha256"] for r in ok if r.get("pcm_sha256")]
    rtfs = [r["rtf"] for r in ok if r.get("rtf") is not None]
    # robust throughput: one runaway can set a finite run's wall time, so also report the audio finished by the time
    # 90% of the requests had finished, over that time, and how many requests took > 3x the median latency
    done = sorted(((r["t_start"] + r["latency"] - run_t0, r) for r in rows), key=lambda x: x[0])
    k90 = max(1, math.ceil(0.9 * len(done)))
    t90 = done[k90 - 1][0] if done else 0.0
    audio90 = sum(r.get("audio_s") or 0 for _, r in done[:k90] if not r["error"])
    med = statistics.median(lat) if lat else None
    voices = [lane.voice for lane in lanes]
    kinds = Counter(error_kind(r["error"]) for r in rows if r["error"])
    summary = {"run": run, "folder": run, "tag": args.tag, "invocation": args.invocation, "started": started,
               "voice": "+".join(v.id for v in voices), "size": size, "c": c, "n": len(jobs), "texts": n,
               "takes": args.takes, "seed": args.seed, "stream": args.stream, "voice_mode": mode_label(args),
               "url": args.url, "ok": len(ok), "errors": len(jobs) - len(ok),
               "error_kinds": json.dumps(dict(kinds)) if kinds else "",
               "suspect": sum(bool(r.get("suspect")) for r in ok),
               "suspect_short": sum(r.get("suspect_reason") == "too_short" for r in ok),
               "suspect_long": sum(r.get("suspect_reason") == "too_long" for r in ok),
               "dup_audio": len(hashes) - len(set(hashes)),
               "retried": sum(1 for x in retries if x), "retries_total": sum(retries),
               "gw_suspect": sum(1 for h in hdr if h.get("x-tts-suspect") == "1"),
               "qc_pass": qc.get("pass", 0), "qc_fail": qc.get("fail", 0), "qc_error": qc.get("error", 0),
               "wall_s": round(wall, 2),
               "lat_mean": round(statistics.mean(lat), 3) if lat else None, "lat_p50": pct(lat, 50),
               "lat_p90": pct(lat, 90), "lat_p95": pct(lat, 95), "lat_p99": pct(lat, 99),
               "lat_max": round(max(lat), 3) if lat else None,
               "ttfa_mean": round(statistics.mean(ttfa), 3) if ttfa else None,
               "ttfa_p50": pct(ttfa, 50), "ttfa_p90": pct(ttfa, 90), "ttfa_p99": pct(ttfa, 99),
               "audio_s": round(audio, 1), "audio_mean_s": round(audio / len(ok), 2) if ok else None,
               "throughput_x_realtime": round(audio / wall, 2) if wall else None,
               "x_realtime_p90wall": round(audio90 / t90, 2) if t90 > 0 else None, "t90_s": round(t90, 2),
               "stragglers": sum(1 for r in rows if med and r["latency"] > 3 * med),
               "req_per_s": round(len(ok) / wall, 2) if wall else None,
               "rtf_mean": round(statistics.mean(rtfs), 3) if rtfs else None,
               "rtf_p50": pct(rtfs, 50), "rtf_p90": pct(rtfs, 90),
               "pace_ratio_p10": pct(ratios, 10), "pace_ratio_p50": pct(ratios, 50), "pace_ratio_p90": pct(ratios, 90),
               "pace_s_per_letter": round(voices[0].pace, 4) if len(voices) == 1 else None,
               "pace_source": voices[0].pace_source if len(voices) == 1 else None,
               "mean_words": round(statistics.mean(r["words"] for r in rows), 1),
               "language": args.language or "", "max_new_tokens": str(args.max_new_tokens or ""),
               "params": json.dumps(args.params, ensure_ascii=False) if args.params else "",
               "extra_params": json.dumps(args.extra, ensure_ascii=False) if args.extra else "",
               "meta": json.dumps(args.meta, ensure_ascii=False) if args.meta else "",
               **gpu.since(mark)}
    rows.sort(key=lambda r: (r["voice"], r["idx"], r["take"]))
    with open(run_dir / "requests.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (run_dir / "requests.partial.jsonl").unlink(missing_ok=True)
    with open(out_dir / "requests.jsonl", "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({**r, "file": f"{run}/{r['file']}"} if r.get("file") else r, ensure_ascii=False) + "\n")
    (run_dir / "summary.json").write_text(json.dumps({"summary": summary, "config": cfg}, indent=1, ensure_ascii=False)
                                          + "\n", encoding="utf-8")
    t = f" ttfa p50={summary['ttfa_p50']}s p90={summary['ttfa_p90']}s |" if args.stream else ""
    dup = f" DUPLICATE AUDIO x{summary['dup_audio']}" if summary["dup_audio"] else ""
    print(f"  {run}: ok {summary['ok']}/{len(jobs)} err {summary['errors']} suspect {summary['suspect']}"
          f" (short {summary['suspect_short']}, long {summary['suspect_long']}; pace x{summary['pace_ratio_p50']}){dup} | "
          f"lat p50={summary['lat_p50']}s p90={summary['lat_p90']}s p99={summary['lat_p99']}s |{t} "
          f"{summary['throughput_x_realtime']}x realtime (p90-wall {summary['x_realtime_p90wall']}x, stragglers "
          f"{summary['stragglers']}), {summary['req_per_s']} req/s | "
          f"gpu {summary['gpu_mem_peak_mib']} MiB {summary['gpu_util_mean']}%", flush=True)
    for r in [r for r in rows if r["error"]][:3]:
        print(f"    ERR[{r['voice']} {r['idx']}] {r['error']}")
    return summary


SUMMARY_COLS = ["run", "folder", "tag", "invocation", "started", "voice", "size", "c", "n", "texts", "takes", "seed",
                "stream", "voice_mode", "url", "ok", "errors", "error_kinds", "suspect", "suspect_short",
                "suspect_long", "dup_audio", "retried", "retries_total", "gw_suspect", "qc_pass", "qc_fail",
                "qc_error", "wall_s", "lat_mean", "lat_p50", "lat_p90", "lat_p95", "lat_p99", "lat_max",
                "ttfa_mean", "ttfa_p50", "ttfa_p90", "ttfa_p99", "audio_s", "audio_mean_s", "throughput_x_realtime",
                "x_realtime_p90wall", "t90_s", "stragglers", "req_per_s", "rtf_mean", "rtf_p50", "rtf_p90", "pace_ratio_p10", "pace_ratio_p50", "pace_ratio_p90",
                "pace_s_per_letter", "pace_source", "mean_words", "language", "max_new_tokens", "params",
                "extra_params", "meta", "gpu_mem_first_mib", "gpu_mem_peak_mib", "gpu_util_mean"]


def _typed(v: str):
    """A summary.csv cell back to its JSON type (earlier runs, when summary.json is missing)."""
    if v in ("", None):
        return None
    if v in ("True", "False"):
        return v == "True"
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    return v


def write_tables(out_dir: Path, summaries: list[dict], invocations: list[dict]) -> None:
    with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_COLS, extrasaction="ignore", restval="")
        w.writeheader()
        w.writerows(summaries)
    tmp = out_dir / "summary.json.tmp"
    tmp.write_text(json.dumps({"columns": SUMMARY_COLS, "invocations": invocations, "runs": summaries},
                              indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(out_dir / "summary.json")
    cols = ("run", "n", "ok", "errors", "suspect", "lat_p50", "lat_p90", "lat_p99", "ttfa_p50", "ttfa_p90",
            "audio_mean_s", "throughput_x_realtime", "x_realtime_p90wall", "stragglers", "rtf_p50", "req_per_s",
            "gpu_mem_peak_mib", "gpu_util_mean")
    md = ["| run | n | ok | err | suspect | lat p50 | lat p90 | lat p99 | TTFA p50 | TTFA p90 | audio s/req | x realtime "
          "| x realtime (p90 wall) | stragglers | RTF p50 | req/s | GPU MiB | GPU % |", "|" + "---|" * len(cols)]
    for s in summaries:
        md.append("| " + " | ".join(str(s.get(k)) if s.get(k) not in (None, "") else "–" for k in cols) + " |")
    (out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def load_previous(out_dir: Path) -> tuple[list[dict], list[dict]]:
    """Runs and invocation configs already in a reused --out, so the tables keep them."""
    js = out_dir / "summary.json"
    if js.exists():
        data = json.loads(js.read_text(encoding="utf-8"))
        return list(data.get("runs") or []), list(data.get("invocations") or [])
    if (out_dir / "summary.csv").exists():
        with open(out_dir / "summary.csv", encoding="utf-8") as f:
            return [{k: _typed(v) for k, v in row.items()} for row in csv.DictReader(f)], []
    return [], []


# ------------------------------------------------------------------------------------------------ arguments

def parse_param(s: str):
    k, _, v = s.partition("=")
    if not k:
        raise argparse.ArgumentTypeError(f"expected K=V, got {s!r}")
    try:
        return k, json.loads(v)
    except json.JSONDecodeError:
        return k, v


def parse_meta(s: str) -> tuple[str, str]:
    k, _, v = s.partition("=")
    if not k:
        raise argparse.ArgumentTypeError(f"--meta wants K=V, got {s!r}")
    return k, v


def parse_pace(s: str) -> tuple[str, float]:
    k, _, v = s.partition("=")
    try:
        x = float(v)
    except ValueError:
        x = 0.0
    if not k or x <= 0:
        raise argparse.ArgumentTypeError(f"--pace wants VOICE=SECONDS_PER_LETTER (> 0), got {s!r}")
    return k, x


def parse_band(s: str) -> tuple[float, float]:
    try:
        lo, hi = (float(x) for x in s.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"--suspect-band wants LO,HI, got {s!r}") from None
    if not 0 <= lo < 1 < hi:
        raise argparse.ArgumentTypeError(f"--suspect-band wants 0 <= LO < 1 < HI, got {s!r}")
    return lo, hi


def parse_cap(s: str):
    if s.lower() in ("auto", "words"):
        return s.lower()
    try:
        n = int(s)
    except ValueError:
        n = 0
    if not 1 <= n <= MAX_NEW_TOKENS:
        raise argparse.ArgumentTypeError(f"--max-new-tokens wants auto, words or 1..{MAX_NEW_TOKENS}, got {s!r}")
    return n


def parse_n_rule(s: str) -> tuple[int, float, int | None]:
    try:
        parts = s.split(":")
        lo, mult = int(parts[0]), float(parts[1])
        hi = int(parts[2]) if len(parts) > 2 and parts[2] else None
        if len(parts) > 3 or lo < 1 or mult < 0 or (hi is not None and hi < lo):
            raise ValueError
    except (ValueError, IndexError):
        raise argparse.ArgumentTypeError(f"--n-rule wants MIN:MULT[:MAX] (MIN >= 1, MAX >= MIN), got {s!r}") from None
    return lo, mult, hi


def n_for(args, c: int, texts: int, size: str) -> int:
    """Distinct texts per voice for a run at concurrency c."""
    if args.n:
        return args.n
    if args.n_rule:
        lo, mult, hi = args.n_rule
        n = max(lo, math.ceil(mult * c))
        return min(n, hi) if hi else n
    return texts if size == "prompts" else max(8, 2 * c)


def build_parser() -> argparse.ArgumentParser:
    intro, _, rest = __doc__.partition("\n\n")
    ap = argparse.ArgumentParser(description=" ".join(intro.split()), epilog=rest,
                                 formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    ap.add_argument("--url", default=os.environ.get("TTS_BENCH_URL", "http://127.0.0.1:8091"),
                    help="server base URL (default $TTS_BENCH_URL or http://127.0.0.1:8091, the engine port; our "
                         "gateway listens on :8090)")
    ap.add_argument("--voice", nargs="+", default=["shehbaz"], help="voice id(s) from voices/")
    ap.add_argument("--voices-dir", type=Path, default=Path(os.environ.get("TTS_VOICES_DIR") or REPO / "voices"),
                    help="voice-server/v1 folders (default $TTS_VOICES_DIR or <repo>/voices)")
    ap.add_argument("--size", nargs="+", choices=SIZES, default=["short"], help="text sizes (see above)")
    ap.add_argument("--prompts-file", type=Path, default=None,
                    help="benchmark JSON for --size prompts (default: benchmarks/trump_en.json for trump, "
                         "benchmarks/shehbaz_ur.json for shehbaz; e.g. benchmarks/shehbaz_ur_expressive.json)")
    ap.add_argument("-n", type=int, default=None,
                    help="distinct texts per voice per run (default: max(8, 2 x c); --size prompts: all prompts)")
    ap.add_argument("--n-rule", type=parse_n_rule, default=None, metavar="MIN:MULT[:MAX]",
                    help="n per concurrency instead of -n: max(MIN, MULT x c), capped at MAX; e.g. 16:2 = max(16, 2c). "
                         "One command then sweeps with distinct texts throughout")
    ap.add_argument("-c", type=int, default=8, help="concurrency (ignored with --sweep)")
    ap.add_argument("--sweep", default=None, help="comma-separated concurrencies, e.g. 1,2,4,8,16,32")
    ap.add_argument("--matrix", action="store_true",
                    help=f"every pool size ({', '.join(POOL_SIZES)}) x sweep {','.join(map(str, DEFAULT_SWEEP))}")
    ap.add_argument("--mix", action="store_true",
                    help="all --voice voices in ONE run, alternating, so their requests share the batch (the "
                         "mixed-batch payload-leak guard: compare speaker similarity with single-voice runs; the "
                         "summary's dup_audio counts identical PCM between requests)")
    ap.add_argument("--stream", action="store_true", help="stream=true, stream_format=audio; measures time to first audio")
    ap.add_argument("--format", choices=["wav", "pcm", "flac", "mp3", "opus"], default="wav")
    ap.add_argument("--pcm-rate", type=int, default=24000, help="sample rate of --format pcm (s16 mono)")
    ap.add_argument("--language", default=None,
                    help="override (default: English for en voices, Auto otherwise; 'none' omits the field)")
    ap.add_argument("--voice-mode", choices=VOICE_MODES, default="inline",
                    help="inline: ref_audio + ref_text in every request. upload: POST /v1/audio/voices once, then "
                         "voice=<name>. server: only voice=<name>, for a server that already knows the voice (our "
                         "gateway; vLLM-Omni custom voices from custom_voice_dir). nocache: like inline, but one "
                         "reference sample's least significant bit is flipped per request, so every request's "
                         "reference is new to the server. vllm-omni 0.28.0 caches inline references twice, and "
                         "both keys change: serving_speech.py _get_ref_audio_cache_key = sha1 of the ref_audio "
                         "string (the data: URL) for the decoded waveform (LRU 256 entries / 256 MiB), and "
                         "_make_ref_audio_artifact_cache_key = sha1(sample rate, sample count, float32 samples) "
                         "for the encoded reference (ref_code + x-vector: the API's 'artifact ready' set and "
                         "prompt_embeds_builder's LRU of 256, same key). So each nocache request decodes, ships and "
                         "re-encodes its reference on the GPU. Registered voices use utils/speaker_cache.py "
                         "SpeakerEmbeddingCache, keyed by (name, model, created_at), 512 MiB LRU")
    ap.add_argument("--voice-name", default=None, metavar="TEMPLATE",
                    help="voice name sent in upload/server mode; {voice} is replaced by the voice id (default: "
                         "'bench-{voice}' for upload, '{voice}' for server; e.g. '{voice}-avg' for an engine custom "
                         "voice with an averaged speaker embedding)")
    ap.add_argument("--consent", default="benchmark", help="consent id for POST /v1/audio/voices")
    ap.add_argument("--param", action="append", default=[], metavar="K=V",
                    help="extra TOP-LEVEL request field, JSON value (null removes a field), e.g. "
                         "non_streaming_mode=true. vLLM-Omni ignores top-level sampling fields: use --extra-param "
                         "for those (our gateway takes temperature/top_k/top_p/repetition_penalty/retries top-level)")
    ap.add_argument("--extra-param", action="append", default=[], metavar="K=V",
                    help="field merged into the request's extra_params (JSON value), e.g. temperature=0.9, top_k=50, "
                         "repetition_penalty=1.15 (the last one needs engine/patches on vLLM-Omni 0.28)")
    ap.add_argument("--max-new-tokens", type=parse_cap, default=None, metavar="auto|words|N",
                    help="codec-frame cap per request. auto = what the gateway sends: min(words cap, pace cap), words "
                         "cap = words/2.5 x 12.5 x 2.4 + 60, pace cap = 12.5 x (--cap-headroom x the suspect band's "
                         "upper edge x the voice's expected s/letter x letters + 2); both clamped to 96..4096. words = "
                         "the words cap alone. N = fixed. With a cap, a runaway ends as HTTP 500 (counted as an error). "
                         "Unset: the engine's own cap (12 frames per text token, ~190 s for a long Urdu text) and its "
                         "one built-in retry of non-streaming, unseeded runaways")
    ap.add_argument("--cap-headroom", type=float, default=1.2,
                    help="headroom of the pace cap (default 1.2, the gateway's TTS_LENGTH_CAP_HEADROOM)")
    ap.add_argument("--pools", type=Path, default=None,
                    help="custom pools JSON {short|medium|long|xlong|xxlong: [texts]} instead of "
                         "bench/pools/<lang>.json (e.g. an existing benchmark's sentence lists, for an apples-to-apples "
                         "comparison)")
    ap.add_argument("--takes", type=int, default=1, help="requests per distinct text (independent takes), for failure rates")
    ap.add_argument("--seed", type=int, default=None,
                    help="base seed; each request gets seed + 100 x position + take, where position counts the texts "
                         "this command has sent for the voice and size. Not for vLLM-Omni 0.28: its seeded output does "
                         "not reproduce even sequentially at c=1 (docs/EXPERIMENTS.md E04), a seed serialises the code "
                         "predictor of the whole batch and disables the engine's built-in retry (run_plan.py refuses "
                         "it). Repeat unseeded takes with --takes instead")
    ap.add_argument("--pace-file", default=os.environ.get("TTS_PACE_FILE") or str(DEFAULT_PACE_FILE),
                    help="expected pace per voice, JSON {voice: {\"s_per_letter\": x}} (default $TTS_PACE_FILE or "
                         "server/calibration/pace.json, which the gateway reads too; 'none' = off). A voice missing "
                         "there uses its reference clip's pace: clip seconds / letters of its transcript")
    ap.add_argument("--pace", action="append", default=[], type=parse_pace, metavar="VOICE=S_PER_LETTER",
                    help="override a voice's expected seconds per letter (calibration)")
    ap.add_argument("--suspect-band", default=SUSPECT_BAND, type=parse_band, metavar="LO,HI",
                    help=f"a take is suspect when its seconds per letter is below LO x or above HI x the voice's "
                         f"expected pace (default {SUSPECT_BAND}, the gateway's default). Letters = str.isalnum() "
                         f"characters in any script")
    ap.add_argument("--api-key", default=os.environ.get("TTS_API_KEY"),
                    help="Bearer token (default: $TTS_API_KEY; prefer the environment, argv is visible in ps)")
    ap.add_argument("--gpus", default=os.environ.get("BENCH_GPUS"), help="nvidia-smi GPU ids to sample, e.g. 0 (default: all)")
    ap.add_argument("--tag", default="", help="label prefixed to run names, e.g. rp1.15")
    ap.add_argument("--meta", action="append", default=[], type=parse_meta, metavar="K=V",
                    help="free-form label stored in every run summary (run_plan.py records phase, engine, gateway)")
    ap.add_argument("--timeout", type=float, default=None,
                    help="per-request deadline in seconds (default: by size, scaled by c/16)")
    ap.add_argument("--warmup", type=int, default=2, help="short requests per voice before the runs (not recorded)")
    ap.add_argument("--out", type=Path, default=None, help="results dir (default results/<timestamp>); reusing one appends")
    ap.add_argument("--no-audio", action="store_true", help="don't save the generated audio")
    ap.add_argument("--estimate", action="store_true",
                    help="print the runs, request counts and expected audio seconds as JSON; send nothing")
    return ap


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        args.params = dict(parse_param(p) for p in args.param)
        args.extra = dict(parse_param(p) for p in args.extra_param)
    except argparse.ArgumentTypeError as exc:
        ap.error(str(exc))
    if "extra_params" in args.params and not isinstance(args.params["extra_params"], (dict, type(None))):
        ap.error("--param extra_params=... must be a JSON object")
    args.meta = dict(args.meta)
    args.pace = dict(args.pace)
    args.band = args.suspect_band
    args.pace_file = None if str(args.pace_file).lower() in ("", "none") else Path(args.pace_file)
    args.auth = {"Authorization": f"Bearer {args.api_key}"} if args.api_key else None
    args.ref_counter = 0
    args.invocation = 0
    if args.voice_name is None and args.voice_mode in DEFAULT_VOICE_NAME:
        args.voice_name = DEFAULT_VOICE_NAME[args.voice_mode]
    if args.voice_name and len(args.voice) > 1 and "{voice}" not in args.voice_name:
        ap.error(f"--voice-name {args.voice_name!r} would give every voice the same name; use a {{voice}} template")
    if args.voice_mode in ("inline", "nocache") and args.voice_name:
        ap.error("--voice-name only applies to --voice-mode upload or server")
    if args.takes < 1 or args.warmup < 0 or (args.n is not None and args.n < 1) or args.c < 1:
        ap.error("--takes, -n and -c must be >= 1, --warmup >= 0")
    if args.n and args.n_rule:
        ap.error("-n and --n-rule exclude each other")
    if args.mix and len(args.voice) < 2:
        ap.error("--mix needs at least two --voice")
    try:
        args.sweep_list = DEFAULT_SWEEP if args.matrix and not args.sweep else \
            tuple(int(x) for x in args.sweep.split(",")) if args.sweep else (args.c,)
    except ValueError:
        ap.error(f"--sweep wants comma-separated integers, got {args.sweep!r}")
    if min(args.sweep_list) < 1:
        ap.error("concurrencies must be >= 1")
    args.sizes = POOL_SIZES if args.matrix else tuple(dict.fromkeys(args.size))
    return args


def load_voices(args) -> list[Voice]:
    voices = [Voice(v, args.voices_dir) for v in args.voice]
    resolve_paces(voices, args)
    for v in voices:
        v.engine_name = args.voice_name.format(voice=v.id) if args.voice_name else None
    return voices


@dataclass
class Planned:
    group: list[Voice]          # one voice, or all of them with --mix
    size: str
    lanes: list[Lane] | None    # None: a voice has no texts of this size (the source lacks it)
    source: str
    c: int = 0
    n: int = 0


def plan_runs(args, voices: list[Voice]):
    """Every run in execution order: voice (group) -> size -> concurrency. Lanes are shared by the runs of one size,
    so each run continues in the texts where the previous one stopped."""
    groups = [voices] if args.mix else [[v] for v in voices]
    for group in groups:
        for size in args.sizes:
            lanes, sources = [], []
            for v in group:
                texts, source = texts_for(args, v, size)
                lanes.append(Lane(v, texts))
                sources.append(source)
            if any(not lane.texts for lane in lanes):
                yield Planned(group, size, None, ", ".join(dict.fromkeys(sources)))
                continue
            for c in args.sweep_list:
                n = n_for(args, c, min(len(lane.texts) for lane in lanes), size)
                yield Planned(group, size, lanes, ", ".join(dict.fromkeys(sources)), c, n)


def estimate(argv: list[str] | None = None) -> dict:
    """What the command would send, without sending it: per run the voice, size, c, n, takes, requests and the
    expected audio seconds (letters x the voice's expected pace); plus warm-up requests."""
    args = parse_args(argv)
    voices = load_voices(args)
    runs, warm_s = [], 0.0
    for v in voices:
        for w in range(args.warmup):
            warm_s += count_letters(warm_text(args, v, w)) * v.pace
    for p in plan_runs(args, voices):
        if p.lanes is None:
            runs.append({"voice": "+".join(v.id for v in p.group), "size": p.size, "skipped": f"not in {p.source}"})
            continue
        letters_s = 0.0
        for lane in p.lanes:
            for i in range(p.n):
                text, _ = lane.texts[(lane.cursor + i) % len(lane.texts)]
                letters_s += count_letters(text) * lane.voice.pace * args.takes
            lane.cursor += p.n
        runs.append({"voice": "+".join(v.id for v in p.group), "size": p.size, "c": p.c, "n": p.n,
                     "takes": args.takes, "requests": p.n * args.takes * len(p.group), "audio_s": round(letters_s, 1),
                     "stream": args.stream, "seeded": args.seed is not None, "voice_mode": args.voice_mode,
                     "timeout_s": args.timeout or TIMEOUT[p.size] * max(1.0, p.c / 16)})
    return {"runs": runs, "requests": sum(r.get("requests", 0) for r in runs),
            "warmup_requests": args.warmup * len(voices) + (len(voices) if args.voice_mode == "upload" else 0),
            "audio_s": round(sum(r.get("audio_s", 0) for r in runs), 1), "warmup_audio_s": round(warm_s, 1)}


def config_of(args) -> dict:
    skip = {"api_key", "auth", "ref_counter", "band", "sweep_list", "sizes", "param", "extra_param", "suspect_band"}
    cfg = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items() if k not in skip}
    cfg.update(suspect_band=list(args.band), sweep=list(args.sweep_list), sizes=list(args.sizes), started=iso(),
               argv=sys.argv[1:], api_key_set=bool(args.api_key), bench_sha256=hashlib.sha256(
                   Path(__file__).read_bytes()).hexdigest())
    if "--api-key" in cfg["argv"]:
        cfg["argv"] = [("<redacted>" if cfg["argv"][i - 1] == "--api-key" else a) for i, a in enumerate(cfg["argv"])]
    cfg["argv"] = [a if not a.startswith("--api-key=") else "--api-key=<redacted>" for a in cfg["argv"]]
    return cfg


def _terminate(signum, frame) -> None:
    raise SystemExit(128 + signum)                            # run the finally blocks (stop nvidia-smi, keep tables)


async def main() -> None:
    args = parse_args()
    if args.estimate:
        print(json.dumps(estimate(sys.argv[1:]), indent=1))
        return
    if httpx is None:
        raise SystemExit("bench_tts.py needs httpx (pip install httpx)")
    voices = load_voices(args)
    out_dir = args.out or REPO / "results" / now_label()
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries, invocations = load_previous(out_dir)             # --out reused: keep earlier runs in the tables
    args.invocation = len(invocations)
    cfg = config_of(args)
    cfg["voices"] = {v.id: {"lang": v.lang, "ref": v.ref_path.name, "ref_seconds": round(v.ref_seconds, 3),
                            "ref_letters": v.ref_letters, "ref_pace": round(v.ref_pace, 4), "pace": round(v.pace, 4),
                            "pace_source": v.pace_source, "engine_name": v.engine_name} for v in voices}
    invocations.append(cfg)
    if not args.no_audio:
        (out_dir / "AI_GENERATED_AUDIO.txt").write_text(AI_LABEL + "\n", encoding="utf-8")
    for v in voices:
        print(f"voice {v.id} ({v.lang}): ref {v.ref_path.name} {v.ref_seconds:.2f} s / {v.ref_letters} letters; "
              f"expected pace {v.pace:.4f} s/letter ({v.pace_source}); suspect outside "
              f"{args.band[0]}-{args.band[1]} x" + (f"; voice={v.engine_name!r}" if v.engine_name else ""))
    signal.signal(signal.SIGTERM, _terminate)
    gpu = GpuMonitor(args.gpus)
    taken = {s.get("run") for s in summaries}
    limits = httpx.Limits(max_connections=max(args.sweep_list) + 8, max_keepalive_connections=max(args.sweep_list) + 8)
    try:
        async with httpx.AsyncClient(limits=limits, trust_env=False) as client:
            ready: set[str] = set()
            for p in plan_runs(args, voices):
                for voice in p.group:
                    if voice.id in ready:
                        continue
                    ready.add(voice.id)
                    if args.voice_mode == "upload":
                        await register_voice(client, args, voice)
                    elif args.voice_mode == "server":
                        await check_server_voice(client, args, voice)
                    for w in range(args.warmup):
                        payload, _ = build_payload(args, voice, warm_text(args, voice, w))
                        res = await one_request(client, args.url.rstrip("/") + "/v1/audio/speech", payload,
                                                TIMEOUT["short"], args.format, args.auth)
                        print(f"warmup {voice.id} {w + 1}: {res['latency']:.2f}s {res['error'] or 'ok'}")
                if p.lanes is None:
                    print(f"  skip {'+'.join(v.id for v in p.group)} {p.size}: not in {p.source}")
                    continue
                if p.c == args.sweep_list[0]:
                    print(f"{'+'.join(v.id for v in p.group)} {p.size} ({p.source}): " + ", ".join(
                        f"{lane.voice.id} {len(lane.texts)} texts" for lane in p.lanes))
                summaries.append(await run_one(client, args, p.lanes, p.size, p.n, p.c, gpu, out_dir, taken, cfg))
                write_tables(out_dir, summaries, invocations)
    finally:
        gpu.stop()
        write_tables(out_dir, summaries, invocations)
    print(f"\nresults: {out_dir}\n" + (out_dir / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    asyncio.run(main())
