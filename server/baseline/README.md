# qwen-tts baseline server

A plain `qwen-tts` 0.1.1 (transformers) server for `Qwen/Qwen3-TTS-12Hz-1.7B-Base` voice cloning. It speaks the
vLLM-Omni 0.28 `/v1/audio/speech` request shape, so `bench/bench_tts.py` can run the same requests against
vLLM-Omni (the production engine) and against this stock baseline. It is a control for the benchmark, not a
production engine: there is no streaming, no continuous batching, and one generate call runs at a time.

| file | what |
|---|---|
| `qwen_tts_server.py` | CLI, FastAPI routes, request validation, JSON logs |
| `engine.py` | references and repo voices, voice-clone prompt cache, averaged embedding, the model worker, the dynamic batcher |
| `wavlabel.py` | PCM16 WAV with the AI-generated LIST/INFO ICMT label (byte-identical to `server/gateway/tts_gateway/audio.py`) |
| `smoke.py` | GPU smoke client (standard library only; starts nothing) |
| `tests/` | 86 pytest tests with a fake model (CPU, no weights) |
| `results/cpu-e2e-check.json` | the real-model CPU end-to-end check (numbers) |

## Environment

Venv: `server/venvs/qwentts` (Python 3.12.6). Versions as reported by `importlib.metadata`:

| package | version | | package | version |
|---|---|---|---|---|
| qwen-tts | 0.1.1 | | fastapi | 0.136.3 |
| transformers | 4.57.3 | | uvicorn | 0.53.0 |
| torch | 2.13.0 (CUDA 13.0 build) | | pydantic | 2.13.5 |
| torchaudio | 2.11.0 (not imported by qwen-tts) | | python-multipart | 0.0.32 |
| accelerate | 1.12.0 | | numpy | 2.3.5 |
| tokenizers | 0.22.2 | | soundfile | 0.14.0 |
| huggingface-hub | 0.36.2 | | librosa | 1.0.0 |
| safetensors | 0.8.0 | | httpx / pytest / pytest-asyncio | 0.28.1 / 9.1.1 / 1.4.0 |

Model: the HF cache snapshot `models--Qwen--Qwen3-TTS-12Hz-1.7B-Base/snapshots/fd4b2543...`. The server sets
`HF_HUB_OFFLINE=1` (unless already set) and resolves `--model` to that local snapshot. **Loading by hub id does not
work offline:** transformers 4.57.3 `_patch_mistral_regex` calls `huggingface_hub.model_info()` for non-local paths
and raises `OfflineModeIsEnabled`. A local-dir load with qwen-tts' `fix_mistral_regex=True` gets the Mistral
pre-tokenizer regex (qwen-tts-internals finding 19). Measured here: the trump reference transcript tokenizes to 67
tokens either way; the shehbaz transcript to 111 (stock) vs 112 (Qwen2 regex) tokens. `--qwen-regex` reloads the text
tokenizer with `fix_mistral_regex=False`; the default is the stock behaviour.

## Run

GPU (the normal case; the model needs about 4.2 GB for bf16 weights, plus activations that grow with batch and
length):

```bash
cd /home/vector/Documents/abdullah_workspace/qwen-server/tts-reference-voices
CUDA_VISIBLE_DEVICES=0 server/venvs/qwentts/bin/python server/baseline/qwen_tts_server.py \
    --host 127.0.0.1 --port 8093 --device cuda:0 --dtype bfloat16 --attn sdpa --max-batch 8 --batch-window-ms 20 \
    > /path/to/logs/qwentts-baseline.jsonl 2>&1 &
until curl -sf http://127.0.0.1:8093/health; do sleep 5; done      # 503 while loading, then {"status":"healthy"}
```

The benchmark arms map to flags: `--max-batch 1` = sequential; `--no-prompt-cache` = "voice-prompt cache off";
`--avg-embedding` = the NOTES.md averaged speaker embedding; `--length-policy truncate` = return capped audio instead
of vLLM-Omni's HTTP 500.

### CLI

