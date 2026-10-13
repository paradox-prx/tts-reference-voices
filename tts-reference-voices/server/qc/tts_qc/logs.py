"""JSON logs to stdout (one object per line, for journald), timestamped in local time with its UTC offset (default
Asia/Karachi), in the same shape as the gateway's: {"ts", "level", "event", ...fields}."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, tzinfo
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger("tts_qc")
_tz: tzinfo = ZoneInfo("Asia/Karachi")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields: dict[str, Any] | None = getattr(record, "fields", None)
        entry: dict[str, Any] = {"ts": datetime.fromtimestamp(record.created, _tz).isoformat(timespec="milliseconds"),
                                 "level": record.levelname.lower()}
        if fields is None:            # a foreign record (uvicorn, faster_whisper)
            entry |= {"event": "log", "logger": record.name, "msg": record.getMessage()}
        else:
            entry |= {"event": record.getMessage(), **fields}
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def setup(level: str = "INFO", tz: str | None = None) -> None:
    global _tz
    if tz:
        _tz = ZoneInfo(tz)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    for name in ("tts_qc", "uvicorn", "uvicorn.error", "faster_whisper"):
        log = logging.getLogger(name)
        log.handlers[:] = [handler]
        log.setLevel("WARNING" if name == "faster_whisper" else level.upper())
        log.propagate = False


def event(name: str, level: int = logging.INFO, exc_info: BaseException | None = None, **fields: Any) -> None:
    logger.log(level, name, extra={"fields": fields}, exc_info=exc_info)
