# Qwen3-TTS voice-clone server on one RTX 3090: benchmark report and recommended production config

**Model:** Qwen/Qwen3-TTS-12Hz-1.7B-Base (voice clone, 24 kHz). **Voices:** `trump` (English), `shehbaz` (Urdu,
language "Auto"). **Hardware:** one RTX 3090 24 GB that also drives a desktop. **Engine:** vLLM-Omni 0.28.0 behind our
gateway (`server/gateway`). Measured 2026-09-24/25 on the machine `vector`. Every number below comes from
`server/results/` (local, gitignored; every take is kept there with its numbers) via `bench/collect.py` and
`bench/report_extract.py`; the experiment-by-experiment log is [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

> All generated audio is AI-generated imitation of real people. It is kept locally, labelled in every file, and must
> not be published.

## 1. Summary

| | |
|---|---|
| **Engine** | vLLM-Omni 0.28.0 (+ vllm 0.28.0, torch 2.13 cu130), bf16 talker, fp32 Code2Wav, CUDA graphs, async_chunk **on**, FlashInfer sampler **off** |
| **Speed** | RTF ≈ 0.18-0.20 per request (5-5.7x realtime) at c=1; streaming first audio **0.12 s**; **31-35x realtime aggregate** at 32 concurrent on 15-60 s texts, 38-40x at 64. About 3x the plain qwen-tts baseline per request and 3-4x its aggregate |
| **Capacity** | 32 requests in flight: long texts (~16-33 s of audio) p50 14-26 s; short sentences p50 3.6-4.4 s, 5.5-7 req/s; roughly 30 simultaneous real-time streams |
| **English quality** | WER 0.6-1.5%, severe failures 0-2% per take, speaker similarity 0.98 (WavLM base-plus-sv; the Kaggle "0.97" scale) / 0.82-0.87 (WavLM-Large) |
| **Urdu quality** | Accented but intelligible (WER ~0.37, CER ~0.17, by stock Whisper large-v3); **severe failures** (skipped passage, garble, loop, runaway) **15.5% per take** on the 43 ~95-word prompts with default settings, **7.7% with `non_streaming_mode=true`**, and up to 93% on ~200-word texts unless mitigated (16% with `non_streaming_mode`, 12% with it plus sentence splitting) |
| **Guardrails** | `non_streaming_mode` for Urdu (free), length cap (3x throughput on runaways), sentence splitting (60 words), pace + runaway retry (cheap: severe 7.7% → 5.8%); with the ASR QC sidecar and 1-2 retries Urdu severe failures fall to **1.9% / 0.5%**, but ASR-QC inline on the same GPU cuts throughput 2-7x under load |
| **Recommendation** | Section 8: engine as above with the precomputed voices; gateway with 32 in flight, length cap, `non_streaming_mode` for Urdu, 60-word splitting, 1 retry on pace/engine errors; streaming for interactive use; ASR QC only at low load or on a second GPU |

## 2. Setup and method

- **Machine:** RTX 3090 24 GB (GPU 0, also runs the desktop: 335 MiB and some GPU time; every number includes that),
  driver 580.95.05 (CUDA 13.0), Intel i9-14900K (governor powersave, EPP balance_performance, not changed: no root),
  30 GB RAM, Ubuntu 25.04.
- **Software:** vllm 0.28.0, vllm-omni 0.28.0, torch 2.13.0+cu130, transformers 5.14.1, flashinfer-python
  0.6.16.post3 (sampler off), Python 3.12.6. Baseline: qwen-tts 0.1.1 / transformers 4.57.3. Eval: faster-whisper
  1.2.1 (CTranslate2 4.8.2) with **stock** Whisper large-v3 (Systran/faster-whisper-large-v3), WavLM-Large + ECAPA
  (seed-tts-eval SIM) and microsoft/wavlm-base-plus-sv. Exact package lists per phase: `results/<phase>/versions/`.
- **Voices:** in-context cloning from `voices/<id>/references/qwen3-tts.wav` + its transcript (trump 23 s, shehbaz
  28 s), registered with the engine once (or sent inline where stated). Sampling: temperature 0.9, top_k 50,
  repetition_penalty 1.05 (the model defaults).
- **Texts:** `bench/pools/{en,ur}.json`: short (1 sentence, ~3-5 s), medium (20-45 words, ~7-10 s), long (55-70 words,
  ~16-22 s), xlong (one of the 43 benchmark prompts, ~32 s: "medium (~30 s)"), xxlong (two prompts joined, ~60-64 s:
  "long (~60 s)"); quality runs use the 43 `benchmarks/*.json` prompts (`plain_text`). A run never repeats a text.
- **Load generator:** `bench/bench_tts.py`, orchestrated by `server/bench/run_plan.py` (one engine configuration per
  phase, fresh or reused, GPU release verified). Latency = request start to last byte; TTFA = first audio byte past
  the WAV header; x realtime = audio seconds per wall second; **"x realtime" in this report is the straggler-robust
  p90-wall value** (audio of the requests finished by the time 90% had finished, over that time), because one runaway
  can otherwise dominate a finite run; the plain wall value is in `results/REPORT_tables.md`. No seeds anywhere: on
  vLLM-Omni 0.28 a seed does not reproduce a take even at c=1 (E04).
- **Quality:** `server/eval/score_run.py` on every take (Whisper large-v3 fp16, beam 5, language forced, word
  timestamps; SIM vs the prompt clip and vs held-out clips); failure tiers by `eval/failure_classes.py`: **severe** =
  unusable (runaway; pace outside 0.6-1.8x the voice's calibrated s/letter; a skipped passage of >= 12 words Urdu /
  5 English or < 80% of the characters; garbled: CER-nospace > 0.45 / WER > 0.30; a loop Whisper swallowed; a voiced
  gap > 3 s; wrong speaker); **moderate** = local (a skipped phrase of 6-11 words, repeats, 80-88% of the characters);
  the rest is **clean** (for Urdu: accent-level recognition errors). Thresholds were calibrated on the takes
  themselves after the human-speech values failed 69% of correct Urdu takes (EXPERIMENTS.md, quality). 95% intervals
  are Wilson (rates) or bootstrap over prompts (retry study).
- **Knobs verified before trusting them** (vLLM-Omni silently ignores unknown fields): `extra_params.repetition_penalty`
  (patched engine) and `extra_params.temperature` are read (invalid values → 400) while the same top-level fields are
  ignored; `non_streaming_mode`, `language`, custom voices and `max_new_tokens` are read (E04, `P0_knobs`, and a check
  before every phase that depends on one).

## 3. Serving options

| option | verdict | evidence |
|---|---|---|
| **vLLM-Omni 0.28.0** | **chosen** | serves Qwen3-TTS Base voice clone behind `/v1/audio/speech` with continuous batching, CUDA graphs, streaming, a voice registry and reference caches; measured 3x faster per request and 3-4x more aggregate than qwen-tts (§6); the source-level review of 0.28 is in docs/research/omni-source.md |
| vLLM-Omni 0.30.0rc1 | not used | experimental MRV2 runner by default; its 0.30.0 release CI produced looping voice-clone audio (#8091); disk was too tight for a second engine venv |
| qwen-tts 0.1.1 (transformers) | baseline only | no streaming, static batches (one runaway row holds the batch), not thread-safe; measured in P9 |
| SGLang-Omni / faster-qwen3-tts / qwentts.cpp | not built | ranked in docs/research/alternatives.md; SGLang-Omni matters later for Higgs Audio v3 |

Engine variants screened (P1, medium texts, x realtime at c = 1 / 8 / 32):

| variant | trump | shehbaz | verdict |
|---|---|---|---|
| prod (bf16, graphs, async_chunk on, 64 seqs) | 5.3 / 16.2 / 25.4 | 5.5 / 17.4 / 27.7 | chosen |
| eager (no CUDA graphs) | 2.0 / 9.8 / 22.4 | 2.3 / 15.6 / 27.3 | 2.4-2.7x slower at low load |
| async_chunk off | – | – / 14.4 / – | -5..-21% throughput, TTFA = whole generation, +3.5-4.5 GB (E03) |
| max_num_seqs 32 / 128 | 5.4 / 15.2 / 24.8 · 5.3 / 15.0 / 24.9 | 5.5 / 16.9 / 27.0 · 5.4 / 17.2 / 27.4 | no difference at c <= 32 |
| stage-0 memory 0.45 instead of 0.60 | 5.3 / 16.2 / 25.6 | 5.5 / 17.2 / 27.7 | same speed; KV 58k instead of 91k tokens |
| Code2Wav graph buckets 1/2/4 | 5.3 / 15.1 / 25.2 | 5.4 / 17.4 / 28.1 | same speed, +4.7 GB |
| Code2Wav batch 8 | – | – | does not fit (stage 1 needs ~12 GB for its graphs) |
| fp16 / fp32 talker | – | – | crash on the first request (encoders are hard-coded bf16 in 0.28) |

Precision is therefore bf16 (talker) + fp32 (Code2Wav), the only working combination on 0.28, and the right one
anyway (the weights are bf16; fp16 overflows on this model).

## 4. Performance

### 4.1 Throughput and latency vs concurrency (P2 + P2_high_c; non-streaming, engine direct with the gateway's length cap)

x realtime (straggler-robust) and latency p50 / p99 in seconds:

| voice | size (audio/req) | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 | c=64 |
|---|---|---|---|---|---|---|---|---|
| trump | short (3 s) | 5.0x · 0.79 / 1.01 | 8.1x · 0.63 / 1.16 | 10.6x · 0.89 / 1.39 | 12.6x · 1.36 / 2.86 | 14.8x · 2.40 / 4.49 | 18.4x · 3.64 / 6.85 | 21.3x · 6.66 / 14.2 |
| trump | medium (7 s) | 5.3x · 1.20 / 1.84 | 9.4x · 1.33 / 1.68 | 12.3x · 1.71 / 3.06 | 16.2x · 2.54 / 3.98 | 21.7x · 4.31 / 7.12 | 26.9x · 6.43 / 11.9 | 29.1x · 12.3 / 20.8 |
| trump | long (16 s) | 5.5x · 3.03 / 3.05 | 9.9x · 3.03 / 3.47 | 14.7x · 4.23 / 4.26 | 19.1x · 6.01 / 6.43 | 24.6x · 9.10 / 10.0 | 30.8x · 14.0 / 15.3 | – |
| trump | xlong (32 s) | 5.6x · 5.52 / 6.31 | 10.5x · 5.93 / 6.59 | 13.5x · 7.48 / 8.12 | 17.9x · 11.8 / 15.4 | 26.6x · 16.4 / 17.8 | 33.9x · 25.4 / 30.5 | 38.1x · 45.7 / 49.5 |
| trump | xxlong (63 s) | 5.7x · 11.2 / 12.0 | 10.6x · 11.7 / 11.7 | 15.4x · 15.4 / 16.2 | 20.7x · 22.7 / 23.7 | 26.2x · 31.8 / 38.3 | 34.8x · 49.5 / 56.0 | – |
| shehbaz | short (4 s) | 5.1x · 1.05 / 1.35 | 8.0x · 0.94 / 1.18 | 11.4x · 1.48 / 2.26 | 13.7x · 1.82 / 3.39 | 17.8x · 2.68 / 5.88 | 21.4x · 4.36 / 9.27 | 23.0x · 7.79 / 16.3 |
| shehbaz | medium (10 s) | 5.4x · 2.27 / 2.67 | 9.1x · 2.07 / 2.93 | 13.1x · 2.54 / 3.37 | 17.2x · 3.94 / 5.03 | 22.1x · 5.63 / 7.40 | 28.3x · 9.13 / 13.8 | 32.2x · 15.7 / 27.8 |
| shehbaz | long (22 s) | 5.6x · 4.25 / 4.38 | 10.1x · 4.14 / 4.77 | 14.8x · 5.98 / 6.08 | 19.6x · 8.51 / 9.00 | 26.0x · 12.3 / 12.9 | 31.8x · 17.8 / 20.3 | – |
| shehbaz | xlong (33 s) | 5.6x · 5.89 / 6.26 | 10.1x · 6.25 / 7.01 | 13.6x · 7.79 / 9.04 | 19.6x · 13.5 / 14.4 | 26.1x · 16.6 / 18.3 | 33.3x · 26.5 / 28.7 | 36.3x · 47.8 / 55.3 |

- Throughput saturates at ~31-35x for 15-60 s texts from c=32 (c=64 adds 10-15% at twice the latency); short
  sentences saturate lower (18-23x) because the per-request overhead (reference prefill, first chunk) dominates.
  Requests per second at c=32: short 5.5-7.0, medium 3.0-4.1, long 1.6-2.1.
- No preemption at any concurrency (KV cache 91,120 tokens; a 60 s take needs ~1,250). GPU utilisation 94-100% from
  c=1 on. Quality does not degrade with concurrency: WER and SIM are flat from c=1 to c=32 (P2 scores).
- shehbaz xxlong (two Urdu prompts, ~200 words) is not in the table: in the default layout 31 of 68 requests hit the
  length cap and most of the rest skipped text (§5).
- Published RTX 3090 numbers for this model on older vLLM-Omni (PR #5253, 0.25): 4.07x at c=1, 17.4x at c=64. vLLM-Omni
  0.28 on this box is ~1.3x faster at c=1 and ~2x at high concurrency.

### 4.2 Streaming (P3): time to first audio

TTFA p50 / p99 in seconds (first audio byte past the WAV header), and x realtime:

| voice, size | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| trump short | 0.116 / 0.143 · 5.0x | 0.169 / 0.191 · 7.8x | 0.358 / 0.363 · 10.2x | 0.430 / 0.660 · 12.4x | 0.807 / 1.26 · 15.6x | 1.77 / 2.47 · 18.5x |
| trump xlong | 0.118 / 0.125 · 5.6x | 0.134 / 0.197 · 10.1x | 0.353 / 0.356 · 13.2x | 0.654 / 0.659 · 17.5x | 1.24 / 1.26 · 26.5x | 2.42 / 2.44 · 33.0x |
| shehbaz short | 0.121 / 0.134 · 5.2x | 0.142 / 0.197 · 8.0x | 0.365 / 0.375 · 11.7x | 0.370 / 0.697 · 14.1x | 0.460 / 1.31 · 17.1x | 1.02 / 2.55 · 21.4x |
| shehbaz xlong | 0.122 / 0.137 · 5.6x | 0.157 / 0.216 · 6.7x | 0.354 / 0.359 · 8.3x | 0.694 / 0.711 · 19.0x | 1.25 / 1.28 · 26.1x | 2.53 / 2.58 · 32.8x |

(xxlong: trump 0.126 s at c=1, 0.639 s at c=8.) Streaming costs no throughput. Audio arrives in 2-s chunks after the
first. Per-stream RTF (total time / audio) stays below 1 for 30-60 s texts up to c=32 (p90 0.38 at c=8, 0.53 at c=16,
0.83 at c=32), so on average each stream is produced faster than it plays; for short sentences at c=32 it is 1.3-1.9
(the 1.8-2.5 s wait for the first audio dominates). Chunk-to-chunk gaps were not measured; upstream reports audible
gaps under load on 3090s (#2562), so players should buffer a chunk. A streamed take cannot be retried,
so streamed Urdu carries the per-take failure rate (§5). `non_streaming_mode=true` adds 7-36 ms to TTFA at c=1 and
~180 ms at c=8 on ~95-word Urdu (X9).

### 4.3 Voice-prompt cache (P4), short sentences

| reference | c=1 lat p50 · x | c=8 lat p50 · x | c=32 lat p50 · x | TTFA c=1 / c=8 / c=32 (streaming) |
|---|---|---|---|---|
| registered (uploaded once) | trump 0.78 · 5.1x, shehbaz 0.90 · 5.2x | 1.35 · 11.4x / 2.19 · 14.1x | 3.76 · 17.6x / 4.20 · 19.2x | – |
| inline ref_audio (cached by hash) | 0.72 · 5.0x / 1.04 · 5.1x | 1.17 · 11.7x / 2.01 · 14.0x | 3.89 · 17.3x / 4.54 · 20.3x | 0.114-0.118 / 0.32-0.50 / 2.35-2.49 |
| **cache defeated** (a new reference every request) | 0.86 · 4.6x / 1.15 · 4.8x | 1.82 · 9.4x / 2.47 · 11.4x | 6.19 · 11.5x / 7.35 · 12.8x | 0.27-0.31 / 0.66-1.45 / 6.2-7.3 |

The engine caches each reference's codec codes and speaker vector (keyed by a hash of the audio). With the cache,
registered and inline references cost the same compute (inline still sends ~2 MB per request). Without it, every
request re-encodes the reference on the GPU inside the talker step: -37% throughput at c=32 and 2.5-3x TTFA. The
gateway registers voices at startup; the qwen-tts baseline shows no cache effect because it re-decodes the reference
on every call anyway.

### 4.4 GPU memory

nvidia-smi totals of the card, including the desktop's 0.34 GB:

| configuration | idle | under load (peak) |
|---|---|---|
| prod YAML (stage 0 0.60, stage 1 0.18) | 18.8 GB | 20.4 GB (c=64, 30-60 s texts) |
| stage 0 0.45 | 15.2 GB | 16.1 GB |
| async_chunk off | 22.4 GB | 23.2 GB |
| QC sidecar (Whisper large-v3 fp16, 2 workers, both SIM models) | +6.2 GB | + ASR activations |
| qwen-tts baseline | 5.8 GB | 18.7 GB (batch 8, 60 s) |
 Startup: ~95 s (talker torch.compile 17 s, CUDA graphs), then the gateway
registers and warms up both voices in ~1.5 s.

### 4.5 Gateway overhead (P7)

Through the gateway vs engine direct, short sentences: c=1 latency p50 0.711 vs 0.712 s (trump), 1.03 vs 1.00 s
(shehbaz); c=16 x realtime 15.9 vs 15.2 (trump), 18.9 vs 19.2 (shehbaz). The gateway (auth, admission, pace check,
labels, logs) adds no measurable latency. With 1 retry at c=32 on long Urdu, one take was retried and all 64 succeeded.

## 5. Quality

### 5.1 Per voice (non-severe takes; P2, P5, X-phases)

| | English (trump) | Urdu (shehbaz) |
|---|---|---|
| WER (stock Whisper large-v3) | 0.3-1.5% | 0.34-0.38 |
| CER / CER-nospace | 0.3-0.7% | 0.14-0.18 |
| SIM WavLM base-plus-sv vs prompt | 0.96 (short) - 0.99 | 0.96 (short) - 0.98 |
| SIM WavLM-Large (seed-tts-eval) vs prompt | 0.70 (short) - 0.87 | 0.70 (short) - 0.79 (held-out clips 0.81) |
| severe failures per take | 0-2% | 1.5-4.4% up to ~70 words; 15.5% at ~95 words; 91% at ~200 words (default layout) |

For scale: the same Whisper transcribes this speaker's real recordings at WER 0.12, CER-nospace 0.037, so Qwen's Urdu
is intelligible but clearly accented; English matches the Kaggle observation (< 1% WER). WavLM-Large SIM of real
same-speaker pairs is 0.90-0.94 (cross-speaker 0.10-0.18), so the clones are recognisably the target voice but not
indistinguishable; SIM is lower on short clips for any speaker. The Kaggle "~0.97 similarity" is on the base-plus-sv
scale, where we measure 0.98. No cross-talk in mixed-voice batches (X5, both voices interleaved at c=16: 0 duplicate
outputs, and each voice's SIM-Large in the mixed batch (trump 0.68 short / 0.85 xlong, shehbaz 0.72 / 0.76) is within
noise of its single-voice runs (0.70 / 0.84, 0.70 / 0.77)).

### 5.2 Urdu failures and what fixes them

Severe failure rate per take (43 benchmark prompts of ~95 words unless noted):

| setting | takes | severe [95% CI] | moderate |
|---|---|---|---|
| default layout, rp 1.05 | 258 | 15.5% [12-20] | 16.7% |
| rp 1.10 / 1.15 / 1.20 | 258 each | 16.3% / 15.9% / 14.7% | 15.9% / 12.4% / 16.3% |
| **`non_streaming_mode=true`**, rp 1.05 | 258 | **7.7% [5-12]** | 7.7% |
| averaged speaker embedding (`shehbaz-avg`) / prompt embedding | 43 / 43 | 16.3% / 11.6% | 11.6% / 14.0% |
| length cap on / off (engine's own cap + retry) | 43 / 43 | 9.3% / 11.6% | 16.3% / 16.3% |
| **~200-word texts:** default | 43 | 93% | 5% |
| ~200 words, `non_streaming_mode=true` | 43 | 16.3% | 30.2% |
| ~200 words, split into ≤60-word parts | 43 | 23.3% | 20.9% |
| **~200 words, split + `non_streaming_mode`** | 43 | **11.6%** | 18.6% |

- The failures are the Kaggle ones, now measured: whole passages skipped (often after a repeated word such as
  "گڑھے ہی گڑھے"), unintelligible stretches at a normal duration, runaways that never emit end-of-speech, and repeated
  syllables. About 70% of them happen at a normal duration (the pace + runaway check catches 20-34%), invisible to
  any length check.
- **`non_streaming_mode=true` halves the rate** (paired by prompt: -7.7 points [0.0, 15.1] at no retry, -7.0 [1.4,
  13.5] with one) and fixes long Urdu. Cause, confirmed by X6: in the Base default layout the text beyond the reference
  is fed one token per codec frame (12.5/s); Urdu needs ~3.2 Qwen tokens per word, so the text feed barely stays ahead
  of the speech and the model loses its place; English (1.3 tokens/word) never gets close. Cost: -5% throughput, +7-180
  ms TTFA.
- **repetition_penalty 1.10-1.20 does not help** (the talker's penalty is presence-based on codebook 0 only).
- **Averaging the speaker embedding over all clips changes nothing measurable** (cosine to the prompt embedding 0.995,
  identical SIM and failure rate): the in-context reference codes carry the voice.
- **Length cap:** it does not change the failure rate but it is what keeps throughput: without it a runaway runs to
  the engine's own cap (12 frames per text token, ~3 min of audio for a long Urdu text) and holds a batch slot; X4:
  26.7x vs 8.5x realtime, p99 28 s vs 147 s.

### 5.3 Retry policy (offline simulation over K=6 takes per prompt, `results/P5_retry_study/`)

Final severe rate, mean attempts and extra compute; 95% CIs bootstrap over prompts. "Full gate" = what the QC sidecar
computes (pace + Whisper ASR + SIM + audio detectors; recall 1.0, precision 0.51-0.57 against severe); "pace gate" =
what the gateway computes without the sidecar (pace band + runaway).

| layout | gate | R=0 | R=1 | R=2 | R=3 |
|---|---|---|---|---|---|
| default, rp 1.05 | full | 15.5% | 8.8% [3.6-15.2] · 1.31 · +31% | 7.2% · 1.47 · +48% | 6.7% · +61% |
| default, rp 1.10 / 1.15 | full | 16.3% / 15.9% | 6.2% / 6.5% · +28-31% | 3.5% / 3.4% · +40-47% | 2.2% / 1.9% |
| default, rp 1.05 | pace | 15.5% | 13.6% · +3.5% | 13.5% | 13.5% |
| **`non_streaming_mode`** | pace | 7.7% | **5.8%** [2.7-9.7] · 1.02 · +2% | 5.8% | – |
| **`non_streaming_mode`** | full | 7.7% | **1.9%** [0.6-3.3] · 1.14 · +15% | **0.5%** [0-1.3] · 1.19 · +19% | 0.2% |

Failures cluster on hard prompts (21 of 43 prompts had at least one severe take in six; none had all six), so the
i.i.d. estimate f^(R+1) is far too optimistic; the simulation uses the actual takes. English needs no retries beyond
runaways (0-2% severe).

### 5.4 The online QC sidecar in practice (P8)

The full gate needs Whisper on every take. Next to a saturated engine on the same 3090 it does not keep up: at c=16 the
sidecar's ASR took p50 24 s (English) / 58 s (Urdu) per take with beam 5, 17.5 s / 41 s greedy (0.5 s on an idle GPU),
so calls timed out and throughput fell from ~25x to 10x (English) / 4-9x (Urdu); the first attempt with Whisper in
float16 next to the engine at stage-0 0.45 ran the card out of memory. The QC sidecar is therefore an option for low
load (a few concurrent requests) or a second GPU, not for peak load on one card.

## 6. vLLM-Omni vs the plain qwen-tts baseline (P9)

qwen-tts 0.1.1 (transformers 4.57.3, bf16, sdpa) behind the same request shape, one GPU worker, dynamic batching up to
8, prompt cache on:

| | qwen-tts | vLLM-Omni |
|---|---|---|
| RTF at c=1 (short / xlong) | 0.61-0.64 / 0.58 | 0.20 / 0.18 |
| x realtime c=4 (short / xlong) | 3.9-4.3x / 6.2-6.4x | 10.6-11.4x / 13.5-13.6x |
| x realtime c=8 (xlong / xxlong) | 9.9-11.0x / 11.6x | 17.9-19.6x / 20.7x |
| best aggregate | ~11-12x (batch 8) | 31-35x (c=32), 38-40x (c=64) |
| latency p50, xlong at c=16 | 40-56 s (queued behind batches of 8) | 16.4-16.6 s |
| streaming | none | TTFA 0.12 s |
| a runaway | holds its whole static batch (Urdu xxlong c=8: 153 s for every row) | occupies one slot until the length cap |
| quality | the same model: English WER 0-1.3%, the same Urdu failure modes (Urdu xlong severe 31% in one run of 16, xxlong 100% of 10) | – |

## 7. Against the team's XTTS / Auralis numbers (P6)

Auralis was **not** run here (instruction). Its numbers are the user-provided README figures for the **Pashto** model on
the same GPU model (RTX 3090), through its full proxy stack, with `benchmark_tts.py` (not these pools). Qwen3-TTS ran
the Auralis **Urdu** pools (`bench/pools/auralis_ur.json`) at Auralis's default n=20, c=20:

| | Qwen3-TTS 1.7B (this report) | Auralis/XTTS (Pashto, their numbers) |
|---|---|---|
| single request | 0.69 s for 3.4 s of audio (short pool); 2.9 s for 16 s (long pool) | 0.32 s |
| 20 concurrent, short (~3.4 s clips) | p50 3.19 s, p99 3.47 s | p50 0.52 s (~3 s clips) |
| 20 concurrent, medium (~5.9 s clips) | mean 4.69 s, p50 5.13 s, p99 5.35 s | mean 0.73 s, p99 0.90 s (~5 s clips) |
| 20 concurrent, long (~16 s clips) | p50 11.2 s, p99 12.3 s | – |
| aggregate | 17-26x realtime (19-26x wall) | ~110x realtime |
| through our gateway (n=20, c=20) | short p50 3.19 s, medium 4.87 s, long 11.2 s | full proxy stack |

Qwen3-TTS 1.7B is **4-7x slower in latency and ~4x lower in aggregate throughput** than the optimised XTTS/Auralis
stack on this GPU class. That is expected: 1.7 B parameters and 16 codebooks per 80 ms frame (1 talker + 15 code-
predictor passes) against XTTS's ~0.5 B GPT. The comparison is only indicative (different language, text lengths,
proxy stack, and their measurements). What Qwen buys is cloning quality in English; its Urdu is accented and needs the
guardrails above.

## 8. Recommended production configuration

| setting | value | why |
|---|---|---|
| engine | vLLM-Omni 0.28.0 + vllm 0.28.0 (`engine/constraints-omni28.txt`), `engine/deploy/variants/custom_voices.yaml` | fastest measured option; stable release; voices preloaded (no cold start) |
| precision | bf16 talker, fp32 Code2Wav (0.28 default) | the only working combination; the checkpoint is bf16 |
| CUDA graphs / async_chunk | on / on | 2.4-2.7x faster at low load; async_chunk off is slower, uses 4 GB more and breaks streaming |
| FlashInfer sampler | `VLLM_USE_FLASHINFER_SAMPLER=0` | its JIT does not compile with the pip toolchain here (nvcc 13.4 vs CUDA 13.0 headers) |
| stage memory | stage 0 0.60, stage 1 0.18 (0.45 if the QC sidecar shares the GPU) | KV 91k tokens: 64 concurrent 60 s takes without preemption; leaves ~3.5 GB for the desktop |
| `max_num_seqs` | 64 | above the gateway's in-flight limit; KV cache fits it |
| voice mode | `TTS_VOICE_MODE=registered` (reference uploaded once at startup) | cached like inline without 2 MB per request; the averaged embedding gave no benefit (`precomputed` + `{id}-avg` stays available) |
| language | English for trump, Auto for Urdu | X2: English vs Auto for trump made no difference; Urdu has no language id |
| sampling | temperature 0.9, top_k 50, repetition_penalty 1.05 | rp 1.10-1.20 changed nothing measurable |
| max in flight / queue | `TTS_MAX_INFLIGHT=32`, `TTS_MAX_QUEUE=128`, `TTS_QUEUE_TIMEOUT_S=60` | throughput plateau (31-35x) at 32; 64 adds 10-15% for 2x latency |
| length cap | on (pace-based, `TTS_LENGTH_CAP_HEADROOM=1.2`) | keeps runaways from holding slots (3x throughput, 5x lower p99 in X4) |
| Urdu layout | `TTS_NON_STREAMING_MODE_LANGS=ur` | halves severe Urdu failures, fixes long Urdu; -5% throughput |
| long texts | `TTS_SPLIT_WORDS=60` | long Urdu 93% → 12% severe with the above; parts run in parallel (lower latency for long English too: p50 23 → 14 s) |
| retries | `TTS_RETRY_MAX=1`, `TTS_RETRY_ON=suspect,engine_error` | catches runaways and pace outliers for +2-4% compute (Urdu severe 7.7% → 5.8%) |
| QC sidecar | off at peak load on one GPU; for low-load or quality-critical Urdu (or on a second GPU): `TTS_QC_URL`, `TTS_RETRY_MAX=2`, `TTS_RETRY_ON=suspect,engine_error,qc` | full-gate retries take Urdu to 1.9% (R=1) / 0.5% (R=2) severe, but Whisper inline costs 2-7x throughput under load on the same card |
| streaming | for interactive use (TTFA 0.12 s at c=1, < 0.7 s at c <= 8, 1.3 s at c=16); non-streaming where Urdu quality matters most (only non-streaming takes can be retried) | |
| capacity planning | ~30 simultaneous real-time streams, or 5-7 short sentences/s, per 3090 | P2/P3 |

These are the values in `deploy/env.example` and the installed units (`~/.config/qwen3-tts/env`).

## 9. Caveats

- **Shared GPU:** the 3090 also drives the desktop (0.34 GB and some GPU time during every measurement). The CPU ran
  with the `powersave` governor (EPP balance_performance); the talker step is partly host-bound, so a performance
  governor could add a little. Not changed (no root).
- **Versions:** vLLM-Omni 0.28.0 is a fast-moving project; 0.30 changes the default runner and the decoder precision.
  Re-run `bench/run_plan.py` after an upgrade.
- **Quality numbers are automatic**, from stock Whisper large-v3 and WavLM, not human listening. Whisper's own Urdu
  error is 13-26% WER on real speech, so Urdu WER mostly measures accent; the severe/moderate tiers were calibrated on
  these takes by reading transcripts, not by listening, and English "moderate" over-counts onomatopoeia in the
  prompts ("haha" → "ha ha"). A human listening pass over the flagged takes (the paths are in `scores.jsonl`) is the
  next step before trusting the absolute Urdu rates; the relative comparisons (non_streaming_mode, splitting, retries)
  use the same yardstick on the same prompts.
- **Sample sizes:** 258 takes per main Urdu setting (CIs ±4-5 points); 43 per side experiment (CIs ±8-15 points).
- **Seeds do not reproduce** on vLLM-Omni 0.28 (CUDA graphs on), so no experiment is deterministic; comparisons pair
  by prompt.
- **Not measured:** vLLM-Omni 0.30 / MRV2 (disk), SGLang-Omni, a second GPU, sustained multi-hour soak, the FlashInfer
  sampler (it does not build here), the QC sidecar on its own GPU, streaming playback gaps (chunk timing was not
  captured per chunk).
- **Auralis numbers are theirs** (Pashto, different setup), not re-measured.
- The Whisper STT servers on pb-ai-pc1 (`:8000`, `:8012`) that session 1 stopped are still down there
  (`ops/STOPPED_WHISPER_SERVERS.md`); nothing on this machine depends on them.

## 10. Reproduce

```bash
cd server
venvs/gateway/bin/python bench/run_plan.py --list                     # every phase with its estimate
venvs/gateway/bin/python bench/run_plan.py --only 'P2_matrix,P3_stream'   # the runner starts/stops the engine
eval/run.sh eval/score_run.py results/P5_urdu_nsm --device cuda --workers 2
python3 eval/failure_classes.py results/P5_urdu_nsm
eval/run.sh eval/retry_sim.py results/P5_urdu_rp105/takes_all.jsonl results/P5_urdu_nsm/takes_all.jsonl --combine results/P5_retry_study/nsm
venvs/gateway/bin/python bench/collect.py && venvs/gateway/bin/python bench/report_extract.py
```
