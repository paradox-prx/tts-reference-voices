#!/usr/bin/env bash
# Install the qwen3-tts systemd user units and the secrets file. Starts or enables nothing unless --enable is given.
#
#   deploy/install_units.sh [--enable]
#
# Copies deploy/systemd/*.service to ~/.config/systemd/user, creates ~/.config/qwen3-tts/env from deploy/env.example
# with fresh random keys (mode 600; an existing file is never overwritten) and runs `systemctl --user daemon-reload`.
# --enable additionally enables and starts both units.
set -euo pipefail

die() { echo "install_units: $*" >&2; exit 1; }
enable=0
case ${1:-} in
    --enable) enable=1 ;;
    "") ;;
    *) die "usage: $0 [--enable]" ;;
esac
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=$(dirname "$here")
config=${XDG_CONFIG_HOME:-$HOME/.config}
unit_dir=$config/systemd/user
env_file=$config/qwen3-tts/env
units=(qwen3-tts-engine.service qwen3-tts-gateway.service)

# The units address the project as %h/qwen3-tts-server.
[[ $root == "$HOME/qwen3-tts-server" ]] || echo "install_units: warning: the units expect $HOME/qwen3-tts-server, not $root" >&2

install -d -m 755 "$unit_dir"
for unit in "${units[@]}"; do
    install -m 644 "$here/systemd/$unit" "$unit_dir/$unit"
done

install -d -m 700 "$(dirname "$env_file")"
if [[ -e $env_file ]]; then
    echo "install_units: keeping existing $env_file"
else
    api_key=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
    engine_key=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
    tmp=$(mktemp "$env_file.XXXXXX")
    sed -e "s|^TTS_API_KEY=.*|TTS_API_KEY=$api_key|" \
        -e "s|^TTS_ENGINE_API_KEY=.*|TTS_ENGINE_API_KEY=$engine_key|" \
        -e "s|/home/vector/qwen3-tts-server|$root|g" "$here/env.example" >"$tmp"
    chmod 600 "$tmp"
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
if ((enable)); then
    systemctl --user enable --now "${units[@]}"
else
    echo "install_units: installed ${units[*]} (not enabled, not started). Start with:"
    echo "  XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR systemctl --user start ${units[1]}"
fi
