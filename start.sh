#!/usr/bin/env bash
# Start the engine and/or the studio in the background (no systemd), logs in data/logs/, pids in data/run/.
#
#   ./start.sh [all|engine|studio]          default all; waits until the engine answers /health
#
# With the systemd units installed (./install_units.sh) use systemctl --user instead.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/scripts/common.sh"
what=${1:-all}
mkdir -p "$RUN_DIR" "$LOG_DIR"

running() { [[ -f $RUN_DIR/$1.pid ]] && kill -0 "$(<"$RUN_DIR/$1.pid")" 2>/dev/null; }

launch() {   # name script
    if running "$1"; then say "$1 already running (pid $(<"$RUN_DIR/$1.pid"))"; return; fi
    # own session, so stop.sh can signal the whole process group (the engine forks stage workers)
    setsid nohup "$2" >>"$LOG_DIR/$1.log" 2>&1 </dev/null &
    echo $! >"$RUN_DIR/$1.pid"
    say "$1 started (pid $!, log data/logs/$1.log)"
}

engine_up() { curl -sf -o /dev/null --max-time 3 "$STUDIO_ENGINE_URL/health"; }

case $what in
    all|engine)
        if engine_up && ! running engine; then
            say "an engine already answers at $STUDIO_ENGINE_URL; not starting another"
        else
            free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$HIGGS_ENGINE_GPU" 2>/dev/null || echo 0)
            ((free >= 21000)) || say "warning: only ${free} MiB free on GPU $HIGGS_ENGINE_GPU (the engine needs ~21 GB)"
            launch engine "$ROOT/engine/run_engine.sh"
            say "waiting for the engine (first start: model load + warm-up, a few minutes)…"
            for ((i = 0; i < 300; i++)); do
                engine_up && break
                running engine || die "engine exited; see data/logs/engine.log"
                sleep 5
            done
            engine_up && say "engine ready at $STUDIO_ENGINE_URL" || die "engine not ready after 25 min; see data/logs/engine.log"
        fi ;;&
    all|studio)
        launch studio "$ROOT/scripts/run_studio.sh"
        for ((i = 0; i < 30; i++)); do
            curl -sf -o /dev/null --max-time 2 "http://127.0.0.1:$STUDIO_PORT/api/status" && break
            sleep 1
        done
        curl -sf -o /dev/null "http://127.0.0.1:$STUDIO_PORT/api/status" || die "studio not answering; see data/logs/studio.log"
        say "studio: http://$(hostname -I 2>/dev/null | awk '{print $1}'):$STUDIO_PORT/studio  ·  /dev" ;;
    engine) ;;
    *) die "usage: $0 [all|engine|studio]" ;;
esac
