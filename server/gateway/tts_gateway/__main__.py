"""Entry point: python -m tts_gateway (settings from TTS_* environment variables)."""

from __future__ import annotations

import logging
import sys

import uvicorn
from pydantic import ValidationError

from . import logs
from .app import create_app
from .config import Settings


def main() -> None:
    try:
        settings = Settings()
    except ValidationError as exc:
        logs.setup()
        logs.event("config_error", logging.ERROR, error=str(exc))
        sys.exit(2)
    logs.setup(settings.log_level)
    try:
        app = create_app(settings)
    except Exception as exc:  # noqa: BLE001 - no voices, unknown backend, ...: exit with one clear log line
        logs.event("startup_failed", logging.ERROR, exc_info=exc, error=f"{type(exc).__name__}: {exc}")
        sys.exit(2)
    # access log off: every speech request gets one JSON line from the app itself
    uvicorn.run(app, host=settings.host, port=settings.port, loop="uvloop", http="httptools", log_config=None,
                access_log=False, server_header=False, timeout_graceful_shutdown=settings.shutdown_grace_s)


if __name__ == "__main__":
    main()
