#!/usr/bin/env bash
# One-shot setup of the Higgs TTS 3 engine (bosonai/higgs-tts-3-4b) on a new Linux box with an NVIDIA GPU (~24 GB,
# CUDA 13 driver). Run from the repository root:
#
#   higgs/setup.sh [--with-eval] [--start] [--skip-models]
#
# Steps (each is skipped when already done, so re-running is cheap):
#   1. checks: Python 3.12, uv (installed into ~/.local/bin if missing), nvidia-smi, GNU patch
#   2. engine venv server/venvs/engine: vLLM 0.28.0 + vLLM-Omni 0.28.0 (torch 2.13 cu130), pinned by
#      server/engine/constraints-omni28.txt, built by server/engine/install_engine.sh (~4 GB download)
#   3. the vllm-omni PR #7065 patch (without it every voice-clone request fails with HTTP 400)
#   4. the model and its reference-audio codec in the Hugging Face cache (~10 GB)
#   5. gateway venv server/venvs/gateway (gateway, bench/bench_tts.py)
#   6. with --with-eval: eval venv server/venvs/eval (Whisper / speaker-similarity scoring)
#   7. with --start: start the engine on port 8095 (flash_attn.yaml) and wait for /health
#
# Environment: PY312 (a Python 3.12 binary), HF_TOKEN (if the Hub asks for one), HF_HOME (cache location).
# Licence: Higgs TTS 3 is research / non-commercial only; serving it to users needs a licence from Boson AI.
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo"
server=$repo/server
log() { printf '\n== %s\n' "$*"; }
die() { echo "higgs/setup.sh: $*" >&2; exit 1; }

with_eval=0 start=0 skip_models=0
for a in "$@"; do
    case $a in
        --with-eval) with_eval=1 ;; --start) start=1 ;; --skip-models) skip_models=1 ;;
        -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
        *) die "unknown option $a (see --help)" ;;
    esac
done

# ---- 1. prerequisites -----------------------------------------------------------------------------------------------
log "1/7 prerequisites"
[[ -f server/engine/install_engine.sh && -d higgs ]] || die "run from the tts-reference-voices checkout"
command -v nvidia-smi >/dev/null || die "nvidia-smi not found: install the NVIDIA driver first"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
command -v patch >/dev/null || die "GNU patch not found (apt install patch)"
py312=${PY312:-}
if [[ -z $py312 ]]; then
    for c in python3.12 "$(pyenv root 2>/dev/null)"/versions/3.12.*/bin/python3.12; do
        if [[ -n $c ]] && "$c" -c 'import sys; assert sys.version_info[:2] == (3, 12)' 2>/dev/null; then
            py312=$(command -v "$c" || echo "$c"); break
        fi
    done
fi
[[ -n $py312 ]] || die "Python 3.12 not found: install it (apt install python3.12 python3.12-venv, or pyenv) or set PY312"
export PY312=$py312
echo "python: $py312 ($("$py312" -V))"
if ! command -v uv >/dev/null; then
    echo "uv not found: installing it into ~/.local/bin"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH=$HOME/.local/bin:$PATH
fi
echo "uv: $(command -v uv) ($(uv --version))"
export UV_HTTP_TIMEOUT=${UV_HTTP_TIMEOUT:-900}

# ---- 2. engine venv -------------------------------------------------------------------------------------------------
log "2/7 engine venv (server/venvs/engine)"
engine_ok() {
    [[ -x server/venvs/engine/bin/python ]] && CUDA_VISIBLE_DEVICES="" server/venvs/engine/bin/python -c \
        'import vllm, vllm_omni, torch; assert vllm.__version__ == "0.28.0" and vllm_omni.__version__ == "0.28.0"' \
        >/dev/null 2>&1
}
if engine_ok; then
    echo "already installed (vllm 0.28.0, vllm-omni 0.28.0)"
else
    server/engine/install_engine.sh server/venvs/engine - 0.28.0 0.28.0
    engine_ok || die "engine venv did not import after install"
fi

# ---- 3. PR #7065 patch ----------------------------------------------------------------------------------------------
log "3/7 Higgs voice-clone patch (vllm-omni PR #7065)"
higgs/engine/patches/apply_pr7065.sh server/venvs/engine

# ---- 4. model weights -----------------------------------------------------------------------------------------------
log "4/7 model weights (Hugging Face cache)"
hf=server/venvs/engine/bin/hf
if ((skip_models)); then
    echo "skipped (--skip-models)"
else
    HF_HUB_OFFLINE=0 "$hf" download bosonai/higgs-tts-3-4b
    HF_HUB_OFFLINE=0 "$hf" download k2-fsa/OmniVoice --include "audio_tokenizer/*"
fi

# ---- 5. gateway venv ------------------------------------------------------------------------------------------------
log "5/7 gateway venv (server/venvs/gateway)"
[[ -x server/venvs/gateway/bin/python ]] || uv venv -p "$py312" server/venvs/gateway
uv pip install -p server/venvs/gateway/bin/python fastapi 'uvicorn[standard]' httpx numpy soundfile pydantic \
    pydantic-settings orjson prometheus-client pyyaml pytest pytest-asyncio

# ---- 6. eval venv (optional) ----------------------------------------------------------------------------------------
log "6/7 eval venv (server/venvs/eval)"
if ((with_eval)); then
    [[ -x server/venvs/eval/bin/python ]] || uv venv -p "$py312" server/venvs/eval
    uv pip install -p server/venvs/eval/bin/python -r server/eval/requirements-eval.txt
    echo "scoring models: server/venvs/gateway/bin/python server/eval/fetch_models.py (needs huggingface_hub)"
else
    echo "skipped (add --with-eval for Whisper / speaker-similarity scoring)"
fi

# ---- 7. start (optional) --------------------------------------------------------------------------------------------
log "7/7 start"
cmd="higgs/engine/run_higgs.sh higgs/engine/deploy/flash_attn.yaml 8095"
if ((start)); then
    mkdir -p higgs/logs
    nohup $cmd > higgs/logs/engine_setup_start.log 2>&1 &
    echo "engine starting (pid $!), log higgs/logs/engine_setup_start.log; first start compiles kernels (a few min)"
    for _ in $(seq 1 180); do
        curl -sf localhost:8095/health >/dev/null && { echo "engine healthy on http://127.0.0.1:8095"; break; }
        kill -0 $! 2>/dev/null || die "engine exited; see higgs/logs/engine_setup_start.log"
        sleep 5
    done
else
    echo "not started. Start it with:  $cmd"
fi

cat <<EOF

Done. Next:
  start the engine:   $cmd
  health check:       curl -s localhost:8095/health
  gateway (optional): higgs/engine/run_gateway.sh 8090
  a clone request:    see higgs/README.md ("Run")
Only one engine fits on a 24 GB GPU: stop any other TTS engine on the card first.
EOF
