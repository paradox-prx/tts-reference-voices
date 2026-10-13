"""HTTP API of the QC sidecar (the contract server/gateway/tts_gateway/qc.py is written against):

  GET  /health  -> 200 {"status": "ok", "asr": bool, "sim": bool, "device": "cuda"|"cpu"} once the models are loaded;
                   503 {"status": "loading"|"error", ...} before (or when loading failed)
  POST /v1/qc   {"request_id": str, "voice": str ("" = inline reference: no SIM, no pace; engine variants such as
                 "trump-avg", "shehbaz-prompt" or "<id>-<sha10>" are judged against voices/<id>),
                 "lang": "en"|"ur"|"und",
                 "text": str, "sample_rate": int, "pcm_b64": str (base64 PCM16 LE mono),
                 "checks": ["asr","sim","audio"] (optional; default: every check this server has enabled)}
                -> 200 {"pass": bool, "reasons": [str], "metrics": {..., "asr_text"}, "ms": {asr, sim, audio, total}}
                   400 bad input (validation, base64, empty or too long audio), 404 unknown voice, 503 still loading
The verdict is policy.gate() with this server's thresholds (TTS_QC_* env) and SIM model (TTS_QC_SIM_MODEL).
'und' text gets no ASR checks (no normalizer, no forced language); audio and SIM still run.
"""
from __future__ import annotations

import asyncio
import logging
import math
import time
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import __version__, policy
from .audio import AudioError, pcm16_from_b64
from .config import Settings
from .logs import event
from .scorer import Scorer, ScorerConfig
from .voices import resolve_voice

RESPONSE_DROP = ("ref_norm", "hyp_norm", "words")   # bulky; the gateway does not need them (offline scores keep them)


class QCRequest(BaseModel):
    request_id: str = Field("", max_length=256)
    voice: str = Field("", max_length=128)
    lang: Literal["en", "ur", "und"]
    text: str = Field(..., max_length=100_000)
    sample_rate: int = Field(..., ge=4000, le=192_000)
    pcm_b64: str
    checks: list[Literal["asr", "sim", "audio"]] | None = None


def _clean(value: Any) -> Any:
    """JSON-safe metrics: numpy scalars -> Python, NaN/inf -> None."""
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def build_scorer(settings: Settings) -> Scorer:
    return Scorer(ScorerConfig(
        device=settings.device, device_index=settings.device_index, asr=settings.asr,
        asr_compute=settings.asr_compute, beam=settings.beam, workers=settings.workers,
        cpu_threads=settings.cpu_threads, sim_models=(settings.sim_model,) if settings.sim else (),
        models_dir=settings.models_dir, voices_dir=settings.voices_dir, pace_file=settings.pace_file))


def create_app(settings: Settings | None = None, scorer: Scorer | None = None) -> FastAPI:
    """`scorer` defaults to one built from `settings`; it is loaded in a worker thread at startup unless it is ready
    already, so /health answers 503 while the models load."""
    settings = settings or Settings.from_env()
    scorer = scorer or build_scorer(settings)
    state: dict[str, Any] = {"error": None, "started": time.time()}

    def _load() -> None:
        t0 = time.perf_counter()
        try:
            scorer.load()
        except Exception as exc:                          # keep serving /health with the error
            state["error"] = f"{type(exc).__name__}: {exc}"
            event("load_failed", logging.ERROR, exc_info=exc, error=state["error"])
            return
        event("ready", load_s=round(time.perf_counter() - t0, 1), **settings.public(),
              voices=sorted(scorer.voices), model_load_s=getattr(scorer, "load_s", {}))

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        event("starting", version=__version__, **settings.public(), thresholds=settings.thresholds.as_dict())
        task = None if scorer.ready else asyncio.create_task(asyncio.to_thread(_load))
        yield
        if task is not None and not task.done():
            task.cancel()

    app = FastAPI(title="tts-qc", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.scorer, app.state.settings = scorer, settings

    @app.exception_handler(RequestValidationError)
    async def _bad_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse({"error": "bad_request", "detail": jsonable_encoder(exc.errors())}, status_code=400)

    @app.get("/health")
    def health() -> JSONResponse:
        if not scorer.ready:
            status = "error" if state["error"] else "loading"
            return JSONResponse({"status": status, "error": state["error"], "device": settings.device}, 503)
        return JSONResponse({"status": "ok", "asr": scorer.asr is not None, "sim": bool(scorer.embedders),
                             "device": settings.device, "sim_model": settings.sim_model if scorer.embedders else None,
                             "voices": sorted(scorer.voices), "version": __version__})

    @app.post("/v1/qc")
    def qc(body: QCRequest) -> JSONResponse:              # sync: runs in the threadpool; the models are thread-safe
        if not scorer.ready:
            return JSONResponse({"error": "loading"}, 503)
        if body.voice and resolve_voice(body.voice, scorer.voices) is None:
            return JSONResponse({"error": "unknown_voice", "voice": body.voice, "voices": sorted(scorer.voices)}, 404)
        try:
            pcm = pcm16_from_b64(body.pcm_b64)
        except AudioError as exc:
            return JSONResponse({"error": "bad_audio", "detail": str(exc)}, 400)
        seconds = len(pcm) / body.sample_rate
        if not len(pcm):
            return JSONResponse({"error": "bad_audio", "detail": "empty audio"}, 400)
        if seconds > settings.max_seconds:
            return JSONResponse({"error": "bad_audio", "detail": f"{seconds:.1f} s > {settings.max_seconds:g} s"}, 400)
        wanted = set(body.checks if body.checks is not None else policy.CHECKS)
        run = {c for c in wanted if (c != "asr" or scorer.asr is not None) and (c != "sim" or scorer.embedders)}
        if not body.voice:
            run.discard("sim")
        if body.lang == "und":
            run.discard("asr")
        try:
            metrics, ms = scorer.score(pcm, body.sample_rate, body.text, body.lang, body.voice or None, run)
        except Exception as exc:
            event("qc_error", logging.ERROR, exc_info=exc, request_id=body.request_id, voice=body.voice)
            return JSONResponse({"error": "internal", "detail": f"{type(exc).__name__}: {exc}"}, 500)
        reasons = policy.gate(metrics, body.lang, settings.thresholds, settings.sim_model, run)
        metrics = {k: v for k, v in metrics.items() if k not in RESPONSE_DROP}
        metrics["checks"] = sorted(run)
        event("qc", request_id=body.request_id, voice=body.voice, lang=body.lang, audio_s=round(seconds, 2),
              passed=not reasons, reasons=reasons, ms=ms, checks=sorted(run),
              wer=metrics.get("wer"), cer_nospace=metrics.get("cer_nospace"),
              sim=metrics.get(f"sim_prompt_{settings.sim_model}"), pace_ratio=metrics.get("pace_ratio"))
        return JSONResponse({"pass": not reasons, "reasons": reasons, "metrics": _clean(metrics), "ms": ms})

    return app
