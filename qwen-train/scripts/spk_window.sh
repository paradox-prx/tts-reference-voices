#!/usr/bin/env bash
# Pause production, embed speakers on the GPU (WavLM-base-plus-sv), restart production.
#   bash scripts/spk_window.sh [manifest] [out_dir]
set -uo pipefail
cd "$(dirname "$0")/.."
SERVER=../tts-reference-voices/server
P=$SERVER/venvs/qwentts/bin/python
MANIFEST=${1:-data/mix4/manifest.jsonl}
OUT=${2:-data/mix4/spk}
restart() { systemctl --user start qwen3-tts-engine qwen3-tts-engine-watchdog qwen3-tts-qc qwen3-tts-gateway; echo "== prod restarted $(date -Is)"; }
trap restart EXIT
systemctl --user stop qwen3-tts-gateway qwen3-tts-qc qwen3-tts-engine-watchdog qwen3-tts-engine
sleep 8
echo "== prod stopped $(date -Is); GPU $(nvidia-smi --query-gpu=memory.used --format=csv,noheader)"
SPK_MODEL=$SERVER/models/eval/wavlm-base-plus-sv $P -m qwen_train.speakers embed --manifest "$MANIFEST" --out "$OUT" \
    --device cuda --batch 64 --workers 16
echo "== embed exit $? $(date -Is)"
