#!/usr/bin/env bash
# Does unmodified vLLM-Omni accept the GGUF? Starts higgs-studio/engine/run_engine.sh (unchanged) on the GGUF weights
# dir WITHOUT the harness, in two ways, and records how each ends:
#   stock_auto  production deploy YAML (load_format auto): what `engine.sh` does if you just point it at the GGUF
#   stock_gguf  deploy/stock_load_format_gguf.yaml: vLLM's own `load_format: gguf` per stage
# Each attempt runs until the engine is healthy (unexpected) or exits / times out (TIMEOUT, default 600 s).
# Needs the GPU free (stop higgs-engine first). Logs: results/<RUN_DIR>/<case>.log, verdicts in summary.txt.
#
#   scripts/test_stock_vllm_omni.sh [weights dir]   (default weights/higgs-tts-3-4b-Q8_0)
set -uo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
STUDIO_DIR=${STUDIO_DIR:-$HERE/../higgs-studio}
weights=$(realpath "${1:-$HERE/weights/higgs-tts-3-4b-Q8_0}")
out=$HERE/results/${RUN_DIR:-03_stock_vllm_omni}
port=${GGUF_ENGINE_PORT:-8096}
timeout=${TIMEOUT:-600}
mkdir -p "$out"
: >"$out/summary.txt"

attempt() {  # name deploy-yaml
    local name=$1 yaml=$2 log=$out/$1.log pid verdict t0=$SECONDS
    echo "== $name: $weights with $(basename "$yaml")" | tee -a "$out/summary.txt"
    (unset HIGGS_GGUF_HARNESS PYTHONPATH
     HIGGS_MODEL=$weights HIGGS_ENGINE_DEPLOY=$yaml HIGGS_ENGINE_PORT=$port \
         setsid "$STUDIO_DIR/engine/run_engine.sh") >"$log" 2>&1 &
    pid=$!
    verdict="TIMEOUT after ${timeout}s"
    while (( SECONDS - t0 < timeout )); do
        if curl -sf -o /dev/null --max-time 2 "http://127.0.0.1:$port/health"; then verdict="ACCEPTED (engine healthy)"; break; fi
        kill -0 $pid 2>/dev/null || { wait $pid; verdict="REJECTED (exit $?)"; break; }
        sleep 3
    done
    kill -TERM -- -$pid 2>/dev/null; sleep 5; kill -KILL -- -$pid 2>/dev/null; wait $pid 2>/dev/null
    pkill -f -- "--port $port" 2>/dev/null; sleep 3
    echo "   $verdict after $((SECONDS - t0))s" | tee -a "$out/summary.txt"
    grep -E "Error|error:|Exception|RuntimeError|ValueError|FileNotFound|not supported" "$log" | grep -v "^\s*$" |
        sort -u | head -8 | sed 's/^/   | /' | tee -a "$out/summary.txt"
}

attempt stock_auto "$STUDIO_DIR/engine/deploy/higgs_3090_32.yaml"
attempt stock_gguf "$HERE/deploy/stock_load_format_gguf.yaml"
