#!/usr/bin/env bash
# Pause production, compute WavLM-Large (seed-tts-eval SIM) speaker embeddings on the GPU, run the clustering ANALYSIS
# (report only; nothing is applied to the data), restart production.
#   bash scripts/spk_large_window.sh [manifest] [out_dir]
set -uo pipefail
cd "$(dirname "$0")/.."
SERVER=../tts-reference-voices/server
MANIFEST=${1:-data/mix4/manifest.jsonl}
OUT=${2:-data/mix4/spk}
restart() { systemctl --user start qwen3-tts-engine qwen3-tts-engine-watchdog qwen3-tts-qc qwen3-tts-gateway; echo "== prod restarted $(date -Is)"; }
trap restart EXIT
systemctl --user stop qwen3-tts-gateway qwen3-tts-qc qwen3-tts-engine-watchdog qwen3-tts-engine
sleep 8
echo "== prod stopped $(date -Is); GPU $(nvidia-smi --query-gpu=memory.used --format=csv,noheader)"
PYTHONPATH=.:$SERVER/qc $SERVER/eval/run.sh -m qwen_train.speakers embed --backend large --models-dir "$SERVER/models/eval" \
    --manifest "$MANIFEST" --out "$OUT" --device cuda --workers 12
echo "== large embed exit $? $(date -Is)"
