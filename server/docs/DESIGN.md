# qwen3-tts-server: design

Production voice-clone TTS for **Qwen/Qwen3-TTS-12Hz-1.7B-Base** on one RTX 3090, behind an OpenAI-compatible
`POST /v1/audio/speech`. A thin gateway owns everything production needs (auth, admission control, voices, retries,
quality guardrails, logs, metrics, AI-generated labelling). The model runs in a separate engine process behind a
swappable backend interface, so Higgs Audio v3 (SGLang-Omni) or another engine can be added later.

```
client ──HTTP──▶ gateway (FastAPI, :8090, auth, queue, retries, labels)
                   │  backend = vllm_omni | stub | (qwen_native | higgs_sglang later)
                   ▼
                 engine (vLLM-Omni `vllm serve ... --omni`, 127.0.0.1:8091, CUDA_VISIBLE_DEVICES=1)
                   stage 0: talker (codebook 0, continuous batching) + code predictor (codebooks 1-15)
                   stage 1: code2wav (12 Hz speech-tokenizer decoder, 24 kHz PCM)
```

## Layout

```
/home/vector/qwen3-tts-server/
  gateway/tts_gateway/        the gateway package (python -m tts_gateway)
    config.py                 Settings from env (prefix TTS_), see below
    voices.py                 VoiceRegistry over VOICES_DIR/<id>/ (voice-server/v1 layout)
    textproc.py               word count, sentence split (en + ur), length cap, duration band
    audio.py                  WAV/PCM helpers, LIST/INFO "AI-generated" label, duration
    admission.py              bounded in-flight + bounded queue with timeout -> 429 / 503
    quality.py                suspect detection + retry policy + best-take selection
    logs.py                   JSON logs, request ids
    metrics.py                Prometheus metrics
    backends/base.py          TTSBackend interface + SynthesisRequest/SynthesisResult dataclasses
    backends/vllm_omni.py     HTTP backend for vLLM-Omni /v1/audio/speech + /v1/audio/voices
    backends/stub.py          deterministic fake engine for tests and gateway-overhead runs
    backends/higgs_sglang.py  placeholder: documents what a Higgs Audio v3 backend must do
    app.py                    FastAPI app and routes
    __main__.py               uvicorn entry point
  gateway/tests/              pytest (stub backend; no GPU)
  engine/
    deploy/                   vLLM-Omni deploy YAMLs (production + benchmark variants)
    patches/                  small, verified patches to vLLM-Omni (e.g. per-request repetition_penalty)
    run_engine.sh             starts the engine with a clean CUDA environment
  deploy/systemd/             qwen3-tts-engine.service, qwen3-tts-gateway.service, env.example
  bench/                      run plan, quality evaluation, retry simulation, report builder
  results/                    benchmark outputs (AI-generated audio: never publish)
  docs/                       this file, auralis_baseline.md, research notes
  ops/                        operational notes (e.g. STOPPED_WHISPER_SERVERS.md)
  venvs/                      gateway, engine (vllm-omni 0.28), engine30 (0.30.0rc1), eval, tools
```

The load generator is `/home/vector/tts-reference-voices/bench/bench_tts.py` (already extended: per-GPU memory,
TTFA past the WAV header, `--api-key`, `--takes/--seed`, `--tag`, response-header capture, labelled audio).

## Engine facts that shape the gateway (vLLM-Omni 0.28.0 source, verified)

- Request fields: `input, voice, task_type (Base), ref_audio (data:/http/file://), ref_text, language (English|Auto|...;
  "Urdu" is a 400), response_format (wav|pcm|flac|mp3|opus), stream, stream_format (sse|audio), max_new_tokens,
  seed, speed, x_vector_only_mode, speaker_embedding, extra_params`. Unknown top-level fields are **silently ignored**.
- Per-request sampling: only `extra_params.{temperature, top_p, top_k}` reach the talker (codebook 0).
  `repetition_penalty` is server-side only (deploy YAML `default_sampling_params`) unless patched. Sub-talker
  sampling is server-side only.
