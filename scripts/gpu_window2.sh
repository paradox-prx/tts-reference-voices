#!/usr/bin/env bash
# Second short window: regenerate the smoke checkpoint with the fixed export and prove vLLM-Omni serves it.
set -uo pipefail
cd "$(dirname "$0")/.."
SERVER=../tts-reference-voices/server
P=$SERVER/venvs/qwentts/bin/python
W=runs/gpu_window2_$(date +%Y%m%d_%H%M%S)
mkdir -p "$W"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
restart() { systemctl --user start qwen3-tts-engine qwen3-tts-engine-watchdog qwen3-tts-qc qwen3-tts-gateway; echo "== prod restarted $(date -Is)"; }
trap restart EXIT
systemctl --user stop qwen3-tts-gateway qwen3-tts-qc qwen3-tts-engine-watchdog qwen3-tts-engine
sleep 8
echo "== prod stopped $(date -Is); GPU $(nvidia-smi --query-gpu=memory.used --format=csv,noheader); disk $(df -h / | awk 'NR==2{print $4}') free"
echo "== smoke training start $(date -Is)"
rm -rf runs/smoke
$P -m qwen_train.train --config configs/smoke.yaml --set data_dir=data/f50 --set max_steps=12 --set eval_every=6 --set save_every=12 > "$W/smoke.log" 2>&1
echo "   exit $?"; grep -E "^step|^eval|saved|done in|Error" "$W/smoke.log" | tail -6
ls runs/smoke/latest/
echo "== serve check start $(date -Is)"
bash serve_check.sh runs/smoke/latest 8093 > "$W/serve_check.log" 2>&1; echo "   exit $?"; grep -E "ready after|engine died|^\| |ok [0-9]|audio and numbers" "$W/serve_check.log" | tail -8
cp -r runs/serve_check_* "$W/" 2>/dev/null; rm -rf runs/serve_check_*
rm -rf runs/smoke/step_* runs/smoke/latest; echo "   smoke checkpoint deleted (disk)"
echo "== score baseline start $(date -Is)"
E=$SERVER/eval/run.sh
PYTHONPATH=. $E -m qwen_train.score --synth runs/baseline_eval/synth.jsonl --sim "$SERVER/models/eval/wavlm-base-plus-sv" \
    --asr "$SERVER/models/eval/faster-whisper-large-v3" --score-gt > "$W/score_baseline.log" 2>&1; echo "   exit $?"; grep -v "^ " "$W/score_baseline.log" | tail -6
echo "== window2 done $(date -Is); disk $(df -h / | awk 'NR==2{print $4}') free"
