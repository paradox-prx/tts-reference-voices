#!/usr/bin/env bash
# Restart higgs-engine when its API server is up but the engine behind it is dead (e.g. a stage crashed on a CUDA
# OOM: the main process keeps running and /health answers 503, so systemd's Restart= never fires). Run every minute
# by higgs-engine-watchdog.timer (install_units.sh). Does nothing while the unit is starting or stopped.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/common.sh"
[[ $(systemctl --user show higgs-engine -p ActiveState --value) == active ]] || exit 0
for i in 1 2 3; do
    curl -sf -o /dev/null --max-time 5 "$STUDIO_ENGINE_URL/health" && exit 0
    ((i < 3)) && sleep 10
done
say "engine unhealthy for 20 s while active: restarting higgs-engine"
systemctl --user restart --no-block higgs-engine
