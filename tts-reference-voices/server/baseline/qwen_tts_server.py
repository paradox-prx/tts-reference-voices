#!/usr/bin/env python3
"""Plain qwen-tts (transformers) baseline server for Qwen3-TTS-12Hz-1.7B-Base voice cloning.

It speaks the vLLM-Omni 0.28 /v1/audio/speech request shape (docs/research/omni-source.md finding 5) so that
bench/bench_tts.py can compare vLLM-Omni against the stock qwen-tts 0.1.1 package on the same requests:

    POST   /v1/audio/speech          JSON: input, voice | ref_audio (+ref_text), task_type Base, language,
                                     response_format wav|pcm, max_new_tokens, seed, non_streaming_mode,
                                     x_vector_only_mode, extra_params {temperature, top_k, top_p, repetition_penalty}
    GET    /v1/audio/voices          {"voices": [...], "uploaded_voices": [...]}
    POST   /v1/audio/voices          multipart: audio_sample, name, consent, ref_text (optional; none = x-vector only)
    DELETE /v1/audio/voices/{name}
    GET    /health                   200 {"status": "healthy"} once the model is loaded and the voices are prepared
    GET    /v1/baseline/info         config, versions, voice preparation numbers, cache/batch counters

Run (see server/baseline/README.md):
    CUDA_VISIBLE_DEVICES=0 server/venvs/qwentts/bin/python server/baseline/qwen_tts_server.py --port 8093

Every response carrying audio is AI-labelled: WAV LIST/INFO ICMT comment plus the X-AI-Generated: true header.
"""

from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # before anything imports huggingface_hub: never touch the network

import argparse
import asyncio
import contextlib
import dataclasses
import importlib.metadata
import json
import logging
import re
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, tzinfo
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine as eng  # noqa: E402
from wavlabel import float_to_pcm16, pcm_to_wav  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

logger = logging.getLogger("qwen_tts_baseline")
_tz: tzinfo = ZoneInfo("Asia/Karachi")
_REQUEST_ID = re.compile(r"[A-Za-z0-9._:/+=-]{1,128}")
URDU_NAMES = {"urdu", "ur", "ur-pk", "ur_pk"}


# ------------------------------------------------------------------------------------------------ logging

class JsonFormatter(logging.Formatter):
    """One JSON object per line; `ts` is local time in the configured zone (default Asia/Karachi) with its offset."""

    def format(self, record: logging.LogRecord) -> str:
        fields = getattr(record, "fields", None)
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, _tz).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
        }
        if fields is None:
            entry |= {"event": "log", "logger": record.name, "msg": record.getMessage()}
        else:
            entry |= {"event": record.getMessage(), **fields}
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO", tz: str | None = None) -> None:
    global _tz
    if tz:
        _tz = ZoneInfo(tz)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    for name in ("qwen_tts_baseline", "uvicorn", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers[:] = [handler]
        lg.setLevel(level.upper())
        lg.propagate = False


def event(_event: str, _level: int = logging.INFO, /, _exc: BaseException | None = None, **fields: Any) -> None:
    """One JSON log line: {"ts", "level", "event": _event, **fields}."""
    logger.log(_level, _event, extra={"fields": fields}, exc_info=_exc)


# ------------------------------------------------------------------------------------------------ CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False,
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8093)
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help="hub id (resolved to its local HF-cache snapshot; HF_HUB_OFFLINE=1) or a local model dir")
    ap.add_argument("--device", default="cuda:0", help="torch device, e.g. cuda:0 or cpu")
    ap.add_argument("--dtype", default="bfloat16", choices=["bfloat16", "float32"],
                    help="float16 is not offered: Qwen3-TTS logits overflow fp16 (qwen-tts #43, PR #355)")
    ap.add_argument("--attn", default="sdpa", choices=["sdpa", "eager", "flash_attention_2"],
                    help="attention implementation (FA2 gave NaN logits in qwen-tts #333)")
    ap.add_argument("--voices-dir", type=Path, default=REPO / "voices", help="repo voices: <dir>/<id>/references/")
    ap.add_argument("--max-batch", type=int, default=8, help="rows per generate call; 1 = sequential")
    ap.add_argument("--batch-window-ms", type=float, default=20.0,
                    help="when the worker is idle, how long the oldest request waits for batch mates")
    ap.add_argument("--no-prompt-cache", action="store_true",
                    help="run create_voice_clone_prompt for every request (the 'voice-prompt cache off' arm)")
    ap.add_argument("--prompt-cache-size", type=int, default=256,
                    help="LRU entries for inline/uploaded references (repo voices are pinned on top)")
    ap.add_argument("--avg-embedding", action="store_true",
                    help="repo voices: speaker embedding = mean over the voice's clips, rescaled to the mean clip norm")
    ap.add_argument("--length-policy", choices=["error", "truncate"], default="error",
                    help="row without EOS inside its cap: 'error' = vLLM-Omni 0.28 (one retry if the request had no "
                         "seed and no max_new_tokens, else HTTP 500); 'truncate' = return the capped audio")
    ap.add_argument("--no-length-retry", action="store_true", help="with --length-policy error: never retry")
    ap.add_argument("--qwen-regex", action="store_true",
                    help="reload the text tokenizer with fix_mistral_regex=False (Qwen2 pre-tokenizer regex). Default "
                         "is stock qwen-tts, which loads the local snapshot with fix_mistral_regex=True and, under "
                         "transformers 4.57.3, gets the Mistral regex (qwen-tts-internals finding 19)")
    ap.add_argument("--max-queue", type=int, default=512, help="pending requests before HTTP 503 (0 = unlimited)")
    ap.add_argument("--threads", type=int, default=0, help="torch.set_num_threads (0 = torch default); for CPU runs")
    ap.add_argument("--no-warmup", action="store_true", help="skip the one short warm-up generation at startup")
    ap.add_argument("--log-level", default="INFO")
    ap.add_argument("--log-tz", default="Asia/Karachi", help="time zone of the log timestamps")
    return ap


