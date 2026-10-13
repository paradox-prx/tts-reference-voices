"""Dev console dataset jobs: SQLite-backed, resumable (a page refresh or a server restart continues where it stopped,
rows already done are skipped), pausable, cancellable; several jobs can exist, each runs at dev priority."""
from __future__ import annotations

import asyncio
import json
import random
import shutil
import sqlite3
import threading
import time
import traceback
import uuid
from collections import Counter
from pathlib import Path

from . import audio
from .distribution import assign
from .engine import Engine, EngineError, Sampling
from .rows_io import Row
from .scheduler import DEV, Scheduler
from .synth import QCConfig, Ref, SynthRequest, synthesize
from .tags import TagError, parse_tag_list, random_tags, strip_tags, validate_text
from .text import apply_delivery, letters, split_sentences

DEFAULT_CONFIG = {
    "name": "dataset",
    "distribution": {"mode": "balanced", "weights": {}, "seed": 1234},
    "sampling": {"temperature": 0.8, "top_k": 50, "top_p": 1.0},
    "seeds": {"mode": "base", "base": 1000},          # base: base + row index; random: drawn per row (logged)
    "takes": 1,
    "split": {"max_part_s": 25.0, "gap_s": 0.3},
    "reference": {"max_s": 29.5},
    "tags": {"mode": "none", "random_pct": 30, "pool": [], "strength": "light", "export_text": "keep"},
    "audio": {"loudness_lufs": -20.0, "sample_rate": 24000},
    "qc": {"enabled": True, "duration": True, "silence": True, "clipping": True, "retries": 2,
           "include_flagged": False},
}


def merge_config(user: dict | None) -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    for k, v in (user or {}).items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k] |= v
        else:
            cfg[k] = v
    return cfg


def row_text(row: dict, cfg: dict, rng: random.Random) -> tuple[str, str]:
    """(text sent to the engine, tags column as applied) for a stored row (text, tags_in). Raises TagError on invalid
    tags."""
    mode, strength = cfg["tags"]["mode"], cfg["tags"].get("strength", "light")
    text = row["text"]
    if mode == "strip":
        return strip_tags(text), ""
    errs = validate_text(text)
    if errs:
        raise TagError("; ".join(errs))
    tags = []
    if mode == "keep":
        tags = parse_tag_list(row.get("tags_in") or "")   # the rows file's tags column
    elif mode == "random":
        pool = parse_tag_list(cfg["tags"].get("pool") or [])
        if pool and rng.random() * 100 < float(cfg["tags"].get("random_pct", 0)):
            tags = random_tags(rng, pool, k=int(cfg["tags"].get("per_row", 1)))
    if not tags:
        return " ".join(split_sentences(text)), ""
    # the tags column uses the rows-file format ("emotion:anger;prosody:speed_fast"), so an export re-imports as is
    return (apply_delivery(text, tags, strength if strength != "none" else "light"),
            ";".join(f"{t.category}:{t.value}" for t in tags))


