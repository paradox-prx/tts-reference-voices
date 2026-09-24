#!/usr/bin/env bash
# Start the vLLM-Omni engine for Qwen3-TTS-12Hz-1.7B-Base with a clean CUDA environment (execs `vllm serve`).
#
#   run_engine.sh [<deploy-yaml> [port] [venv]] [-- extra `vllm serve` args]
#
# Missing positionals fall back to $TTS_ENGINE_DEPLOY, $TTS_ENGINE_PORT, $TTS_ENGINE_VENV, then to
# engine/deploy/qwen3_tts_prod.yaml, 8091 and venvs/engine. Other environment (all optional):
#   CUDA_VISIBLE_DEVICES     physical GPU, default 1 (PCI bus order, as nvidia-smi numbers them)
#   TTS_ENGINE_MODEL         HF repo id or local directory (default Qwen/Qwen3-TTS-12Hz-1.7B-Base); with
#                            HF_HUB_OFFLINE=1 (the default) a repo id is resolved to its HF cache snapshot
#   TTS_ENGINE_HOST          bind address, default 127.0.0.1
#   TTS_ENGINE_API_KEY       key for /v1 (passed as VLLM_API_KEY so it never shows in argv)
#   TTS_ENGINE_ALLOWED_MEDIA_PATH  directory that file:// ref_audio may read (--allowed-local-media-path)
#   TTS_ENGINE_STAGE_INIT_TIMEOUT / TTS_ENGINE_INIT_TIMEOUT  seconds (defaults 900 / 1200: the first start
#                            compiles the talker and captures CUDA graphs)
#   TTS_ENGINE_EXTRA_ARGS    extra `vllm serve` args (word-split), before the ones given after --
#   SPEAKER_SAMPLES_DIR      where uploaded voices persist, default state/speakers
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
die() { echo "run_engine: $*" >&2; exit 1; }

