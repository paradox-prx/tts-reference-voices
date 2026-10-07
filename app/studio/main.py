"""higgs-studio: the Dev console (dataset generation) and the Customer console (one sample at a time) on top of one
Higgs Audio v3 engine. Internal network only: no login.

    uvicorn studio.main:app --host 0.0.0.0 --port 8100     (start.sh does this)
"""
from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import audio, export
from .distribution import DistributionError, assign, preview
from .engine import Engine, Sampling
from .jobs import DEFAULT_CONFIG, JobRunner, JobStore, export_rows, merge_config, ref_from_upload
from .rows_io import RowsError, parse_rows, parse_speakers_csv, speaker_tag
from .scheduler import CUSTOMER, Scheduler
from .settings import ROOT, settings
from .synth import QCConfig, Ref, SynthRequest
from .tags import EVENT_TAGS, SFX_SOUND, VOCAB, TagError, tag, validate_text
from .takes import Take, TakeStore, run_take
from .text import apply_delivery, estimate_seconds, plan_parts
from .voices import LANGUAGES, VoiceRegistry

WEB = ROOT / "web" / "dist"
DELIVERY_PRESETS = {
    "fast_agent": {"label": "Fast energetic call-centre agent", "speed": "fast", "expressiveness": "high",
                   "pitch": "normal", "emotion": "enthusiasm", "strength": "light"},
    "news_anchor": {"label": "News anchor", "speed": "normal", "expressiveness": "normal", "pitch": "normal",
                    "emotion": "", "strength": "light"},
    "storyteller": {"label": "Storyteller", "speed": "slow", "expressiveness": "high", "pitch": "normal",
                    "emotion": "", "strength": "light"},
    "calm_support": {"label": "Calm support agent", "speed": "slow", "expressiveness": "low", "pitch": "normal",
                     "emotion": "contentment", "strength": "light"},
    "sports": {"label": "Hyped sports commentator", "speed": "very_fast", "expressiveness": "high", "pitch": "high",
               "emotion": "elation", "strength": "light"},
    "fiery_speech": {"label": "Fiery speech", "speed": "fast", "expressiveness": "high", "pitch": "normal",
                     "emotion": "determination", "strength": "strong"},
}


def delivery_tags(d: dict) -> list:
    out = []
    sp = d.get("speed", "normal")
    if sp and sp != "normal":
        out.append(tag("prosody", f"speed_{sp}"))
    ex = d.get("expressiveness", "normal")
    if ex in ("low", "high"):
        out.append(tag("prosody", f"expressive_{ex}"))
    pi = d.get("pitch", "normal")
    if pi in ("low", "high"):
        out.append(tag("prosody", f"pitch_{pi}"))
    if d.get("emotion"):
        out.append(tag("emotion", d["emotion"]))
    return out


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    app.state.engine = Engine()
    app.state.sched = Scheduler(settings.max_inflight, settings.dev_max_inflight, settings.customer_queue_max)
    app.state.voices = VoiceRegistry()
    app.state.takes = TakeStore(settings.data_dir / "takes", settings.take_ttl_h)
    app.state.store = JobStore(settings.data_dir)
    app.state.runner = JobRunner(app.state.store, app.state.engine, app.state.sched, settings.dev_max_inflight)
    app.state.runner.resume_all()
    yield
    await app.state.engine.close()


app = FastAPI(title="higgs-studio", lifespan=lifespan)
UPLOADS = lambda: settings.data_dir / "uploads"  # noqa: E731


# ---- common ---------------------------------------------------------------------------------------------------------

@app.get("/api/status")
async def status():
    return {"engine": await app.state.engine.health(), "engine_url": settings.engine_url,
            "queue": app.state.sched.status()}