class JobStore:
    def __init__(self, data_dir: Path):
        self.dir = Path(data_dir) / "jobs"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(Path(data_dir) / "studio.db"), check_same_thread=False, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.lock = threading.Lock()
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, name TEXT, status TEXT, config TEXT, speakers TEXT,
            created REAL, updated REAL, started REAL, active_s REAL DEFAULT 0, errors TEXT DEFAULT '[]');
        CREATE TABLE IF NOT EXISTS rows (job TEXT, idx INTEGER, id TEXT, text TEXT, pinned TEXT, speaker TEXT,
            tags_in TEXT, seed_in INTEGER, status TEXT, text_sent TEXT, tags TEXT, seed INTEGER, attempts INTEGER,
            seconds REAL, qc TEXT, path TEXT, error TEXT, updated REAL, PRIMARY KEY (job, idx));
        """)

    def q(self, sql: str, args=()) -> list[sqlite3.Row]:
        with self.lock:
            self.db.row_factory = sqlite3.Row
            return self.db.execute(sql, args).fetchall()

    def x(self, sql: str, args=()) -> None:
        with self.lock:
            self.db.execute(sql, args)

    def job_dir(self, jid: str) -> Path:
        return self.dir / jid

    def create(self, name: str, config: dict, speakers: list[dict], rows: list[Row]) -> str:
        """speakers: [{tag, wav (bytes, 24 kHz mono), transcript, seconds, s_per_letter}]"""
        jid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        d = self.job_dir(jid)
        (d / "speakers").mkdir(parents=True)
        spk_meta = []
        for s in speakers:
            (d / "speakers" / f"{s['tag']}.wav").write_bytes(s["wav"])
            spk_meta.append({k: s[k] for k in ("tag", "transcript", "seconds", "s_per_letter", "source")})
        tags = [s["tag"] for s in speakers]
        dist = config["distribution"]
        assigned = assign([r.speaker for r in rows], tags, dist["mode"], dist.get("weights"), int(dist.get("seed", 0)))
        now = time.time()
        with self.lock:
            self.db.execute("BEGIN")
            self.db.execute("INSERT INTO jobs (id, name, status, config, speakers, created, updated) VALUES (?,?,?,?,?,?,?)",
                            (jid, name, "queued", json.dumps(config, ensure_ascii=False),
                             json.dumps(spk_meta, ensure_ascii=False), now, now))
            self.db.executemany(
                "INSERT INTO rows (job, idx, id, text, pinned, speaker, tags_in, seed_in, status, updated) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                [(jid, r.index, r.id, r.text, r.speaker, spk, r.tags, r.seed, "pending", now)
                 for r, spk in zip(rows, assigned)])
            self.db.execute("COMMIT")
        return jid

    def job(self, jid: str) -> dict | None:
        r = self.q("SELECT * FROM jobs WHERE id=?", (jid,))
        if not r:
            return None
        j = dict(r[0])
        j["config"] = json.loads(j["config"])
        j["speakers"] = json.loads(j["speakers"])
        j["errors"] = json.loads(j["errors"] or "[]")
        return j

    def jobs(self) -> list[dict]:
        return [self.summary(r["id"]) for r in self.q("SELECT id FROM jobs ORDER BY created DESC")]

    def summary(self, jid: str) -> dict:
        j = self.job(jid)
        st = Counter({r["status"]: r["n"] for r in self.q("SELECT status, COUNT(*) n FROM rows WHERE job=? GROUP BY status", (jid,))})
        per = {r["speaker"]: {"total": r["n"], "done": r["d"], "flagged": r["f"]} for r in self.q(
            "SELECT speaker, COUNT(*) n, SUM(status='done') d, SUM(status='flagged') f FROM rows WHERE job=? GROUP BY speaker",
            (jid,))}
        secs = self.q("SELECT COALESCE(SUM(seconds),0) s FROM rows WHERE job=? AND status IN ('done','flagged')", (jid,))[0]["s"]
        total = sum(st.values())
        finished = st["done"] + st["flagged"] + st["error"]
        active = j["active_s"] + (time.time() - j["started"] if j["status"] == "running" and j["started"] else 0)
        rate = finished / active if active > 0 else 0
        eta = (total - finished) / rate if rate > 0 else None
        return {"id": jid, "name": j["name"], "status": j["status"], "created": j["created"], "total": total,
                "counts": dict(st), "finished": finished, "per_speaker": per, "audio_s": round(secs, 1),
                "active_s": round(active, 1), "rtf_x": round(secs / active, 2) if active > 0 else None,
                "eta_s": round(eta) if eta else None, "errors": j["errors"][-50:]}

    def set_status(self, jid: str, status: str) -> None:
        j = self.job(jid)
        now = time.time()
        if j["status"] == "running" and status != "running" and j["started"]:
            self.x("UPDATE jobs SET active_s=active_s+?, started=NULL WHERE id=?", (now - j["started"], jid))
        if status == "running":
            self.x("UPDATE jobs SET started=? WHERE id=?", (now, jid))
        self.x("UPDATE jobs SET status=?, updated=? WHERE id=?", (status, now, jid))

    def log_error(self, jid: str, msg: str) -> None:
        j = self.job(jid)
        errs = (j["errors"] + [{"t": time.time(), "msg": msg[:500]}])[-200:]
        self.x("UPDATE jobs SET errors=? WHERE id=?", (json.dumps(errs, ensure_ascii=False), jid))

    def rows(self, jid: str, status: str | None = None) -> list[dict]:
        if status:
            return [dict(r) for r in self.q("SELECT * FROM rows WHERE job=? AND status=? ORDER BY idx", (jid, status))]
        return [dict(r) for r in self.q("SELECT * FROM rows WHERE job=? ORDER BY idx", (jid,))]

    def row(self, jid: str, idx: int) -> dict | None:
        r = self.q("SELECT * FROM rows WHERE job=? AND idx=?", (jid, idx))
        return dict(r[0]) if r else None

    def update_row(self, jid: str, idx: int, **kw) -> None:
        kw["updated"] = time.time()
        cols = ", ".join(f"{k}=?" for k in kw)
        self.x(f"UPDATE rows SET {cols} WHERE job=? AND idx=?", (*kw.values(), jid, idx))

    def delete(self, jid: str) -> None:
        self.x("DELETE FROM rows WHERE job=?", (jid,))
        self.x("DELETE FROM jobs WHERE id=?", (jid,))
        shutil.rmtree(self.job_dir(jid), ignore_errors=True)


class EngineDown(RuntimeError):
    """The engine stopped answering mid-job: the row goes back to the queue instead of being marked as an error."""


class JobRunner:
    """Runs jobs in the background: one task per running job, rows processed by `concurrency` workers; the shared
    scheduler decides how many reach the engine."""

    def __init__(self, store: JobStore, engine: Engine, sched: Scheduler, concurrency: int):
        self.store, self.engine, self.sched, self.concurrency = store, engine, sched, concurrency
        self.tasks: dict[str, asyncio.Task] = {}
        self._outage = asyncio.Lock()

    async def _wait_engine(self, jid: str, why: str) -> None:
        """Block until the engine is healthy again (one worker polls and logs; the others wait on the lock)."""
        async with self._outage:
            if await self.engine.health():
                return
            self.store.log_error(jid, f"engine down ({why[:200]}); rows are requeued, waiting for it to come back")
            while self.store.job(jid)["status"] == "running" and not await self.engine.health():
                await asyncio.sleep(5)

    def resume_all(self) -> None:
        for r in self.store.q("SELECT id FROM jobs WHERE status IN ('running','queued')"):
            self.store.x("UPDATE rows SET status='pending' WHERE job=? AND status='running'", (r["id"],))
            self.store.x("UPDATE jobs SET started=NULL WHERE id=?", (r["id"],))
            self.start(r["id"])

    def start(self, jid: str) -> None:
        if jid in self.tasks and not self.tasks[jid].done():
            return
        self.store.set_status(jid, "running")
        self.tasks[jid] = asyncio.create_task(self._run(jid))

    def pause(self, jid: str) -> None:
        self.store.set_status(jid, "paused")

    def cancel(self, jid: str) -> None:
        self.store.set_status(jid, "cancelled")
        t = self.tasks.get(jid)
        if t and not t.done():
            t.cancel()

    def refs(self, job: dict) -> dict[str, Ref]:
        d = self.store.job_dir(job["id"]) / "speakers"
        return {s["tag"]: Ref((d / f"{s['tag']}.wav").read_bytes(), s["transcript"], s["s_per_letter"])
                for s in job["speakers"]}

    async def _run(self, jid: str) -> None:
        job = self.store.job(jid)
        refs = self.refs(job)
        pending = asyncio.Queue()
        for r in self.store.rows(jid, "pending"):
            pending.put_nowait(r)

        async def worker():
            while True:
                if self.store.job(jid)["status"] != "running":
                    return
                try:
                    row = pending.get_nowait()
                except asyncio.QueueEmpty:
                    return
                try:
                    await self.process(job, refs, row)
                except EngineDown as e:
                    pending.put_nowait(self.store.row(jid, row["idx"]))
                    await self._wait_engine(jid, str(e))

        try:
            await asyncio.gather(*[worker() for _ in range(self.concurrency)])
            if self.store.job(jid)["status"] == "running":
                self.store.set_status(jid, "done")
        except asyncio.CancelledError:
            self.store.x("UPDATE rows SET status='pending' WHERE job=? AND status='running'", (jid,))
            raise
        except Exception as e:  # noqa: BLE001 - a job never takes the server down
            self.store.log_error(jid, f"job stopped: {e}\n{traceback.format_exc()[-800:]}")
            self.store.set_status(jid, "error")

    async def process(self, job: dict, refs: dict[str, Ref], row: dict, seed: int | None = None,
                      priority: int = DEV) -> dict:
        jid, cfg, idx = job["id"], job["config"], row["idx"]
        self.store.update_row(jid, idx, status="running")
        rng = random.Random(f"{cfg['distribution'].get('seed', 0)}:{idx}")
        try:
            text_sent, tags = row_text(row, cfg, rng)
        except TagError as e:
            self.store.update_row(jid, idx, status="error", error=f"invalid tags: {e}")
            self.store.log_error(jid, f"row {row['id']}: invalid tags: {e}")
            return self.store.row(jid, idx)
        if seed is None:
            if row.get("seed_in") is not None:
                seed = int(row["seed_in"])
            elif cfg["seeds"].get("mode") == "random":
                seed = random.randrange(1, 2 ** 31 - 1)
            else:
                seed = int(cfg["seeds"].get("base", 0)) + idx
        qc_on = cfg["qc"].get("enabled", True)
        qc = QCConfig(duration=qc_on and cfg["qc"].get("duration", True), silence=qc_on and cfg["qc"].get("silence", True),
                      clipping=qc_on and cfg["qc"].get("clipping", True),
                      retries=int(cfg["qc"].get("retries", 2)) if qc_on else 0)
        best, attempts, last_err = None, 0, None
        for take in range(max(1, int(cfg.get("takes", 1)))):
            req = SynthRequest(text_sent, refs[row["speaker"]], Sampling(**cfg["sampling"]),
                               (seed + 7919 * take) % (2 ** 31 - 1), float(cfg["split"]["max_part_s"]),
                               float(cfg["split"]["gap_s"]), cfg["audio"].get("loudness_lufs"),
                               int(cfg["audio"].get("sample_rate", 24000)), qc, priority)
            try:
                res = await synthesize(self.engine, self.sched, req)
            except (EngineError, ValueError) as e:
                last_err = e
                continue
            attempts += sum(p.attempts for p in res.parts)
            ratio = sum(p.seconds for p in res.parts) / max(0.1, sum(p.est_s for p in res.parts))
            score = (1 if res.ok else 0, -abs(ratio - 1))
            if best is None or score > best[0]:
                best = (score, res, req.seed)
        if best is None and priority == DEV and isinstance(last_err, EngineError) and last_err.retryable \
                and not await self.engine.health():
            self.store.update_row(jid, idx, status="pending")
            raise EngineDown(str(last_err))
        if best is None:
            self.store.update_row(jid, idx, status="error", error=str(last_err)[:500], text_sent=text_sent, tags=tags)
            self.store.log_error(jid, f"row {row['id']}: {last_err}")
            return self.store.row(jid, idx)
        _, res, used_seed = best
        rel = f"wavs/{row['speaker']}/{row['id']}.wav"
        p = self.store.job_dir(jid) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(audio.wav_bytes(res.audio, res.sample_rate))
        status = "done" if (res.ok or not qc_on) else "flagged"
        self.store.update_row(jid, idx, status=status, text_sent=text_sent, tags=tags, seed=used_seed,
                              attempts=attempts, seconds=round(res.seconds, 3), path=rel,
                              qc=json.dumps({"ok": res.ok, "reasons": res.reasons,
                                             "parts": [p.qc for p in res.parts]}, ensure_ascii=False),
                              error=None)
        return self.store.row(jid, idx)


def export_rows(job: dict, rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """(metadata rows, rejected rows) for the zip, following the job's export settings."""
    cfg = job["config"]
    keep_tags = cfg["tags"].get("export_text", "keep") == "keep"
    include_flagged = cfg["qc"].get("include_flagged", False)
    meta, rejected = [], []
    for r in rows:
        qc = json.loads(r["qc"]) if r.get("qc") else {}
        text = r["text_sent"] or r["text"]
        if not keep_tags:
            text = strip_tags(text)
        if r["status"] == "done" or (r["status"] == "flagged" and include_flagged):
            meta.append({"audio_path": r["path"], "text": text, "speaker": r["speaker"], "tags": r["tags"] or "",
                         "seed": r["seed"], "duration_s": r["seconds"], "sample_rate": cfg["audio"]["sample_rate"],
                         "qc_status": "pass" if r["status"] == "done" else "flagged", "wer": "", "_idx": r["idx"],
                         "_id": r["id"]})
        if r["status"] in ("flagged", "error"):
            rejected.append({"id": r["id"], "text": r["text"], "speaker": r["speaker"], "tags": r["tags"] or "",
                             "seed": r["seed"], "attempts": r["attempts"],
                             "reason": r["error"] or "; ".join(qc.get("reasons", []))})
    return meta, rejected


def ref_from_upload(wav24: bytes, transcript: str, source: str, max_s: float) -> dict:
    """A dev speaker reference: fitted under the engine's limit, with its pace."""
    x, sr = audio.read_wav_bytes(wav24)
    fit = audio.fit_reference(audio.resample(x, sr, audio.SR), transcript, max_s)
    n_sent = max(1, len(split_sentences(fit.text)))
    spl = max(0.03, (fit.seconds - 0.25 * (n_sent - 1)) / max(1, letters(fit.text)))
    return {"wav": audio.wav_bytes(fit.audio), "transcript": fit.text, "seconds": round(fit.seconds, 2),
            "s_per_letter": round(spl, 4), "source": source, "note": fit.note}
