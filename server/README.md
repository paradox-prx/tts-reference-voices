# qwen3-tts-server

Production voice-clone text-to-speech for **Qwen/Qwen3-TTS-12Hz-1.7B-Base** on one NVIDIA RTX 3090, behind an
OpenAI-compatible `POST /v1/audio/speech`. It clones the repo's voices (`trump`, English; `shehbaz`, Urdu), streams
audio, queues and limits load, retries bad takes, labels every output as AI-generated, and exposes health, readiness,
Prometheus metrics and structured JSON logs. The model runs in a separate engine behind a pluggable backend, so another
engine (e.g. Higgs Audio v3) can be added later.

**Benchmark results and the recommended production configuration are in [REPORT.md](REPORT.md).** Every experiment and
its numbers are logged in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md); the architecture is in [docs/DESIGN.md](docs/DESIGN.md).

> Everything this service produces is AI-generated speech imitating real people. Never publish it or present it as a
> real recording. Every file carries an AI-generated label (WAV LIST/INFO comment, FLAC/Opus Vorbis comment, MP3 ID3
> comment) and every response the header `X-AI-Generated: true`.

## How it fits together

```
client ──HTTP──▶ gateway :8090  (server/gateway, FastAPI)            auth, admission queue (429/503), voices,
                   │                                                  pace guardrail + retries, length cap, labels,
                   │                                                  JSON logs (Asia/Karachi), /metrics
                   ├──▶ engine 127.0.0.1:8091  (vLLM-Omni 0.28, GPU)   stage 0 talker + code predictor (bf16, CUDA graphs,
                   │                                                  continuous batching), stage 1 Code2Wav (24 kHz)
                   └──▶ QC sidecar 127.0.0.1:8092 (optional, GPU)      Whisper large-v3 ASR + WavLM speaker similarity +
                                                                      loop/skip/silence detectors per take
```

| part | where | venv |
|---|---|---|
| gateway | `gateway/tts_gateway` (`python -m tts_gateway`) | `venvs/gateway` |
| engine | `engine/run_engine.sh` → `vllm serve … --omni` | `venvs/engine` (vllm 0.28.0, vllm-omni 0.28.0, torch 2.13.0 cu130) |
| QC sidecar | `qc/tts_qc` (`eval/run.sh -m tts_qc`) | `venvs/eval` |
| units | `deploy/` (systemd user units, env file, watchdog) | – |
| benchmark | `../bench/bench_tts.py`, `bench/run_plan.py`, `bench/collect.py` | `venvs/gateway` |
| offline quality | `eval/score_run.py`, `eval/retry_sim.py` | `venvs/eval` |
| baseline | `baseline/qwen_tts_server.py` (plain qwen-tts, for comparison only) | `venvs/qwentts` |

## Requirements

- Linux x86_64, an NVIDIA GPU with bf16 (Ampere or newer; tested on an RTX 3090 24 GB) and a driver for CUDA 13.0
  (tested: 580.95.05). No system CUDA toolkit is needed.
