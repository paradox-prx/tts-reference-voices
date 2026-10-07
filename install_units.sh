#!/usr/bin/env bash
# Install systemd user units for the engine and the studio (they read .env through the scripts).
#
#   ./install_units.sh [--now]      --now also enables and (re)starts both
#
# Units: higgs-engine.service (engine/run_engine.sh), higgs-studio.service (scripts/run_studio.sh, wants the engine)
# and higgs-engine-watchdog.timer (engine/watchdog.sh: restarts the engine when /health fails while it is active,
# e.g. after a stage crashed but the API server stayed up). To keep them running without a login session and start them at boot: sudo loginctl enable-linger $USER
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/scripts/common.sh"
dir=${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user
mkdir -p "$dir"

cat >"$dir/higgs-engine.service" <<EOF
# Written by $ROOT/install_units.sh
[Unit]
Description=Higgs TTS 3 engine (vLLM-Omni, $HIGGS_ENGINE_HOST:$HIGGS_ENGINE_PORT)
# one 24 GB GPU cannot hold both TTS engines
Conflicts=qwen3-tts-engine.service
StartLimitIntervalSec=1800
StartLimitBurst=3

[Service]
Type=exec
ExecStart=$ROOT/engine/run_engine.sh
# active only once /health answers (model load + warm-up take minutes on a cold start)
ExecStartPost=/bin/bash -c 'for i in \$(seq 600); do kill -0 \$\$MAINPID 2>/dev/null || exit 1; curl -sf -o /dev/null --max-time 3 $STUDIO_ENGINE_URL/health && exit 0; sleep 3; done; exit 1'
TimeoutStartSec=1900
Restart=on-failure
RestartSec=15
KillMode=mixed
TimeoutStopSec=90
LimitNOFILE=65536
UMask=0077
SyslogIdentifier=higgs-engine

[Install]
WantedBy=default.target
EOF

cat >"$dir/higgs-studio.service" <<EOF
# Written by $ROOT/install_units.sh
[Unit]
Description=Higgs Studio consoles + API (port $STUDIO_PORT)
Wants=higgs-engine.service
After=higgs-engine.service

[Service]
Type=exec
ExecStart=$ROOT/scripts/run_studio.sh
Restart=on-failure
RestartSec=5
TimeoutStopSec=20
UMask=0077
SyslogIdentifier=higgs-studio

[Install]
WantedBy=default.target
EOF

cat >"$dir/higgs-engine-watchdog.service" <<EOF
# Written by $ROOT/install_units.sh
[Unit]
Description=Restart higgs-engine when its /health fails while it is active

[Service]
Type=oneshot
ExecStart=$ROOT/engine/watchdog.sh
SyslogIdentifier=higgs-engine-watchdog
EOF

cat >"$dir/higgs-engine-watchdog.timer" <<EOF
# Written by $ROOT/install_units.sh
[Unit]
Description=Check higgs-engine health every minute

[Timer]
OnBootSec=5min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
say "installed $dir/higgs-engine.service, higgs-studio.service, higgs-engine-watchdog.{service,timer}"
if [[ ${1:-} == --now ]]; then
    systemctl --user enable higgs-engine.service higgs-studio.service higgs-engine-watchdog.timer
    systemctl --user restart higgs-engine.service
    systemctl --user restart higgs-studio.service
    systemctl --user restart higgs-engine-watchdog.timer
    systemctl --user --no-pager status higgs-engine.service higgs-studio.service | grep -E '●|Active:'
else
    say "start with: systemctl --user enable --now higgs-engine higgs-studio higgs-engine-watchdog.timer"
fi
[[ $(loginctl show-user "$USER" -p Linger --value 2>/dev/null) == yes ]] ||
    say "note: lingering is off; the units stop when you log out. Fix: sudo loginctl enable-linger $USER"
