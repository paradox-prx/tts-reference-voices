# qwen3-tts-server: design

Production voice-clone TTS for **Qwen/Qwen3-TTS-12Hz-1.7B-Base** on one RTX 3090, behind an OpenAI-compatible
`POST /v1/audio/speech`. A thin gateway owns everything production needs (auth, admission control, voices, retries,
quality guardrails, logs, metrics, AI-generated labelling). The model runs in a separate engine process behind a
swappable backend interface, so Higgs Audio v3 (SGLang-Omni) or another engine can be added later.

```
client ──HTTP──▶ gateway (FastAPI, :8090, auth, queue, retries, labels)
                   │  backend = vllm_omni | stub | (qwen_native | higgs_sglang later)
                   ▼
                 engine (vLLM-Omni `vllm serve ... --omni`, 127.0.0.1:8091, GPU from TTS_ENGINE_GPU, default 0)
                   stage 0: talker (codebook 0, continuous batching) + code predictor (codebooks 1-15)
                   stage 1: code2wav (12 Hz speech-tokenizer decoder, 24 kHz PCM)
                 qc sidecar (optional, server/qc, 127.0.0.1:8092): Whisper large-v3 + WavLM checks per take
```

## Layout

```
<checkout>/server/               (the repo's server/ folder; paths are derived from the checkout, never hard-coded)
  gateway/tts_gateway/        the gateway package (python -m tts_gateway)
    config.py                 Settings from env (prefix TTS_), see below
    voices.py                 VoiceRegistry over VOICES_DIR/<id>/ (voice-server/v1 layout)
    textproc.py               word/letter count, sentence split (en + ur), length cap, pace bands
    qc.py                     client of the QC sidecar
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
    deploy/                   vLLM-Omni deploy YAMLs (production + benchmark variants, variants/custom_voices.yaml)
    patches/                  small, verified patches to vLLM-Omni (per-request repetition_penalty)
    precompute_voices.py      averaged-embedding (+ prompt-embedding) custom voices for custom_voice_dir
    install_engine.sh, run_engine.sh, wait_ready.py, make_variant.py, constraints-omni28.txt
  deploy/                     systemd unit templates, install_units.sh, env.example, health_watchdog.py
  qc/                         QC sidecar (tts_qc): Whisper large-v3 + WavLM + detectors, POST /v1/qc
  eval/                       offline scoring (score_run.py), retry simulation, calibration, GPU self-check
  baseline/                   plain qwen-tts 0.1.1 server with the same request shape (benchmark baseline)
  bench/                      run_plan.py / plan.py (phases), collect.py (tables), verify_knobs.py
  calibration/pace.json       expected output pace per voice (s/letter), shared by gateway, bench and QC
  results/                    benchmark outputs (AI-generated audio: never publish; gitignored)
  docs/                       this file, EXPERIMENTS.md, auralis_baseline.md, research notes
  venvs/                      gateway, engine (vllm-omni 0.28), eval (ASR + SIM), qwentts (baseline), tools
```

The load generator is `<checkout>/bench/bench_tts.py` (see `bench/README.md`).

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

`POST /v1/audio/speech` (JSON; works with the official `openai` SDK). OpenAI fields: `model` (ignored), `input` (required), `voice` (a
registered voice id, required unless inline cloning is enabled and `ref_audio` is given), `response_format`
(`wav` default, `pcm`, `flac`, `mp3`, `opus`; streaming: `wav` or `pcm`; every format carries the AI-generated label: WAV LIST/INFO ICMT, FLAC/Opus Vorbis comment, MP3 ID3 comment), `speed` (non-streaming only, passed through), `stream` (bool; raw audio chunks).
Extensions: `language` (default from the voice: `English` for en, `Auto` otherwise), `temperature`, `top_k`, `top_p`,
`repetition_penalty` (only if the backend advertises it), `seed`, `max_new_tokens`, `ref_audio` + `ref_text` (inline
cloning, only when `TTS_ALLOW_INLINE_REF=1`), `retries` (0..TTS_RETRY_MAX, per request override).

