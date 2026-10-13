#!/usr/bin/env bash
# Start the Higgs gateway, wait until it is healthy, run the burst load test, then shut the gateway down.

set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$here"

py=${PYTHON:-python}
port=${GATEWAY_PORT:-8000}
out=${OUT:-results/burst_$(date +%Y-%m-%d_%H%M%S)}
mkdir -p "$out"

# Set HIGGS_ENGINE_CMD to use your custom engine script
export HIGGS_ENGINE_CMD="${HIGGS_ENGINE_CMD:-$here/engine/run_engine.sh}"

# Reference voice layout
voices_dir=${VOICES_DIR:-/home/vector/Documents/abdullah_workspace/qwen-server/tts-reference-voices/voices}
voice=${VOICE:-shehbaz}
ref_name=${REF_NAME:-higgs-v3-25s}
ref_audio=${REF_AUDIO:-$voices_dir/$voice/references/$ref_name.wav}
ref_json=${REF_JSON:-$(dirname "$ref_audio")/references.json}
ref_key=${REF_KEY:-$(basename "${ref_audio%.wav}")}

[[ -f "$ref_audio" ]] || { echo "missing reference clip: $ref_audio"; exit 1; }
[[ -f "$ref_json" ]] || { echo "missing transcripts json: $ref_json (set REF_JSON)"; exit 1; }

server_args=(--ref-audio "$ref_audio" --ref-json "$ref_json" --ref-key "$ref_key" --port "$port")
[[ -n "${HIGGS_ENGINE_CMD:-}" ]] && server_args+=(--launch-engine)

"$py" higgs_server.py "${server_args[@]}" > "$out/server.log" 2>&1 &
srv=$!
cleanup() { kill "$srv" 2>/dev/null || true; wait "$srv" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "gateway pid $srv, waiting for http://127.0.0.1:$port/health (log: $out/server.log)"
for _ in $(seq 1 600); do
    kill -0 "$srv" 2>/dev/null || { echo "gateway died:"; tail -30 "$out/server.log"; exit 1; }
    curl -sf "http://127.0.0.1:$port/health" >/dev/null && break
    sleep 2
done
curl -sf "http://127.0.0.1:$port/health" >/dev/null || { echo "gateway never became healthy"; exit 1; }
echo "gateway up"

"$py" burst_load.py --url "http://127.0.0.1:$port" --bursts "${BURSTS:-100}" --out "$out" "$@" || load_rc=$?
[[ -f "$out/requests.jsonl" ]] && "$py" make_report.py "$out"
echo
echo "done -> $out"
ls -1 "$out"
exit "${load_rc:-0}"