@app.get("/api/config")
async def config():
    return {"tags": VOCAB, "sfx_sounds": SFX_SOUND, "events": sorted(f"{c}:{v}" for c, v in EVENT_TAGS),
            "languages": LANGUAGES, "delivery_presets": DELIVERY_PRESETS, "defaults": DEFAULT_CONFIG,
            "limits": {"max_part_s": settings.max_part_s, "max_ref_s": settings.max_ref_s, "takes_max": 3,
                       "upload_min_s": 5, "upload_max_s": 60, "dev_ref_warn": [5, 90]},
            "speeds": ["very_slow", "slow", "normal", "fast", "very_fast"]}


@app.get("/api/voices")
async def voices(all: bool = False):
    vs = app.state.voices.scan()
    return [v.card() for v in vs.values() if all or not v.hidden]


@app.get("/api/voices/{vid}/reference.wav")
async def voice_reference(vid: str):
    try:
        ref = await asyncio.to_thread(app.state.voices.reference, vid)
    except KeyError:
        raise HTTPException(404, f"unknown voice {vid}")
    return Response(ref.wav, media_type="audio/wav")


@app.get("/api/voices/{vid}")
async def voice_detail(vid: str):
    vs = app.state.voices.scan()
    if vid not in vs:
        raise HTTPException(404, f"unknown voice {vid}")
    ref = await asyncio.to_thread(app.state.voices.reference, vid)
    return vs[vid].card() | {"reference_text": ref.text, "reference_seconds": ref.seconds,
                             "s_per_letter": ref.s_per_letter, "reference_note": ref.note}


async def _save_upload(f: UploadFile, max_s: float) -> dict:
    data = await f.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"file over {settings.max_upload_mb} MB")
    try:
        x = await asyncio.to_thread(audio.decode, data)
    except ValueError as e:
        raise HTTPException(422, str(e))
    secs = len(x) / audio.SR
    if secs > max_s:
        raise HTTPException(422, f"{f.filename}: {secs:.1f}s is over the {max_s:.0f}s limit")
    uid = uuid.uuid4().hex[:12]
    UPLOADS().mkdir(parents=True, exist_ok=True)
    (UPLOADS() / f"{uid}.wav").write_bytes(audio.wav_bytes(x))
    meta = {"id": uid, "filename": f.filename, "seconds": round(secs, 2), "peaks": audio.peaks(x, 400),
            "speech_s": round(audio.speech_seconds(x), 2)}
    (UPLOADS() / f"{uid}.json").write_text(json.dumps(meta, ensure_ascii=False))
    return meta


def _upload(uid: str) -> tuple[bytes, dict]:
    p = UPLOADS() / f"{uid}.wav"
    if not uid.isalnum() or not p.exists():
        raise HTTPException(404, f"unknown upload {uid}")
    return p.read_bytes(), json.loads((UPLOADS() / f"{uid}.json").read_text())


@app.get("/api/uploads/{uid}.wav")
async def upload_audio(uid: str):
    return Response(_upload(uid)[0], media_type="audio/wav")


# ---- customer console -----------------------------------------------------------------------------------------------

@app.post("/api/studio/upload")
async def studio_upload(file: UploadFile = File(...)):
    meta = await _save_upload(file, 60.5)
    if meta["seconds"] < 5:
        meta["warning"] = "under 5 s: the clone will be less stable"
    return meta


@app.post("/api/studio/estimate")
async def studio_estimate(body: dict = Body(...)):
    spl = 0.075
    if body.get("voice"):
        try:
            spl = (await asyncio.to_thread(app.state.voices.reference, body["voice"])).s_per_letter
        except (KeyError, ValueError):
            pass
    text = body.get("text", "")
    parts = plan_parts(text, settings.max_part_s, spl) if text.strip() else []
    return {"seconds": round(estimate_seconds(text, spl), 1) if text.strip() else 0, "parts": len(parts),
            "errors": validate_text(text)}


