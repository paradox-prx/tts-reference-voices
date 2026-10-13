#!/usr/bin/env bash
# One-shot setup of higgs-studio on a Linux box with an NVIDIA GPU (24 GB; tested on one RTX 3090).
#
#   ./setup.sh [--skip-engine] [--skip-models] [--skip-web] [--skip-tests]
#
# Steps (each one is skipped when already done, so re-running is cheap):
#   1. .env from .env.example (edit it afterwards; the scripts and the app read it)
#   2. engine venv (vLLM + vLLM-Omni 0.28.0 + PR #7065 patch): an existing one at $HIGGS_ENGINE_VENV is reused
#      after its patch is checked; otherwise engine/install_engine.sh builds engine/.venv (~4 GB download)
#   3. Higgs checkpoint + codec in the HF cache: reused when present, else downloaded (~9.5 GB)
#   4. app venv (.venv, Python 3.12) from app/requirements.txt
#   5. web consoles: npm ci + build into web/dist (needs node >= 18)
#   6. unit tests
# Then: ./start.sh (foreground processes in the background, logs in data/logs) or ./install_units.sh (systemd).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ -f .env ]] || { cp .env.example .env; echo "setup.sh: created .env from .env.example" >&2; }
source scripts/common.sh

skip_engine=0 skip_models=0 skip_web=0 skip_tests=0
for a in "$@"; do
    case $a in
        --skip-engine) skip_engine=1 ;; --skip-models) skip_models=1 ;;
        --skip-web) skip_web=1 ;; --skip-tests) skip_tests=1 ;;
        -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
        *) die "unknown option $a" ;;
    esac
done

command -v ffmpeg >/dev/null || die "ffmpeg is required (apt install ffmpeg)"
command -v nvidia-smi >/dev/null || say "warning: nvidia-smi not found; the engine needs an NVIDIA GPU"
uv=${UV:-$(command -v uv || true)}

# --- 2. engine venv
if ((skip_engine)); then
    say "engine venv: skipped"
elif [[ -x $HIGGS_ENGINE_VENV/bin/vllm ]]; then
    say "engine venv: reusing $HIGGS_ENGINE_VENV"
    v=$("$HIGGS_ENGINE_VENV/bin/python" -c 'import importlib.metadata as m; print(m.version("vllm"), m.version("vllm-omni"))')
    [[ $v == "$VLLM_VERSION $VLLM_OMNI_VERSION" ]] ||
        die "$HIGGS_ENGINE_VENV has vllm/vllm-omni $v, need $VLLM_VERSION/$VLLM_OMNI_VERSION (unset HIGGS_ENGINE_VENV to build engine/.venv)"
    engine/apply_pr7065.sh "$HIGGS_ENGINE_VENV"
    if [[ ! -e $HIGGS_ENGINE_VENV/cuda13-link/libcudart.so ]]; then
        site=$("$HIGGS_ENGINE_VENV/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
        mkdir -p "$HIGGS_ENGINE_VENV/cuda13-link"
        ln -sfn "$site/nvidia/cu13/lib/libcudart.so.13" "$HIGGS_ENGINE_VENV/cuda13-link/libcudart.so"
    fi
    [[ -x $HIGGS_ENGINE_VENV/bin/hf ]] || {
        if [[ -n $uv ]]; then "$uv" pip install -p "$HIGGS_ENGINE_VENV/bin/python" "huggingface_hub[cli]"
        else "$HIGGS_ENGINE_VENV/bin/python" -m pip install "huggingface_hub[cli]"; fi; }
else
    engine/install_engine.sh "$HIGGS_ENGINE_VENV"
fi

# --- 3. checkpoint + codec
((skip_models)) && say "models: skipped" || engine/download_models.sh

# --- 4. app venv
if [[ ! -x $STUDIO_VENV/bin/python ]]; then
    if [[ -n $uv ]]; then "$uv" venv -p 3.12 "$STUDIO_VENV"
    else
        py=${PY312:-$(command -v python3.12 || command -v python3)}
        "$py" -c 'import sys; sys.exit(sys.version_info < (3, 10))' || die "need Python >= 3.10 (or uv)"
        "$py" -m venv "$STUDIO_VENV"
    fi
fi
if [[ -n $uv ]]; then "$uv" pip install -q -p "$STUDIO_VENV/bin/python" -r app/requirements.txt
else "$STUDIO_VENV/bin/python" -m pip install -q --disable-pip-version-check -r app/requirements.txt; fi
say "app venv: $STUDIO_VENV"

# --- 5. web
if ((skip_web)); then
    say "web: skipped"
elif command -v npm >/dev/null && node -e 'process.exit(parseInt(process.versions.node) < 18 ? 1 : 0)'; then
    (cd web && npm ci --no-audit --no-fund --loglevel=error && npm run build --silent | tail -1)
    say "web: built web/dist"
elif [[ -f web/dist/index.html ]]; then
    say "web: node >= 18 not found; keeping the existing web/dist"
else
    say "warning: node >= 18 not found, the consoles are not built (the API still works). Install node and rerun."
fi

# --- 6. tests
if ((skip_tests == 0)); then
    (cd app && "$STUDIO_VENV/bin/python" -m pytest -q tests) || die "unit tests failed"
fi

voices=$(cd app && "$STUDIO_VENV/bin/python" -c 'from studio.settings import settings; print(settings.voices_dir)')
mkdir -p "$ROOT/data" "$voices"
say "done. Voices: $voices ($(find "$voices" -mindepth 1 -maxdepth 1 -type d | wc -l) folders)."
say "next: ./start.sh   (or ./install_units.sh for systemd)   then open http://<host>:$STUDIO_PORT/studio and /dev"