# ------------------------------------------------------------------------------------------------ model loading

def load_qwen_tts(args: argparse.Namespace) -> tuple[Any, dict]:
    """Qwen3TTSModel.from_pretrained on the local snapshot (runs on the worker thread)."""
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from qwen_tts import Qwen3TTSModel

    # transformers warns "Setting `pad_token_id` to `eos_token_id`" as plain text on every generate call; keep stdout
    # JSON-only (errors still show)
    transformers.logging.set_verbosity_error()
    if args.threads:
        torch.set_num_threads(args.threads)
    t0 = time.perf_counter()
    path = args.model if Path(args.model).is_dir() else snapshot_download(args.model, local_files_only=True)
    tts = Qwen3TTSModel.from_pretrained(path, device_map=args.device, dtype=getattr(torch, args.dtype),
                                        attn_implementation=args.attn)
    info = {"model_path": str(path), "revision": Path(path).name, "tokenizer_regex": "stock (fix_mistral_regex=True)"}
    if args.qwen_regex:
        from transformers import AutoProcessor

        tts.processor = AutoProcessor.from_pretrained(path, fix_mistral_regex=False)
        info["tokenizer_regex"] = "qwen2 (fix_mistral_regex=False)"
    info["load_s"] = round(time.perf_counter() - t0, 2)
    info["attn_implementation"] = getattr(tts.model.config, "_attn_implementation", args.attn)
    if str(args.device).startswith("cuda"):
        info["cuda_mem_after_load_gib"] = round(torch.cuda.memory_allocated() / 2**30, 3)
    return tts, info