@app.post("/api/studio/generate")
async def studio_generate(body: dict = Body(...)):
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(422, "text is empty")
    errs = validate_text(text)
    if errs:
        raise HTTPException(422, {"tag_errors": errs})
    voice = body.get("voice") or {}
    if voice.get("preset"):
        try:
            r = await asyncio.to_thread(app.state.voices.reference, voice["preset"])
        except KeyError:
            raise HTTPException(404, f"unknown voice {voice['preset']}")
        except ValueError as e:
            raise HTTPException(422, str(e))
        ref = Ref(r.wav, r.text, r.s_per_letter)
    elif voice.get("upload"):
        wav, meta = _upload(voice["upload"])
        transcript = (voice.get("transcript") or "").strip()
        if not transcript:
            raise HTTPException(422, "an uploaded reference needs its exact transcript")
        start, end = float(voice.get("start", 0)), float(voice.get("end", meta["seconds"]))
        if end - start > settings.max_ref_s + 0.05:
            raise HTTPException(422, f"trim the reference to at most {settings.max_ref_s:.0f} s (selected {end - start:.1f} s)")
        if end - start < 3:
            raise HTTPException(422, "the selected reference is under 3 s")
        x, sr = audio.read_wav_bytes(wav)
        seg = audio.trim_silence(x[int(start * sr):int(end * sr)])
        dt = max(0.5, len(seg) / audio.SR)
        from .text import letters, split_sentences
        spl = max(0.03, (dt - 0.25 * (max(1, len(split_sentences(transcript))) - 1)) / max(1, letters(transcript)))
        ref = Ref(audio.wav_bytes(seg), transcript, spl)
    else:
        raise HTTPException(422, "choose a voice (preset or upload)")
    d = body.get("delivery") or {}
    try:
        tags = delivery_tags(d)
        text_sent = apply_delivery(text, tags, d.get("strength", "light"))
    except (TagError, ValueError) as e:
        raise HTTPException(422, str(e))
    n = max(1, min(3, int(body.get("takes", 1))))
    seed = body.get("seed")
    seed = int(seed) if seed not in (None, "") else random.randrange(1, 2 ** 31 - 1)
    exact = bool(body.get("exact", False))
    stream = bool(body.get("stream", True))
    fmt_sr = int(body.get("sample_rate", audio.SR))
    waiting = app.state.sched.status()["waiting"]["customer"]
    if waiting >= settings.customer_queue_max:
        raise HTTPException(503, f"server busy: {waiting} requests waiting, try again shortly")
    takes = []
    for k in range(n):
        s = (seed + 7919 * k) % (2 ** 31 - 1)
        req = SynthRequest(text_sent, ref, Sampling(**(body.get("sampling") or {})), s, settings.max_part_s,
                           settings.join_gap_s, body.get("loudness_lufs", -20.0), fmt_sr,
                           QCConfig(retries=0 if exact else 1), CUSTOMER, exact)
        t = Take(s, stream and k == 0, {"text": text, "text_sent": text_sent}, settings.data_dir / "takes")
        app.state.takes.add(t)
        asyncio.create_task(run_take(t, app.state.engine, app.state.sched, req))
        takes.append({"id": t.id, "seed": s, "stream": t.stream})
    parts = plan_parts(text_sent, settings.max_part_s, ref.s_per_letter)
    return {"takes": takes, "text_sent": text_sent, "parts": len(parts),
            "est_s": round(sum(p.est_s for p in parts), 1), "queue": app.state.sched.status()}


def _take(tid: str) -> Take:
    t = app.state.takes.get(tid)
    if t is None:
        raise HTTPException(404, "unknown or expired take")
    return t


@app.get("/api/studio/takes/{tid}/events")
async def take_events(tid: str):
    t = _take(tid)

    async def gen():
        i = 0
        while True:
            while i < len(t.events):
                yield f"data: {json.dumps(t.events[i], ensure_ascii=False)}\n\n"
                i += 1
            if t.state in ("done", "error") and i >= len(t.events):
                return
            await t.wait_change(10.0)
            if i >= len(t.events):
                yield ": keep-alive\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/api/studio/takes/{tid}/live.pcm")
