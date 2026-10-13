#!/usr/bin/env bash
# Validation window on the production box: pause the qwen3-tts units, run every GPU-bound check, restart them.
# Everything is logged to runs/gpu_window_<ts>/ ; each stage writes its own files under data/ and runs/.
set -uo pipefail
cd "$(dirname "$0")/.."
SERVER=../tts-reference-voices/server
P=$SERVER/venvs/qwentts/bin/python
E=$SERVER/eval/run.sh
TS=$(date +%Y%m%d_%H%M%S)
W=runs/gpu_window_$TS
mkdir -p "$W"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
WHISPER=${WHISPER_MODEL:-$SERVER/models/eval/faster-whisper-large-v3}
SIM=${SIM_MODEL:-$SERVER/models/eval/wavlm-base-plus-sv}
restart() { systemctl --user start qwen3-tts-engine qwen3-tts-engine-watchdog qwen3-tts-qc qwen3-tts-gateway; echo "== prod restarted $(date -Is)"; }
trap restart EXIT
systemctl --user stop qwen3-tts-gateway qwen3-tts-qc qwen3-tts-engine-watchdog qwen3-tts-engine
sleep 8
echo "== prod stopped $(date -Is); GPU $(nvidia-smi --query-gpu=memory.used --format=csv,noheader); disk $(df -h / | awk 'NR==2{print $4}') free"

stage() { echo "== $1 start $(date -Is)"; }

stage "alignment (sample, 200 utts, GPU)"
$P -m qwen_train.check_alignment --data data/sample --n 200 --max-tokens 6000 --language-id 2080 --copy-test \
    > "$W/alignment.log" 2>&1; echo "   exit $? $(tail -1 "$W/alignment.log")"

stage "smoke training (f50, 30 steps, full bf16)"
rm -rf runs/smoke
$P -m qwen_train.train --config configs/smoke.yaml --set data_dir=data/f50 > "$W/smoke.log" 2>&1
echo "   exit $?"; grep -E "^step|^eval|saved|trainable|batches|done in|Error|error" "$W/smoke.log" | tail -14

stage "serve check (vLLM-Omni on runs/smoke/latest)"
bash serve_check.sh runs/smoke/latest 8093 > "$W/serve_check.log" 2>&1; echo "   exit $?"; tail -6 "$W/serve_check.log"
cp "$W/serve_check.log" runs/ 2>/dev/null; rm -rf runs/smoke/step_* runs/smoke/latest; echo "   smoke checkpoint deleted (disk)"; sleep 5

stage "baseline synth (pretrained) on f50 eval+holdout + external refs"
$P -m qwen_train.synth_eval --model Qwen/Qwen3-TTS-12Hz-1.7B-Base --data data/f50 --splits eval,holdout --per-speaker 3 \
    --refs configs/eval_refs.json --out runs/baseline_eval > "$W/synth_baseline.log" 2>&1; echo "   exit $? $(tail -1 "$W/synth_baseline.log")"

stage "score baseline"
PYTHONPATH=. $E -m qwen_train.score --synth runs/baseline_eval/synth.jsonl --sim "$SIM" --asr "$WHISPER" \
    --score-gt > "$W/score_baseline.log" 2>&1; echo "   exit $?"; grep -v "^ " "$W/score_baseline.log" | tail -6

stage "whisper transcript QC (sample, 300 utts, GPU fp16)"
rm -f data/sample/qc_asr300.jsonl
PYTHONPATH=. $E -m qwen_train.qc --manifest data/sample/manifest.jsonl --out data/sample/qc_asr300.jsonl --asr "$WHISPER" \
    --device cuda --limit 300 --workers 4 > "$W/qc_asr.log" 2>&1; echo "   exit $?"; tail -9 "$W/qc_asr.log"

echo "== window done $(date -Is); disk $(df -h / | awk 'NR==2{print $4}') free"
