#!/usr/bin/env bash
# Start the Higgs TTS 3 engine (vLLM-Omni `vllm serve --omni`) in the foreground with a clean CUDA environment.
#
#   engine/run_engine.sh [-- extra `vllm serve` args]
#
# Settings (.env or environment): HIGGS_ENGINE_VENV, HIGGS_ENGINE_HOST (127.0.0.1), HIGGS_ENGINE_PORT (8095),
# HIGGS_ENGINE_GPU (0; a non-empty CUDA_VISIBLE_DEVICES wins), HIGGS_ENGINE_DEPLOY (engine/deploy/higgs_3090_32.yaml),
# HIGGS_MODEL, HIGGS_AUDIO_TOKENIZER_PATH, HIGGS_ENGINE_API_KEY (passed as VLLM_API_KEY, never in argv),
# HIGGS_ENGINE_EXTRA_ARGS. The engine needs ~22 GB of a 24 GB card: nothing else may hold the GPU.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/common.sh"

[[ ${1:-} == -- ]] && shift
venv=$HIGGS_ENGINE_VENV
yaml=$HIGGS_ENGINE_DEPLOY
[[ -x $venv/bin/vllm ]] || die "$venv/bin/vllm not found: run ./setup.sh (or engine/install_engine.sh)"
[[ -f $yaml ]] || die "deploy config $yaml not found"
[[ $HIGGS_ENGINE_PORT =~ ^[0-9]+$ ]] || die "bad HIGGS_ENGINE_PORT '$HIGGS_ENGINE_PORT'"
grep -q prepare_prompt_for_engine \
    "$("$venv/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')/vllm_omni/entrypoints/openai/serving_speech.py" ||
    die "vllm-omni in $venv lacks the PR #7065 fix (voice cloning would fail): run engine/apply_pr7065.sh"

# --- CUDA toolchain: only the venv's pip CUDA 13 (site-packages/nvidia/cu13), never a system nvcc / CUDA 12.
site=$("$venv/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
cu13=$site/nvidia/cu13
[[ -x $cu13/bin/nvcc ]] || die "no CUDA 13 nvcc in $cu13: rerun engine/install_engine.sh"
[[ -e $venv/cuda13-link/libcudart.so ]] || die "$venv/cuda13-link/libcudart.so missing: rerun engine/install_engine.sh"
unset CUDA_PATH CUDA_ROOT CUDA_TOOLKIT_ROOT_DIR CUDACXX NVCC_PREPEND_FLAGS NVCC_APPEND_FLAGS LIBRARY_PATH CPATH
export CUDA_HOME=$cu13 FLASHINFER_NVCC=$cu13/bin/nvcc
export PATH=$venv/bin:$cu13/bin:/usr/local/bin:/usr/bin:/bin
export LD_LIBRARY_PATH=$cu13/lib
export FLASHINFER_EXTRA_LDFLAGS="-L$venv/cuda13-link"
export FLASHINFER_CUDA_ARCH_LIST=${FLASHINFER_CUDA_ARCH_LIST:-8.6} TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.6}
# vllm 0.28 pulls nvcc 13.4 while torch pins the CUDA headers to 13.0, so FlashInfer's JIT sampler cannot compile:
# use vLLM's PyTorch top-k/top-p sampler. The deploy YAMLs use FLASH_ATTN attention for the same reason.
export VLLM_USE_FLASHINFER_SAMPLER=${VLLM_USE_FLASHINFER_SAMPLER:-0}
# vllm_omni/deploy/README_higgs_audio_v3.md: keep DeepGEMM off for this model.
export VLLM_USE_DEEP_GEMM=0 VLLM_MOE_USE_DEEP_GEMM=0

# --- GPU and runtime
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-$HIGGS_ENGINE_GPU}
export HF_HUB_OFFLINE=${HF_HUB_OFFLINE:-1} TRANSFORMERS_OFFLINE=${TRANSFORMERS_OFFLINE:-${HF_HUB_OFFLINE:-1}}
export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1 PYTHONUNBUFFERED=1
export VLLM_ENGINE_READY_TIMEOUT_S=${VLLM_ENGINE_READY_TIMEOUT_S:-1200}
[[ -z ${HIGGS_ENGINE_API_KEY:-} ]] || export VLLM_API_KEY=$HIGGS_ENGINE_API_KEY
unset HIGGS_ENGINE_API_KEY STUDIO_ENGINE_API_KEY

# --- model and codec: local snapshot paths, so nothing touches the Hub at run time
model=$HIGGS_MODEL
if [[ -d $model ]]; then
    model=$(realpath "$model")
else
    snap=$(hf_snapshot "$model") || true
    [[ -n $snap && -s $snap/config.json ]] || die "$model is not in the HF cache ($HF_HUB): run engine/download_models.sh"
    model=$snap
fi
if [[ -z ${HIGGS_AUDIO_TOKENIZER_PATH:-} ]]; then
    snap=$(hf_snapshot "$HIGGS_CODEC_REPO") || true
    HIGGS_AUDIO_TOKENIZER_PATH=${snap:+$snap/audio_tokenizer}
fi
[[ -s ${HIGGS_AUDIO_TOKENIZER_PATH:-/nonexistent}/model.safetensors ]] ||
    die "Higgs codec not found ($HIGGS_CODEC_REPO audio_tokenizer): run engine/download_models.sh"
export HIGGS_AUDIO_TOKENIZER_PATH

read -ra extra <<<"${HIGGS_ENGINE_EXTRA_ARGS:-}"
args=(serve "$model" --omni --deploy-config "$yaml" --host "$HIGGS_ENGINE_HOST" --port "$HIGGS_ENGINE_PORT"
      --trust-remote-code --served-model-name "${HIGGS_SERVED_NAME:-higgs-tts-3-4b}"
      --stage-init-timeout 900 --init-timeout 1200 --disable-access-log-for-endpoints "/health,/metrics"
      "${extra[@]}" "$@")
say "GPU $CUDA_VISIBLE_DEVICES, $HIGGS_ENGINE_HOST:$HIGGS_ENGINE_PORT, ${yaml#"$ROOT"/}, venv $venv," \
    "model $model, codec $HIGGS_AUDIO_TOKENIZER_PATH, auth $([[ -n ${VLLM_API_KEY:-} ]] && echo on || echo off)"
mkdir -p "$ROOT/data/engine"
cd "$ROOT/data/engine"
exec "$venv/bin/vllm" "${args[@]}"
