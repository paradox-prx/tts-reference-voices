#!/usr/bin/env bash
# Start the repo's gateway (server/gateway, OpenAI-compatible /v1/audio/speech with admission control, sentence
# splitting, pace guardrail and retries) in front of the Higgs TTS 3 engine on :8095, for the gateway experiments.
# Benchmark settings: no auth, no QC sidecar, voices registered with the engine once (POST /v1/audio/voices), the
# Higgs pace calibration, Higgs request shape (no task_type / language, 25 fps caps).
#
#   higgs/engine/run_gateway.sh [port]        default 8090 (the Qwen gateway unit must be stopped)
# Override anything with TTS_* in the environment, e.g. TTS_SPLIT_WORDS=0 TTS_RETRY_MAX=1.
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../.." && pwd)
export TTS_BACKEND=vllm_omni
export TTS_MODEL=${TTS_MODEL:-bosonai/higgs-tts-3-4b}
export TTS_ENGINE_URL=${TTS_ENGINE_URL:-http://127.0.0.1:8095}
export TTS_ENGINE_TASK_TYPE=${TTS_ENGINE_TASK_TYPE:-none}
export TTS_ENGINE_LANGUAGE=${TTS_ENGINE_LANGUAGE:-0}
export TTS_CODEC_HZ=${TTS_CODEC_HZ:-25}
export TTS_REFERENCE_KEY=${TTS_REFERENCE_KEY:-qwen3-tts}
export TTS_PACE_FILE=${TTS_PACE_FILE:-$repo/higgs/calibration/pace.json}
export TTS_VOICE_MODE=${TTS_VOICE_MODE:-registered}
export TTS_AUTH_DISABLED=${TTS_AUTH_DISABLED:-1}
export TTS_SPLIT_WORDS=${TTS_SPLIT_WORDS:-60}
export TTS_RETRY_MAX=${TTS_RETRY_MAX:-0}
export TTS_RETRY_ON=${TTS_RETRY_ON:-suspect,engine_error}
export TTS_LENGTH_CAP=${TTS_LENGTH_CAP:-1}
export TTS_MAX_INFLIGHT=${TTS_MAX_INFLIGHT:-32}
export TTS_NON_STREAMING_MODE_LANGS=${TTS_NON_STREAMING_MODE_LANGS:-}
export TTS_DEFAULT_TEMPERATURE=${TTS_DEFAULT_TEMPERATURE:-0.8}
export TTS_DEFAULT_TOP_K=${TTS_DEFAULT_TOP_K:-50}
export TTS_PORT=${1:-${TTS_PORT:-8090}}
export TTS_HOST=${TTS_HOST:-127.0.0.1}
export SPEAKER_SAMPLES_DIR=${SPEAKER_SAMPLES_DIR:-$repo/higgs/state/speakers}
cd "$repo/server/gateway"
echo "run_gateway: :$TTS_PORT -> $TTS_ENGINE_URL, split $TTS_SPLIT_WORDS words, retries $TTS_RETRY_MAX on $TTS_RETRY_ON, voices $TTS_VOICE_MODE" >&2
exec "$repo/server/venvs/gateway/bin/python" -m tts_gateway