Response: audio bytes with `Content-Type` per format, and headers `X-Request-Id`, `X-AI-Generated: true`,
`X-TTS-Voice`, `X-TTS-Audio-Seconds`, `X-TTS-Retries`, `X-TTS-Suspect` (0/1, final take), `X-TTS-Suspect-Reason`
(`too_short`/`too_long`/`qc`), `X-TTS-Pace-Ratio` (the delivered take's pace / the voice's expected pace),
`X-TTS-QC` (`pass`/`fail`/`error`/`off`), `X-TTS-QC-Reasons`, `X-TTS-Queue-Ms`, `X-TTS-Engine-Ms`. WAV output carries a LIST/INFO `ICMT` comment "AI-generated speech (Qwen3-TTS voice clone)...".
Streaming responses send a WAV header with streaming sizes, then PCM (headers limited to those known up front).

Errors: JSON `{"error": {"message", "type", "code"}}` (OpenAI shape). 400 validation, 401 missing/bad key,
404 unknown voice, 413 input too long, 429 queue full (with `Retry-After`), 503 not ready / queue timeout / engine down,
504 engine timeout, 502 engine error after retries.

Other routes: `GET /health` (liveness, no auth), `GET /ready` (engine healthy + voices registered + warmup done; no
auth), `GET /metrics` (Prometheus; no auth, bind-local recommended), `GET /v1/voices` (alias `GET /v1/audio/voices`)
and `GET /v1/models` (auth). `/ready` also reports the QC sidecar's health when one is configured, but never turns
red because of it (QC is advisory).

## Config (env, prefix `TTS_`)

| var | default | meaning |
|---|---|---|
| `TTS_API_KEY` | (required unless `TTS_AUTH_DISABLED=1`) | Bearer key; compared in constant time. Several keys may be comma-separated |
| `TTS_BACKEND` | `vllm_omni` | `vllm_omni` or `stub` |
| `TTS_ENGINE_URL` | `http://127.0.0.1:8091` | engine base URL |
| `TTS_ENGINE_API_KEY` | – | key the engine expects (`--api-key`), if any |
| `TTS_ENGINE_PER_REQUEST_RP` | `0` | the engine has the `rep_penalty` patch (engine/patches): send `extra_params.repetition_penalty` and accept `repetition_penalty` per request |
| `TTS_VOICES_DIR` | `<checkout>/voices` | voice-server/v1 folders |
| `TTS_VOICE_MODE` | `registered` | `registered` (upload once, send `voice`), `inline` (send ref_audio every time) or `precomputed` (the engine loaded the voice at startup from `custom_voice_dir`, e.g. with an averaged speaker embedding; the gateway sends `TTS_PRECOMPUTED_VOICE_NAME`) |
| `TTS_PRECOMPUTED_VOICE_NAME` | `{id}-avg` | engine voice name per repo voice id in `precomputed` mode |
| `TTS_MAX_INFLIGHT` | 32 | requests sent to the engine at once |
| `TTS_MAX_QUEUE` | 128 | waiting requests beyond in-flight; more -> 429 |
| `TTS_QUEUE_TIMEOUT_S` | 60 | max wait for an in-flight slot -> 503 |
| `TTS_REQUEST_TIMEOUT_S` | 300 | per engine call |
| `TTS_MAX_INPUT_CHARS` | 3000 | -> 413 |
| `TTS_RETRY_MAX` | 1 | extra takes when a take is suspect or the engine fails (non-streaming only) |
| `TTS_RETRY_ON` | `suspect,engine_error,qc` | which failures trigger a retry |
| `TTS_LENGTH_CAP` | `1` | send `max_new_tokens = words/2.5*12.5*2.4 + 60` (bounded 96..4096) |
| `TTS_SUSPECT_BAND` | `0.6,1.8` | a take is suspect when its seconds per letter fall outside this multiple of the voice's expected pace |
| `TTS_PACE_FILE` | `<checkout>/server/calibration/pace.json` | expected output pace per voice (s/letter); a voice missing there uses its reference clip's pace |
| `TTS_PACE` | – | overrides, `voice=s_per_letter,...` |
| `TTS_SPW_EN` / `TTS_SPW_UR` | `0.18,0.9` / `0.18,1.1` | fallback seconds-per-word bands for text in a language other than the voice's |
| `TTS_QC_URL` | – | QC sidecar (server/qc) base URL, e.g. `http://127.0.0.1:8092`; unset = no ASR/SIM checks |
| `TTS_QC_CHECKS` | `asr,sim,audio` | checks requested per take (SIM is skipped for inline references) |
| `TTS_QC_TIMEOUT_S` | 30 | per QC call; on timeout or error the take is kept (fail open) |
| `TTS_LOG_TZ` | `Asia/Karachi` | JSON log timestamps are local time in this zone, with the UTC offset |
| `TTS_DEFAULT_TEMPERATURE` / `TTS_DEFAULT_TOP_K` | 0.9 / 50 | sent as `extra_params` unless the request overrides |
| `TTS_WARMUP` | `1` | one short request per voice before `/ready` turns green |
| `TTS_ALLOW_INLINE_REF` | `0` | accept `ref_audio`/`ref_text` in requests |
| `TTS_LOG_LEVEL` | `INFO` | JSON logs to stdout (journald) |
| `TTS_HOST` / `TTS_PORT` | `0.0.0.0` / `8090` | bind |

