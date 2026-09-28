# Higgs TTS 3 experiment log

Machine `vector`: 1x RTX 3090 24 GB (GPU 0, also the desktop's), driver 580.95.05 / CUDA 13.0, i9-14900K, 30 GB RAM,
Ubuntu 25.04. Engine: vLLM-Omni 0.28.0 + vLLM 0.28.0 + torch 2.13.0 cu130 (`server/venvs/engine`, the Qwen3-TTS
venv). Model `bosonai/higgs-tts-3-4b` (HF rev 239f63fb), codec `k2-fsa/OmniVoice/audio_tokenizer`. Every run keeps
its audio, `requests.jsonl` and `summary.json` under `higgs/results/<experiment>/<run>/`; the numbers of a run are in
its `summary.json`, the per-request rows (latency, time to first audio, audio seconds, pace, headers) in
`requests.jsonl`. Times are Asia/Karachi.

| id | what | result |
|---|---|---|
| H00 | setup | weights + codec cached, launcher, bench flags, deploy variants |
| H01 | first start, upstream profile (FLASHINFER attention) | FAILED: FlashInfer JIT (nvcc 13.4 vs CUDA 13.0 headers), same root cause as the Qwen sampler |
| H02 | start with FLASH_ATTN; first clone requests | engine up in 30 s; plain TTS ok; every clone request HTTP 400 "Token id -100 is out of vocabulary" (vllm-omni #6837) |
| H03 | backport of PR #7065; smoke | clone works: c=1 RTF ~0.4, TTFA 0.22 s, Urdu WER 5 % / English 0 %, SIM-L 0.77 |
| B0 | baseline, `flash_attn.yaml` (upstream default profile) | 648 takes, 3.5 h audio, 0 errors: Urdu 2.5x realtime at c=1, 12-20x at c=16, TTFA 0.34 s; Urdu WER 1-6 % up to ~65 words, SIM-L 0.84-0.86; 43 % of ~100-word and 100 % of ~200-word texts truncated |
| S1a | `low_latency.yaml` / `low_latency_fa.yaml` (FULL_DECODE_ONLY CUDA graphs) | FAILED: FlashInfer JIT; then `cudaErrorStreamCaptureUnsupported` during graph capture |
| S1 | `piecewise.yaml` (PIECEWISE CUDA graphs, FLASH_ATTN) | SLOWER than eager: c=1 1.5x vs 2.5x realtime, c=16 17x vs 19x (8 runs, stopped early) |
| S2 | `mem080_seqs32.yaml` (stage-0 0.80 -> KV 79,232 tokens, max_num_seqs 32) | c=32: short 17x, long 32.7x, xlong 26.4x realtime; GPU 23.5 GB peak |
| Q1-Q4 | the 43 prompts per voice, K=2 takes, c=8: sampling 0.8 vs 1.0, Qwen clip vs 25 s Higgs clip, expressive set plain vs tags | 0.8/50 wins (38 % vs 56 % bad), Qwen clip wins (38 % vs 51 %); failure = text length (Urdu <= 90 words 14 %, 91-110 41 %, > 110 100 %); tags: re-scoring |
| G0-G2 | gateway: no split / split 60 words / split + 1 pace retry, on ~100- and ~200-word texts | unsplit 71 % / 100 % bad -> split 25 % / 46 % -> split + retry 0 % / 4 % (Urdu WER 0.036); latency down too (parallel parts) |

## H00 setup (2026-09-28 17:3x-18:xx)

- Disk was 3.4 GB free: purged `~/.cache/pip` (8.2 GB, an HTTP cache) and the Qwen engine's torch.compile cache
  (`~/.cache/vllm/torch_compile_cache`, 1.4 GB, rebuilt at its next start). Weights 9.3 GB + codec 0.8 GB leave ~3 GB.
- The HF xet download stalled at 3.0 GB after ~8 min (0 B/s); restarted with `HF_HUB_DISABLE_XET=1` at ~11 MB/s.
- Engine venv reused as is (Higgs support is built into vllm-omni 0.28.0, `higgs/docs/research.md`). Changes:
  `server/engine/run_engine.sh` no longer insists on Qwen's `speech_tokenizer/` files for a non-Qwen checkpoint;
  `higgs/engine/run_higgs.sh` wraps it (model, codec path, DeepGEMM off, port 8095); `bench/bench_tts.py` gained
  `--task-type`, `--ref-key`, `--codec-hz`, `--engine-label` so the same tool drives both engines.
- Deploy YAMLs `higgs/engine/deploy/{base,low_latency,flash_attn,seqs64}.yaml` from the upstream profiles (seed
  removed, Boson's cloning sampling).

## H01 first start: upstream `base.yaml` (`logs/engine_base.log`)

Stage 0 initialises, then FlashInfer JIT-compiles `batch_prefill_with_kv_cache_dtype_q_bf16..._head_dim_qk_128` for
sm_86 and nvcc fails: `cuda/std/__cccl/cuda_toolkit.h:41: #error "CUDA compiler and CUDA toolkit headers are
incompatible"` (pip nvidia-cuda-nvcc 13.4.92 vs the CUDA 13.0 runtime headers this venv's torch pins; the Qwen engine
hit the same wall in its sampler, `server/docs/EXPERIMENTS.md` E00a). The Higgs profiles pin `attention_backend:
FLASHINFER` (upstream's Hopper XQA workaround), which the Qwen profiles never needed. Engine core init failed, no
model on the GPU. Fix: `flash_attn.yaml` (stage-0 `attention_backend: FLASH_ATTN`, vLLM's FlashAttention-2 on
Ampere, nothing JIT-compiled). Upstream's XQA argument does not apply to sm_86 (no TRT-LLM XQA kernel there).

## H02 `flash_attn.yaml`: engine up, cloning broken (`logs/engine_flash_attn.log`, `results/00_smoke` first attempt)

| item | value |
|---|---|
| start to `Application startup complete` | 30 s (no compile: both stages `enforce_eager`) |
| stage 0 weights | 7.61 GiB ("Model loading took 7.61 GiB memory and 1.5 s") |
| stage 0 KV cache | 6.17 GiB = **44,928 tokens**, "maximum concurrency for 8,192 tokens per request: 5.48x" |
| stage 1 | 0.04 GiB model memory; 730 MiB process; the 0.25 reservation is mostly unused |
| card total | 15.5 GB idle (stage 0 14.5 GB + stage 1 0.7 GB + desktop 0.3 GB) |
| plain TTS (no reference), English sentence | HTTP 200, 4.8 s of audio in 3.84 s |
| voice clone (ref_audio + ref_text) | HTTP 400 `Speech generation failed: Token id -100 is out of vocabulary`, both voices, stream and non-stream |

Cause: vllm-omni 0.28.0's Higgs prompt builder puts `-100` sentinels where the reference-audio embeddings go, and
vLLM 0.28.0's input processor rejects negative token ids (`vllm/v1/engine/input_processor.py:499`). Upstream issue
#6837, fixed after the release by PR #7065 (the sentinels become the `<|tts|>` id and their positions travel in
`additional_information["audio_placeholder_positions"]`; the talker substitutes the embeddings at those positions).
Backported with `higgs/engine/patches/apply_pr7065.sh` (the PR's three package files apply to 0.28.0 at an offset
of 20 lines; note the first attempt with `git apply` inside this checkout reported success without touching the venv,
so the script uses GNU patch and verifies).

## H03 smoke on the patched engine (`results/00_smoke`, 2026-09-28 18:21)

`flash_attn.yaml` (upstream sampling replaced by 0.8 / 50 / 1.0, no seed), engine direct, inline reference
(`references/qwen3-tts.wav` + transcript), short sentences, c=1, n=3 per voice, 1 warm-up each.

| run | ok | lat p50 / p90 s | TTFA p50 s | gapless start p50 s | audio s/req | x realtime | pace ratio p50 | GPU peak MiB |
|---|---|---|---|---|---|---|---|---|
| shehbaz short non-stream | 3/3 | 1.64 / 2.76 | - | - | 4.7 | 2.35 | 1.13 | 17,818 |
| trump short non-stream | 3/3 | 1.52 / 2.48 | - | - | 4.3 | 2.35 | 0.98 | 17,818 |
| shehbaz short stream | 3/3 | 1.69 / 3.01 | 0.227 | 0.555 | 5.1 | 2.51 | 1.07 | 17,818 |
| trump short stream | 3/3 | 1.69 / 2.57 | 0.220 | 0.546 | 4.6 | 2.50 | 1.10 | 17,818 |

Per-request RTF 0.40-0.45 at c=1 (Qwen3-TTS on this card: 0.19-0.21, `server/results/00_first_engine_smoke`).
Output token counts confirm 25 frames per second of audio. TTFA 0.22 s vs Qwen's 0.12 s; the first chunk is one
40 ms frame, then 1 s chunks, so a gap-free playback could start at 0.55 s (bench `play_start`).

Quality (`results/00_smoke/scores_summary.md`; Whisper large-v3 int8 on CPU, forced language, WavLM-large + ECAPA
SIM vs the prompt clip, wavlm-base-plus-sv as the secondary): English WER 0.000 on 6 takes; Urdu corpus WER 0.053,
CER-nospace 0.016 on 6 takes (the only edit: بہنو/بھائیو transcribed with the plural-vocative ں, a spelling
variant); SIM-large 0.77 (shehbaz 0.76, trump 0.78), SIM-base 0.956; gate fail 0/12, bad 0/12. For scale, the Qwen3-TTS
takes of this speaker score WER 0.34-0.38 in Urdu (accented) at SIM-large 0.70 (short) - 0.79 (`server/REPORT.md`
§5.1), and Whisper transcribes the speaker's real recordings at WER 0.12.

## B0 baseline (`results/B0_baseline_flash_attn`, 18:23-18:51, scored 19:01 on the GPU)

`higgs/bench/baseline.sh` on `flash_attn.yaml`: shehbaz short/medium/long/xlong/xxlong x c=1,2,4,8,16 non-streaming;
shehbaz short/long/xlong x c=1,4,8,16 streaming; trump short/xlong x c=1,8 both ways. 45 runs, 648 takes, 3.49 h of
audio, 0 HTTP errors, 83 pace-suspect takes (72 of them the xxlong truncations). Full tables: `COMPARE.md` (against
the Qwen matrix), `QUALITY.md`, and `REPORT.md` §3-4. Headlines: Urdu 2.5x realtime at c=1 (RTF 0.38-0.41), 12-20x at
c=16; TTFA 0.34 s at c=1, 1.9-2.5 s at c=16; GPU peak 18.3 GB; Urdu WER 0.034-0.052 on medium/long texts (SIM-L
0.84-0.86), 0.14 on ~98-word texts (43 % `bad`, mostly deletion runs), 0.83 on ~200-word texts (every take stops at
15-20 s); English WER 0.004 short, 0.064 on 155-word texts (67 % `bad`, deletions). Two runaways in 648 takes. Scoring
took 9.5 min on the GPU (engine stopped meanwhile). Samples: `samples/higgs-tts-3/` (26 labelled WAVs, best / mid /
worst per voice, political texts skipped).

## S1a low-latency profile: two failures (`logs/engine_low_latency.log`, `logs/engine_low_latency_fa.log`)

Upstream's `higgs_multimodal_qwen3_low_latency.yaml` (stage 0 `enforce_eager: false`, `cudagraph_mode:
FULL_DECODE_ONLY`, capture sizes 1-16) first died in FlashInfer's JIT like H01; with FLASH_ATTN it loaded the model
(same 44,928-token KV cache) and died while capturing the first decode graph: `torch.AcceleratorError: CUDA error:
operation not permitted when stream is capturing (cudaErrorStreamCaptureUnsupported)` inside
`gpu_model_runner.capture_model`, so something in the Higgs talker's decode step (upstream calls this graph path
experimental) issues a non-capturable call on this stack. Not pursued further today.

## S1 `piecewise.yaml` (vLLM's default PIECEWISE graphs, FLASH_ATTN)

Starts: "Capturing CUDA graphs (mixed prefill-decode, PIECEWISE) 5/5, finished in 1 s, 0.02 GiB"; "Inductor
compilation was disabled by user settings" (the Higgs config turns torch.compile off, so the piecewise graphs wrap
uncompiled ops). Plain TTS smoke ok. Screen `results/S1_piecewise`, stopped after 8 runs because the trend was clear:

| run (shehbaz) | piecewise lat p50 s | piecewise xRT | eager (B0) lat p50 s | eager xRT |
|---|---|---|---|---|
| short c=1 | 3.50 | 1.5 | 2.53 | 2.5 |
| short c=4 | 3.36 | 3.2 | 3.91 | 4.2 |
| short c=8 | 5.55 | 7.6 | 2.71 | 9.2 |
| short c=16 | 6.01 | 10.2 | 4.35 | 12.0 |
| long c=1 | 15.65 | 1.6 | 9.75 | 2.6 |
| long c=4 | 16.40 | 5.8 | 11.50 | 7.8 |
| long c=8 | 19.25 | 9.8 | 13.39 | 13.0 |
| long c=16 | 21.23 | 17.4 | 18.17 | 19.4 |

Reason (upstream README_higgs_audio_v3.md): with `enforce_eager: false` the talker switches off its own local MLP
CUDA graph, and vLLM's piecewise graphs without torch.compile don't make up for it. The eager profile is the fastest
talker available on this stack; a real decode graph would need the FULL_DECODE capture fixed for sm_86.

## S2 `mem080_seqs32.yaml` (`results/S2_mem080_seqs32`, from 19:12)

Stage 0 `gpu_memory_utilization` 0.80 (KV cache 11 GiB = 79,232 tokens, "9.67x for 8,192-token requests"), stage 1
0.08, `max_num_seqs` 32, otherwise `flash_attn.yaml`. shehbaz short/long/xlong at c=16 and c=32 (n = 32 / 64):

| size | c | lat p50 / p90 / p99 s | xRT (p90-wall) | req/s | suspects | GPU peak MiB | Qwen c=32 xRT |
|---|---|---|---|---|---|---|---|
| short | 16 | 4.57 / 6.97 / 16.6 | 13.4 (one 16 s straggler) | 1.43 | 2 | 23,090 | 17.8 (c=16) |
| short | 32 | 7.18 / 11.50 / 13.2 | 16.2 | 3.44 | 5 | 23,211 | 21.4 |
| long | 16 | 17.73 / 21.00 / 22.9 | 19.6 | 0.84 | 0 | 23,386 | 26.0 (c=16) |
| long | 32 | 22.34 / 24.83 / 26.6 | 31.4 | 1.27 | 0 | 23,388 | 31.8 |
| xlong | 16 | 23.23 / 27.66 / 33.8 | 19.5 | 0.58 | 0 | 23,522 | 26.1 (c=16) |
| xlong | 32 | 31.02 / 34.91 / 41.8 | 28.8 | 0.78 | 5 (4 short) | 23,524 | 33.3 |

At 32 in flight Higgs reaches 31 x realtime on ~25 s texts, the same as Qwen at c=32, at the cost of 22-31 s p50
latency; the card is full (23.5 GB of 24 GB peak, desktop included), so 32 is the ceiling on this GPU. Streaming
c=16/32 and trump c=32 rows: the run folder.

## Q1-Q4 the 43 benchmark prompts (`results/Q_prompts`, 19:21-19:47, scored 19:50-20:04 on the GPU)

`higgs/bench/quality_runs.sh`: `--size prompts --takes 2 -c 8` on `mem080_seqs32.yaml`, pace from
`higgs/calibration/pace.json`, 86 takes per arm, 516 takes, 4.6 h of audio, 0 errors. Speed was the same in every arm
(lat p50 15-18 s, 14.3-15.4 x realtime). Quality (`QUALITY.md` with `--by tag,voice`):

| arm | voice | WER | CER-ns | SIM-L | pace | gate fail | bad | leading reasons |
|---|---|---|---|---|---|---|---|---|
| Q1 temperature 0.8 / top_k 50, Qwen clip | shehbaz | 0.146 | 0.114 | 0.851 | 0.96 | 36.0 % | 38.4 % [29, 49] | del_run 29, char_ratio 27, cer 11 |
| Q1 | trump | 0.088 | 0.082 | 0.830 | 0.96 | 66.3 % | 66.3 % [56, 75] | del_run 55, wer 27, char_ratio 18 |
| Q2 temperature 1.0 / top_p 0.95 (upstream) | shehbaz | 0.232 | 0.195 | 0.864 | 0.86 | 50.0 % | 55.8 % [45, 66] | del_run 44, char_ratio 37, cer 23 |
| Q3 25 s Higgs-style reference (clips 08+05) | shehbaz | 0.166 | 0.135 | 0.861 | 0.96 | 45.3 % | 51.2 % [41, 61] | del_run 43, char_ratio 29 |
| Q4 expressive set, plain text | shehbaz | 0.193 | 0.162 | 0.862 | 0.90 | 45.3 % | 46.5 % [36, 57] | del_run 38, char_ratio 36 |
| Q4 expressive set, with the 43 control tags | shehbaz | 0.234 | 0.200 | 0.810 | 0.97 | 57.0 % | 60.5 % [50, 70] | del_run 43, char_ratio 39, cer 23 |

- These prompts are long (Urdu 71-130 words, English 91-160), i.e. the length where Higgs drops passages. By length,
  Q1 Urdu: <= 90 words 2/14 bad (14 %), 91-110 words 29/70 (41 %), 111-130 words 2/2; English: 91-110 words 17/30
  (57 %), 111-130 36/52 (69 %), > 130 4/4. Bad takes have a median char_ratio of 0.81 (a fifth of the text missing)
  and are *shorter* (median 30 s vs 35 s for good takes): the model ends early rather than looping.
- Of the 43 Urdu prompts, 9 failed in both takes, 15 in one, 19 in neither: a retry recovers ~60 % of failures at this
  length; splitting to <= 60-word parts (where the baseline measured 1-7 % bad) is the structural fix (G1/G2).
- Sampling: Boson's 0.8 / 50 beats upstream's 1.0 / top_p 0.95 by 17 points of bad rate and 9 WER points; the
  higher temperature makes the model drop more text (pace ratio 0.86). Kept 0.8 / 50.
- Reference: the Qwen benchmark's 28 s clip beats the livelier 25 s Higgs-style clip (51 % vs 38 % bad, WER 0.166 vs
  0.146) at equal similarity, so the Kaggle finding "the livelier reference beats the long one" does not carry over
  to this engine's 30 s limit and prompt layout. Kept `qwen3-tts`.
- Control tags (re-scored against the plain words, `higgs/bench/strip_tags.py`): the tagged texts are spoken as the
  plain words, but they cost quality on this engine: bad 60.5 % vs 46.5 % for the same texts untagged, WER 0.234 vs
  0.193, SIM-L 0.81 vs 0.86 (more dropped passages, a slightly different voice). Whether the emotion / style is
  audible needs listening: `samples/higgs-tts-3/tags/` holds two plain / tagged pairs (whispering, laughter).

## G0-G2 the gateway in front of Higgs (`results/G_gateway`, 20:05-20:22, scored 20:23-20:31)

`higgs/bench/gateway_runs.sh`: the repo's gateway (`higgs/engine/run_gateway.sh`: Higgs request shape, voices
registered with the engine once, pace from `higgs/calibration/pace.json`, `max_new_tokens` at 25 fps, no auth, no QC
sidecar) on `mem080_seqs32.yaml`, `--voice-mode server`. Three arms, each its own gateway process; per arm shehbaz
xlong (~98 words) and xxlong (~200 words) at c=1 and c=8, trump xlong at c=8, one streaming run. 240 takes, 3.05 h.
Note that the three arms drew different texts from the pools (each run continues where the previous stopped), so
arm-to-arm differences of a few takes are within that noise; the unsplit-vs-split contrast is not.

| arm | shehbaz xlong c=1 lat p50 s | xlong c=8 lat p50 / xRT | xxlong c=1 lat p50 / xRT | xxlong c=8 lat p50 / xRT | trump xlong c=8 lat p50 / xRT | stream xlong c=8 TTFA p50 s |
|---|---|---|---|---|---|---|
| G0 no split, no retries | 12.96 | 16.20 / 13.4 | 11.05 / 2.5 (truncated audio) | 13.39 / 10.1 (truncated) | 15.67 / 14.4 | 1.35 |
| G1 split at 60 words | 9.60 | 15.26 / 17.2 | 11.03 / 7.7 | 22.12 / 25.9 | 13.13 / 21.4 | 1.19 |
| G2 split + 1 retry on pace / engine error | 9.38 | 15.06 / 19.9 | 10.93 / 7.5 | 23.43 / 25.7 | 13.21 / 21.6 | 1.21 |

| arm | shehbaz xlong: WER / bad | shehbaz xxlong: WER / bad | trump xlong: WER / bad | shehbaz xlong stream: WER / bad |
|---|---|---|---|---|
| G0 | 0.275 / 70.8 % (24) | 0.784 / 100 % (24) | 0.039 / 43.8 % (16) | 0.083 / 31.2 % (16) |
| G1 | 0.071 / 25.0 % | 0.093 / 45.8 % | 0.003 / 0 % | 0.036 / 0 % |
| G2 | 0.036 / 0 % | 0.036 / 4.2 % | 0.004 / 6.2 % | 0.030 / 0 % |

- Splitting turns the ~200-word texts from unusable (every take stops at 15-20 s) into 83 s takes at the calibrated
  pace, and makes long texts *faster*: the parts run in parallel on free engine slots, so a 200-word Urdu text takes
  11 s at c=1 (7.5 x realtime from a single request) and a 100-word one 9.4 s instead of 13.
- Splitting alone still leaves some parts with dropped words and adds `word_gap` flags at part joins (G1: word_gap 8,
  del_run 8 on xxlong); with one retry on pace-suspect takes G2 reaches WER 0.036 on both lengths with 0-4 % bad,
  the same quality as single 25 s texts (B0 long: WER 0.052, 6.6 % bad). Retries were rare (1 in 16 xxlong c=8
  requests), so most of the G1 -> G2 gap is text-window noise; the split-vs-unsplit gap is not.
- The gateway's overhead is invisible next to the engine (G0 xlong c=1 12.96 s vs 13.45 s engine direct in B0).
- The gateway registered both voices with the Higgs engine through `POST /v1/audio/voices` at start-up and served
  them by name; streaming through the gateway kept TTFA at the engine's level (1.2-1.35 s at c=8).