- `seed` in 0.28 makes the code predictor run row by row when the batch is > 1 (under full CUDA graphs): **never send
  seeds on the throughput path**.
- Built-in retry: non-streaming, no `seed`, no `max_new_tokens` -> one retry on codec-limit (no EOS). Sending
  `max_new_tokens` disables it and a runaway becomes HTTP 500. Skipped words / cut-short takes end with a normal EOS
  and are never retried by the engine.
- Voices: `POST /v1/audio/voices` (multipart `audio_sample`, `name`, `consent`, `ref_text`), `GET /v1/audio/voices`,
  `DELETE /v1/audio/voices/{name}`; persisted under `SPEAKER_SAMPLES_DIR`; features cached in memory.
- Streaming raw WAV: 44-byte header with 0xFFFFFFFF sizes, then PCM16 chunks (first after 1 codec frame, then every
  25 frames = 2 s). Non-streaming responses carry `X-VLLM-OMNI-OUTPUT-TOKENS` (codec frames, 12.5/s).
- No admission control: requests beyond `max_num_seqs` queue without limit. `/health` and `/metrics` exist; `--api-key`
  guards `/v1`.

## Gateway API

`POST /v1/audio/speech` (JSON). OpenAI fields: `model` (ignored or must match), `input` (required), `voice` (a
registered voice id, required unless inline cloning is enabled and `ref_audio` is given), `response_format`
(`wav` default, `pcm`, `flac`), `speed` (non-streaming only, passed through), `stream` (bool; raw audio chunks).
Extensions: `language` (default from the voice: `English` for en, `Auto` otherwise), `temperature`, `top_k`, `top_p`,
`repetition_penalty` (only if the backend advertises it), `seed`, `max_new_tokens`, `ref_audio` + `ref_text` (inline
cloning, only when `TTS_ALLOW_INLINE_REF=1`), `retries` (0..TTS_RETRY_MAX, per request override).

Response: audio bytes with `Content-Type` per format, and headers `X-Request-Id`, `X-AI-Generated: true`,
`X-TTS-Voice`, `X-TTS-Audio-Seconds`, `X-TTS-Retries`, `X-TTS-Suspect` (0/1, final take), `X-TTS-Queue-Ms`,
`X-TTS-Engine-Ms`. WAV output carries a LIST/INFO `ICMT` comment "AI-generated speech (Qwen3-TTS voice clone)...".
Streaming responses send a WAV header with streaming sizes, then PCM (headers limited to those known up front).

Errors: JSON `{"error": {"message", "type", "code"}}` (OpenAI shape). 400 validation, 401 missing/bad key,
404 unknown voice, 413 input too long, 429 queue full (with `Retry-After`), 503 not ready / queue timeout / engine down,
504 engine timeout, 502 engine error after retries.

Other routes: `GET /health` (liveness, no auth), `GET /ready` (engine healthy + voices registered + warmup done; no
auth), `GET /metrics` (Prometheus; no auth, bind-local recommended), `GET /v1/audio/voices` and `GET /v1/models`
(auth).

## Config (env, prefix `TTS_`)