## Retry and quality policy (non-streaming)

1. Generate a take (no seed on the first attempt).
2. **Pace check:** letters = characters for which `str.isalnum()` holds (any script; spaces, punctuation and combining
   marks don't count). The take is suspect (`too_short`: skipped or cut-off text; `too_long`: a loop, filler or
   padding) when its seconds per letter fall outside `TTS_SUSPECT_BAND` × the voice's expected pace. Letters rather
   than words because Urdu word segmentation varies (صورتحال vs صورت حال). The expected pace comes from
   `calibration/pace.json`, not blindly from the reference clip: the shehbaz clip is a slow, pause-heavy address
   (0.183 s/letter) while Qwen's Urdu runs ~2x faster. The old fixed seconds-per-word band (0.18-1.1 for Urdu) missed
   all four known Kaggle Urdu failures (0.22, 0.25, 1.01, 1.01 s/word).
3. **QC check** (only when `TTS_QC_URL` is set and the pace check passed): the sidecar transcribes the take (stock
   Whisper large-v3; Urdu gated on CER without spaces, not WER), measures speaker similarity to the voice's reference
   clips, and runs loop/skip/silence detectors. A failed verdict makes the take suspect (`qc`). The sidecar being
   down or slow never fails a request: the take is kept and `X-TTS-QC: error` is sent.
4. The engine returning a codec-limit/5xx error counts as a retryable failure (`engine_error`).
5. While the take is suspect and retries remain: generate again (a new take; the engine samples fresh). Keep the best
   take: clean first, then QC-only failures, then pace failures, ties broken by the pace closest to the expected one.
6. Streaming requests cannot be retried after the first byte; they rely on the length cap to bound runaways. Their
   pace is still logged and counted.

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

systemd **user** units rendered by `deploy/install_units.sh` with this checkout's paths: `qwen3-tts-engine.service`
runs `engine/run_engine.sh` (GPU `TTS_ENGINE_GPU`, `VLLM_USE_FLASHINFER_SAMPLER=0`, clean `PATH`/`CUDA_HOME`) and is
active once `engine/wait_ready.py` got audio back; `qwen3-tts-engine-watchdog.service` restarts the engine when
`/health` keeps failing (a dead stage leaves the API answering 503, so `Restart=on-failure` alone never fires);
`qwen3-tts-gateway.service` (`After=`/`Wants=` the engine); optional `qwen3-tts-qc.service`. Secrets live in
`~/.config/qwen3-tts/env` (mode 600). User units stop at logout unless lingering is enabled
(`loginctl enable-linger $USER`). See README.md.
