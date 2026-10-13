#!/usr/bin/env bash
# End-to-end load test of one GGUF through the harness: start the engine (scripts/run_gguf_engine.sh), wait until
# healthy, record the loader lines + VRAM, run scripts/smoke_tts.py twice (run_a, run_b), stop the engine.
#
#   scripts/run_load_test.sh <weights dir> <results subdir>
#   e.g. scripts/run_load_test.sh weights/higgs-tts-3-4b-Q8_0 04_harness/q8_0
# Needs the GPU free (stop higgs-engine first). TIMEOUT (900 s) bounds the start-up.
set -uo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
weights=$(realpath "$1")
out=$HERE/results/$2
port=${GGUF_ENGINE_PORT:-8096}
timeout=${TIMEOUT:-900}
PY=${PY:-$(realpath "$HERE/../tts-reference-voices/server/venvs/engine/bin/python")}
mkdir -p "$out"
log=$out/engine.log

t0=$SECONDS
GGUF_ENGINE_PORT=$port setsid "$HERE/scripts/run_gguf_engine.sh" "$weights" >"$log" 2>&1 &
pid=$!
stop() { kill -TERM -- -$pid 2>/dev/null; sleep 8; kill -KILL -- -$pid 2>/dev/null; wait $pid 2>/dev/null; }
trap stop EXIT
status=fail
while (( SECONDS - t0 < timeout )); do
    curl -sf -o /dev/null --max-time 2 "http://127.0.0.1:$port/health" && { status=healthy; break; }
    kill -0 $pid 2>/dev/null || break
    sleep 3
done
startup=$((SECONDS - t0))
{
    echo "weights: $weights ($(du -shL "$weights"/*.gguf | cut -f1))"
    echo "engine: $status after ${startup}s"
    grep -E "higgs_gguf|Registered model loader|HiggsAudioV3Talker: loaded|HiggsAudioV3Code2Wav|Loading weights took|Model loading took" "$log" | sed 's/^/  /'
    nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader | sed 's/^/  gpu: /'
} | tee "$out/load.txt"
[[ $status == healthy ]] || { echo "engine did not come up; last log lines:"; tail -30 "$log"; exit 1; }

rc=0
for r in a b; do
    "$PY" -I "$HERE/scripts/smoke_tts.py" --url "http://127.0.0.1:$port" --out "$out/run_$r" \
        --label "GGUF via higgs_gguf harness: $weights" || rc=1
done
exit $rc
