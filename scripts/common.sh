# Sourced by every higgs-studio script: repo root, .env, defaults. Not executable on its own.
#
# Settings live in higgs-studio/.env (copy .env.example). HIGGS_* configure the engine, STUDIO_* the web app; the
# environment of the calling shell wins over .env.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

_load_env() {
    local f=$ROOT/.env line key
    [[ -f $f ]] || return 0
    while IFS= read -r line || [[ -n $line ]]; do
        [[ $line =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)= ]] || continue
        key=${BASH_REMATCH[1]}
        [[ -n ${!key+x} ]] && continue        # already set by the caller
        eval "export $line"
    done <"$f"
}
_load_env

# relative paths in .env are relative to the repo root, whatever the working directory (systemd uses $HOME)
_abs() { [[ $1 == /* ]] && realpath -m "$1" || realpath -m "$ROOT/$1"; }

export HF_HOME=${HF_HOME:-$HOME/.cache/huggingface}
HF_HUB=${HF_HUB_CACHE:-$HF_HOME/hub}

HIGGS_ENGINE_VENV=$(_abs "${HIGGS_ENGINE_VENV:-engine/.venv}")
HIGGS_ENGINE_HOST=${HIGGS_ENGINE_HOST:-127.0.0.1}
HIGGS_ENGINE_PORT=${HIGGS_ENGINE_PORT:-8095}
HIGGS_ENGINE_GPU=${HIGGS_ENGINE_GPU:-0}
HIGGS_ENGINE_DEPLOY=$(_abs "${HIGGS_ENGINE_DEPLOY:-engine/deploy/higgs_3090_32.yaml}")
HIGGS_MODEL=${HIGGS_MODEL:-bosonai/higgs-tts-3-4b}
HIGGS_CODEC_REPO=${HIGGS_CODEC_REPO:-k2-fsa/OmniVoice}
VLLM_VERSION=0.28.0
VLLM_OMNI_VERSION=0.28.0

STUDIO_VENV=$ROOT/.venv
export STUDIO_ENGINE_URL=${STUDIO_ENGINE_URL:-http://127.0.0.1:$HIGGS_ENGINE_PORT}
[[ -z ${HIGGS_AUDIO_TOKENIZER_PATH:-} ]] || HIGGS_AUDIO_TOKENIZER_PATH=$(_abs "$HIGGS_AUDIO_TOKENIZER_PATH")
[[ -z ${HIGGS_ENGINE_API_KEY:-} || -n ${STUDIO_ENGINE_API_KEY:-} ]] || export STUDIO_ENGINE_API_KEY=$HIGGS_ENGINE_API_KEY
STUDIO_PORT=${STUDIO_PORT:-8100}
STUDIO_HOST=${STUDIO_HOST:-0.0.0.0}
RUN_DIR=$ROOT/data/run
LOG_DIR=$ROOT/data/logs

# HF cache snapshot directory of a repo id (empty when it is not cached)
hf_snapshot() {
    local repo=$HF_HUB/models--${1//\//--}
    [[ -f $repo/refs/main ]] && echo "$repo/snapshots/$(<"$repo/refs/main")"
}

say() { echo -e "\033[1m${0##*/}:\033[0m $*" >&2; }
die() { echo -e "\033[1;31m${0##*/}:\033[0m $*" >&2; exit 1; }
