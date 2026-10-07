#!/usr/bin/env bash
# Run the studio web app (FastAPI: both consoles + API) in the foreground on $STUDIO_HOST:$STUDIO_PORT.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

[[ -x $STUDIO_VENV/bin/uvicorn ]] || die "$STUDIO_VENV missing: run ./setup.sh"
[[ -f $ROOT/web/dist/index.html ]] || say "web/dist not built: the API works, the consoles do not (./setup.sh builds them; needs node)"
export PYTHONUNBUFFERED=1
cd "$ROOT/app"
exec "$STUDIO_VENV/bin/uvicorn" studio.main:app --host "$STUDIO_HOST" --port "$STUDIO_PORT" \
    --timeout-graceful-shutdown 10 --no-access-log
