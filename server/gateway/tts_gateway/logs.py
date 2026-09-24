"""JSON logs to stdout (one object per line, for journald) and request ids."""

from __future__ import annotations

import logging
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, tzinfo
from typing import Any
from zoneinfo import ZoneInfo

import orjson

logger = logging.getLogger("tts_gateway")
_tz: tzinfo = ZoneInfo("Asia/Karachi")  # set from TTS_LOG_TZ by setup()

_REQUEST_ID = re.compile(r"[A-Za-z0-9._:/+=-]{1,128}")
_QC_SEVERITY = ("pass", "error", "fail")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields: dict[str, Any] | None = getattr(record, "fields", None)
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, _tz).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
        }
        if fields is None:  # a foreign record (uvicorn)
            entry |= {"event": "log", "logger": record.name, "msg": record.getMessage()}
        else:
            entry |= {"event": record.getMessage(), **fields}
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return orjson.dumps(entry, default=str).decode()


def setup(level: str = "INFO", tz: str | None = None) -> None:
    """Route our logger and uvicorn's to stdout as JSON lines, timestamped in local time of `tz` (with its offset)."""
    global _tz
    if tz:
        _tz = ZoneInfo(tz)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    for name in ("tts_gateway", "uvicorn", "uvicorn.error"):
        log = logging.getLogger(name)
        log.handlers[:] = [handler]
        log.setLevel(level.upper())
        log.propagate = False


def event(name: str, level: int = logging.INFO, exc_info: BaseException | None = None, **fields: Any) -> None:
    logger.log(level, name, extra={"fields": fields}, exc_info=exc_info)


def request_id(header: str | None) -> str:
    """The client's X-Request-Id when it is sane, else a fresh one."""
    return header if header and _REQUEST_ID.fullmatch(header) else uuid.uuid4().hex


@dataclass
class RequestLog:
    """The one log line written per speech request."""

    request_id: str
    voice: str | None = None
    lang: str | None = None
    chars: int | None = None
    words: int | None = None
    stream: bool = False
    format: str | None = None
    status: str = "ok"
    http_status: int = 200
    queue_ms: float | None = None
    engine_ms: float = 0.0
    total_ms: float | None = None
    audio_s: float | None = None
    rtf: float | None = None
    retries: int = 0
    suspect: bool = False
    suspect_reason: str | None = None  # of the delivered take: too_short / too_long (pace band) or qc
    pace_ratio: float | None = None  # delivered take's pace / the voice's expected pace
    qc: str | None = None  # QC sidecar verdict on the delivered take: pass / fail / error (None: not checked)
    qc_reasons: list[str] | None = None
    qc_ms: float | None = None  # QC time over all takes
    error: str | None = None
    started: float = field(default_factory=time.perf_counter, repr=False)

    def fail(self, status: str, http_status: int, error: str) -> None:
        self.status, self.http_status, self.error = status, http_status, error

    def take(self, take: Any, qc_ms: float = 0.0) -> None:
        """Record the delivered take of one part (a quality.Take) and the QC time spent on all of that part's takes;
        a multi-part request keeps the worst part."""
        self.suspect |= take.suspect
        self.suspect_reason = self.suspect_reason or take.reason
        if take.ratio is not None and (self.pace_ratio is None or abs(take.ratio - 1) > abs(self.pace_ratio - 1)):
            self.pace_ratio = round(take.ratio, 3)
        if take.qc is not None:
            self.qc = max(self.qc or "pass", take.qc.status, key=_QC_SEVERITY.index)
            self.qc_reasons = (self.qc_reasons or []) + list(take.qc.reasons)
        if qc_ms:
            self.qc_ms = round((self.qc_ms or 0.0) + qc_ms, 1)

    def emit(self) -> None:
        total_s = time.perf_counter() - self.started
        self.total_ms = round(total_s * 1000, 1)
        if self.audio_s:
            self.rtf = round(total_s / self.audio_s, 3)
        fields = asdict(self)
        del fields["started"]
        for key in ("queue_ms", "engine_ms"):
            if fields[key] is not None:
                fields[key] = round(fields[key], 1)
        if self.audio_s is not None:
            fields["audio_s"] = round(self.audio_s, 3)
        event("request", logging.ERROR if self.http_status >= 500 else logging.INFO, **fields)
