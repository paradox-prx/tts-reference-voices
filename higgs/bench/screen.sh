#!/usr/bin/env bash
# Screen one Higgs engine config against the baseline: a reduced matrix (shehbaz short/long/xlong x c=1,4,8,16
# non-streaming, short/xlong x c=1,4,8 streaming, trump xlong c=1,8), engine direct.
#
#   higgs/bench/screen.sh <tag> [<results-dir>] [extra bench_tts.py args...]
#   e.g. higgs/bench/screen.sh S1_low_latency "" --meta deploy=low_latency.yaml
#        higgs/bench/screen.sh S3_temp1 "" --extra-param temperature=1.0 --extra-param top_p=0.95
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../.." && pwd)
tag=${1:?tag}
out=${2:-}; [[ -n $out ]] || out=$repo/higgs/results/${tag}_$(date +%Y-%m-%d_%H%M%S)
shift; [[ $# -gt 0 ]] && shift
url=${HIGGS_URL:-http://127.0.0.1:8095}
py=$repo/server/venvs/gateway/bin/python
common=(--url "$url" --task-type none --language none --ref-key "${HIGGS_REF_KEY:-qwen3-tts}" --codec-hz 25
        --engine-label "Higgs TTS 3" --gpus "${TTS_BENCH_GPU:-0}" --out "$out" --warmup 2
        --meta engine=vllm-omni-0.28.0+pr7065 --meta model=bosonai/higgs-tts-3-4b "$@")
mkdir -p "$out"
{
    echo "screen $tag started $(date --iso-8601=seconds) url=$url extra: $*"
    nvidia-smi --query-gpu=name,driver_version,memory.used,memory.total --format=csv
} | tee "$out/RUN_INFO.txt"
run() { echo "== bench $*" | tee -a "$out/RUN_INFO.txt"; "$py" "$repo/bench/bench_tts.py" "${common[@]}" "$@"; }
run --tag ur_ns --voice shehbaz --size short long xlong --sweep 1,4,8,16 --n-rule 8:2
run --tag ur_st --voice shehbaz --size short xlong --sweep 1,4,8 --n-rule 8:2 --stream --format wav
run --tag en_ns --voice trump --size xlong --sweep 1,8 --n-rule 8:2
echo "screen $tag finished $(date --iso-8601=seconds)" | tee -a "$out/RUN_INFO.txt"
