#!/usr/bin/env bash
# Install the qwen3-tts systemd user units and the secrets file. Starts or enables nothing unless asked to.
#
#   deploy/install_units.sh [--enable] [--with-qc]
#
# Renders deploy/systemd/*.service (templates) into ${XDG_CONFIG_HOME:-~/.config}/systemd/user with this checkout's
# real paths: @SERVER@ = the server/ directory this script lives in, @ENV_FILE@ = the secrets file, @PYTHON3@ = the
# system python3 for the stdlib helpers (wait_ready.py, health_watchdog.py; override with PYTHON3=...). The units run
# venvs/engine (engine) and venvs/gateway (gateway) of this checkout, and venvs/eval (optional QC sidecar).
# Creates ~/.config/qwen3-tts/env from deploy/env.example with fresh random keys (mode 600; an existing file is never
# overwritten, only checked) and runs `systemctl --user daemon-reload`.
#   --enable   also enable and start the engine, its /health watchdog and the gateway
#   --with-qc  with --enable, also enable and start qwen3-tts-qc.service (set TTS_QC_URL in the env file to use it)
# Units:
#   qwen3-tts-engine.service           engine/run_engine.sh; active once engine/wait_ready.py got audio back
#   qwen3-tts-engine-watchdog.service  deploy/health_watchdog.py: restarts the engine when /health keeps failing
#   qwen3-tts-gateway.service          the gateway (:8090); wants the engine, orders itself after the optional QC
#   qwen3-tts-qc.service               optional QC sidecar (127.0.0.1:8092); nothing depends on it
# User units stop at logout unless lingering is on. Optional (not done here): `loginctl enable-linger "$USER"` keeps
# them running without a login session and starts them at boot.
set -euo pipefail

die() { echo "install_units: $*" >&2; exit 1; }
enable=0 with_qc=0
for arg in "$@"; do
    case $arg in
        --enable) enable=1 ;;
        --with-qc) with_qc=1 ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) die "usage: $0 [--enable] [--with-qc]" ;;
    esac
done
((with_qc == 0 || enable == 1)) || die "--with-qc only makes sense with --enable"

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=$(dirname "$here")
config=${XDG_CONFIG_HOME:-$HOME/.config}
unit_dir=$config/systemd/user
env_file=$config/qwen3-tts/env
python3=${PYTHON3:-/usr/bin/python3}
units=(qwen3-tts-engine.service qwen3-tts-engine-watchdog.service qwen3-tts-gateway.service qwen3-tts-qc.service)

# systemd unit files split on whitespace and expand %-specifiers, and sed below treats & and | specially: refuse
# paths they would mangle.
for path in "$root" "$env_file" "$python3"; do
    [[ $path != *[[:space:]%\&\|]* ]] || die "path '$path' contains whitespace, %, & or |; not usable in a unit file"
done
[[ -x $python3 ]] || die "$python3 not found (set PYTHON3 to a python3 >= 3.9 for the stdlib helpers)"
for venv in engine gateway; do
    [[ -x $root/venvs/$venv/bin/python ]] || echo "install_units: warning: $root/venvs/$venv is missing" >&2
done
[[ -x $root/venvs/eval/bin/python ]] || echo "install_units: note: no venvs/eval; qwen3-tts-qc.service cannot run" >&2

install -d -m 755 "$unit_dir"
for unit in "${units[@]}"; do
    tmp=$(mktemp "$unit_dir/.$unit.XXXXXX")
    sed -e "s|@SERVER@|$root|g" -e "s|@ENV_FILE@|$env_file|g" -e "s|@PYTHON3@|$python3|g" \
        "$here/systemd/$unit" >"$tmp"
    ! grep -n '@[A-Z0-9_]*@' "$tmp" || { rm -f "$tmp"; die "unrendered placeholder in $unit"; }
    chmod 644 "$tmp"
    mv "$tmp" "$unit_dir/$unit"
done

install -d -m 700 "$(dirname "$env_file")"
if [[ -e $env_file ]]; then
    echo "install_units: keeping existing $env_file"
    # Settings an older install wrote that no longer fit this machine / checkout.
    grep -n '^CUDA_VISIBLE_DEVICES=' "$env_file" >&2 &&
        echo "install_units: warning: $env_file sets CUDA_VISIBLE_DEVICES for every unit; use TTS_ENGINE_GPU" >&2
    grep -n '/home/vector/qwen3-tts-server' "$env_file" >&2 &&
        echo "install_units: warning: $env_file points at /home/vector/qwen3-tts-server, not $root" >&2
    true
else
    api_key=$("$python3" -c 'import secrets; print(secrets.token_urlsafe(32))')
    engine_key=$("$python3" -c 'import secrets; print(secrets.token_urlsafe(32))')
    tmp=$(mktemp "$env_file.XXXXXX")
    chmod 600 "$tmp"
    sed -e "s|^TTS_API_KEY=.*|TTS_API_KEY=$api_key|" \
        -e "s|^TTS_ENGINE_API_KEY=.*|TTS_ENGINE_API_KEY=$engine_key|" \
        -e "s|@SERVER@|$root|g" "$here/env.example" >"$tmp"
    mv "$tmp" "$env_file"
    echo "install_units: created $env_file with new keys"
fi
if [[ $(stat -c %a "$env_file") != 600 ]]; then
    chmod 600 "$env_file"
    echo "install_units: $env_file was not mode 600; fixed" >&2
fi

export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
export DBUS_SESSION_BUS_ADDRESS=${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}
systemctl --user daemon-reload
echo "install_units: installed ${units[*]} into $unit_dir (server $root)"
if ((enable)); then
    start=(qwen3-tts-engine.service qwen3-tts-engine-watchdog.service qwen3-tts-gateway.service)
    ((with_qc == 0)) || start+=(qwen3-tts-qc.service)
    systemctl --user enable --now "${start[@]}"
else
    echo "install_units: nothing enabled or started. Start with:"
    echo "  XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR systemctl --user start qwen3-tts-gateway.service \\"
    echo "      qwen3-tts-engine-watchdog.service"
    echo "  optional QC sidecar: also start qwen3-tts-qc.service and set TTS_QC_URL=http://127.0.0.1:8092 in $env_file"
fi
if [[ $(loginctl show-user "$(id -un)" -p Linger --value 2>/dev/null || true) != yes ]]; then
    echo "install_units: note: lingering is off, so the units stop at logout;" \
         "optional: loginctl enable-linger $(id -un)"
fi
