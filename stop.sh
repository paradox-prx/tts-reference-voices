#!/usr/bin/env bash
# Stop what ./start.sh started:  ./stop.sh [all|engine|studio]   (dev jobs resume on the next start)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/scripts/common.sh"
what=${1:-all}

stop() {
    local f=$RUN_DIR/$1.pid pid
    [[ -f $f ]] || { say "$1: not started by start.sh"; return; }
    pid=$(<"$f")
    if kill -0 "$pid" 2>/dev/null; then
        kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid"
        for ((i = 0; i < 60; i++)); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
        kill -0 "$pid" 2>/dev/null && { kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid"; say "$1 killed"; } ||
            say "$1 stopped"
    else
        say "$1 was not running"
    fi
    rm -f "$f"
}

case $what in
    all) stop studio; stop engine ;;
    engine|studio) stop "$what" ;;
    *) die "usage: $0 [all|engine|studio]" ;;
esac
