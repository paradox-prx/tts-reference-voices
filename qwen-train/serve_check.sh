#!/usr/bin/env bash
# Prove a checkpoint is servable: start vLLM-Omni on it (the production engine script of tts-reference-voices),
# send Urdu and English voice-clone requests, print the timings, stop it.
#   bash serve_check.sh runs/smoke/latest [port]
# Needs the tts-reference-voices checkout next to this folder (engine venv + bench_tts.py) and a free GPU.
set -euo pipefail
CKPT=$(realpath "${1:?checkpoint dir}")
PORT=${2:-8093}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=${TTS_REPO:-$HERE/../tts-reference-voices}
SERVER=$REPO/server
OUT=$HERE/runs/serve_check_$(date +%Y%m%d_%H%M%S)
mkdir -p "$OUT"
echo "engine: $CKPT on :$PORT; log $OUT/engine.log"
( cd "$SERVER" && CUDA_VISIBLE_DEVICES=${TTS_ENGINE_GPU:-0} TTS_ENGINE_MODEL="$CKPT" VLLM_USE_FLASHINFER_SAMPLER=0 \
    exec setsid bash engine/run_engine.sh engine/deploy/qwen3_tts_prod.yaml "$PORT" venvs/engine > "$OUT/engine.log" 2>&1 ) &
ENGINE_PID=$!
stop_engine() {  # the engine forks stage workers that hold the GPU: kill its whole process group and wait for the card
  echo stopping
  PG=$(ps -o pgid= -p "$ENGINE_PID" 2>/dev/null | tr -d ' ')
  [ -n "$PG" ] && kill -TERM -- "-$PG" 2>/dev/null
  for i in $(seq 1 30); do
    kill -0 "$ENGINE_PID" 2>/dev/null || { [ -z "$PG" ] || ! pgrep -g "$PG" >/dev/null 2>&1; } && break
    sleep 1
  done
  [ -n "$PG" ] && pgrep -g "$PG" >/dev/null 2>&1 && kill -KILL -- "-$PG" 2>/dev/null
  for i in $(seq 1 20); do
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "${TTS_ENGINE_GPU:-0}" 2>/dev/null | head -1)
    [ -n "$used" ] && [ "$used" -lt 6000 ] && break
    sleep 2
  done
  echo "engine stopped; GPU ${used:-?} MiB used"
}
trap stop_engine EXIT
for i in $(seq 1 240); do
  if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then echo "ready after $((i*5)) s"; break; fi
  if ! kill -0 $ENGINE_PID 2>/dev/null; then echo "engine died, see $OUT/engine.log"; tail -30 "$OUT/engine.log"; exit 1; fi
  sleep 5
done
curl -s "http://127.0.0.1:$PORT/health" && echo
"$SERVER/venvs/gateway/bin/python" "$REPO/bench/bench_tts.py" --url "http://127.0.0.1:$PORT" --voice shehbaz trump \
    --size short -n 3 -c 1 --voice-mode inline --warmup 1 --out "$OUT" --tag servecheck \
    --param non_streaming_mode=true --language Auto 2>&1 | grep -v "^voice\|warmup" | tail -8
echo "audio and numbers in $OUT (AI-generated audio)"
