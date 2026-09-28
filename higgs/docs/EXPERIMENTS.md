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
| B0 | baseline, `flash_attn.yaml` (upstream default profile) | running from 18:23 |

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
takes of this speaker score WER ~0.37 in Urdu (accented) at SIM-large ~0.8 (`server/REPORT.md` §5).