def versions() -> dict[str, str | None]:
    out = {}
    for pkg in ("qwen-tts", "transformers", "torch", "torchaudio", "accelerate", "tokenizers", "fastapi", "uvicorn",
                "numpy", "soundfile", "librosa"):
        try:
            out[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            out[pkg] = None
    try:
        import torch

        out["torch_cuda"] = torch.version.cuda
    except Exception:  # noqa: BLE001
        pass
    out["python"] = sys.version.split()[0]
    return out


# ------------------------------------------------------------------------------------------------ API

class ApiError(Exception):
    def __init__(self, status: int, message: str, err_type: str | None = None) -> None:
        super().__init__(message)
        self.status, self.message = status, message
        self.err_type = err_type or {400: "BadRequestError", 404: "NotFoundError", 503: "ServiceUnavailableError"}.get(
            status, "InternalServerError")


def error_response(status: int, message: str, err_type: str | None = None, headers: dict | None = None) -> JSONResponse:
    """vLLM's ErrorResponse shape: {"error": {"message", "type", "param", "code"}}."""
    e = ApiError(status, message, err_type)
    return JSONResponse({"error": {"message": message, "type": e.err_type, "param": None, "code": status}},
                        status_code=status, headers=headers)


class SpeechRequest(BaseModel):
    """vLLM-Omni 0.28 OpenAICreateSpeechRequest fields. Unknown fields are ignored (and logged once), like vLLM-Omni."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    input: str
    model: str | None = None
    voice: str | None = Field(default=None, validation_alias=AliasChoices("voice", "speaker"))
    instructions: str | None = None
    response_format: str = "wav"
    speed: float | None = 1.0
    stream: bool = False
    stream_format: str | None = None
    task_type: str | None = None
    language: str | None = None
    ref_audio: str | None = None
    ref_text: str | None = None
    x_vector_only_mode: bool | None = None
    speaker_embedding: Any = None
    max_new_tokens: int | None = None
    seed: int | None = None
    initial_codec_chunk_frames: int | None = None
    non_streaming_mode: bool | None = None
    extra_params: dict[str, Any] | None = None
    word_timestamps: bool = False


SAMPLING_KEYS = {"temperature": float, "top_k": int, "top_p": float, "repetition_penalty": float}
IGNORED_FIELDS = ("model", "instructions", "stream_format", "initial_codec_chunk_frames")


def _first_error(exc: ValidationError) -> str:
    err = exc.errors()[0]
    loc = ".".join(str(x) for x in err.get("loc", ())) or "body"
    return f"{loc}: {err.get('msg')}"


@dataclasses.dataclass
class State:
    args: argparse.Namespace
    loader: Callable[[argparse.Namespace], tuple[Any, dict]]
    executor: ThreadPoolExecutor
    engine: eng.Engine | None = None
    batcher: eng.Batcher | None = None
    voices: dict[str, eng.Reference] = dataclasses.field(default_factory=dict)   # repo voices by lower-case id
    uploaded: dict[str, dict] = dataclasses.field(default_factory=dict)          # lower-case name -> meta + ref
    ready: bool = False
    error: str | None = None
    startup: dict = dataclasses.field(default_factory=dict)
    logged_once: set = dataclasses.field(default_factory=set)
    tasks: list = dataclasses.field(default_factory=list)
    server: Any = None          # uvicorn.Server, to exit when startup fails
    upload_lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)

    def once(self, key: str, name: str, **fields: Any) -> None:
        if key not in self.logged_once:
            self.logged_once.add(key)
            event(name, logging.WARNING, **fields)


def normalize_language(st: State, lang: str | None, default: str) -> str:
    if lang is None or not lang.strip():
        return default
    name = lang.strip().title()
    if name.lower() in URDU_NAMES:
        st.once("lang:urdu", "language_mapped", requested=lang, used="Auto",
                note="Urdu is not a Qwen3-TTS language; Auto sets no language tag")
        return "Auto"
    if name not in st.engine.languages:
        raise ApiError(400, f"Invalid language '{name}'. Supported: {', '.join(st.engine.languages)}")
    return name


def build_sampling(st: State, extra: dict[str, Any] | None) -> eng.Sampling:
    d = st.engine.defaults
    if not extra:
        return d
    if not isinstance(extra, dict):
        raise ApiError(400, "extra_params must be an object")
    values = dataclasses.asdict(d)
    for key, val in extra.items():
        if key not in SAMPLING_KEYS:
            st.once(f"extra:{key}", "extra_param_ignored", field=key,
                    note="extra_params supports temperature, top_k, top_p, repetition_penalty")
            continue
        typ = SAMPLING_KEYS[key]
        if isinstance(val, bool) or not isinstance(val, (int, float)) or (typ is int and float(val) != int(val)):
            raise ApiError(400, f"extra_params.{key} must be a number" + (" (integer)" if typ is int else ""))
        values[key] = typ(val)
    s = eng.Sampling(**values)
    if not s.temperature > 0:
        raise ApiError(400, "extra_params.temperature must be > 0")
    if s.top_k < 0:
        raise ApiError(400, "extra_params.top_k must be >= 0")
    if not 0 < s.top_p <= 1:
        raise ApiError(400, "extra_params.top_p must be in (0, 1]")
    if not s.repetition_penalty > 0:
        raise ApiError(400, "extra_params.repetition_penalty must be > 0")
    return s


async def build_job(st: State, req: SpeechRequest, rid: str) -> eng.Job:
    """Validate a speech request the way vLLM-Omni does (where it applies) and turn it into a Job."""
    for key in sorted(req.model_extra or {}):
        st.once(f"unknown:{key}", "unknown_field_ignored", field=key)
    for key in IGNORED_FIELDS:
        if getattr(req, key) is not None:
            st.once(f"ignored:{key}", "field_ignored", field=key, note="accepted but has no effect in the baseline")
    if req.stream:
        raise ApiError(400, "streaming not supported by the qwen-tts baseline")
    if req.task_type not in (None, "Base"):
        raise ApiError(400, f"task_type '{req.task_type}' is not supported by the qwen-tts baseline (Base voice clone "
                            "only)")
    text = req.input.strip()  # a leading newline would shift qwen-tts' text slice (qwen-tts-internals finding 20)
    if not text:
        raise ApiError(400, "Input text cannot be empty")
    fmt = (req.response_format or "wav").lower()
    if fmt not in ("wav", "pcm"):
        raise ApiError(400, f"response_format '{req.response_format}' is not supported by the qwen-tts baseline "
                            "(wav, pcm)")
    if req.speed not in (None, 1.0):
        raise ApiError(400, "speed is not supported by the qwen-tts baseline (only 1.0)")
    if req.word_timestamps:
        raise ApiError(400, "word_timestamps is not supported by the qwen-tts baseline")
    if req.speaker_embedding is not None:
        raise ApiError(400, "speaker_embedding is not supported by the qwen-tts baseline; send ref_audio or a voice")
    if req.max_new_tokens is not None:
        if req.max_new_tokens < 1:
            raise ApiError(400, "max_new_tokens must be at least 1")
        if req.max_new_tokens > eng.MAX_NEW_TOKENS_MAX:
            raise ApiError(400, f"max_new_tokens cannot exceed {eng.MAX_NEW_TOKENS_MAX}")
    sampling = build_sampling(st, req.extra_params)

    ref: eng.Reference | None = None
    if req.voice is not None:
        name = req.voice.strip().lower()
        ref = st.voices.get(name) or (st.uploaded.get(name) or {}).get("ref")
        if ref is None and req.ref_audio is None:
            known = sorted(set(st.voices) | {m["name"] for m in st.uploaded.values()})
            raise ApiError(400, f"Unknown voice '{req.voice}'. Available: {', '.join(known)}")
        if ref is not None and (req.ref_audio is not None or req.ref_text is not None):
            st.once("voice+ref", "ref_ignored_for_voice",
                    note="voice names a known voice; its stored reference is used, ref_audio/ref_text are ignored")
    if ref is None:
        if req.ref_audio is None:
            raise ApiError(400, "Base task requires 'ref_audio' or a known 'voice' for voice cloning")
        try:
            data = eng.decode_ref_audio_string(req.ref_audio)
            ref = await asyncio.to_thread(eng.make_reference, data, req.ref_text, bool(req.x_vector_only_mode),
                                          "inline")
        except ValueError as exc:
            raise ApiError(400, str(exc)) from None
    elif req.x_vector_only_mode:
        ref = ref.as_x_vector_only()
    language = normalize_language(st, req.language, ref.language)
    return eng.Job(rid=rid, text=text, language=language, ref=ref, sampling=sampling,
                   non_streaming_mode=bool(req.non_streaming_mode), max_new_tokens=req.max_new_tokens, seed=req.seed)


def request_id(header: str | None) -> str:
    return header if header and _REQUEST_ID.fullmatch(header) else uuid.uuid4().hex


def _validate_voice_name(name: str) -> str:
    trimmed = (name or "").strip()
    if not trimmed or trimmed in (".", "..") or any(c in trimmed for c in "/\\\x00"):
        raise ApiError(400, f"Invalid voice name {name!r}: must be non-empty, no path separators or NUL")
    return trimmed


# ------------------------------------------------------------------------------------------------ app

def create_app(args: argparse.Namespace, loader: Callable | None = None) -> FastAPI:
    st = State(args=args, loader=loader or load_qwen_tts,
               executor=ThreadPoolExecutor(max_workers=1, thread_name_prefix="qwen-tts-worker"))

    async def startup() -> None:
        loop = asyncio.get_running_loop()
        run = lambda fn, *a: loop.run_in_executor(st.executor, fn, *a)  # noqa: E731 - everything model-side: 1 thread
        t0 = time.perf_counter()
        try:
            tts, info = await run(st.loader, args)
            engine = eng.Engine(tts, prompt_cache=not args.no_prompt_cache, cache_size=args.prompt_cache_size)
            st.startup |= {"model": info, "generation_config": engine.generation_config,
                           "languages": engine.languages, "samples_per_frame": engine.spf}
            voices = await asyncio.to_thread(eng.load_repo_voices, args.voices_dir)
            if not voices:
                raise RuntimeError(f"no voices with a references.json 'qwen3-tts' entry under {args.voices_dir}")
            prep = []
            for v in voices:
                ref, stats = await run(engine.prepare_voice, v, args.avg_embedding)
                st.voices[v.id.lower()] = ref
                prep.append(stats)
                event("voice_prepared", **stats)
            st.startup["voices"] = prep
            if not args.no_warmup:
                ref = next(iter(st.voices.values()))
                job = eng.Job(rid="warmup", text="Hello.", language=ref.language, ref=ref, sampling=engine.defaults,
                              max_new_tokens=24)
                t = time.perf_counter()
                res = (await run(engine.run_batch, [job]))[0]
                if isinstance(res, BaseException):
                    raise res
                st.startup["warmup"] = {"ms": round((time.perf_counter() - t) * 1000, 1), "voice": ref.name,
                                        "codec_frames": res.codec_frames, "finish_reason": res.finish_reason}
            st.engine = engine
            st.batcher = eng.Batcher(engine.run_batch, st.executor, max_batch=args.max_batch,
                                     window_s=args.batch_window_ms / 1000, max_queue=args.max_queue,
                                     length_policy=args.length_policy, retry_length=not args.no_length_retry)
            st.tasks.append(asyncio.create_task(st.batcher.run(), name="batcher"))
            st.startup["ready_s"] = round(time.perf_counter() - t0, 2)
            st.ready = True
            event("ready", **{k: st.startup[k] for k in ("ready_s", "model") if k in st.startup},
                  warmup=st.startup.get("warmup"), voices=sorted(st.voices))
        except Exception as exc:  # noqa: BLE001 - report, then stop the server (a supervisor restarts it)
            st.error = f"{type(exc).__name__}: {exc}"
            event("startup_failed", logging.ERROR, _exc=exc, error=st.error)
            if st.server is not None:
                st.server.should_exit = True

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        event("starting", config={k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
              versions=versions())
        st.tasks.append(asyncio.create_task(startup(), name="startup"))
        yield
        for t in st.tasks:
            t.cancel()
        st.executor.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(title="qwen-tts baseline", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.st = st

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        err = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(x) for x in err.get("loc", ())) or "request"
        return error_response(400, f"{loc}: {err.get('msg', 'invalid request')}")

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status, exc.message, exc.err_type)

    @app.get("/health")
    async def health() -> JSONResponse:
        if st.ready:
            return JSONResponse({"status": "healthy"})
        if st.error:
            return JSONResponse({"status": "unhealthy", "error": st.error}, status_code=503)
        return JSONResponse({"status": "loading"}, status_code=503)

    @app.get("/v1/baseline/info")
    async def info() -> JSONResponse:
        out: dict[str, Any] = {"ready": st.ready, "error": st.error,
                               "config": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
                               "versions": versions(), "startup": st.startup}
        if st.engine:
            out["engine"] = {"stats": dict(st.engine.stats), "defaults": dataclasses.asdict(st.engine.defaults),
                             "prompt_cache_entries": len(st.engine._cache), "pinned_prompts": len(st.engine._pinned)}
        if st.batcher:
            out["batcher"] = {"stats": dict(st.batcher.stats), "pending": len(st.batcher.pending),
                              "busy": st.batcher.busy,
                              "batch_sizes": {str(k): v for k, v in sorted(st.batcher.batch_sizes.items())}}
        if str(args.device).startswith("cuda"):
            try:
                import torch

                out["cuda"] = {"allocated_gib": round(torch.cuda.memory_allocated() / 2**30, 3),
                               "max_allocated_gib": round(torch.cuda.max_memory_allocated() / 2**30, 3),
                               "reserved_gib": round(torch.cuda.memory_reserved() / 2**30, 3)}
            except Exception as exc:  # noqa: BLE001
                out["cuda"] = {"error": str(exc)}
        return JSONResponse(json.loads(json.dumps(out, default=str)))

    @app.get("/v1/audio/voices")
    async def list_voices() -> JSONResponse:
        uploaded = [{k: v for k, v in m.items() if k != "ref"} for m in st.uploaded.values()]
        names = sorted(set(st.voices) | {m["name"] for m in uploaded})
        return JSONResponse({"voices": names, "uploaded_voices": uploaded})

    @app.post("/v1/audio/voices")
    async def upload_voice(audio_sample: UploadFile | None = File(None), speaker_embedding: str | None = Form(None),
                           consent: str = Form(...), name: str = Form(...), ref_text: str | None = Form(None),
                           speaker_description: str | None = Form(None)) -> JSONResponse:
        if speaker_embedding is not None:
            raise ApiError(400, "speaker_embedding uploads are not supported by the qwen-tts baseline; upload "
                                "audio_sample")
        if audio_sample is None:
            raise ApiError(400, "Either 'audio_sample' or 'speaker_embedding' must be provided")
        name = _validate_voice_name(name)
        lower = name.lower()
        if lower in st.voices:
            raise ApiError(400, f"Voice name '{name}' is a built-in (repo) voice")
        data = await audio_sample.read()
        if len(data) > eng.UPLOAD_MAX_BYTES:
            raise ApiError(400, f"File size exceeds maximum limit of 10MB. Got {len(data)} bytes.")
        text = (ref_text or "").strip() or None
        try:
            ref = await asyncio.to_thread(eng.make_reference, data, text, text is None, "upload", name)
        except ValueError as exc:
            raise ApiError(400, str(exc)) from None
        async with st.upload_lock:
            meta = {"name": name, "consent": consent, "created_at": int(time.time()),
                    "mime_type": audio_sample.content_type or "audio/wav", "file_size": len(data),
                    "embedding_source": "audio", "sample_rate": ref.sr, "duration_s": round(ref.seconds, 3),
                    "mode": "x_vector_only" if ref.x_vector_only else "icl"}
            if text:
                meta["ref_text"] = text
            if speaker_description and speaker_description.strip():
                meta["speaker_description"] = speaker_description.strip()
            replaced = lower in st.uploaded
            st.uploaded[lower] = {**meta, "ref": ref}
        event("voice_uploaded", name=name, replaced=replaced, bytes=len(data), seconds=round(ref.seconds, 3),
              sample_rate=ref.sr, mode=meta["mode"])
        return JSONResponse({"success": True, "voice": meta})

    @app.delete("/v1/audio/voices/{name}")
    async def delete_voice(name: str) -> JSONResponse:
        async with st.upload_lock:
            meta = st.uploaded.pop(name.strip().lower(), None)
        if meta is None:
            raise ApiError(404, f"Voice '{name}' not found")
        event("voice_deleted", name=meta["name"])
        return JSONResponse({"success": True, "message": f"Voice '{meta['name']}' deleted successfully"})

    @app.post("/v1/audio/speech")
    async def speech(request: Request) -> Response:
        t0 = time.perf_counter()
        rid = request_id(request.headers.get("x-request-id"))
        rec: dict[str, Any] = {"request_id": rid, "status": "ok", "http_status": 200}
        base_headers = {"X-Request-Id": rid}
        try:
            try:
                body = await request.json()
            except Exception:  # noqa: BLE001
                raise ApiError(400, "request body must be JSON") from None
            if not isinstance(body, dict):
                raise ApiError(400, "request body must be a JSON object")
            try:
                req = SpeechRequest.model_validate(body)
            except ValidationError as exc:
                raise ApiError(400, _first_error(exc)) from None
            rec |= {"voice": req.voice, "chars": len(req.input), "format": req.response_format, "seed": req.seed,
                    "max_new_tokens": req.max_new_tokens}
            if not st.ready:
                raise ApiError(503, "model is not ready" if not st.error else f"startup failed: {st.error}")
            job = await build_job(st, req, rid)
            rec |= {"ref": job.ref.source, "lang": job.language, "non_streaming_mode": job.non_streaming_mode,
                    "sampling": dataclasses.asdict(job.sampling)}
            try:
                res = await st.batcher.submit(job)
            except eng.QueueFull as exc:
                raise ApiError(503, str(exc)) from None
            except eng.CodecLimitError as exc:
                rec["retries"] = job.retries
                raise ApiError(500, str(exc)) from None
            except ApiError:
                raise
            except Exception as exc:  # noqa: BLE001
                rec["retries"] = job.retries
                event("generation_error", logging.ERROR, _exc=exc, request_id=rid)
                raise ApiError(500, f"generation failed: {type(exc).__name__}: {exc}") from None
            pcm = float_to_pcm16(res.wav)
            fmt = req.response_format.lower()
            content = pcm_to_wav(pcm, res.sample_rate) if fmt == "wav" else pcm
            headers = base_headers | {
                "X-AI-Generated": "true",
                "X-Baseline-Batch-Size": str(res.batch_size),
                "X-Baseline-Batch-Id": str(res.batch_id),
                "X-Baseline-Queue-Ms": f"{res.queue_ms:.1f}",
                "X-Baseline-Prompt-Ms": f"{res.prompt_ms:.1f}",
                "X-Baseline-Gen-Ms": f"{res.gen_ms:.1f}",
                "X-Baseline-Codec-Frames": str(res.codec_frames),
                "X-Baseline-Text-Tokens": str(res.text_tokens),
                "X-Baseline-Max-New-Tokens": str(res.cap),
                "X-Baseline-Batch-Max-New-Tokens": str(res.batch_cap),
                "X-Baseline-Finish-Reason": res.finish_reason,
                "X-Baseline-Prompt-Cache": res.prompt_cache,
                "X-Baseline-Retries": str(job.retries),
                "X-Baseline-Sample-Rate": str(res.sample_rate),
            }
            rec |= {"batch_size": res.batch_size, "batch_id": res.batch_id, "queue_ms": round(res.queue_ms, 1),
                    "prompt_ms": round(res.prompt_ms, 1), "gen_ms": round(res.gen_ms, 1),
                    "prompt_cache": res.prompt_cache, "text_tokens": res.text_tokens, "codec_frames": res.codec_frames,
                    "cap": res.cap, "batch_cap": res.batch_cap, "finish_reason": res.finish_reason,
                    "retries": job.retries, "audio_s": round(res.audio_s, 3)}
            media = "audio/wav" if fmt == "wav" else "audio/pcm"
            return Response(content=content, media_type=media, headers=headers)
        except ApiError as exc:
            rec |= {"status": "error", "http_status": exc.status, "error": exc.message}
            return error_response(exc.status, exc.message, exc.err_type, headers=base_headers)
        except asyncio.CancelledError:
            rec |= {"status": "cancelled", "http_status": 499, "error": "client disconnected"}
            raise
        finally:
            total = time.perf_counter() - t0
            rec["total_ms"] = round(total * 1000, 1)
            if rec.get("audio_s"):
                rec["rtf"] = round(total / rec["audio_s"], 3)
            event("request", logging.ERROR if rec["http_status"] >= 500 else logging.INFO, **rec)

    return app


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level, args.log_tz)
    import uvicorn

    app = create_app(args)
    config = uvicorn.Config(app, host=args.host, port=args.port, log_config=None, access_log=False,
                            server_header=False, timeout_graceful_shutdown=5)
    server = uvicorn.Server(config)
    app.state.st.server = server
    server.run()
    if app.state.st.error:
        sys.exit(2)


if __name__ == "__main__":
    main()
