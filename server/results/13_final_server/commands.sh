#!/usr/bin/env bash
# 13_final_server: the production service as deployed (systemd units, ~/.config/qwen3-tts/env = deploy/env.example
# values: custom_voices engine, Urdu non_streaming_mode, 60-word splitting, retries 1 on suspect/engine_error/qc, QC
# sidecar SIM + audio). Every request goes through the gateway on :8090 exactly as a client would send it.
set -uo pipefail
cd "$(dirname "$0")/../../.."          # repo root
set -a; . ~/.config/qwen3-tts/env; set +a  # TTS_API_KEY (never printed)
PY=server/venvs/tools/bin/python
OUT=server/results/13_final_server
B=(bench/bench_tts.py --url http://127.0.0.1:8090 --voice-mode server --out "$OUT" --gpus 0 --meta phase=13_final_server)
for v in trump shehbaz; do
  "$PY" "${B[@]}" --voice $v --size short -n 16 -c 1 --tag final_c1
  "$PY" "${B[@]}" --voice $v --size short -n 16 -c 1 --stream --tag final_c1 --warmup 0
  "$PY" "${B[@]}" --voice $v --size short -n 64 -c 16 --tag final_c16 --warmup 0
  "$PY" "${B[@]}" --voice $v --size medium -n 64 -c 16 --tag final_c16 --warmup 0
  "$PY" "${B[@]}" --voice $v --size long -n 43 -c 16 --tag final_c16 --warmup 0
  "$PY" "${B[@]}" --voice $v --size prompts -n 43 -c 16 --tag final_c16 --warmup 0
  "$PY" "${B[@]}" --voice $v --size xxlong -n 43 -c 16 --tag final_c16 --warmup 0
  "$PY" "${B[@]}" --voice $v --size medium -n 128 -c 32 --tag final_c32 --warmup 0
done
echo "DONE $(date -Is)"
