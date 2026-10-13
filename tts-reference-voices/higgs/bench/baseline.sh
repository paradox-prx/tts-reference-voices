#!/usr/bin/env bash
# Higgs TTS 3 baseline on one RTX 3090: engine direct (vLLM-Omni on :8095), the same reference clips, texts and
# bench tool as the Qwen3-TTS benchmark (bench/bench_tts.py), so the two engines compare row for row.
#
#   higgs/bench/baseline.sh [<results-dir>]      default higgs/results/B0_baseline_<timestamp>
#
# Phases (each bench invocation is one run folder with its audio, requests.jsonl and summary.json):
#   ur_nonstream   shehbaz x short/medium/long/xlong/xxlong x c=1,2,4,8,16, n = max(8, 2c)   latency, x realtime, RTF
#   ur_stream      shehbaz x short/long/xlong x c=1,4,8,16 with --stream                      time to first audio
#   en_check       trump x short/xlong x c=1,8                                                English cross-check
# Sizes: short = 1 sentence (~3 s), medium ~7 s, long ~17 s, xlong = one 43-prompt text (~28 s ur), xxlong = two
# joined (~56 s ur). Requests carry no task_type / language (Higgs clones from ref_audio + ref_text and detects the
# language), no max_new_tokens (the engine's 2048-frame = 82 s cap and its retry apply), no seeds.
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../.." && pwd)
out=${1:-$repo/higgs/results/B0_baseline_$(date +%Y-%m-%d_%H%M%S)}
url=${HIGGS_URL:-http://127.0.0.1:8095}
py=$repo/server/venvs/gateway/bin/python
common=(--url "$url" --task-type none --language none --ref-key "${HIGGS_REF_KEY:-qwen3-tts}" --codec-hz 25
        --engine-label "Higgs TTS 3" --gpus "${TTS_BENCH_GPU:-0}" --out "$out" --warmup 2
        --meta engine=vllm-omni-0.28.0 --meta model=bosonai/higgs-tts-3-4b --meta deploy="${HIGGS_DEPLOY:-base.yaml}")
mkdir -p "$out"
{
    echo "baseline started $(date --iso-8601=seconds) url=$url deploy=${HIGGS_DEPLOY:-base.yaml}"
    nvidia-smi --query-gpu=name,driver_version,memory.used,memory.total --format=csv
    "$py" -c "import importlib.metadata as m; print({n: m.version(n) for n in ('vllm','vllm-omni','torch','transformers')})" \
        2>/dev/null || "$repo/server/venvs/engine/bin/python" -c "import importlib.metadata as m; print({n: m.version(n) for n in ('vllm','vllm-omni','torch','transformers')})"
} | tee "$out/RUN_INFO.txt"

run() { echo "== bench $*" | tee -a "$out/RUN_INFO.txt"; "$py" "$repo/bench/bench_tts.py" "${common[@]}" "$@"; }

run --tag ur_ns --voice shehbaz --size short medium long xlong xxlong --sweep 1,2,4,8,16 --n-rule 8:2
run --tag ur_st --voice shehbaz --size short long xlong --sweep 1,4,8,16 --n-rule 8:2 --stream --format wav
run --tag en_ns --voice trump --size short xlong --sweep 1,8 --n-rule 8:2
run --tag en_st --voice trump --size short xlong --sweep 1,8 --n-rule 8:2 --stream --format wav
echo "baseline finished $(date --iso-8601=seconds)" | tee -a "$out/RUN_INFO.txt"
