#!/usr/bin/env bash
# Start the vLLM-Omni engine for Higgs TTS 3 (bosonai/higgs-tts-3-4b) on this box, reusing the Qwen3-TTS engine venv
# and launcher (server/engine/run_engine.sh: clean CUDA 13 toolchain, GPU pinning, FlashInfer sampler off, offline
# HF cache, VLLM_API_KEY from TTS_ENGINE_API_KEY).
#
#   higgs/engine/run_higgs.sh [<deploy-yaml> [port]] [-- extra `vllm serve` args]
#
# Defaults: higgs/engine/deploy/base.yaml and port 8095 (the Qwen engine keeps 8091). Environment (optional):
#   TTS_ENGINE_GPU / CUDA_VISIBLE_DEVICES   physical GPU, default 0 (one 3090: the Qwen units must be stopped first,
#                                           they hold ~21 GB; Higgs needs ~20 GB at the upstream 0.60 / 0.25 split)
#   HIGGS_AUDIO_TOKENIZER_PATH              the Higgs codec used to encode reference clips (k2-fsa/OmniVoice
#                                           audio_tokenizer/, 806 MB). Default: its snapshot in the HF cache, which
#                                           `hf download k2-fsa/OmniVoice --include "audio_tokenizer/*"` fills; with
#                                           HF_HUB_OFFLINE=1 the engine would otherwise fail at the first clone request
#   TTS_ENGINE_API_KEY, TTS_ENGINE_HOST, TTS_ENGINE_EXTRA_ARGS, ...   as in server/engine/run_engine.sh
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../.." && pwd)
die() { echo "run_higgs: $*" >&2; exit 1; }

positional=()
while [[ $# -gt 0 && $1 != -- ]]; do positional+=("$1"); shift; done
if [[ $# -gt 0 ]]; then shift; fi
((${#positional[@]} <= 2)) || die "usage: $0 [<deploy-yaml> [port]] [-- extra vllm serve args]"
yaml=$(realpath "${positional[0]:-${TTS_ENGINE_DEPLOY:-$here/deploy/base.yaml}}")
port=${positional[1]:-${TTS_ENGINE_PORT:-8095}}

hub=${HF_HUB_CACHE:-${HF_HOME:-$HOME/.cache/huggingface}/hub}
if [[ -z ${HIGGS_AUDIO_TOKENIZER_PATH:-} ]]; then
    omni=$hub/models--k2-fsa--OmniVoice
    [[ -f $omni/refs/main ]] || die "k2-fsa/OmniVoice is not in the HF cache; run: hf download k2-fsa/OmniVoice --include 'audio_tokenizer/*'"
    HIGGS_AUDIO_TOKENIZER_PATH=$omni/snapshots/$(<"$omni/refs/main")/audio_tokenizer
fi
[[ -s $HIGGS_AUDIO_TOKENIZER_PATH/model.safetensors && -s $HIGGS_AUDIO_TOKENIZER_PATH/config.json ]] ||
    die "$HIGGS_AUDIO_TOKENIZER_PATH lacks model.safetensors / config.json"
export HIGGS_AUDIO_TOKENIZER_PATH

# vllm_omni/deploy/README_higgs_audio_v3.md: keep DeepGEMM off for this model.
export VLLM_USE_DEEP_GEMM=0 VLLM_MOE_USE_DEEP_GEMM=0
export TTS_ENGINE_MODEL=${TTS_ENGINE_MODEL:-bosonai/higgs-tts-3-4b}
export TTS_ENGINE_VENV=${TTS_ENGINE_VENV:-$repo/server/venvs/engine}
export SPEAKER_SAMPLES_DIR=${SPEAKER_SAMPLES_DIR:-$repo/higgs/state/speakers}
echo "run_higgs: codec $HIGGS_AUDIO_TOKENIZER_PATH" >&2
exec "$repo/server/engine/run_engine.sh" "$yaml" "$port" "$TTS_ENGINE_VENV" -- "$@"
