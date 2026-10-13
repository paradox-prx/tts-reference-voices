"""python -m tts_qc: the QC sidecar on TTS_QC_HOST:TTS_QC_PORT (default 127.0.0.1:8092). Start it through
server/eval/run.sh so ctranslate2 finds cuBLAS 12:  cd server/qc && ../eval/run.sh -m tts_qc
Settings: tts_qc/config.py (environment only)."""
from __future__ import annotations

import sys

import uvicorn

from .app import create_app
from .config import Settings
from .logs import event, setup


def main() -> int:
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        print(f"tts_qc: bad configuration: {exc}", file=sys.stderr)
        return 2
    setup(settings.log_level, settings.tz)
    event("config", host=settings.host, port=settings.port, **settings.public())
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, log_config=None, access_log=False,
                timeout_graceful_shutdown=10)
    return 0


if __name__ == "__main__":
    sys.exit(main())