| var | default | meaning |
|---|---|---|
| `TTS_API_KEY` | (required unless `TTS_AUTH_DISABLED=1`) | Bearer key; compared in constant time. Several keys may be comma-separated |
| `TTS_BACKEND` | `vllm_omni` | `vllm_omni` or `stub` |
| `TTS_ENGINE_URL` | `http://127.0.0.1:8091` | engine base URL |
| `TTS_ENGINE_API_KEY` | – | key the engine expects (`--api-key`), if any |
| `TTS_ENGINE_PER_REQUEST_RP` | `0` | the engine has the `rep_penalty` patch (engine/patches): send `extra_params.repetition_penalty` and accept `repetition_penalty` per request |
| `TTS_VOICES_DIR` | `/home/vector/tts-reference-voices/voices` | voice-server/v1 folders |
| `TTS_VOICE_MODE` | `registered` | `registered` (upload once, send `voice`) or `inline` (send ref_audio every time) |
| `TTS_MAX_INFLIGHT` | 32 | requests sent to the engine at once |
| `TTS_MAX_QUEUE` | 128 | waiting requests beyond in-flight; more -> 429 |
| `TTS_QUEUE_TIMEOUT_S` | 60 | max wait for an in-flight slot -> 503 |
| `TTS_REQUEST_TIMEOUT_S` | 300 | per engine call |
| `TTS_MAX_INPUT_CHARS` | 3000 | -> 413 |
| `TTS_RETRY_MAX` | 1 | extra takes when a take is suspect or the engine fails (non-streaming only) |
| `TTS_RETRY_ON` | `suspect,engine_error` | which failures trigger a retry |
| `TTS_LENGTH_CAP` | `1` | send `max_new_tokens = words/2.5*12.5*2.4 + 60` (bounded 96..4096) |
| `TTS_SPW_EN` / `TTS_SPW_UR` | `0.18,0.9` / `0.18,1.1` | seconds-per-word band; outside = suspect |
| `TTS_DEFAULT_TEMPERATURE` / `TTS_DEFAULT_TOP_K` | 0.9 / 50 | sent as `extra_params` unless the request overrides |
| `TTS_WARMUP` | `1` | one short request per voice before `/ready` turns green |
| `TTS_ALLOW_INLINE_REF` | `0` | accept `ref_audio`/`ref_text` in requests |
| `TTS_LOG_LEVEL` | `INFO` | JSON logs to stdout (journald) |
| `TTS_HOST` / `TTS_PORT` | `0.0.0.0` / `8090` | bind |

## Retry and quality policy (non-streaming)

1. Generate a take (no seed on the first attempt).
2. It is **suspect** if seconds-per-word falls outside the language band (skipped text, cut short, loop, padding), or
   the engine returns a codec-limit/5xx error.
3. While suspect and retries remain: generate again (a new take; the engine samples fresh). Keep the best take
   (non-suspect preferred; among suspects, the one whose seconds-per-word is closest to the language median).
4. Streaming requests cannot be retried after the first byte; they rely on the length cap to bound runaways.

The benchmark measures how often each failure happens, what retries fix, and what they cost, so the defaults above
are provisional until REPORT.md.

## Backend interface (backends/base.py)

```python
@dataclass
class SynthesisRequest:
    text: str; voice: Voice | None; language: str; response_format: str   # "pcm" internally
    temperature: float | None; top_k: int | None; top_p: float | None; repetition_penalty: float | None
    seed: int | None; max_new_tokens: int | None; speed: float | None
    ref_audio: bytes | None; ref_text: str | None; request_id: str

@dataclass
class SynthesisResult:
    pcm: bytes; sample_rate: int; engine_ms: float; codec_frames: int | None; meta: dict

class TTSBackend(Protocol):
    name: str
    capabilities: Capabilities   # streaming, per_request_repetition_penalty, voice_registry, max_seconds_per_call
    async def start(self) -> None; async def close(self) -> None
    async def health(self) -> dict                         # {"ok": bool, ...}
    async def register_voice(self, voice: Voice) -> None  # idempotent
    async def synthesize(self, req: SynthesisRequest) -> SynthesisResult
    def stream(self, req: SynthesisRequest) -> AsyncIterator[bytes]   # PCM16 chunks
```

A backend with `max_seconds_per_call` (Higgs: ~30 s) gets sentence-split text from the gateway and the parts are
joined with short silences; Qwen3-TTS has no such ceiling.

## Deployment

systemd **user** units (linger is on; no docker access): `qwen3-tts-engine.service` runs `engine/run_engine.sh`
(`CUDA_VISIBLE_DEVICES=1`, clean `PATH`/`CUDA_HOME` so FlashInfer JIT uses the pip CUDA 13 toolchain), and
`qwen3-tts-gateway.service` (`After=`/`Wants=` the engine; waits for `/ready`). Secrets live in
`~/.config/qwen3-tts/env` (mode 600). Use `XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user ...`.
