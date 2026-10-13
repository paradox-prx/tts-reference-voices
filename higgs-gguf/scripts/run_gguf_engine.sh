#!/usr/bin/env bash
# Start the Higgs engine on a GGUF through higgs-studio's own launcher (higgs-studio/engine/run_engine.sh, unchanged),
# with the harness that teaches vLLM-Omni the `higgs_gguf` load format.
#
#   scripts/run_gguf_engine.sh [weights dir | model.gguf] [-- extra `vllm serve` args]
#   default weights dir: weights/higgs-tts-3-4b-Q8_0
#
# Env: GGUF_ENGINE_PORT (8096, so it never collides with production on 8095), GGUF_DEPLOY
# (deploy/higgs_gguf_3090_32.yaml), STUDIO_DIR (../higgs-studio). The engine needs the whole GPU: stop the production
# unit first (systemctl --user stop higgs-engine higgs-engine-watchdog.timer) and start it again afterwards.
#
# What the harness changes, and nothing else:
#   PYTHONPATH=harness + HIGGS_GGUF_HARNESS=1 -> harness/sitecustomize.py registers load format `higgs_gguf` in every
#                                               vLLM process (API server and both stages);
#   HIGGS_MODEL=<weights dir>                 -> config.json / tokenizer files + model.gguf (no safetensors);
#   HIGGS_ENGINE_DEPLOY=deploy/...yaml        -> the production profile plus `load_format: higgs_gguf` per stage.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
STUDIO_DIR=${STUDIO_DIR:-$HERE/../higgs-studio}
launcher=$STUDIO_DIR/engine/run_engine.sh
[[ -x $launcher ]] || { echo "run_gguf_engine.sh: $launcher not found (set STUDIO_DIR)" >&2; exit 1; }

src=$HERE/weights/higgs-tts-3-4b-Q8_0
[[ $# -gt 0 && $1 != -- ]] && { src=$1; shift; }
[[ ${1:-} == -- ]] && shift
src=$(realpath "$src")
if [[ -f $src && $src == *.gguf ]]; then
    export HIGGS_GGUF_FILE=$src
    src=$(dirname "$src")
fi
[[ -d $src && -s $src/config.json ]] || { echo "run_gguf_engine.sh: $src has no config.json (run scripts/gguf_model_dir.py)" >&2; exit 1; }
compgen -G "$src/*.gguf" >/dev/null || { echo "run_gguf_engine.sh: no *.gguf in $src" >&2; exit 1; }
if compgen -G "$src/*.safetensors" >/dev/null; then
    echo "run_gguf_engine.sh: $src also holds safetensors; refusing (the test must load the GGUF only)" >&2; exit 1
fi

export HIGGS_MODEL=$src
export HIGGS_ENGINE_DEPLOY=$(realpath "${GGUF_DEPLOY:-$HERE/deploy/higgs_gguf_3090_32.yaml}")
export HIGGS_ENGINE_PORT=${GGUF_ENGINE_PORT:-8096}
export HIGGS_SERVED_NAME=${HIGGS_SERVED_NAME:-higgs-tts-3-4b}
export HIGGS_GGUF_HARNESS=1
export PYTHONPATH=$HERE/harness${PYTHONPATH:+:$PYTHONPATH}
exec "$launcher" -- "$@"
