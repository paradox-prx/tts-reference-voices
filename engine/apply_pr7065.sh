#!/usr/bin/env bash
# Backport of vllm-omni PR #7065 ("[Bugfix] Fix Higgs Audio v3 voice-clone token validation") onto vllm-omni 0.28.0.
# Unpatched, vLLM 0.28.0 rejects the -100 reference-audio sentinels in the Higgs voice-clone prompt ("Token id -100 is
# out of vocabulary", vllm-omni issue #6837), so every voice-clone request fails with HTTP 400. The fix sends the
# <|tts|> id in their place and records the positions for the talker's embedding substitution
# (patches/pr7065-package.diff = the three package files of the PR). GNU patch against site-packages; idempotent.
#
#   engine/apply_pr7065.sh [<venv>]        default $HIGGS_ENGINE_VENV (engine/.venv)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/common.sh"

venv=$(realpath "${1:-$HIGGS_ENGINE_VENV}")
diff=$ROOT/engine/patches/pr7065-package.diff
[[ -x $venv/bin/python ]] || die "$venv is not a venv"
command -v patch >/dev/null || die "GNU patch is required (apt install patch)"
site=$("$venv/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
cd "$site"
if patch -p1 -R --dry-run --silent <"$diff" >/dev/null 2>&1; then
    say "PR #7065 already applied in $site"
    exit 0
fi
patch -p1 --forward --dry-run --silent <"$diff" >/dev/null ||
    die "the patch does not apply to $site (is this vllm-omni $VLLM_OMNI_VERSION?)"
patch -p1 --forward <"$diff"
"$venv/bin/python" -m py_compile vllm_omni/entrypoints/openai/serving_speech.py \
    vllm_omni/model_executor/models/higgs_audio_v3/higgs_audio_v3_talker.py \
    vllm_omni/model_executor/models/higgs_audio_v3/higgs_audio_v3_tokenizer.py
grep -q "prepare_prompt_for_engine" vllm_omni/entrypoints/openai/serving_speech.py || die "patch did not land"
say "PR #7065 applied to $site"