positional=()
while [[ $# -gt 0 && $1 != -- ]]; do positional+=("$1"); shift; done
[[ $# -gt 0 ]] && shift
((${#positional[@]} <= 3)) || die "usage: $0 [<deploy-yaml> [port] [venv]] [-- extra vllm serve args]"
yaml=$(realpath "${positional[0]:-${TTS_ENGINE_DEPLOY:-$root/engine/deploy/qwen3_tts_prod.yaml}}")
port=${positional[1]:-${TTS_ENGINE_PORT:-8091}}
venv=$(realpath "${positional[2]:-${TTS_ENGINE_VENV:-$root/venvs/engine}}")
read -ra extra <<<"${TTS_ENGINE_EXTRA_ARGS:-}"
extra+=("$@")
[[ -f $yaml ]] || die "deploy config $yaml not found"
[[ $port =~ ^[0-9]+$ ]] || die "bad port '$port'"
[[ -x $venv/bin/vllm ]] || die "$venv/bin/vllm not found (engine/install_engine.sh builds the venv)"

# --- CUDA toolchain: only the venv's pip CUDA 13 (site-packages/nvidia/cu13), never /usr/bin/nvcc (12.0) or the
# incomplete /usr/local/cuda. FlashInfer JIT takes $CUDA_HOME (else $CUDA_PATH, else `which nvcc`, else
# /usr/local/cuda) and runs $FLASHINFER_NVCC (default $CUDA_HOME/bin/nvcc); flashinfer/jit/cpp_ext.py L47-64, L270.
site=$("$venv/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
cu13=$site/nvidia/cu13
[[ -x $cu13/bin/nvcc ]] || die "no CUDA 13 nvcc in $cu13 (nvidia-cuda-nvcc); rerun engine/install_engine.sh"
unset CUDA_PATH CUDA_ROOT CUDA_TOOLKIT_ROOT_DIR CUDACXX NVCC_PREPEND_FLAGS NVCC_APPEND_FLAGS LIBRARY_PATH CPATH
export CUDA_HOME=$cu13
export FLASHINFER_NVCC=$cu13/bin/nvcc
export PATH=$venv/bin:$cu13/bin:/usr/local/bin:/usr/bin:/bin
export LD_LIBRARY_PATH=$cu13/lib
# JIT for the 3090 only, as SASS: the r580 driver (CUDA 13.0) cannot JIT PTX from nvcc 13.4.
export FLASHINFER_CUDA_ARCH_LIST=${FLASHINFER_CUDA_ARCH_LIST:-8.6} TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.6}
# FlashInfer links JIT modules with -lcudart; install_engine.sh points cuda13-link/libcudart.so at the venv's
# libcudart.so.13 so the system CUDA 12.0 libcudart.so is never linked.
[[ -e $venv/cuda13-link/libcudart.so ]] || die "$venv/cuda13-link/libcudart.so missing; rerun install_engine.sh"
export FLASHINFER_EXTRA_LDFLAGS="-L$venv/cuda13-link"

# --- GPU placement and runtime
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-1}
export HF_HUB_OFFLINE=${HF_HUB_OFFLINE:-1} TRANSFORMERS_OFFLINE=${TRANSFORMERS_OFFLINE:-${HF_HUB_OFFLINE:-1}}
export SPEAKER_SAMPLES_DIR=${SPEAKER_SAMPLES_DIR:-$root/state/speakers}
mkdir -p -m 700 "$SPEAKER_SAMPLES_DIR"
export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1 PYTHONUNBUFFERED=1
export VLLM_ENGINE_READY_TIMEOUT_S=${VLLM_ENGINE_READY_TIMEOUT_S:-1200}
if [[ -n ${TTS_ENGINE_API_KEY:-} ]]; then
    export VLLM_API_KEY=$TTS_ENGINE_API_KEY
fi
unset TTS_API_KEY TTS_ENGINE_API_KEY

# --- model: a local path when offline, so no code path tries the Hub
model=${TTS_ENGINE_MODEL:-Qwen/Qwen3-TTS-12Hz-1.7B-Base}
served=${model%/}
if [[ -d $model ]]; then
    served=$(basename "$served")
elif [[ $HF_HUB_OFFLINE == 1 ]]; then
    repo=${HF_HUB_CACHE:-${HF_HOME:-$HOME/.cache/huggingface}/hub}/models--${model//\//--}
    [[ -f $repo/refs/main ]] || die "$model is not in the HF cache ($repo)"
    model=$repo/snapshots/$(<"$repo/refs/main")
fi
for f in config.json model.safetensors speech_tokenizer/config.json speech_tokenizer/model.safetensors; do
    [[ -d $model && ! -e $model/$f ]] && die "model directory $model lacks $f (incomplete download?)"
done

args=(serve "$model" --omni --deploy-config "$yaml" --host "${TTS_ENGINE_HOST:-127.0.0.1}" --port "$port"
      --trust-remote-code --served-model-name "$served"
      --stage-init-timeout "${TTS_ENGINE_STAGE_INIT_TIMEOUT:-900}" --init-timeout "${TTS_ENGINE_INIT_TIMEOUT:-1200}"
      --disable-access-log-for-endpoints /health,/metrics)
if [[ -n ${TTS_ENGINE_ALLOWED_MEDIA_PATH:-} ]]; then
    args+=(--allowed-local-media-path "$TTS_ENGINE_ALLOWED_MEDIA_PATH")
fi
args+=("${extra[@]}")

echo "run_engine: GPU $CUDA_VISIBLE_DEVICES, $yaml, port $port, venv $venv, model $model," \
     "nvcc $("$FLASHINFER_NVCC" --version | sed -n 's/.*release \([0-9.]*\),.*/\1/p'), auth $([[ -n ${VLLM_API_KEY:-} ]] && echo on || echo off)" >&2
exec "$venv/bin/vllm" "${args[@]}"