async def take_live(tid: str):
    """Raw s16le 24 kHz mono PCM as it is generated (streaming takes)."""
    t = _take(tid)
    if not t.stream:
        raise HTTPException(409, "this take is not streamed")

    async def gen():
        sent = 0
        while True:
            if sent < len(t.pcm):
                chunk = bytes(t.pcm[sent:])
                sent += len(chunk)
                yield chunk
            elif t.pcm_done:
                return
            else:
                await t.wait_change(10.0)
    return StreamingResponse(gen(), media_type="application/octet-stream",
                             headers={"X-Sample-Rate": str(audio.SR), "Cache-Control": "no-cache"})


@app.get("/api/studio/takes/{tid}.wav")
async def take_wav(tid: str):
    t = _take(tid)
    if t.state != "done":
        raise HTTPException(409, f"take is {t.state}")
    return FileResponse(t.path, media_type="audio/wav", filename=f"higgs_{t.seed}.wav")


@app.get("/api/studio/takes/{tid}.mp3")
async def take_mp3(tid: str):
    t = _take(tid)
    if t.state != "done":
        raise HTTPException(409, f"take is {t.state}")
    x, sr = audio.read_wav_bytes(t.path.read_bytes())
    return Response(await asyncio.to_thread(audio.mp3_bytes, x, sr), media_type="audio/mpeg",
                    headers={"Content-Disposition": f'attachment; filename="higgs_{t.seed}.mp3"'})


# registered after the .wav / .mp3 routes: "{tid}" would otherwise also match "<id>.wav"
@app.get("/api/studio/takes/{tid}")
async def take_info(tid: str):
    return _take(tid).info()


# ---- dev console ----------------------------------------------------------------------------------------------------

@app.post("/api/dev/speakers")
async def dev_speaker_upload(file: UploadFile = File(...)):
    meta = await _save_upload(file, 600)
    meta["tag"] = speaker_tag(file.filename or "speaker")
    w = []
    if meta["seconds"] < 5:
        w.append("under 5 s: the clone will be less stable")
    if meta["seconds"] > 90:
        w.append("over 90 s: only the first ~30 s (cut at a sentence) is used as the reference")
    elif meta["seconds"] > settings.max_ref_s:
        w.append(f"over {settings.max_ref_s:.0f} s: cut at a sentence boundary; check the transcript of the kept part")
    meta["warnings"] = w
    return meta


@app.post("/api/dev/speakers_csv")
async def dev_speakers_csv(file: UploadFile = File(...)):
    return parse_speakers_csv(await file.read())


@app.post("/api/dev/rows")
async def dev_rows(file: UploadFile = File(...)):
    try:
        rows = parse_rows(await file.read(), file.filename or "rows.csv")
    except (RowsError, ValueError) as e:
        raise HTTPException(422, str(e))
    rid = uuid.uuid4().hex[:12]
    UPLOADS().mkdir(parents=True, exist_ok=True)
    (UPLOADS() / f"{rid}.rows.json").write_text(json.dumps([r.__dict__ for r in rows], ensure_ascii=False))
    tag_errors = [{"id": r.id, "errors": validate_text(r.text)} for r in rows if validate_text(r.text)]
    pinned = {}
    for r in rows:
        if r.speaker:
            pinned[r.speaker] = pinned.get(r.speaker, 0) + 1
    return {"id": rid, "count": len(rows), "preview": [r.__dict__ for r in rows[:20]], "pinned": pinned,
            "with_tags": sum(1 for r in rows if r.tags), "with_seed": sum(1 for r in rows if r.seed is not None),
            "tag_errors": tag_errors[:50], "tag_error_count": len(tag_errors)}


def _load_rows(rid: str):
    from .rows_io import Row
    p = UPLOADS() / f"{rid}.rows.json"
    if not rid.isalnum() or not p.exists():
        raise HTTPException(404, f"unknown rows upload {rid}")
    return [Row(**r) for r in json.loads(p.read_text())]


