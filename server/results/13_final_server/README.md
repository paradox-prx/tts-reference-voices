# 13_final_server: the production service as deployed (2026-09-28)

> **AI-generated audio.** Every FLAC here is synthetic speech from Qwen3-TTS voice cloning that imitates real people
> (`trump`: Donald Trump, `shehbaz`: Shehbaz Sharif). None of it is a real recording, and the speakers never said these
> words: the texts are fictional benchmark prompts. The label is in each file's metadata (Vorbis `COMMENT` / `TITLE`).
> Do not present, cut or redistribute these clips as anything other than labelled AI-generated benchmark output.

What a client of the running service gets today: every request went through the production gateway (`:8090`) of the
systemd units, with the deployed settings ([`../../deploy/env.example`](../../deploy/env.example), REPORT §8):

- engine: vLLM-Omni 0.28.0, `engine/deploy/variants/custom_voices.yaml` (bf16 talker, CUDA graphs, async_chunk, 64
  sequences), precomputed voices; sampling temperature 0.9, top_k 50, the model's repetition penalty (1.05)
- gateway: Urdu with `non_streaming_mode`, texts over 60 words split at sentence ends (parts in parallel on free
  slots), length cap, 1 retry on a suspect pace / engine error / failed QC, at most 32 requests at the engine
- QC sidecar in its cheap mode: speaker similarity (WavLM base-plus-sv) and audio checks, no Whisper
- one RTX 3090 24 GB, which also drives the desktop

The commands are in [`commands.sh`](commands.sh), the console in [`console.log`](console.log). Each run folder holds
`requests.jsonl` (every request with its response headers), `summary.json` and `audio/NNN.flac`. The takes are also
listed with their quality metrics in `scores.jsonl`, and with failure tiers in `takes_all.jsonl` and
`failure_classes.json`.

## Speed

832 requests (plus warm-ups), **0 errors**, 9 retried (pace or QC), 0 shipped as suspect.

| voice | run | requests | latency p50 / p90 / p99 s | time to first audio p50 | audio per request | x realtime |
|---|---|---|---|---|---|---|
| trump | short, 1 at a time | 16 | 0.65 / 1.02 / 1.03 | – | 3.2 s | 4.8 |
| trump | short, 1 at a time, streaming | 16 | 0.61 / 0.99 / 1.06 | **0.11 s** | 3.2 s | 5.0 |
| trump | short, 16 concurrent | 64 | 2.38 / 4.39 / 5.02 | – | 3.1 s | 17.2 |
| trump | medium, 16 concurrent | 64 | 4.32 / 5.79 / 6.27 | – | 6.5 s | 22.0 |
| trump | long, 16 concurrent | 43 | 9.46 / 11.14 / 11.64 | – | 15.9 s | 24.6 |
| trump | ~30 s (the 43 prompts), 16 concurrent | 43 | 14.7 / 27.0 / 39.6 | – | 32.8 s | 27.2 |
| trump | ~60 s, 16 concurrent | 43 | 19.4 / 70.5 / 73.0 | – | 65.8 s | 28.0 |
| trump | medium, 32 concurrent | 128 | 6.83 / 9.12 / 11.69 | – | 6.6 s | 26.9 |
| shehbaz | short, 1 at a time | 16 | 1.01 / 1.80 / 1.86 | – | 4.6 s | 4.6 |
| shehbaz | short, 1 at a time, streaming | 16 | 0.88 / 1.32 / 1.38 | **0.12 s** | 4.4 s | 5.0 |
| shehbaz | short, 16 concurrent | 64 | 3.55 / 5.53 / 6.63 | – | 4.8 s | 19.4 |
| shehbaz | medium, 16 concurrent | 64 | 6.66 / 8.43 / 9.62 | – | 10.4 s | 23.1 |
| shehbaz | long, 16 concurrent | 43 | 14.1 / 17.1 / 18.9 | – | 23.7 s | 24.3 |
| shehbaz | ~30 s (the 43 prompts), 16 concurrent | 43 | 18.5 / 22.0 / 57.1 | – | 37.6 s | 28.3 |
| shehbaz | ~60 s, 16 concurrent | 43 | 22.5 / 88.9 / 99.5 | – | 76.0 s | 28.2 |
| shehbaz | medium, 32 concurrent | 128 | 10.6 / 13.5 / 16.4 | – | 10.7 s | 29.1 |

