# Benchmark results: every run's numbers, and where its audio is

> **All audio of this benchmark is AI-generated speech.** It imitates real people (`trump`: Donald Trump, `shehbaz`:
> Shehbaz Sharif) with Qwen/Qwen3-TTS-12Hz-1.7B-Base voice cloning. None of it is a real recording, and the speakers
> never said these words: the texts are fictional benchmark prompts. Every published file carries the label in its
> metadata (FLAC Vorbis `COMMENT` / `TITLE`). Do not present, cut or redistribute it as anything other than labelled
> AI-generated benchmark output.

The analysis is in [`../REPORT.md`](../REPORT.md) and the experiment-by-experiment log in
[`../docs/EXPERIMENTS.md`](../docs/EXPERIMENTS.md); [`INDEX.md`](INDEX.md) indexes the phases (`bench/collect.py`).

## What is where

| what | where |
|---|---|
| numbers of every phase: per-request rows (`requests.jsonl`), per-run and per-phase summaries (`summary.{json,csv,md}`), quality scores (`scores.jsonl`, `takes_all.jsonl`, `failure_classes.json`), config and versions (`phase.json`, `versions/`, `commands.sh`), GPU snapshots, engine / gateway / QC logs | this folder, in git |
| **the final server's outputs** (`13_final_server/`: the production service as deployed, every run with its FLAC audio) | this folder, in git: [13_final_server/](13_final_server/) |
| the audio of every other phase (labelled FLAC, one archive per phase, with `AUDIO_MANIFEST.jsonl`) | GitHub release [`bench-audio-2026-09-28`](https://github.com/paradox-prx/tts-reference-voices/releases/tag/bench-audio-2026-09-28) |
| 40 hand-sorted samples (best / mid / worst) | [`../../samples/qwen3-tts/`](../../samples/qwen3-tts/README.md) |

Each archive unpacks to `<phase>/<run>/audio/<nnn>.flac`, the same paths as the `file` fields of that phase's
`requests.jsonl` with `.wav` → `.flac` (lossless: the same 24 kHz 16-bit samples). `AUDIO_MANIFEST.jsonl` lists every
take of the phase with its text, and the takes that were left out with the reason.

**Left out of every publication:** takes whose text reads as a political statement or an official announcement
(speeches to the nation, promises, inaugurations, accusations; keyword list `POLITICAL` in
[`../eval/pick_samples.py`](../eval/pick_samples.py)), because a realistic clip of a real head of government saying them
is easy to misuse once the label is stripped. Their numbers stay here; only the audio is withheld. The keyword filter
is conservative (it also drops some harmless texts) and not perfect.

## The final server at a glance ([13_final_server/](13_final_server/README.md))

832 requests through the production gateway, 0 errors. Streaming time to first audio: 0.11 s (English), 0.12 s (Urdu).
At 16-32 concurrent: 17-29x realtime. English: WER 0.5%, no severe failures in 417 takes. Urdu: CER-nospace 14%
(mostly accent), severe failures 3.1% of takes, 16% on ~60 s texts.

## Release archives

| phase | takes published | left out: political / official text | left out: text not found | audio h | archive MB |
|---|---|---|---|---|---|
| 00_first_engine_smoke | 4 | 4 | 0 | 0.00 | 0.5 |
| 00_first_gateway_smoke | 14 | 6 | 0 | 0.02 | 2.0 |
| 01_probe_scaling_engine_direct | 556 | 148 | 0 | 2.85 | 271.4 |
| 02_probe_gateway_urdu_c48 | 59 | 37 | 0 | 0.37 | 34.7 |
| 03_ab_async_chunk | 358 | 90 | 0 | 1.83 | 174.1 |
| 04_knob_verification | 0 | 65 | 0 | 0.00 | – (no archive) |
| 06_baseline_gpu_smoke | 0 | 7 | 0 | 0.00 | – (no archive) |
| 10_production_verification | 1 | 3 | 0 | 0.00 | 0.1 |
| 11_production_sim_guard | 448 | 32 | 0 | 0.77 | 73.5 |
| 12_failure_recovery | 0 | 0 | 1 | 0.00 | – (no archive) |
| _attic | 58 | 29 | 0 | 0.51 | 48.1 |
| P0_knobs | 0 | 4 | 0 | 0.00 | – (no archive) |
| P0_smoke | 5 | 5 | 0 | 0.01 | 0.5 |
| P1_screen_decode4g_m045 | 101 | 11 | 0 | 0.22 | 21.3 |
| P1_screen_default | 101 | 11 | 0 | 0.22 | 21.4 |
| P1_screen_default_m045 | 101 | 11 | 0 | 0.22 | 21.5 |
| P1_screen_eager | 101 | 11 | 0 | 0.22 | 21.5 |
| P1_screen_no_async_chunk | 13 | 3 | 0 | 0.04 | 3.9 |
| P1_screen_seqs128 | 101 | 11 | 0 | 0.22 | 21.7 |
| P1_screen_seqs32 | 101 | 11 | 0 | 0.23 | 21.9 |
| P2_high_c | 912 | 110 | 0 | 2.11 | 202.3 |
| P2_matrix | 772 | 160 | 0 | 3.43 | 324.1 |
| P3_stream | 367 | 69 | 0 | 1.35 | 127.5 |
| P4_voice_cache | 535 | 25 | 0 | 0.56 | 54.4 |
| P5_urdu_nsm | 99 | 156 | 0 | 0.97 | 90.1 |
| P5_urdu_rp105 | 140 | 156 | 0 | 1.28 | 119.2 |
| P5_urdu_rp110 | 98 | 154 | 0 | 0.90 | 83.7 |
| P5_urdu_rp115 | 97 | 150 | 0 | 0.90 | 83.2 |
| P5_urdu_rp120 | 138 | 153 | 0 | 1.27 | 118.0 |
| P6_auralis | 309 | 27 | 0 | 0.71 | 68.0 |
| P7_gateway | 236 | 52 | 0 | 0.67 | 63.9 |
| P8_quality_guard | 58 | 29 | 0 | 0.53 | 49.4 |
| P8_quality_guard_fast | 58 | 29 | 0 | 0.52 | 48.5 |
| P8_quality_raw | 57 | 28 | 0 | 0.52 | 49.5 |
| P9_baseline_b1 | 40 | 8 | 0 | 0.13 | 13.0 |
| P9_baseline_b8 | 195 | 40 | 0 | 0.74 | 70.0 |
| P9_baseline_nocache | 60 | 11 | 0 | 0.19 | 17.7 |
| X1_nsm | 17 | 28 | 0 | 0.17 | 16.1 |
| X2_language | 42 | 3 | 0 | 0.36 | 34.7 |
| X3_custom_voice | 32 | 53 | 0 | 0.29 | 27.1 |
| X4_length_cap | 34 | 52 | 0 | 0.32 | 29.8 |
| X5_mixed_voices | 82 | 14 | 0 | 0.26 | 24.5 |
| X6_nsm_long_urdu | 48 | 67 | 0 | 0.84 | 78.2 |
| X7_split_60 | 44 | 43 | 0 | 0.79 | 74.8 |
| X7_split_off | 42 | 27 | 0 | 0.70 | 66.0 |
| X8_split_nsm | 6 | 38 | 0 | 0.10 | 10.0 |
| X9_nsm_stream | 42 | 21 | 0 | 0.17 | 16.2 |
| **all** | **6682** | **2202** | **1** | **28.5** | **2698** |

13_final_server (in git): 691 published, 143 left out, 2.7 h.
Archives written by `venvs/gateway/bin/python bench/export_audio.py --out <dir>`.
