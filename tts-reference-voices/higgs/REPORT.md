# Higgs TTS 3 on one RTX 3090: baseline benchmark and comparison with Qwen3-TTS

Status: complete for this round (2026-09-28): baseline (B0), engine-profile screens (S1, S2), the 43-prompt quality
arms (Q1-Q4) and the gateway arms (G0-G2); 2,048 scored takes, 15 h of audio, 0 HTTP errors. `docs/EXPERIMENTS.md`
has every run; numbers come from `results/<experiment>/` (`COMPARE.md`, `QUALITY.md`, `ARMS.md`, per run
`summary.json`, per take `requests.jsonl` and `scores.jsonl`).

## 1. Summary

- **Setup:** `bosonai/higgs-tts-3-4b` (4B talker on a Qwen3-4B backbone, 8-codebook 25 fps codec, 24 kHz) served by
  the vLLM-Omni 0.28.0 already installed for Qwen3-TTS, engine direct on `/v1/audio/speech`, voice clone from the same
  reference clips as the Qwen benchmark (`voices/<id>/references/qwen3-tts.wav` + transcript; the engine only takes
  1-30 s clips, so the 39 s Higgs reference of the Kaggle runs is out). Two fixes were needed on this box: FlashAttention
  instead of the FlashInfer attention the upstream profiles pin (FlashInfer's JIT cannot build here), and a backport of
  vllm-omni PR #7065 without which every clone request is rejected (`docs/EXPERIMENTS.md` H01-H02).
- **Speed (Urdu, engine direct, upstream default profile = eager talker):** 2.5x realtime at 1 request (per-request
  RTF 0.38-0.41), 12-20x realtime at 16 in flight (max_num_seqs 16 in this profile). Qwen3-TTS on the same card:
  5.1-5.6x at 1 request (RTF 0.18-0.20) and 18-26x at 16, 31-35x at 32. **Higgs is about 2x slower per request and
  reaches ~75 % of Qwen's throughput at c=16**; a 4B model against a 1.7B one.
- **Latency:** one short Urdu sentence 2.5 s (p50) at c=1, 4.4 s at c=16; a ~30 s text 13.5 s at c=1, 24 s at c=16.
  Qwen: 1.05 / 2.7 s and 5.9 / 16.6 s.
- **Streaming time to first audio:** 0.34 s at c=1, 0.7-0.8 s at c=4, 1.1-1.3 s at c=8, 1.9-2.5 s at c=16 (Qwen: 0.12,
  0.36, 0.37-0.69, 0.46-1.25 s). Gap-free playback can start ~0.33 s after the first chunk (1 frame, then 1 s chunks).
- **Quality, the main result:** **Higgs speaks Urdu that Whisper transcribes at 1-6 % WER** on sentences and
  paragraphs up to ~65 words (CER-nospace 1-3 %), against 34-38 % for Qwen3-TTS on the same speaker (a language Qwen
  does not support), and the speaker similarity is higher (WavLM-Large 0.84-0.86 vs 0.70-0.79). English is at 0-1 %
  WER. **But Higgs drops text from long inputs:** at ~98 words (~30 s of speech) 43 % of Urdu takes and 67 % of English
  takes lose whole passages (deletion runs, WER 6-16 %), and at ~200 words every take stops after 15-20 s of audio.
  **The gateway fixes it:** split at sentence ends into ≤ 60-word parts generated in parallel, plus one retry on
  pace-suspect takes, and the same texts come out at WER 3.6 % with 0 % (100 words) / 4 % (200 words) bad takes,
  faster than unsplit (a 200-word Urdu text in 11 s at c=1) (§4.2).
- **Failures per take on ≤ 65-word texts:** Urdu 1-8 % `bad` (medium 1.4 %, long 6-8 %; short sentences 19 % but that
  is mostly the pace detector on 3 s clips, see §4), 0 errors, 2 runaways in 648 takes (a 10-word sentence that ran
  63 s, a ~30 s text that hit the 82 s cap).
- **GPU memory:** 18.3 GB peak on the card (talker 14.5 GB incl. a 6.2 GiB KV cache of 44,928 tokens, codec 0.7 GB,
  desktop 0.3 GB); Qwen 19.7-20.3 GB with its production profile.
- **Licence:** Higgs TTS 3 is research / non-commercial. Benchmarking it in-house is allowed; serving it to users
  needs a commercial licence from Boson AI (`docs/research.md`). It is therefore a candidate, not a deployment.

## 2. Setup

| item | value |
|---|---|
| machine | `vector`: 1x RTX 3090 24 GB (GPU 0, also the desktop's ~0.3 GB), driver 580.95.05 / CUDA 13.0, i9-14900K, 30 GB RAM |
| engine | vLLM-Omni 0.28.0 + vLLM 0.28.0 + torch 2.13.0 cu130 (`server/venvs/engine`), + `engine/patches/apply_pr7065.sh` |
| model | `bosonai/higgs-tts-3-4b` rev 239f63fb (9.31 GB bf16), codec `k2-fsa/OmniVoice/audio_tokenizer` (806 MB) for reference encoding |
| profile | `engine/deploy/flash_attn.yaml`: upstream `higgs_multimodal_qwen3.yaml` (stage 0 gpu_memory_utilization 0.60, `enforce_eager: true`, max_num_seqs 16, max_model_len 8192, prefix caching on; stage 1 0.25, eager; `async_chunk` with 25-frame = 1 s chunks, first chunk 1 frame) with `attention_backend: FLASH_ATTN`, no fixed seed, sampling temperature 0.8 / top_k 50 / top_p 1.0 (Boson's voice-clone recommendation), `max_tokens` 2048 frames = 82 s |
| requests | inline `ref_audio` (data URL of the 28.0 s shehbaz / 23.2 s trump clip) + `ref_text`; no `task_type`, `language`, `max_new_tokens` or seed; `response_format` wav; streaming runs `stream: true, stream_format: audio` |
| tool | `bench/bench_tts.py` (`--task-type none --language none --ref-key qwen3-tts --codec-hz 25`), 2 warm-up requests per voice, n = max(8, 2c) requests per cell, distinct texts, `bench/baseline.sh` |
| texts | `bench/pools/ur.json` / `en.json`: short = 1 sentence (~4-5 s), medium 20-45 words (~11 s), long 55-70 words (~25 s), xlong = one 43-prompt text (~35 s, 98 words Urdu / 155 English), xxlong = two prompts joined (~200 words) |
| scoring | `server/eval/score_run.py`: stock Whisper large-v3 (fp16, beam 5, language forced) WER / CER-nospace after Urdu/English normalisation; WavLM-Large + ECAPA (seed-tts-eval) and wavlm-base-plus-sv speaker similarity vs the prompt clip; pace, deletion/insertion runs, silence and word-timing detectors (`server/qc/tts_qc/policy.py`); `gate` = the production QC verdict, `bad` = the stricter offline label |

Engine start-up is 30 s (no compile). Bench-side timing is end to end over HTTP on the same machine.

## 3. Performance (engine direct, Urdu `shehbaz`)

Non-streaming, latency = whole WAV received. xRT = audio seconds finished per wall second while 90 % of the requests
were in flight; RTF = per-request compute / audio (p50). Qwen columns: `server/results/P2_matrix` (same texts, tool and
card; Qwen ran with the gateway's length cap, Higgs with the engine's 82 s cap).

| size | c | Higgs lat p50 / p90 s | Higgs xRT | Higgs RTF | Qwen lat p50 / p90 s | Qwen xRT | Qwen RTF |
|---|---|---|---|---|---|---|---|
| short (~5 s) | 1 | 2.53 / 2.67 | 2.5 | 0.41 | 1.05 / 1.22 | 5.1 | 0.20 |
| short | 4 | 3.91 / 4.19 | 4.2 | 0.50 | 1.48 / 1.84 | 11.4 | 0.30 |
| short | 8 | 2.71 / 5.92 | 9.2 | 0.72 | 1.82 / 2.69 | 13.7 | 0.50 |
| short | 16 | 4.35 / 7.53 | 12.0 | 1.14 | 2.68 / 4.79 | 17.8 | 0.75 |
| medium (~11 s) | 1 | 4.84 / 5.95 | 2.5 | 0.39 | 2.27 / 2.59 | 5.4 | 0.19 |
| medium | 4 | 5.02 / 5.54 | 7.6 | 0.48 | 2.54 / 3.00 | 13.1 | 0.28 |
| medium | 8 | 5.93 / 7.87 | 12.3 | 0.58 | 3.94 / 4.92 | 17.2 | 0.42 |
| medium | 16 | 7.85 / 10.03 | 17.6 | 0.82 | 5.63 / 7.00 | 22.1 | 0.61 |
| long (~25 s) | 1 | 9.75 / 10.32 | 2.6 | 0.38 | 4.25 / 4.38 | 5.6 | 0.18 |
| long | 4 | 11.50 / 14.02 | 7.8 | 0.45 | 5.98 / 6.08 | 14.8 | 0.26 |
| long | 8 | 13.39 / 14.92 | 13.0 | 0.54 | 8.51 / 8.91 | 19.6 | 0.38 |
| long | 16 | 18.17 / 20.23 | 19.4 | 0.72 | 12.28 / 12.72 | 26.0 | 0.54 |
| xlong (~35 s) | 1 | 13.45 / 14.05 | 2.6 | 0.38 | 5.89 / 6.23 | 5.6 | 0.18 |
| xlong | 4 | 16.09 / 17.13 | 6.3 | 0.46 | 7.79 / 8.92 | 13.6 | 0.25 |
| xlong | 8 | 18.71 / 21.72 | 13.3 | 0.54 | 13.48 / 13.82 | 19.6 | 0.38 |
| xlong | 16 | 23.89 / 27.73 | 19.6 | 0.73 | 16.61 / 18.00 | 26.1 | 0.53 |
| xxlong (~200 words) | 1-16 | 6.6-15.0 (p50) | 2.5-14.7 | 0.40-0.85 | 7.3-27.3 | 2.2-12.1 | 0.19-0.51 |

The xxlong rows are not comparable: Higgs stops after 15-20 s of audio (§4), Qwen's default layout fails 93 % of these
texts. c=2 rows and the c=32/64 Qwen rows are in `results/B0_baseline_flash_attn/COMPARE.md`. The c=16 short row
carries one 63 s runaway (p99 25 s at c=4 likewise).

Streaming (`stream_format: audio`, WAV): TTFA = first audio byte after the header; "gapless start" = the earliest
point from which playback would never stall.

| size | c | Higgs TTFA p50 / p90 s | Higgs gapless start p50 s | Higgs xRT | Qwen TTFA p50 / p90 s |
|---|---|---|---|---|---|
| short | 1 | 0.34 / 0.34 | 0.67 | 2.4 | 0.12 / 0.12 |
| short | 4 | 0.68 / 0.70 | 1.05 | 5.8 | 0.37 / 0.37 |
| short | 8 | 1.10 / 1.14 | 1.51 | 9.6 | 0.37 / 0.70 |
| short | 16 | 1.93 / 2.01 | 2.43 | 12.6 | 0.46 / 1.30 |
| long | 1 | 0.34 / 0.37 | 0.68 | 2.6 | - |
| long | 4 | 0.79 / 0.81 | 1.17 | 8.0 | - |
| long | 8 | 1.26 / 1.31 | 1.68 | 13.4 | - |
| long | 16 | 2.25 / 2.34 | 2.7 | 19.0 | - |
| xlong | 1 | 0.38 / 0.39 | 0.71 | 2.6 | 0.12 / 0.14 |
| xlong | 4 | 0.82 / 0.84 | 1.2 | 8.3 | 0.35 / 0.36 |
| xlong | 8 | 1.34 / 1.40 | 1.8 | 13.4 | 0.69 / 0.70 |
| xlong | 16 | 2.48 / 2.59 | 2.9 | 19.0 | 1.25 / 1.27 |

TTFA grows almost linearly with the number of requests in flight (each new request's prefill of a ~750-token
reference + text waits behind the running decodes; the eager talker has no decode graph). English (`trump`): short
c=1 1.68 s p50, xlong c=1 12.2 s, c=8 15.7 s (14.6x realtime); streaming TTFA 0.31 s at c=1, 0.9-1.0 s at c=8.

### 3.1 Engine profiles (S1, S2)

The upstream Higgs profiles offer two talker graph paths, mutually exclusive: the default keeps the talker eager with
Higgs' own local MLP CUDA graph; the "low latency" profile captures vLLM FULL_DECODE_ONLY graphs. On this stack the
second fails at capture (`cudaErrorStreamCaptureUnsupported`, S1a), and vLLM's PIECEWISE graphs (S1, `piecewise.yaml`)
are slower than eager, because they switch the local MLP graph off without replacing it (torch.compile is disabled
by the model's config):

| shehbaz, non-streaming | eager (B0) lat p50 s / xRT | piecewise (S1) lat p50 s / xRT |
|---|---|---|
| short c=1 / c=16 | 2.53 / 2.5, 4.35 / 12.0 | 3.50 / 1.5, 6.01 / 10.2 |
| long c=1 / c=16 | 9.75 / 2.6, 18.17 / 19.4 | 15.65 / 1.6, 21.23 / 17.4 |

So the eager talker is the fastest Higgs talker available here, and its per-step cost sets the c=1 speed (RTF 0.4).

The default profile reserves 60 % of the card for the talker (KV cache 44,928 tokens) and 25 % for the codec decoder,
which only uses 0.7 GB. `mem080_seqs32.yaml` moves the split to 0.80 / 0.08 (KV 79,232 tokens) and allows 32
requests in flight (S2, `results/S2_mem080_seqs32`):

| shehbaz | c | lat p50 / p90 / p99 s | xRT | req/s | suspects | GPU peak MiB | Qwen at the same c |
|---|---|---|---|---|---|---|---|
| short | 16 | 4.57 / 6.97 / 16.6 | 13.4 | 1.43 | 2 | 23,090 | 17.8 |
| short | 32 | 7.18 / 11.50 / 13.2 | 16.2 | 3.44 | 5 | 23,211 | 21.4 |
| long | 16 | 17.73 / 21.00 / 22.9 | 19.6 | 0.84 | 0 | 23,386 | 26.0 |
| long | 32 | 22.34 / 24.83 / 26.6 | 31.4 | 1.27 | 0 | 23,388 | 31.8 |
| xlong | 16 | 23.23 / 27.66 / 33.8 | 19.5 | 0.58 | 0 | 23,522 | 26.1 |
| xlong | 32 | 31.02 / 34.91 / 41.8 | 28.8 | 0.78 | 5 | 23,524 | 33.3 |
| xlong stream | 16 / 32 | TTFA p50 2.55 / 1.98 s | 19.4 / 30.3 | | 0 / 4 | | TTFA 1.25 / 2.53 |
| trump xlong | 32 | 26.42 / 30.14 / 32.4 | 31.6 | 1.11 | 1 | 23,504 | 33.9 |

At 32 in flight Higgs matches Qwen's throughput on 25 s texts (31 x realtime) and reaches 29-32 x on 30 s texts, at
22-31 s p50 latency and with the card full (23.5 GB peak, desktop included): 32 is this GPU's ceiling for Higgs.
Between c=16 and c=32 latency grows 25-55 % while throughput grows 45-60 %, so c=16 (19-20 x, 18-23 s p50 on long
texts) is the better production point unless queue depth matters more than latency.

## 4. Quality (`results/B0_baseline_flash_attn/QUALITY.md`)

| voice | size | takes | WER | CER-ns | SIM-L | SIM-B | pace | gate fail | bad | leading bad reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| shehbaz (ur) | short | 136 | 0.089 | 0.057 | 0.72 | 0.954 | 1.34 | 7.4 % | 19.1 % [13, 27] | pace 17, char_ratio 10, cer 5, long_word 3 |
| shehbaz | medium | 72 | 0.034 | 0.011 | 0.84 | 0.979 | 1.18 | 0.0 % | 1.4 % [0, 7] | pace 1 |
| shehbaz | long | 136 | 0.052 | 0.025 | 0.85 | 0.976 | 1.15 | 5.9 % | 6.6 % [4, 12] | del_run 4, pause 3, char_ratio 3, pace 2 |
| shehbaz | xlong | 136 | 0.142 | 0.113 | 0.86 | 0.978 | 0.96 | 39.0 % | 43.4 % [35, 52] | del_run 53, char_ratio 40, cer 18 |
| shehbaz | xxlong | 72 | 0.832 | 0.813 | 0.82 | 0.973 | 0.26 | 100 % | 100 % | every take truncated |
| trump (en) | short | 48 | 0.004 | 0.003 | 0.70 | 0.958 | 1.28 | 4.2 % | 14.6 % [7, 27] | pace 6, wer 1 |
| trump | xlong | 48 | 0.064 | 0.062 | 0.83 | 0.982 | 0.96 | 66.7 % | 66.7 % [53, 78] | del_run 31, wer 9, char_ratio 6 |
| all | | 648 | 0.161 | 0.137 | 0.81 | 0.971 | 1.05 | 27.3 % | 31.8 % | del_run 160, char_ratio 131, pace 109 |

Streaming and non-streaming takes score the same (Urdu long: WER 0.047 vs 0.058; xlong 0.128 vs 0.158; both within
noise). For scale: Whisper transcribes this speaker's *real* recordings at WER 0.12 / CER-nospace 0.037, and Qwen3-TTS
takes at WER 0.34-0.38 / CER-nospace 0.14-0.18 with SIM-L 0.70-0.79 (`server/REPORT.md` §5.1). Real same-speaker
recordings score SIM-L 0.90-0.94, different speakers 0.10-0.18.

What the failures are:

- **Text dropped from long inputs** (the dominant failure): `del_run` (a run of ≥ 6 consecutive words missing from the
  transcript) and `char_ratio < 0.88` (the transcript is shorter than the text). At 98 Urdu words it hits 43 % of
  takes, at 155 English words 67 %, and at ~200 words all of them: the model reaches a stop after ~15-20 s regardless
  of the text (pace ratio 0.17-0.33). The model card's benchmarks are sentence-level (Seed-TTS, CommonVoice), and
  Boson's recommended `max_new_tokens 1024` (41 s) suggests the same envelope. The remedy is the same as for Qwen's
  long-Urdu failures: split at sentence ends into parts of ≤ 60 words and generate the parts in parallel
  (`TTS_SPLIT_WORDS` in the gateway); to be measured in the next phase.
- **Short sentences flagged for pace** (17 of the 26 short `bad` takes): a 3-5 s take at 1.5-2x the calibrated pace.
  The pace calibration (`server/calibration/pace.json`, 0.088 s/letter for shehbaz) was fitted on Qwen; Higgs speaks
  this voice 15-35 % slower on average (pace ratio 1.15-1.35 on short/medium/long), so short takes with a natural pause
  cross the 1.5x line. These transcribe fine (short Urdu WER 0.089 overall, 0.02-0.05 on the c=1/c=2 runs). Recalibrating
  the pace for Higgs is part of the next phase; until then the short-text `bad` rate is overstated.
- **Runaways:** 2 of 648 takes (0.3 %): a 10-word sentence generating 63 s (1,591 frames) and a 98-word text hitting
  the 2,048-frame cap. The engine's own cap (82 s) and a length cap from the text (the gateway's `max_new_tokens`, at
  25 fps) bound the cost; a retry replaces them.
- **Pauses / silence:** `pause > 2 s` inside a take on 3 long takes; no leading-silence, no wrong-voice takes
  (SIM-L never below 0.5; the wrong-voice case Qwen showed at ~1 % did not occur).

### 4.1 The 43 benchmark prompts: sampling, reference clip, control tags (Q1-Q4, `results/Q_prompts`)

Two takes per prompt at c=8 (86 takes per arm), the same texts the Qwen benchmark used (Urdu 71-130 words, English
91-160 words), scored the same way. Speed was identical across arms (14.3-15.4 x realtime, lat p50 15-18 s).

| arm | voice | WER | CER-ns | SIM-L | pace | bad takes (95 % CI) | what fails |
|---|---|---|---|---|---|---|---|
| Q1 temperature 0.8 / top_k 50, Qwen clip (the baseline config) | shehbaz | 0.146 | 0.114 | 0.85 | 0.96 | 38.4 % [29, 49] | deletion runs, short transcripts |
| Q1 | trump | 0.088 | 0.082 | 0.83 | 0.96 | 66.3 % [56, 75] | deletion runs |
| Q2 temperature 1.0 / top_p 0.95 / top_k 50 (upstream default) | shehbaz | 0.232 | 0.195 | 0.86 | 0.86 | 55.8 % [45, 66] | more deletions, faster pace |
| Q3 the 25 s Higgs-style reference (`higgs-v3-25s`) | shehbaz | 0.166 | 0.135 | 0.86 | 0.96 | 51.2 % [41, 61] | deletions |
| Q4 expressive set, plain text | shehbaz | 0.193 | 0.162 | 0.86 | 0.90 | 46.5 % [36, 57] | deletions |
| Q4 expressive set, the 43 control tags in the text | shehbaz | (re-scored against the plain words; see `docs/EXPERIMENTS.md`) | | | | | |

- **Failure is a function of text length.** Q1 Urdu: <= 90 words 14 % bad, 91-110 words 41 %, > 110 words 100 %;
  English: 91-110 words 57 %, 111-130 69 %, > 130 100 %. Bad takes are shorter than good ones (median 30 s vs 35 s)
  with a fifth of the text missing (char ratio 0.81): the model ends early rather than looping. Of the 43 Urdu
  prompts, 9 failed both takes, 15 one take, 19 neither, so one retry recovers ~60 % of the failures at this length;
  keeping parts under ~60 words (1-7 % bad in the baseline) removes most of them (§4.2).
- **Sampling:** Boson's 0.8 / 50 beats upstream's 1.0 / 0.95 by 17 points of bad rate and 9 points of WER; the hotter
  sampling drops more text. Kept.
- **Reference clip:** the Qwen benchmark's 28 s clip (three shehbaz clips) beats the livelier 25 s Higgs-style clip
  by 13 points at equal speaker similarity, so the Kaggle finding that the livelier reference wins does not carry over
  here. Kept `qwen3-tts`.
- **Control tags** (`<|emotion:...|>`, `<|prosody:...|>`, `<|style:...|>`, `<|sfx:...|>` in the text): the tagged
  texts come out as the plain words, transcribed like the plain arm, so tags do not break Urdu speech on this engine;
  whether the requested emotion or style is audible needs listening (`samples/` will carry a pair).

### 4.2 Long texts through the gateway: splitting and retries (G0-G2, `results/G_gateway`)

The repo's gateway in front of the Higgs engine (`engine/run_gateway.sh`; voices registered once, Higgs pace
calibration, caps at 25 fps), three arms on the ~100-word (xlong) and ~200-word (xxlong) texts, c=1 and c=8, 240
takes. The arms drew different texts from the pools, so differences of a few takes between G1 and G2 are noise; the
unsplit-vs-split contrast is not.

| arm | Urdu 100 words: WER / bad | Urdu 200 words: WER / bad | English 155 words: WER / bad | Urdu 100 w c=1 lat p50 | Urdu 200 w c=1 lat / xRT | Urdu 200 w c=8 lat / xRT |
|---|---|---|---|---|---|---|
| G0 as is (no split, no retry) | 0.275 / 71 % | 0.784 / 100 % (stops at 15-20 s) | 0.039 / 44 % | 12.96 s | 11.05 s / 2.5 (truncated) | 13.39 s / 10.1 (truncated) |
| G1 split at 60 words | 0.071 / 25 % | 0.093 / 46 % | 0.003 / 0 % | 9.60 s | 11.03 s / 7.7 | 22.12 s / 25.9 |
| G2 split + 1 retry on pace-suspect / engine-error takes | **0.036 / 0 %** | **0.036 / 4 %** | 0.004 / 6 % | 9.38 s | 10.93 s / 7.5 | 23.43 s / 25.7 |

Splitting makes long texts both correct and faster (the parts run in parallel on free slots: a 200-word text is one
request of 11 s at c=1, 7.5 x realtime); the retry cleans up the parts that still drop words (1 retry in 16 requests
at c=8). Streaming through the gateway (xlong c=8): TTFA 1.19-1.35 s, WER 0.030-0.036, 0 % bad with splitting. The
gateway's own overhead is not measurable next to the engine (12.96 s vs 13.45 s engine direct at c=1).

## 5. Against Qwen3-TTS: what the numbers say

| | Higgs TTS 3 (4B) | Qwen3-TTS 1.7B-Base | note |
|---|---|---|---|
| Urdu intelligibility (WER, Whisper) | **1-6 %** on ≤ 65 words | 34-38 % | Urdu is a supported, "production-quality" language for Higgs; unsupported for Qwen |
| speaker similarity (WavLM-L / base) | **0.84-0.86 / 0.98** | 0.70-0.79 / 0.96-0.98 | both recognisably the speaker |
| English WER | 0-1 % | 0.3-1.5 % | equal |
| long inputs (≥ ~100 words) | drops passages; stops at ~15-20 s for ~200 words; **0-4 % bad, WER 0.036 through the gateway (split 60 + retry)** | 15.5 % / 93 % severe failures without `non_streaming_mode`; 7.7 % / 12 % with it and splitting | both need splitting; Higgs ends up far cleaner |
| per-request speed at c=1 | RTF 0.40 (2.5x) | RTF 0.19 (5x) | Higgs ~2x slower |
| throughput at c=16 / max | 12-20x / (max_num_seqs 16) | 18-26x / 31-35x at c=32-64 | Higgs ~75 % of Qwen at c=16 |
| streaming TTFA at c=1 / c=8 | 0.34 s / 1.1-1.3 s | 0.12 s / 0.4-0.7 s | |
| GPU memory | 18.3 GB peak | 19.7-20.3 GB | |
| engine issues on this box | FlashInfer JIT, PR #7065 needed, no FULL_DECODE CUDA graphs (capture fails) | FlashInfer sampler JIT | |
| licence | research / non-commercial | Apache-2.0 | production use of Higgs needs Boson's commercial licence |

## 6. Recommended configuration for Higgs TTS 3 on this card (benchmark use)

Everything below is what the measurements picked; the licence still decides whether it can be served at all.

| knob | choice | evidence |
|---|---|---|
| engine | vLLM-Omni 0.28.0 + `engine/patches/apply_pr7065.sh`, `engine/deploy/mem080_seqs32.yaml` (FLASH_ATTN, eager talker with its local MLP graph, stage-0 memory 0.80 = 79k-token KV cache, stage-1 0.08, `max_num_seqs` 32) | FlashInfer JIT fails here (H01); FULL_DECODE graphs fail to capture (S1a); piecewise graphs are slower (S1); the codec decoder uses 0.7 GB of its 25 % reservation (H02); 32 in flight needs the bigger KV (S2) |
| concurrency | 16 in flight for latency (18-23 s p50 on 25-30 s texts, 19-20 x realtime), 32 for throughput (29-32 x, 22-31 s p50); never more (the card is full at 32) | S2 |
| sampling | temperature 0.8, top_k 50, top_p 1.0, no fixed seed | Q2: 1.0 / 0.95 drops more text (+17 points bad, +9 WER points) |
| reference | the 28 s three-clip `references/qwen3-tts.wav` + transcript, registered once with the engine | Q3: the livelier 25 s clip loses 13 points; 1-30 s is the engine's limit |
| text length | split at sentence ends into parts of <= 60 words, generated in parallel and joined (`TTS_SPLIT_WORDS=60`) | baseline: 1-7 % bad up to ~65 words vs 41-100 % beyond 90; G1/G2: ~100- and ~200-word texts at WER 0.04-0.09, faster than unsplit |
| guardrail and retries | the gateway's pace band (0.6-1.8 x of `higgs/calibration/pace.json`: 0.122 s/letter shehbaz, 0.081 trump) and `max_new_tokens` from the text at 25 fps; 1 retry on pace-suspect takes and engine errors (`TTS_RETRY_MAX=1`) | G2: WER 0.036, 0-4 % bad on 100-200-word Urdu texts; Q1: a second take recovers ~60 % of failed prompts; runaways 0.3 % of takes (B0) |
| streaming | `stream_format: audio`, WAV or PCM; expect TTFA 0.34 s alone, ~1.2 s at 8 in flight, ~2 s at 16-32 | B0, S2, G1 |
| language field | none (Higgs detects Urdu / English itself); `task_type` none | engine source (`docs/research.md`) |

Against Qwen3-TTS with its production configuration (§5): Higgs is the better *Urdu* engine by a wide margin
(WER 3-6 % vs 34-38 % on paragraph-length texts, higher speaker similarity) at about half the per-request speed, the
same throughput at 32 in flight, 2-3 x the streaming start latency, and a licence that requires a commercial
agreement for production.

## 7. Caveats

- One card shared with the desktop; Higgs ran alone on the GPU (the Qwen units were stopped). Bench, engine and desktop
  share the CPU.
- The upstream profiles pin FlashInfer attention; FlashAttention-2 was used instead. Upstream's FULL_DECODE_ONLY
  CUDA-graph profile fails to capture on this stack (`cudaErrorStreamCaptureUnsupported`), so the baseline talker is
  eager; the piecewise-graph variant is being screened. SGLang-Omni (Boson's reference stack, with CUDA graphs and
  radix-cached references) was not built (~30 GB of disk would be needed for a second CUDA stack; 2.9 GB were free).
- Pace calibration is Qwen's; the short-text `bad` rate for Higgs is inflated by it (§4).
- Reference clips are the Qwen benchmark's 23-28 s clips (the engine limit is 30 s). Boson recommends supplying the
  transcript, which was done. A shorter, livelier reference is a pending A/B.
- The gateway arms drew different text windows from the pools; their per-arm rates rest on 16-24 takes each.
- Control tags were measured only by ASR / similarity (they cost quality on this engine); whether they render the
  intended emotion or style was not judged by listening.
- Whisper's Urdu WER floor on real speech is ~12 % for this speaker; the 1-6 % measured on Higgs takes means Whisper
  finds the clone *easier* to transcribe than the real recordings (clean studio-like output), not that it is
  indistinguishable from the speaker.

## 8. Reproduce

```bash
hf download bosonai/higgs-tts-3-4b && hf download k2-fsa/OmniVoice --include "audio_tokenizer/*"
higgs/engine/patches/apply_pr7065.sh                                   # once, on server/venvs/engine
XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user stop qwen3-tts-engine-watchdog qwen3-tts-gateway qwen3-tts-qc qwen3-tts-engine
higgs/engine/run_higgs.sh higgs/engine/deploy/flash_attn.yaml 8095     # engine, ~30 s to ready
HIGGS_DEPLOY=flash_attn.yaml higgs/bench/baseline.sh higgs/results/B0_baseline_flash_attn
server/eval/run.sh server/eval/score_run.py higgs/results/B0_baseline_flash_attn --device cuda --workers 4
python3 higgs/bench/compare.py higgs/results/B0_baseline_flash_attn    # COMPARE.md vs the Qwen matrix
python3 higgs/bench/quality_table.py higgs/results/B0_baseline_flash_attn
python3 higgs/bench/pick_samples.py higgs/results/B0_baseline_flash_attn   # samples/higgs-tts-3 (labelled WAVs)
```
