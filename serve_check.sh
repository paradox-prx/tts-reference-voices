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
    bash engine/run_engine.sh engine/deploy/qwen3_tts_prod.yaml "$PORT" venvs/engine > "$OUT/engine.log" 2>&1 ) &
ENGINE_PID=$!
trap 'echo stopping; kill $ENGINE_PID 2>/dev/null; sleep 3; pkill -P $ENGINE_PID 2>/dev/null || true' EXIT
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
