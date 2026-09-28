#!/usr/bin/env bash
# Backport of vllm-omni PR #7065 ("[Bugfix] Fix Higgs Audio v3 voice-clone token validation") onto the installed
# vllm-omni 0.28.0: vLLM 0.28.0 rejects the -100 reference-audio sentinels in the Higgs voice-clone prompt ("Token id
# -100 is out of vocabulary", vllm-omni issue #6837), so every clone request failed with HTTP 400. The fix sends the
# <|tts|> id in their place and records the positions for the talker's embedding substitution
# (pr7065-package.diff = the three package files of the PR; the originals are in backup-vllm-omni-0.28.0/).
# Uses GNU patch, not `git apply`: inside this checkout git apply resolves the paths against the repository root, not
# the venv, and reports success without touching site-packages. Idempotent.
#   higgs/engine/patches/apply_pr7065.sh [<venv>]      default server/venvs/engine
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
venv=$(realpath "${1:-$here/../../../server/venvs/engine}")
site=$("$venv/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
cd "$site"
if patch -p1 -R --dry-run --silent < "$here/pr7065-package.diff" >/dev/null 2>&1; then
    echo "apply_pr7065: already applied in $site"; exit 0
fi
patch -p1 --forward < "$here/pr7065-package.diff"
"$venv/bin/python" -m py_compile vllm_omni/entrypoints/openai/serving_speech.py \
    vllm_omni/model_executor/models/higgs_audio_v3/higgs_audio_v3_talker.py \
    vllm_omni/model_executor/models/higgs_audio_v3/higgs_audio_v3_tokenizer.py
grep -q "prepare_prompt_for_engine" vllm_omni/entrypoints/openai/serving_speech.py || { echo "apply_pr7065: patch did not land" >&2; exit 1; }
echo "apply_pr7065: applied to $site"