| flag | default | meaning |
|---|---|---|
| `--host`, `--port` | 127.0.0.1, 8093 | |
| `--model` | Qwen/Qwen3-TTS-12Hz-1.7B-Base | hub id (resolved to the local snapshot) or a model dir |
| `--device` | cuda:0 | `cpu` works (slowly, see below) |
| `--dtype` | bfloat16 | or float32. float16 is not offered: logits overflow fp16 (qwen-tts #43, PR #355) |
| `--attn` | sdpa | or eager, flash_attention_2 (FA2 gave NaN logits in qwen-tts #333; not installed here) |
| `--voices-dir` | `<repo>/voices` | derived from the file location |
| `--max-batch` | 8 | rows per generate call; 1 = sequential |
| `--batch-window-ms` | 20 | how long an idle worker waits for batch mates of the oldest request |
| `--no-prompt-cache` | off | run `create_voice_clone_prompt` for every request |
| `--prompt-cache-size` | 256 | LRU entries for inline and uploaded references (repo voices are pinned on top) |
| `--avg-embedding` | off | repo voices: averaged, rescaled speaker embedding (see below) |
| `--length-policy` | error | `error` = vLLM-Omni 0.28 behaviour; `truncate` = return the capped audio |
| `--no-length-retry` | off | with `error`: never retry a runaway |
| `--qwen-regex` | off | Qwen2 pre-tokenizer regex instead of the stock Mistral one |
| `--max-queue` | 512 | pending requests before HTTP 503 (0 = unlimited) |
| `--threads` | 0 | `torch.set_num_threads` on the worker thread (CPU runs) |
| `--no-warmup` | off | skip the one 24-frame warm-up generation at startup |
| `--log-level`, `--log-tz` | INFO, Asia/Karachi | |

## API

| route | |
|---|---|
| `GET /health` | 200 `{"status":"healthy"}` once the model is loaded, the voices are prepared and the warm-up ran; 503 `{"status":"loading"}` before, 503 `{"status":"unhealthy","error":...}` if startup failed (the process then exits with code 2) |
| `GET /v1/audio/voices` | `{"voices": [repo + uploaded names], "uploaded_voices": [{name, consent, created_at, mime_type, file_size, embedding_source, sample_rate, duration_s, mode, ref_text?}]}` |
| `POST /v1/audio/voices` | multipart `audio_sample` (≤10 MB, 1-30 s, anything libsndfile decodes), `name`, `consent` (both required), `ref_text` (optional; without it the voice is x-vector only), `speaker_description`. Returns `{"success": true, "voice": {...}}`. Names are case-insensitive; re-uploading a name replaces it; a repo voice name is refused. Stored in memory only (lost on restart). `speaker_embedding` uploads are refused |
| `DELETE /v1/audio/voices/{name}` | 200 `{"success": true, ...}` or 404 |
| `POST /v1/audio/speech` | see below |
| `GET /v1/baseline/info` | config, versions, model path, generation_config, voice preparation numbers (prompt ms, ref frames, embedding norms and the averaged-embedding statistics), prompt-cache and batch counters, batch-size histogram, CUDA memory |

Errors use vLLM's shape: `{"error": {"message", "type", "param", "code"}}`. Request validation errors are 400.

### POST /v1/audio/speech

| field | handling |
|---|---|
| `input` | required; stripped (a leading newline would shift qwen-tts' text slice, finding 20); empty → 400 |
| `voice` (alias `speaker`) | repo voice id or uploaded name, case-insensitive. A known voice wins over `ref_audio` / `ref_text` (logged once). Unknown voice without `ref_audio` → 400 |
| `ref_audio` | `data:audio/...;base64,...` or plain base64; http(s)/file/any other URL → 400 (the baseline never fetches). 1-30 s like vLLM-Omni |
| `ref_text` | required for inline ICL unless `x_vector_only_mode` |
| `x_vector_only_mode` | inline, or with a voice (derives an x-vector-only prompt) |
| `task_type` | absent or `Base`; anything else → 400 |
| `language` | case-insensitive `Auto` + the model's 10 languages; `Urdu`/`ur` → `Auto` (logged once); others → 400. Absent: the voice's default (repo `en` voices English, others Auto; inline/uploaded Auto). Languages may differ between rows of one batch (verified in the source: one language per row) |
| `response_format` | `wav` (default: 24 kHz PCM16 mono with the AI label) or `pcm` (raw s16le); others → 400 |
| `max_new_tokens` | 1..4096 (like vLLM-Omni), else 400 |
| `seed` | integer; the request runs alone with `torch.manual_seed(seed)` |
| `non_streaming_mode` | passed to `generate_voice_clone` (default False, the qwen-tts and vLLM-Omni Base default) |
| `extra_params` | `temperature` (>0), `top_k` (int ≥0), `top_p` (0,1], `repetition_penalty` (>0); other keys ignored (logged once). Defaults: generation_config.json (0.9 / 50 / 1.0 / 1.05). The sub-talker keeps generation_config values |
| `stream: true` | 400 `streaming not supported by the qwen-tts baseline` |
| `speed` ≠ 1, `word_timestamps`, `speaker_embedding` | 400 (not supported) |
| `model`, `instructions`, `stream_format`, `initial_codec_chunk_frames` | accepted, no effect (logged once) |
| any other field | ignored like vLLM-Omni (logged once per field name), e.g. top-level `temperature`, `sample_rate` |

Response headers: `X-AI-Generated: true`, `X-Request-Id` (echoes a sane client `X-Request-Id`), and
`X-Baseline-Batch-Size`, `-Batch-Id`, `-Queue-Ms` (enqueue → batch start), `-Prompt-Ms` (prompt lookup/creation for
the batch), `-Gen-Ms` (the generate call, which includes the reference re-decode), `-Codec-Frames` (this row, after
the cap trim), `-Text-Tokens`, `-Max-New-Tokens` (this row's cap), `-Batch-Max-New-Tokens` (what generate got),
`-Finish-Reason` (`stop` | `length`), `-Prompt-Cache` (`hit` | `miss` | `off`), `-Retries`, `-Sample-Rate`.
There are no `X-VLLM-OMNI-*` token headers; `X-Baseline-Codec-Frames` is the equivalent of
`X-VLLM-OMNI-OUTPUT-TOKENS`.

Differences from vLLM-Omni 0.28 that matter for the comparison:
- `extra_params.repetition_penalty` is applied per request here; vLLM-Omni ignores it (server YAML only).
- Plain base64 `ref_audio` is accepted here; vLLM-Omni wants a `data:` URL. URL fetching is refused here.
- `Urdu` maps to `Auto` here; vLLM-Omni returns 400.
- `speed`, `word_timestamps`, `speaker_embedding`, flac/mp3/opus and streaming are refused here.
- Tokenization: stock qwen-tts under transformers 4.57.3 (Mistral regex, see above) vs vLLM-Omni's transformers 5.x.
- The reference is re-decoded and re-prefilled on every request (stock qwen-tts, finding 7); vLLM-Omni caches more.

### Codec budget and runaways (mirrors vLLM-Omni 0.28)

A row's cap is the request's `max_new_tokens`, else `min(max(192, 12 × text_tokens), 4096)` with text tokens
counted by the model's tokenizer on the stripped input (vLLM-Omni `tts_adapters/qwen3_tts.py`). A row with
`codec_frames >= cap` ended without EOS inside its cap (`finish_reason=length`). With `--length-policy error`
(default) it is retried once, at the front of the queue, when the request had neither `seed` nor `max_new_tokens`
(vLLM-Omni retries with a random seed; here the retry is unseeded, so it draws fresh samples from the global RNG),
and otherwise fails with HTTP 500 `Qwen3-TTS Base did not emit codec EOS before its token budget (N/N codec tokens);
the generated audio is incomplete.` `X-Baseline-Retries: 1` marks a retried success. `--length-policy truncate`
returns the capped audio with `X-Baseline-Finish-Reason: length`.

### Prompt cache and averaged embedding

- Repo voices (`voices/<id>/`, id = folder): `references/qwen3-tts.wav` + the `qwen3-tts` transcript from
  `references.json` (its sha256 is checked and reported, not enforced). With the cache on (default) their prompts
  (`ref_code` + speaker embedding) are created at startup and pinned.
- Inline and uploaded references go through an LRU (`--prompt-cache-size`) keyed by sha1 of the audio file bytes +
  mode + sha1 of the transcript. Uploaded voices are encoded lazily on first use (like vLLM-Omni).
- `--no-prompt-cache`: `create_voice_clone_prompt` runs for every request, one per row, even inside one batch.
- `--avg-embedding` (repo voices only): mean of `extract_speaker_embedding` over the voice's clips (`clips.json`,
  48 kHz files resampled to 24 kHz with librosa like qwen-tts), rescaled to the mean per-clip norm, replacing
  `ref_spk_embedding` of the ICL prompt (finding 8). It is computed once at startup; with the cache off it is
  applied to each freshly created prompt. trump has one clip, so its "average" is that clip's embedding (the raw
  48 kHz clip, not the cleaned reference). The statistics (clip norms, cosine to the reference embedding) are in
  `/v1/baseline/info` and the `voice_prepared` log line. An inline request with the same audio does not get it.

## Batching design and limits

qwen-tts is not thread-safe (the talker keeps `rope_deltas` as instance state, finding 15), so every model call
(load, prompts, embeddings, generate) runs on ONE worker thread (`ThreadPoolExecutor(max_workers=1)`), and a
thread-identity check in `Engine` fails loudly otherwise. The batcher runs on the asyncio loop:

- Requests join a FIFO queue. The oldest pending request decides the next batch: all pending requests with the same
  group key, in arrival order, up to `--max-batch`. Group key = the talker sampling params (temperature, top_k,
  top_p, repetition_penalty) + `non_streaming_mode`, because `generate_voice_clone` takes one set of each per call.
  Voice, reference, language and ICL/x-vector mode may differ per row.
- When the worker is idle, a batch waits until it is full or `--batch-window-ms` has passed since its oldest request
  arrived. Requests that queued while the worker was busy start at once. One batch in flight at a time; other groups
  wait for later batches (no reordering beyond "oldest group first").
- Seeded requests run alone: `torch.manual_seed(seed)` right before generate, then `torch.seed()` re-randomises the
  global RNG. A given seed reproduces only for the same text, voice, params, device and software (qwen-tts seeds are
  global, shared across a batch, finding 12).
- `max_new_tokens` of a call is the largest row cap in the batch. Each row is cut to its own cap afterwards
  (`cap × 1920` samples; the decoder is causal and emits exactly 1920 samples per frame, so this equals decoding
  only `cap` frames), and a row that reached its cap is a `length` row as if it had run alone. The compute is not
  saved: static batching runs every row until the whole batch finishes (finding 14), so one long or runaway row
  sets the latency of its batch mates.
- CUDA out-of-memory in a generate call: the batch is split in halves and retried recursively down to single rows
  (`oom_splits` in `/v1/baseline/info`).
- `--max-queue` pending requests → HTTP 503. No request timeout on the server (clients set their own); a client that
  disconnects while queued is removed, one already in a batch still runs.
- Not implemented: continuous batching, streaming, prefix/reference caching beyond the prompt items, sharing the
  reference decode across rows. `--max-batch` is a ceiling, not a VRAM-sized value: size it on the GPU.

## Logs

JSON lines on stdout; `ts` is Asia/Karachi local time with its offset (`--log-tz`). One `request` line per speech
request (request_id, voice, ref source, lang, chars, format, sampling, seed, batch size and id, queue/prompt/gen/total
ms, prompt cache, text tokens, codec frames, row cap and batch cap, finish reason, retries, audio seconds, RTF, HTTP
status, error), plus `starting` (config + versions), `voice_prepared`, `ready`, `startup_failed`, `voice_uploaded`,
`voice_deleted`, `oom_split` and the once-only `unknown_field_ignored` / `field_ignored` / `extra_param_ignored` /
`language_mapped` / `ref_ignored_for_voice` warnings.

## Tests

```bash
cd server/baseline && CUDA_VISIBLE_DEVICES="" ../venvs/qwentts/bin/python -m pytest -q
```

A fake `Qwen3TTSModel` (`tests/fake_qwen_tts.py`: same method names, exactly 1920 samples per frame, `loop` texts
never emit EOS, raises on concurrent calls, records every call and its thread) covers validation (26 bad requests
and 8 bad uploads), labels (WAV ICMT and header; WAV bytes identical to the gateway helper), batching (window,
`--max-batch` 1/2/8, grouping by sampling and `non_streaming_mode` but not language or voice, FIFO, seeds alone and
reproducible, batch cap vs row caps, OOM split, queue full, a cancelled queued request), the length policy and its retry, the prompt cache (on,
off, LRU, pinned voices), the averaged embedding (math and cache-off path), voice upload/list/delete, health/startup
failure/warm-up, one-thread model access, the request log line, the real repo voices' metadata, and `smoke.py`
against a live uvicorn server running the fake model.

## GPU smoke (for the orchestrator)

```bash
cd /home/vector/Documents/abdullah_workspace/qwen-server/tts-reference-voices
OUT=/path/outside/git/qwentts-smoke-$(date +%Y%m%d-%H%M)     # AI-generated audio: never commit or publish
mkdir -p "$OUT"
CUDA_VISIBLE_DEVICES=0 server/venvs/qwentts/bin/python server/baseline/qwen_tts_server.py --port 8093 \
    > "$OUT/server.jsonl" 2>&1 &
echo $! > "$OUT/server.pid"
until curl -sf http://127.0.0.1:8093/health; do sleep 5; done
server/venvs/qwentts/bin/python server/baseline/smoke.py --url http://127.0.0.1:8093 --out "$OUT"
curl -s http://127.0.0.1:8093/v1/baseline/info > "$OUT/info.json"
kill "$(cat "$OUT/server.pid")"
```

`smoke.py` sends one English request (voice=trump, English), one Urdu request (voice=shehbaz, Auto), one inline
`ref_audio` request (trump's reference as a data: URL + transcript) and 4 concurrent requests (trump/shehbaz mixed,
so one batch of 4 with mixed voices and languages is expected). It prints latency, audio seconds, RTF, batch size,
queue ms, codec frames and gen ms per request, checks the WAV label, the `X-AI-Generated` header, 24 kHz PCM16 mono
and `codec_frames × 1920 == samples`, saves the WAVs in `--out`, and writes everything to `--out/smoke.json`. Exit
code 0 only when every step passed.

## CPU end-to-end check

The real model on CPU (`CUDA_VISIBLE_DEVICES=''`, `--device cpu --dtype bfloat16 --threads 4`, `nice -n 19`),
2026-09-25 03:35-04:20 PKT. Every number is in `results/cpu-e2e-check.json`; the audio stayed in the session
scratch dir.

| step | result |
|---|---|
| startup | ready in 98.1 s; prompts: shehbaz 42.9 s (351 ref frames, embedding norm 17.18), trump 52.5 s (291 frames, norm 17.32) |
| 1 request, trump, "Hello there." | server: HTTP 200, 12 codec frames (0.96 s), EOS inside its 192 cap, prompt-cache hit, generate 901.2 s (the client's 900 s timeout expired 1.2 s earlier, so no WAV from this one) |
| 2 concurrent, trump English "Hi there." + shehbaz Urdu→Auto "آپ کا شکریہ۔" | ONE batch of 2 (same batch id); both HTTP 200, 9 and 21 frames (0.72 s, 1.68 s), EOS; WAV ICMT label and `X-AI-Generated` present; `frames × 1920 == samples`; generate 1585.6 s |
| peak RSS | 7,628 MiB (limit 10 GB) |

CPU speed means nothing here: the i9-14900K has no AVX-512/AMX bf16 (`mkldnn bf16 supported: False`), and bf16
generation ran on one busy thread despite `--threads 4`. fp32 would need about 9-10 GB of RSS, so it was not tried.

## Unverified

- Nothing has run on a GPU: VRAM per batch size, speed, and whether `--max-batch 8` fits next to the vLLM engine on
  GPU 0 are unmeasured. The orchestrator's smoke is the first GPU run. At 04:20 PKT GPU 0 had about 15 GB in use
  (vLLM engine + desktop), which leaves about 9 GB; the baseline needs 4.2 GB of bf16 weights plus activations
  that grow with batch size and length (forced `output_hidden_states` roughly doubles per-token memory, finding 4).
- The per-row cap trim relies on the decoder being causal with exactly 1920 samples per frame (source reading,
  finding 3). It was not compared against a lone decode of `cap` frames.
- The retry of a runaway row is unseeded here; vLLM-Omni retries with a random seed. Both give one fresh sample.
- Seed reproducibility on CUDA (the fake test checks the RNG draw only).
- OOM halving on a real CUDA OOM (tested with a fake `torch.OutOfMemoryError`).
- Uploads in formats other than WAV (libsndfile decodes FLAC/OGG/MP3; not tested).