GPU memory: 20.7 GB at rest, up to 22.8 GB under load (engine + QC sidecar + desktop).

**The ~60 s tails (p90 70-89 s) are a gateway scheduling effect.** Each ~60 s text is split into 4-5 parts. The first
7-8 of 16 simultaneous requests take all 32 engine slots, so the requests after them get a single slot each and run
their parts one after another: 55-100 s instead of ~20 s. The gateway takes a request's extra slots only when the
request starts (`gateway/tts_gateway/app.py`, `admission.try_acquire`). Two possible fixes, both untested:
`TTS_MAX_INFLIGHT=64` (the engine already runs 64 sequences), or letting a request pick up slots as they free up.

## Quality

Scored offline like every other phase (`eval/score_run.py`: stock Whisper large-v3 fp16 beam 5, WavLM-Large and
WavLM base-plus-sv similarity to the voice's reference; tiers from `eval/failure_classes.py`). The short rows include
the 1-at-a-time and streaming takes, and the medium rows include the 32-concurrent takes.

| voice | size | takes | WER | CER-nospace | SIM Large / base | severe | moderate |
|---|---|---|---|---|---|---|---|
| trump | short | 96 | 0.2% | 0.1% | 0.72 / 0.960 | 0 | 0 |
| trump | medium | 192 | 0.3% | 0.2% | 0.81 / 0.981 | 0 | 0 |
| trump | long | 43 | 0.5% | 0.3% | 0.85 / 0.987 | 0 | 0 |
| trump | ~30 s | 43 | 1.3% | 0.7% | 0.87 / 0.988 | 0 | 1 |
| trump | ~60 s | 43 | 1.3% | 0.7% | 0.88 / 0.990 | 0 | 2 |
| **trump** | **all** | **417** | **0.5%** | **0.3%** | **0.81 / 0.978** | **0 (0.0%)** | **3 (0.7%)** |
| shehbaz | short | 96 | 31.5% | 13.2% | 0.71 / 0.958 | 2 | 5 |
| shehbaz | medium | 192 | 33.7% | 14.1% | 0.79 / 0.975 | 0 | 12 |
| shehbaz | long | 43 | 35.1% | 16.0% | 0.82 / 0.982 | 3 | 1 |
| shehbaz | ~30 s | 43 | 33.9% | 14.6% | 0.85 / 0.987 | 1 | 7 |
| shehbaz | ~60 s | 43 | 34.0% | 15.3% | 0.86 / 0.988 | 7 | 12 |
| **shehbaz** | **all** | **417** | **33.4%** | **14.3%** | **0.79 / 0.974** | **13 (3.1%)** | **37 (8.9%)** |

- **English:** no severe failure in 417 takes. No take fell below the wrong-voice line (SIM-base 0.85). The lowest
  was 0.86, on a 2.2 s clip; short clips score lower for any speaker.
- **Urdu** is accented but intelligible. Most of the error is accent: the same Whisper transcribes this speaker's real
  recordings at CER-nospace 0.037.
  - Severe failures are 3.1% of takes. On the 43 ~30 s prompts the rate is 2.3%, against 7.7% for the same setting
    without the gateway's retry and QC (P5_urdu_nsm).
  - The ~60 s texts remain the weak spot: 7 of 43 (16% [8-30]) skipped a passage or have a long voiced gap. X8
    measured 11.6% in the same configuration, so the two agree within noise.
  - Only offline Whisper sees these failures. The cheap production QC has no ASR (REPORT §5.3-5.4).

## Audio in this folder

691 of the 834 takes (2.7 h) are here as FLAC: the same 24 kHz 16-bit samples as the WAVs the service returned. The
other 143 are left out because their text reads as a political statement or an official announcement (see
[`../README.md`](../README.md)). [`AUDIO_MANIFEST.jsonl`](AUDIO_MANIFEST.jsonl) lists every take, its text, and the
reason for any take left out.
