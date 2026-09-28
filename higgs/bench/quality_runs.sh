#!/usr/bin/env bash
# Quality runs on the 43 benchmark prompts per voice (K takes each, c=8, engine direct), the arms that decide the
# Higgs configuration: Boson's sampling vs upstream's, the Qwen reference clip vs the 25 s Higgs-style clip, and
# the expressive set plain vs with Higgs control tags. Every take is kept; score with server/eval/score_run.py.
#
#   higgs/bench/quality_runs.sh [<results-dir>] [takes]      default higgs/results/Q_prompts_<timestamp>, 2 takes
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../.." && pwd)
out=${1:-$repo/higgs/results/Q_prompts_$(date +%Y-%m-%d_%H%M%S)}
takes=${2:-2}
url=${HIGGS_URL:-http://127.0.0.1:8095}
py=$repo/server/venvs/gateway/bin/python
common=(--url "$url" --task-type none --language none --codec-hz 25 --engine-label "Higgs TTS 3" --gpus "${TTS_BENCH_GPU:-0}"
        --out "$out" --warmup 1 --pace-file "$repo/higgs/calibration/pace.json" --size prompts --takes "$takes" -c 8
        --meta engine=vllm-omni-0.28.0+pr7065 --meta model=bosonai/higgs-tts-3-4b --meta deploy="${HIGGS_DEPLOY:-mem080_seqs32.yaml}")
mkdir -p "$out"
echo "quality runs started $(date --iso-8601=seconds) url=$url takes=$takes" | tee "$out/RUN_INFO.txt"
run() { echo "== bench $*" | tee -a "$out/RUN_INFO.txt"; "$py" "$repo/bench/bench_tts.py" "${common[@]}" "$@"; }
# Q1 reference config: qwen3-tts clip, temperature 0.8 / top_k 50 (the YAML defaults), both voices
run --tag Q1_t08 --voice shehbaz trump --ref-key qwen3-tts
# Q2 upstream sampling (temperature 1.0, top_p 0.95, top_k 50) per request via extra_params, Urdu
run --tag Q2_t10 --voice shehbaz --ref-key qwen3-tts --extra-param temperature=1.0 --extra-param top_p=0.95
# Q3 the 25 s Higgs-style reference (clips 08 + 05, livelier) instead of the Qwen clip, Urdu
run --tag Q3_ref25 --voice shehbaz --ref-key higgs-v3-25s
# Q4 expressive prompt set: plain text, then the same texts with Higgs inline control tags
run --tag Q4_expr_plain --voice shehbaz --ref-key qwen3-tts --prompts-file "$repo/benchmarks/shehbaz_ur_expressive.json"
run --tag Q4_expr_tags --voice shehbaz --ref-key qwen3-tts --prompts-file "$repo/benchmarks/shehbaz_ur_expressive.json" --prompt-field higgs_text
echo "quality runs finished $(date --iso-8601=seconds)" | tee -a "$out/RUN_INFO.txt"
