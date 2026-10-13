#!/usr/bin/env bash
# The gateway in front of Higgs TTS 3: does sentence splitting fix the long-text truncation, what do pace retries add,
# and what does the gateway cost. Three gateway arms, each started by this script (higgs/engine/run_gateway.sh) and
# stopped again; the engine on :8095 must be running.
#   G0  no splitting, no retries          (engine direct through the gateway: overhead + the truncation as is)
#   G1  split at 60 words, no retries      (parts generated in parallel on free slots, joined with 0.2 s pauses)
#   G2  split at 60 words, 1 retry on pace-suspect / engine-error takes
# Per arm: shehbaz xlong (~98 words) and xxlong (~200 words) at c=1 and c=8, trump xlong at c=8, plus one
# streaming run (xlong c=8; streams cannot be retried).
#
#   higgs/bench/gateway_runs.sh [<results-dir>]      default higgs/results/G_gateway_<timestamp>
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../.." && pwd)
out=${1:-$repo/higgs/results/G_gateway_$(date +%Y-%m-%d_%H%M%S)}
port=${GATEWAY_PORT:-8090}
py=$repo/server/venvs/gateway/bin/python
common=(--url "http://127.0.0.1:$port" --voice-mode server --task-type none --language none --codec-hz 25
        --engine-label "Higgs TTS 3" --gpus "${TTS_BENCH_GPU:-0}" --out "$out" --warmup 1
        --pace-file "$repo/higgs/calibration/pace.json" --meta engine=vllm-omni-0.28.0+pr7065 --meta via=gateway)
mkdir -p "$out"
gw_pid=""
start_gateway() {  # start_gateway <arm> <split-words> <retries>
    TTS_SPLIT_WORDS=$2 TTS_RETRY_MAX=$3 nohup setsid "$repo/higgs/engine/run_gateway.sh" "$port" \
        > "$repo/higgs/logs/gateway_$1.log" 2>&1 &
    gw_pid=$!
    for _ in $(seq 1 100); do
        curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port/ready" 2>/dev/null | grep -q 200 && return 0
        sleep 3
    done
    echo "gateway $1 not ready" >&2; return 1
}
stop_gateway() {
    [[ -n $gw_pid ]] && kill "$gw_pid" 2>/dev/null || true
    for _ in $(seq 1 30); do ss -ltn | grep -q ":$port " || break; sleep 1; done
    gw_pid=""
}
trap stop_gateway EXIT
run() { echo "== bench $*" | tee -a "$out/RUN_INFO.txt"; "$py" "$repo/bench/bench_tts.py" "${common[@]}" "$@"; }
echo "gateway runs started $(date --iso-8601=seconds)" | tee "$out/RUN_INFO.txt"
for arm in "G0 0 0" "G1 60 0" "G2 60 1"; do
    set -- $arm
    echo "== arm $1: split $2 words, retries $3" | tee -a "$out/RUN_INFO.txt"
    start_gateway "$1" "$2" "$3"
    run --tag "$1" --voice shehbaz --size xlong xxlong --sweep 1,8 --n-rule 8:2 --meta arm="$1" --meta split="$2" --meta retries="$3"
    run --tag "$1" --voice trump --size xlong --sweep 8 --n-rule 8:2 --meta arm="$1" --meta split="$2" --meta retries="$3"
    run --tag "$1" --voice shehbaz --size xlong --sweep 8 --n-rule 8:2 --stream --format wav --meta arm="$1" --meta split="$2" --meta retries="$3"
    stop_gateway
done
echo "gateway runs finished $(date --iso-8601=seconds)" | tee -a "$out/RUN_INFO.txt"