@app.post("/api/dev/distribution")
async def dev_distribution(body: dict = Body(...)):
    rows = _load_rows(body["rows"])
    speakers = [speaker_tag(s) for s in body["speakers"]]
    d = body.get("distribution") or {}
    try:
        a = assign([r.speaker for r in rows], speakers, d.get("mode", "balanced"), d.get("weights"),
                   int(d.get("seed", 0)))
    except DistributionError as e:
        raise HTTPException(422, str(e))
    return {"counts": preview(a, speakers), "pinned": sum(1 for r in rows if r.speaker)}


@app.post("/api/dev/jobs")
async def dev_create_job(body: dict = Body(...)):
    cfg = merge_config(body.get("config"))
    name = body.get("name") or cfg.get("name") or "dataset"
    rows = _load_rows(body["rows"])
    speakers = []
    seen = set()
    for s in body.get("speakers") or []:
        wav, meta = _upload(s["upload"])
        tg = speaker_tag(s.get("tag") or meta["filename"])
        if tg in seen:
            raise HTTPException(422, f"duplicate speaker tag {tg}")
        seen.add(tg)
        tr = (s.get("transcript") or "").strip()
        if not tr:
            raise HTTPException(422, f"speaker {tg} needs its reference transcript")
        r = await asyncio.to_thread(ref_from_upload, wav, tr, meta["filename"], float(cfg["reference"]["max_s"]))
        speakers.append({"tag": tg, **r})
    if not speakers:
        raise HTTPException(422, "add at least one speaker")
    cfg["name"] = name
    cfg["speakers"] = [{"tag": s["tag"], "transcript": s["transcript"], "source": s["source"]} for s in speakers]
    try:
        jid = app.state.store.create(name, cfg, speakers, rows)
    except DistributionError as e:
        raise HTTPException(422, str(e))
    app.state.runner.start(jid)
    return app.state.store.summary(jid) | {"speaker_notes": {s["tag"]: s["note"] for s in speakers if s["note"]}}


@app.get("/api/dev/jobs")
async def dev_jobs():
    return app.state.store.jobs()


def _job(jid: str) -> dict:
    j = app.state.store.job(jid)
    if j is None:
        raise HTTPException(404, f"unknown job {jid}")
    return j


@app.get("/api/dev/jobs/{jid}")
async def dev_job(jid: str):
    _job(jid)
    return app.state.store.summary(jid)


@app.post("/api/dev/jobs/{jid}/{action}")
async def dev_job_action(jid: str, action: str):
    _job(jid)
    if action == "pause":
        app.state.runner.pause(jid)
    elif action == "resume":
        app.state.runner.start(jid)
    elif action == "cancel":
        app.state.runner.cancel(jid)
    else:
        raise HTTPException(404, f"unknown action {action}")
    return app.state.store.summary(jid)


@app.delete("/api/dev/jobs/{jid}")
async def dev_job_delete(jid: str):
    _job(jid)
    app.state.runner.cancel(jid)
    app.state.store.delete(jid)
    return {"deleted": jid}


@app.get("/api/dev/jobs/{jid}/config")
async def dev_job_config(jid: str):
    j = _job(jid)
    return JSONResponse(j["config"], headers={"Content-Disposition": f'attachment; filename="job_config_{jid}.json"'})


@app.get("/api/dev/jobs/{jid}/samples")
async def dev_samples(jid: str, n: int = 50, seed: int = 0, speaker: str | None = None):
    _job(jid)
    rows = [r for r in app.state.store.rows(jid) if r["status"] in ("done", "flagged") and
            (speaker is None or r["speaker"] == speaker)]
    rng = random.Random(seed)
    by: dict[str, list] = {}
    for r in rows:
        by.setdefault(r["speaker"], []).append(r)
    for v in by.values():
        rng.shuffle(v)
    picked = []
    while len(picked) < n and any(by.values()):  # round-robin over speakers = stratified
        for k in sorted(by):
            if by[k] and len(picked) < n:
                picked.append(by[k].pop())
    rng.shuffle(picked)
    return [{"idx": r["idx"], "id": r["id"], "speaker": r["speaker"], "text": r["text_sent"] or r["text"],
             "tags": r["tags"], "seed": r["seed"], "seconds": r["seconds"], "status": r["status"],
             "qc": json.loads(r["qc"]) if r["qc"] else None, "attempts": r["attempts"],
             "audio_url": f"/api/dev/jobs/{jid}/audio/{r['idx']}.wav?v={int(r['updated'])}"} for r in picked]


