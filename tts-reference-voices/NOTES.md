# What we learned (Sept 2026, Kaggle T4 x2)

Facts from running Qwen3-TTS and Higgs Audio v3 on these voices. Treat them as a starting point to verify on
new hardware, not as settled answers.

## Qwen3-TTS: the model

- **Clone model:** `Qwen/Qwen3-TTS-12Hz-1.7B-Base`, via the `qwen-tts` package (0.1.1, the latest on PyPI as of
  Sept 2026, which pins transformers 4.57.3). Output is 24 kHz mono at 12.5 codec tokens per second.
- **Loads offline:** `from_pretrained(<local dir>)` also loads `speech_tokenizer/` from the same folder.
- **No style control:** Base has no inline tags and no `instruct`. Bracket tags like `[angry]` or `<happy>` are
  read out loud. CustomVoice and VoiceDesign take a natural-language `instruct` but can't clone, so the open
  weights never give you cloning and instructions together.
- **Languages:** Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian, plus
  "Auto". **Urdu is not supported:** use `language="Auto"`.

## Qwen3-TTS: conditioning and settings we used

- **In-context reference:** `references/qwen3-tts.wav` (≤30 s) plus its *exact* transcript. Whisper's Urdu
  transcript had to be corrected by hand.
- **Speaker embedding:** replaced with the mean of `extract_speaker_embedding` over every clip, rescaled to
  the typical norm.
- **Sampling:** temperature 0.9, top_k 50, repetition_penalty 1.05.
- **Length cap:** `max_new_tokens ≈ words/2.5 × 12.5 × 2.4 + 60`, which stops runaway takes.
- **Batching:** batches of 4 on a T4; halve on out-of-memory.
- **Delivery follows the reference:** a calm reference gives calm output. For varied lecture tones, use a
  separate reference per tone.

## Qwen3-TTS: measured

| | result |
|---|---|
| Speed (T4, fp32, batch 1) | RTF ≈ 2.2–2.5 (2.4 s of compute per 1 s of audio), both languages. No numbers yet for bf16 or newer GPUs |
| English quality (another speaker, best of 2 with retries) | speaker similarity ≈ 0.974 (WavLM), WER ≈ 0.7 % |
| English pace (trump) | 3.3–3.9 words/s |
| Urdu (shehbaz, 1 raw take per prompt) | accented but intelligible, ~3–4 words/s |

**Urdu failures: 5 of 46 takes were bad.**

| take | failure |
|---|---|
| sample 01 | skipped about 25 words (came out 22 s) |
| sample 19 | cut short (25.6 s) |
| sample 17 | 95.9 s, padded with silence and made-up filler |
| sample 38 | 98.8 s, looped on "آآآ" |
| a smoke take | looped on "ایک ایک…" |

Repeated words and syllables trigger the loops.

## Quality guardrails that worked

- **Duration band:** audio seconds per word inside about 0.18–0.9 (English) or 0.18–1.1 (Urdu). `bench_tts.py`
  flags anything outside as `suspect`.
- **WER:** Whisper large-v3 above 0.22 → re-roll with a new seed.
- **Speaker similarity:** WavLM below 0.88 → re-roll. Up to 2 rounds.
- **For Urdu:** also test repetition_penalty 1.1–1.2 against loops, and measure what it costs in quality.

## Serving on vLLM-Omni

Serving Qwen3-TTS on vLLM-Omni is **documented by vLLM but untested by us**. Confirm everything below against
the installed version.

- **Serve:** `vllm serve Qwen/Qwen3-TTS-12Hz-1.7B-Base --deploy-config vllm_omni/deploy/qwen3_tts.yaml --omni --port 8091 --trust-remote-code --enforce-eager`
- **Speech request:** `POST /v1/audio/speech` with `{"input", "task_type": "Base", "ref_audio"}` plus
  `"ref_text", "language": "Auto"|"English", "response_format": "wav"|"pcm"|…, "stream", "stream_format": "audio"|"sse", "max_new_tokens", "speed", "sample_rate"}`.
  `ref_audio` can be a URL, a base64 data URL, or `file://`.
- **Register a voice once:** `POST /v1/audio/voices`, multipart with `audio_sample`, `name`, `consent`, and
  `ref_text`. Later requests then send `"voice": "<name>"`.
- **Per-voice cache:** vLLM-Omni caches each voice's reference features in process.
- **Open questions:** whether sampling parameters are accepted per request, whether the embedding can be
  averaged over several clips, and how batching and streaming behave under load.

Docs:
- https://docs.vllm.ai/projects/vllm-omni/en/latest/serving/speech_api/
- https://vllm.ai/blog/2026-06-23-vllm-omni-tts

## Higgs Audio v3 (only if it's added later)

- **Model:** `bosonai/higgs-tts-3-4b`, officially served with SGLang-Omni. It has 43 inline control tags and
  good Urdu.
- **Measured on a T4 (bf16):** about 8.3 GB of VRAM. RTF 1.7 with a 23 s reference and 3.4 with a 90 s one.
- **30 s ceiling:** each generation stops at about 30 s and drops the rest of the text, so split at sentences.
- **Sampling:** temperature 0.8, top_k 50, top_p off.
- **In Urdu:** the speed tags are weak. `higgs-v3.wav` (a livelier 39 s reference) beats the full 90 s one.
