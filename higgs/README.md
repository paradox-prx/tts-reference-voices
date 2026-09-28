# Higgs TTS 3 (bosonai/higgs-tts-3-4b) on one RTX 3090: setup and benchmark

The second engine of this repo, benchmarked with the same voices, texts, reference clips and tool as the Qwen3-TTS
server under `server/`, so the two compare row for row. **Higgs TTS 3 is licensed for research and non-commercial use
only** (`higgs/docs/research.md`, "The licence"): benchmarking it in-house is allowed, serving it to users is not
without a commercial licence from Boson AI. Nothing here is deployed as a service.

Layout:

| path | what |
|---|---|
| `engine/run_higgs.sh` | starts the engine (vLLM-Omni 0.28.0 from `server/venvs/engine`, port 8095, GPU 0) with a deploy YAML |
| `engine/deploy/*.yaml` | deploy profiles derived from upstream's (`base`, `low_latency`, `flash_attn`, `seqs64`); each header lists its differences |
| `bench/baseline.sh` | the Urdu/English baseline: sizes x concurrency, non-streaming and streaming, engine direct |
| `results/<experiment>/<run>/` | every take (`audio/*.wav`, AI-labelled), `requests.jsonl`, `summary.json`; audio is gitignored, numbers are not |
| `docs/research.md` | what was checked before the first run (model, licence, serving path, limits) with sources |
| `docs/EXPERIMENTS.md` | the log of every experiment with its numbers |
| `REPORT.md` | results and the Qwen3-TTS vs Higgs TTS 3 comparison (written after the runs) |

## Run

The model and its codec must be in the Hugging Face cache (the engine runs offline):

```bash
hf download bosonai/higgs-tts-3-4b                                  # 9.3 GB
hf download k2-fsa/OmniVoice --include "audio_tokenizer/*"          # 0.8 GB, the reference-audio codec
```

One 3090 cannot hold both engines: stop the Qwen3-TTS units first (`XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl
--user stop qwen3-tts-engine-watchdog qwen3-tts-gateway qwen3-tts-qc qwen3-tts-engine`), then

```bash
higgs/engine/run_higgs.sh higgs/engine/deploy/base.yaml 8095        # logs to stdout; first start compiles kernels
curl -s localhost:8095/health
```

A voice-clone request (the reference clip must be 1-30 s; `voices/<id>/references/qwen3-tts.wav` and its transcript
from `references.json`):

```bash
python - <<'EOF'
import base64, json, urllib.request
ref = json.load(open("voices/shehbaz/references/references.json"))["qwen3-tts"]
wav = base64.b64encode(open("voices/shehbaz/references/" + ref["file"], "rb").read()).decode()
body = {"input": "پاکستان کی معیشت میں بہتری کے آثار نمایاں ہیں۔", "ref_audio": "data:audio/wav;base64," + wav,
        "ref_text": ref["text"], "response_format": "wav"}
req = urllib.request.Request("http://127.0.0.1:8095/v1/audio/speech", json.dumps(body).encode(),
                             {"Content-Type": "application/json"})
open("out.wav", "wb").write(urllib.request.urlopen(req).read())
EOF
```

Streaming: add `"stream": true, "stream_format": "audio"` (raw WAV/PCM chunks, first after one 40 ms frame). Sampling
per request: `"extra_params": {"temperature": 0.8, "top_k": 50}`; length cap: `"max_new_tokens": <frames at 25 fps>`.
Inline control tags go in the text (`<|emotion:elation|>`, `<|prosody:pause|>`, ... see the model's PROMPTING.md).

## Benchmark

```bash
higgs/bench/baseline.sh                       # -> higgs/results/B0_baseline_<timestamp>/
```

It calls `bench/bench_tts.py` with `--task-type none --language none --ref-key qwen3-tts --codec-hz 25`. Scoring
(Whisper large-v3 WER/CER, speaker similarity) uses `server/eval/score_run.py` on the result folders, exactly as for
the Qwen runs.