@app.get("/api/dev/jobs/{jid}/rows")
async def dev_rows_list(jid: str, status: str | None = None, offset: int = 0, limit: int = Query(200, le=2000)):
    _job(jid)
    rows = app.state.store.rows(jid, status)
    return {"total": len(rows), "rows": rows[offset:offset + limit]}


@app.get("/api/dev/jobs/{jid}/audio/{idx}.wav")
async def dev_audio(jid: str, idx: int):
    r = app.state.store.row(jid, idx)
    if not r or not r["path"]:
        raise HTTPException(404, "no audio for this row")
    return FileResponse(app.state.store.job_dir(jid) / r["path"], media_type="audio/wav")


@app.post("/api/dev/jobs/{jid}/rows/{idx}/regenerate")
async def dev_regenerate(jid: str, idx: int, body: dict = Body(default={})):
    j = _job(jid)
    r = app.state.store.row(jid, idx)
    if not r:
        raise HTTPException(404, "unknown row")
    seed = body.get("seed")
    seed = int(seed) if seed not in (None, "") else random.randrange(1, 2 ** 31 - 1)
    new = await app.state.runner.process(j, app.state.runner.refs(j), r, seed=seed, priority=CUSTOMER)
    return {k: new[k] for k in ("idx", "id", "status", "seed", "seconds", "error")} | {
        "qc": json.loads(new["qc"]) if new["qc"] else None,
        "audio_url": f"/api/dev/jobs/{jid}/audio/{idx}.wav?v={int(time.time())}"}


@app.get("/api/dev/jobs/{jid}/download.zip")
async def dev_download(jid: str, include_flagged: bool | None = None, extra_format: str | None = None):
    j = _job(jid)
    if include_flagged is not None:
        j["config"]["qc"]["include_flagged"] = include_flagged
    rows = app.state.store.rows(jid)
    meta, rejected = export_rows(j, rows)
    d = app.state.store.job_dir(jid)
    s = app.state.store.summary(jid)
    counts = {"total": s["total"], "done": s["counts"].get("done", 0), "flagged": s["counts"].get("flagged", 0),
              "error": s["counts"].get("error", 0), "seconds": sum(float(m["duration_s"] or 0) for m in meta)}
    per = {}
    for m in meta:
        per[m["speaker"]] = per.get(m["speaker"], 0) + 1
    clean = [{k: v for k, v in m.items() if not k.startswith("_")} for m in meta]

    def entries():
        for m in meta:
            yield m["audio_path"], d / m["audio_path"]
        yield "metadata.csv", export.metadata_csv(clean)
        yield "metadata.jsonl", export.metadata_jsonl(clean)
        yield "rejected.csv", export.rejected_csv(rejected)
        for sp in j["speakers"]:
            yield f"speakers/{sp['tag']}.wav", d / "speakers" / f"{sp['tag']}.wav"
        yield "speakers.csv", export.speakers_csv(j["speakers"])
        yield "job_config.json", json.dumps(j["config"], ensure_ascii=False, indent=1).encode("utf-8")
        yield "README.md", export.readme(j, counts, per)
        if extra_format:
            name, data = export.convert(clean, extra_format)
            yield name, data
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in j["name"])[:40]
    return StreamingResponse(export.iter_zip(entries()), media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="{safe}_{jid}.zip"'})


# ---- web ------------------------------------------------------------------------------------------------------------

if (WEB / "assets").exists():
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
async def spa(path: str):
    index = WEB / "index.html"
    if path.startswith("api/"):
        raise HTTPException(404)
    f = WEB / path
    if path and f.is_file() and WEB in f.resolve().parents:
        return FileResponse(f)
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"error": "web UI not built: run ./setup.sh (needs node) or use the API"}, status_code=404)