- Python 3.12 and [uv](https://docs.astral.sh/uv/) (plain `pip` works too, slower).
- Disk: ~9 GB engine venv, ~4.5 GB model, +5 GB eval models and venv if you use the QC sidecar.
- GPU memory: the engine uses ~19 GB with the production YAML (stage 0 at 0.60), ~15.5 GB with stage 0 at 0.45
  (needed when the QC sidecar, ~6 GB, shares the card). Leave ≥1.5 GB for a desktop if the GPU also drives one.

## Setup

All commands run from this `server/` directory unless noted.

```bash
# 1. engine venv: vllm 0.28.0 + vllm-omni 0.28.0, the exact resolved stack, then the per-request
#    repetition_penalty patch and the post-install checks (import with CUDA hidden, cudart link)
PY312=/path/to/python3.12 bash engine/install_engine.sh venvs/engine - 0.28.0 0.28.0   # constraints picked automatically

# 2. model weights (~4.5 GB) into the Hugging Face cache; the engine then runs offline (HF_HUB_OFFLINE=1)
venvs/tools/bin/hf download Qwen/Qwen3-TTS-12Hz-1.7B-Base      # or any huggingface_hub installation

# 3. gateway venv
uv venv -p python3.12 venvs/gateway
uv pip install -p venvs/gateway/bin/python fastapi 'uvicorn[standard]' httpx numpy soundfile pydantic \
    pydantic-settings orjson prometheus-client pyyaml pytest pytest-asyncio   # gateway/pyproject.toml + bench/tests

# 4. precomputed voices (averaged speaker embedding over all of a voice's clips + in-context reference codes);
#    CPU only, ~1 min; written to state/custom_voices/ and loaded by engine/deploy/variants/custom_voices.yaml
CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 venvs/engine/bin/python engine/precompute_voices.py

# 5. optional: QC sidecar models (Whisper large-v3 CT2, WavLM SV models; sha256-verified) and venv
venvs/tools/bin/python eval/fetch_models.py
uv venv -p python3.12 venvs/eval && uv pip install -p venvs/eval/bin/python -r eval/requirements-eval.txt
```

`engine/install_engine.sh --help` documents offline installs from wheel directories. On this box FlashInfer's JIT
sampler cannot compile (pip resolves nvcc 13.4 against CUDA 13.0 headers), so `run_engine.sh` sets
`VLLM_USE_FLASHINFER_SAMPLER=0` (vLLM's PyTorch sampler; the codec vocabulary is only 3,072 entries). For a rebuild,
pinning `nvidia-cuda-nvcc`, `nvidia-cuda-crt` and `nvidia-nvvm` to 13.0.88 fixes the mismatch.

## Run (foreground, for testing)

```bash
# engine on GPU 0, port 8091 (first start ~95 s: torch.compile + CUDA graph capture)
TTS_ENGINE_API_KEY=engine-secret bash engine/run_engine.sh engine/deploy/variants/custom_voices.yaml 8091 venvs/engine

# gateway on :8090, registering the repo voices with the engine and warming them up; /ready turns 200 when done
cd gateway && TTS_API_KEY=client-secret TTS_ENGINE_API_KEY=engine-secret ../venvs/gateway/bin/python -m tts_gateway

# optional QC sidecar (then set TTS_QC_URL=http://127.0.0.1:8092 on the gateway)
cd qc && ../eval/run.sh -m tts_qc
```

## Run as a service (systemd user units)

```bash
deploy/install_units.sh              # renders the units with this checkout's paths, creates ~/.config/qwen3-tts/env
                                     # (mode 600, fresh random keys) from deploy/env.example; starts nothing
$EDITOR ~/.config/qwen3-tts/env      # e.g. TTS_ENGINE_DEPLOY, TTS_VOICE_MODE, TTS_QC_URL (see REPORT.md)
deploy/install_units.sh --enable     # enable + start engine, its /health watchdog and the gateway
deploy/install_units.sh --enable --with-qc   # ... and the QC sidecar
loginctl enable-linger "$USER"       # optional: keep the units running without a login session and start at boot
```

| unit | what |
|---|---|
| `qwen3-tts-engine.service` | the engine; active once `engine/wait_ready.py` got audio back; `Restart=on-failure` |
| `qwen3-tts-engine-watchdog.service` | restarts the engine when `/health` fails 4 times in a row (a dead stage leaves the API up but answering 503) |
| `qwen3-tts-gateway.service` | the gateway (`After=`/`Wants=` the engine) |
| `qwen3-tts-qc.service` | optional QC sidecar; nothing depends on it |

Operate with `systemctl --user status|restart|stop qwen3-tts-gateway` (from a non-login shell first
`export XDG_RUNTIME_DIR=/run/user/$(id -u)`) and read logs with `journalctl --user -u qwen3-tts-gateway -f`.

## API

All `/v1` routes need `Authorization: Bearer $TTS_API_KEY` (several keys may be comma-separated for rotation).

### `POST /v1/audio/speech`

```bash
curl -s http://HOST:8090/v1/audio/speech -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"Qwen/Qwen3-TTS-12Hz-1.7B-Base","voice":"shehbaz","input":"السلام علیکم، آج موسم بہت اچھا ہے۔","response_format":"wav"}' \
  -o out.wav

# streaming: raw audio as it is generated (first audio in ~0.1 s at low load)
curl -sN http://HOST:8090/v1/audio/speech -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"voice":"trump","input":"Streaming speech, chunk by chunk.","stream":true,"response_format":"pcm"}' > out.pcm
```

```python
from openai import OpenAI          # the official SDK works unchanged
client = OpenAI(base_url="http://HOST:8090/v1", api_key=KEY)
audio = client.audio.speech.create(model="Qwen/Qwen3-TTS-12Hz-1.7B-Base", voice="trump",
                                   input="Hello from the gateway.", response_format="mp3")
audio.write_to_file("hello.mp3")
```

| field | default | notes |
|---|---|---|
| `input` | required | up to `TTS_MAX_INPUT_CHARS` (3000) |
| `voice` | required | a repo voice id: `trump`, `shehbaz` (`GET /v1/voices`) |
| `response_format` | `wav` | `wav`, `pcm` (s16le mono 24 kHz), `flac`, `mp3`, `opus`; streaming: `wav` or `pcm` |
| `stream` | `false` | raw audio chunks; `stream_format` may only be `audio` |
| `model` | – | accepted and ignored (one model per server) |
| `language` | the voice's | `English` for trump, `Auto` for shehbaz (Urdu is not a Qwen language id; `Auto` works) |
| `speed` | – | 0.25-4, non-streaming only (post-hoc time stretch) |
| `temperature`, `top_k`, `top_p` | 0.9, 50, – | sampling of the talker's first codebook |
| `repetition_penalty` | 1.05 | per request (needs the engine patch, applied by install_engine.sh) |
| `max_new_tokens` | pace-based cap | codec frames (12.5 per second of audio) |
| `seed` | – | accepted, but vLLM-Omni 0.28 does not reproduce seeds (docs/EXPERIMENTS.md E04) and seeds slow batches down |
| `retries` | `TTS_RETRY_MAX` | per-request override, clamped to the server's maximum |
| `ref_audio` + `ref_text` | – | inline cloning, only with `TTS_ALLOW_INLINE_REF=1`; base64 or `data:audio/...;base64,` (URLs are refused) |

Unknown fields are rejected with 400 (the engine itself silently ignores them, so a typo would otherwise fall back to a
default without notice).

Response headers: `X-Request-Id`, `X-AI-Generated: true`, `X-TTS-Voice`, `X-TTS-Audio-Seconds`, `X-TTS-Retries`,
`X-TTS-Suspect` (0/1), `X-TTS-Suspect-Reason` (`too_short`, `too_long`, `qc`), `X-TTS-Pace-Ratio`, `X-TTS-QC`
(`pass`/`fail`/`error`/`off`), `X-TTS-QC-Reasons`, `X-TTS-Queue-Ms`, `X-TTS-Engine-Ms`, `X-TTS-Sample-Rate`.

Errors use OpenAI's shape `{"error": {"message", "type", "code"}}`: 400 invalid request, 401 bad key, 404 unknown
voice, 413 input too long, 429 queue full (`Retry-After`), 503 not ready / queue timeout / engine down, 504 engine
timeout, 502 engine error after retries.

### Other routes

| route | auth | |
|---|---|---|
| `GET /health` | no | liveness: 200 while the process is up |
| `GET /ready` | no | 200 once the engine is healthy and every voice is registered and warmed up; 503 otherwise (also reports the QC sidecar) |
| `GET /v1/voices` (alias `/v1/audio/voices`) | yes | the voices, their language and reference length |
| `GET /v1/models` | yes | the served model |
| `GET /metrics` | no | Prometheus: requests by status and voice, latency, queue wait, in-flight, queue depth, retries by reason, suspects, QC verdicts, audio seconds, engine errors |

### Quality guardrails

For every non-streaming take the gateway checks the pace (seconds per letter against the voice's expected pace in
`calibration/pace.json`, band 0.6-1.8x: skipped text, cut-off takes, loops and padding) and, when `TTS_QC_URL` is set,
asks the QC sidecar (Whisper large-v3 CER/WER, speaker similarity, loop/gap/silence detectors). A failing take is
regenerated up to `TTS_RETRY_MAX` times and the best take is returned; the verdict is in the response headers. A
length cap (`max_new_tokens` from the expected pace) stops runaway generations early. Streaming responses cannot be
retried; they are still capped and their pace is logged. Measured effect: REPORT.md.

## Configuration

Everything is environment variables; the full list with defaults and explanations is `deploy/env.example` (gateway
`TTS_*`, engine `TTS_ENGINE_*`, watchdog) and `qc/README.md` (`TTS_QC_*`). The most important ones:

| variable | default | |
|---|---|---|
| `TTS_API_KEY` | required | client bearer key(s) |
| `TTS_ENGINE_DEPLOY` | `engine/deploy/qwen3_tts_prod.yaml` | engine deploy YAML; `engine/deploy/variants/custom_voices.yaml` adds the precomputed voices |
| `TTS_ENGINE_GPU` | `0` | physical GPU |
| `TTS_VOICE_MODE` | `registered` | `registered` (upload the reference clip once), `precomputed` (engine custom voices, e.g. `{id}-avg`), `inline` |
| `TTS_MAX_INFLIGHT` / `TTS_MAX_QUEUE` / `TTS_QUEUE_TIMEOUT_S` | 32 / 128 / 60 | admission control |
| `TTS_RETRY_MAX` / `TTS_RETRY_ON` | 1 / `suspect,engine_error,qc` | retry policy |
| `TTS_QC_URL` | unset | QC sidecar |
| `TTS_HOST` / `TTS_PORT` | `0.0.0.0` / `8090` | bind |

Voices are folders under `voices/<id>/` in the repo (`voice.json` with the language,
`references/references.json` naming the reference clip, its transcript and sha256). A new voice needs such a folder,
an entry in `calibration/pace.json` (optional; its reference clip's pace is used otherwise) and, for the averaged
embedding, a re-run of `engine/precompute_voices.py`.

## Benchmark and evaluation

```bash
venvs/gateway/bin/python bench/run_plan.py --list                 # every phase, estimated audio and GPU time
venvs/gateway/bin/python bench/run_plan.py --only P2_matrix       # run phases (the runner starts/stops the engine)
eval/run.sh eval/score_run.py results/P5_urdu_rp105 --device cuda  # WER/CER/SIM/detectors per take (after load tests)
eval/run.sh eval/retry_sim.py results/P5_urdu_rp1*                # retry policy simulation
venvs/gateway/bin/python bench/collect.py                         # results/INDEX.md, ALL_summary.*, REPORT_tables.md
```

Ad-hoc load tests: `venvs/gateway/bin/python ../bench/bench_tts.py --help` (see `../bench/README.md`). Every run writes
its AI-labelled audio and its numbers into its own folder under `results/<phase>/<run>/` (gitignored; never publish).

## Troubleshooting

| symptom | cause / fix |
|---|---|
| engine start fails with `CUDA compiler and CUDA toolkit headers are incompatible` | FlashInfer JIT sampler; set `VLLM_USE_FLASHINFER_SAMPLER=0` (run_engine.sh default) |
| engine start fails with `CUDA out of memory` in stage 1 | other processes hold VRAM; check `nvidia-smi`, lower `gpu_memory_utilization` of stage 0 in the deploy YAML |
| `/ready` stays 503 | the reason is in the body; usually the engine is still starting (~95 s) or a voice failed to register (`journalctl --user -u qwen3-tts-gateway`) |
| `/health` of the engine answers 503 | a stage died; the watchdog restarts the engine after 4 failed checks |
| 429 / 503 `queue_timeout` | load above capacity; see REPORT.md for the sustainable concurrency, raise `TTS_MAX_QUEUE` only if clients can wait |
| Urdu takes that skip words or loop | inherent to the model (Urdu is not an official Qwen3-TTS language); keep the length cap, retries and (ideally) the QC sidecar on |
| `index_copy_(): ... Half/Float and BFloat16` | fp16/fp32 talker variants are not supported by vLLM-Omni 0.28; use bf16 |
| requests hang after `voice` + `ref_audio` in the same engine request | vLLM-Omni bug #6970; the gateway never sends both |
