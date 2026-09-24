"""JSON logs to stdout (one object per line, for journald) and request ids."""

from __future__ import annotations

import logging
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

import orjson

logger = logging.getLogger("tts_gateway")

_REQUEST_ID = re.compile(r"[A-Za-z0-9._:/+=-]{1,128}")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields: dict[str, Any] | None = getattr(record, "fields", None)
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
        }
        if fields is None:  # a foreign record (uvicorn)
            entry |= {"event": "log", "logger": record.name, "msg": record.getMessage()}
        else:
            entry |= {"event": record.getMessage(), **fields}
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return orjson.dumps(entry, default=str).decode()


def setup(level: str = "INFO") -> None:
    """Route our logger and uvicorn's to stdout as JSON lines."""
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
    error: str | None = None
    started: float = field(default_factory=time.perf_counter, repr=False)

    def fail(self, status: str, http_status: int, error: str) -> None:
        self.status, self.http_status, self.error = status, http_status, error

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
