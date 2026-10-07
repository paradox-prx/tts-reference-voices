#!/usr/bin/env bash
# Make sure the Higgs checkpoint and its audio codec are in the Hugging Face cache ($HF_HOME/hub). Already cached
# files are reused; nothing is downloaded twice.
#
#   bosonai/higgs-tts-3-4b           ~8.7 GB  the model ($HIGGS_MODEL; a local directory is used as is)
#   k2-fsa/OmniVoice audio_tokenizer ~0.8 GB  the codec that encodes reference clips ($HIGGS_AUDIO_TOKENIZER_PATH wins)
#
# Higgs TTS 3 is under Boson's Research and Non-Commercial License: commercial use needs a licence from Boson.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/common.sh"

hf=$HIGGS_ENGINE_VENV/bin/hf
[[ -x $hf ]] || die "$hf not found: build the engine venv first (engine/install_engine.sh)"

# complete enough to serve: config plus every weight file the index names (or a single model.safetensors)
model_ok() {
    local d=$1 f
    [[ -s $d/config.json ]] || return 1
    if [[ -f $d/model.safetensors.index.json ]]; then
        for f in $(grep -o '"[^"]*\.safetensors"' "$d/model.safetensors.index.json" | tr -d '"' | sort -u); do
            [[ -s $d/$f ]] || return 1
        done
    else
        [[ -s $d/model.safetensors ]] || return 1
    fi
}

if [[ -d $HIGGS_MODEL ]]; then
    model_ok "$HIGGS_MODEL" || die "$HIGGS_MODEL is not a complete checkpoint"
    say "model: local directory $HIGGS_MODEL"
elif snap=$(hf_snapshot "$HIGGS_MODEL") && model_ok "$snap"; then
    say "model: reusing cached $HIGGS_MODEL ($snap)"
else
    say "downloading $HIGGS_MODEL (~8.7 GB)"
    HF_HUB_OFFLINE=0 "$hf" download "$HIGGS_MODEL"
fi

if [[ -n ${HIGGS_AUDIO_TOKENIZER_PATH:-} ]]; then
    [[ -s $HIGGS_AUDIO_TOKENIZER_PATH/model.safetensors ]] || die "HIGGS_AUDIO_TOKENIZER_PATH=$HIGGS_AUDIO_TOKENIZER_PATH lacks model.safetensors"
    say "codec: $HIGGS_AUDIO_TOKENIZER_PATH"
elif snap=$(hf_snapshot "$HIGGS_CODEC_REPO") && [[ -s $snap/audio_tokenizer/model.safetensors ]]; then
    say "codec: reusing cached $HIGGS_CODEC_REPO/audio_tokenizer"
else
    say "downloading $HIGGS_CODEC_REPO audio_tokenizer (~0.8 GB)"
    HF_HUB_OFFLINE=0 "$hf" download "$HIGGS_CODEC_REPO" --include 'audio_tokenizer/*'
fi
