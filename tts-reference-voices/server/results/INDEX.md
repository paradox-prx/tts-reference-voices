# Benchmark results index

Generated 2026-09-28T17:20:19+05:00 by `server/bench/collect.py` from `/home/vector/Documents/abdullah_workspace/qwen-server/tts-reference-voices/server/results`.
**All audio under these folders is AI-generated (Qwen3-TTS voice clones). Only 13_final_server/ keeps its FLACs in git; every other phase's audio is in the GitHub release as labelled FLAC (political / official texts left out), see [README.md](README.md).**

Each phase folder holds `phase.json` (config, versions, host, git, engine YAML, GPU baseline/release, commands and exit codes), `commands.sh`, `summary.{csv,md,json}` and `requests.jsonl` (every run), `logs/`, `snapshots/` (nvidia-smi and /metrics around every bench command), `versions/` (every package of every venv used), `knobs/` (knob verification takes) and one folder per run with its `audio/`, `requests.jsonl` and `summary.json`.

## Phases

| phase | status | runs | requests | errors | suspects | engine built-in retries | preemption lines | audio h | minutes | engine | gateway | GPU MiB: idle baseline / engine at rest (above baseline) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [P0_smoke](P0_smoke/) | DONE | 10 | 10 | 0 | 0 | 0 | 0 | 0.02 | 1.1 | vllm-omni default (engine) | {"TTS_RETRY_MAX": "0"} | 333 / 18818 |
| [P0_knobs](P0_knobs/) | DONE | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 | 0.9 | vllm-omni custom_voices (engine) | off | 329 / 18818 |
| [P1_screen_default](P1_screen_default/) | DONE | 6 | 112 | 0 | 0 | 0 | 0 | 0.25 | 1.8 | vllm-omni default (engine) | off | 341 / 18800 |
| [P1_screen_no_async_chunk](P1_screen_no_async_chunk/) | DONE | 1 | 16 | 0 | 0 | 0 | 0 | 0.05 | 1.1 | vllm-omni no_async_chunk (engine) | off | 333 / 22440 |
| [P1_screen_eager](P1_screen_eager/) | DONE | 6 | 112 | 0 | 0 | 0 | 0 | 0.25 | 2.9 | vllm-omni eager (engine) | off | 327 / 16447 |
| [P1_screen_fp16_talker](P1_screen_fp16_talker/) | failed | 0 | 0 | 0 | 0 | 0 | 2 | 0.00 | 2.9 | vllm-omni fp16_talker (engine) | off | 321 / – |
| [P1_screen_fp32_talker](P1_screen_fp32_talker/) | failed | 0 | 0 | 0 | 0 | 0 | 2 | 0.00 | 2 | vllm-omni fp32_talker (engine) | off | 320 / – |
| [P1_screen_seqs32](P1_screen_seqs32/) | DONE | 6 | 112 | 0 | 0 | 0 | 0 | 0.26 | 2.4 | vllm-omni seqs32 (engine) | off | 320 / 18644 |
| [P1_screen_seqs128](P1_screen_seqs128/) | DONE | 6 | 112 | 0 | 0 | 0 | 0 | 0.25 | 2.8 | vllm-omni seqs128 (engine) | off | 318 / 19404 |
| [P1_screen_decode8](P1_screen_decode8/) | failed | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 | 1.7 | vllm-omni decode8 (engine) | off | 324 / – |
| [P1_screen_decode8_m045](P1_screen_decode8_m045/) | failed | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 | 0.8 | vllm-omni decode8_m045 (engine) | off | 335 / – |
| [P1_screen_default_m045](P1_screen_default_m045/) | DONE | 6 | 112 | 0 | 0 | 0 | 0 | 0.25 | 1.8 | vllm-omni default_m045 (engine) | off | 335 / 15228 |
| [P1_screen_decode4g_m045](P1_screen_decode4g_m045/) | DONE | 6 | 112 | 0 | 0 | 0 | 0 | 0.25 | 2.7 | vllm-omni decode4g_m045 (engine) | off | 335 / 19927 |
| [P2_matrix](P2_matrix/) | DONE | 60 | 964 | 32 | 12 | 0 | 0 | 4.68 | 19.5 | vllm-omni custom_voices (engine) | off | 335 / 18809 |
| [P2_high_c](P2_high_c/) | DONE | 10 | 1024 | 2 | 5 | 0 | 0 | 2.64 | 6.8 | vllm-omni custom_voices (engine) | off | 329 / 18800 |
| [P3_stream](P3_stream/) | DONE | 28 | 444 | 8 | 10 | 0 | 0 | 1.90 | 8.7 | vllm-omni custom_voices (engine) | off | 335 / 18809 |
| [P4_voice_cache](P4_voice_cache/) | DONE | 30 | 560 | 0 | 6 | 0 | 0 | 0.59 | 4.1 | vllm-omni custom_voices (engine) | off | 316 / 18812 |
| [P5_urdu_rp105](P5_urdu_rp105/) | DONE | 2 | 301 | 7 | 1 | 0 | 0 | 2.69 | 5.9 | vllm-omni custom_voices (engine) | off | 316 / 18812 |
| [P5_urdu_rp110](P5_urdu_rp110/) | DONE | 1 | 258 | 8 | 1 | 0 | 0 | 2.31 | 5.2 | vllm-omni custom_voices (engine) | off | 316 / 18812 |
| [P5_urdu_rp115](P5_urdu_rp115/) | DONE | 1 | 258 | 13 | 0 | 0 | 0 | 2.26 | 5.3 | vllm-omni custom_voices (engine) | off | 316 / 18812 |
| [P5_urdu_rp120](P5_urdu_rp120/) | DONE | 2 | 301 | 12 | 1 | 0 | 0 | 2.65 | 6.1 | vllm-omni custom_voices (engine) | off | 316 / 18812 |
| [P6_auralis](P6_auralis/) | DONE | 21 | 336 | 0 | 0 | 0 | 0 | 0.81 | 2.7 | vllm-omni custom_voices (engine) | {"TTS_RETRY_MAX": "0"} | 316 / 18812 |
| [P7_gateway](P7_gateway/) | DONE | 10 | 288 | 0 | 3 | 0 | 0 | 0.95 | 2.5 | vllm-omni custom_voices (engine) | {"TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"} | 316 / 18812 |
| [X1_nsm](X1_nsm/) | DONE | 1 | 43 | 0 | 0 | 0 | 0 | 0.42 | 1 | vllm-omni custom_voices (engine) | off | 316 / 18812 |
| [X6_nsm_long_urdu](X6_nsm_long_urdu/) | DONE | 3 | 129 | 16 | 14 | 0 | 0 | 1.99 | 6.1 | vllm-omni custom_voices (engine) | off | 329 / 18800 |
| [X7_split_off](X7_split_off/) | DONE | 2 | 86 | 18 | 16 | 0 | 0 | 1.07 | 5.5 | vllm-omni custom_voices (engine) | {"TTS_RETRY_MAX": "0", "TTS_SPLIT_WORDS": "0"} | 329 / 18800 |
| [X7_split_60](X7_split_60/) | DONE | 2 | 86 | 0 | 0 | 0 | 0 | 1.62 | 3.2 | vllm-omni custom_voices (engine) | {"TTS_RETRY_MAX": "0", "TTS_SPLIT_WORDS": "60"} | 329 / 18800 |
| [P5_urdu_nsm](P5_urdu_nsm/) | DONE | 1 | 258 | 5 | 0 | 0 | 0 | 2.48 | 6.4 | vllm-omni custom_voices (engine) | off | 325 / 18803 |
| [X8_split_nsm](X8_split_nsm/) | DONE | 1 | 43 | 0 | 0 | 0 | 0 | 0.90 | 1.9 | vllm-omni custom_voices (engine) | {"TTS_RETRY_MAX": "0", "TTS_SPLIT_WORDS": "60", "TTS_NON_STREAMING_MODE_LANGS": "ur"} | 325 / 18803 |
| [X9_nsm_stream](X9_nsm_stream/) | DONE | 8 | 64 | 1 | 0 | 0 | 0 | 0.34 | 3.5 | vllm-omni custom_voices (engine) | off | 322 / 18809 |
| [X2_language](X2_language/) | DONE | 1 | 43 | 0 | 0 | 0 | 0 | 0.39 | 0.9 | vllm-omni custom_voices (engine) | off | 316 / 18812 |
| [X3_custom_voice](X3_custom_voice/) | DONE | 2 | 86 | 3 | 0 | 0 | 0 | 0.77 | 2.1 | vllm-omni custom_voices (engine) | off | 316 / 18812 |
| [X4_length_cap](X4_length_cap/) | DONE | 2 | 86 | 1 | 0 | 5 | 0 | 0.79 | 3.8 | vllm-omni custom_voices (engine) | off | 316 / 18812 |
| [X5_mixed_voices](X5_mixed_voices/) | DONE | 2 | 96 | 0 | 1 | 0 | 0 | 0.36 | 0.9 | vllm-omni custom_voices (engine) | off | 316 / 18812 |
| [P8_quality_raw](P8_quality_raw/) | DONE | 2 | 86 | 2 | 0 | 0 | 0 | 0.78 | 2.7 | vllm-omni custom_voices (engine) --stage-overrides {"0": {"gpu_memory_utilization": 0.45}} | {"TTS_RETRY_MAX": "0"} | 311 / 15229 |
| [P8_quality_guard](P8_quality_guard/) | DONE | 2 | 86 | 0 | 0 | 0 | 0 | 0.80 | 6.3 | vllm-omni custom_voices (engine) --stage-overrides {"0": {"gpu_memory_utilization": 0.40}} | {"TTS_RETRY_MAX": "2", "TTS_RETRY_ON": "suspect,engine_error,qc"} + QC | 331 / 13985 |
| [P8_quality_guard_fast](P8_quality_guard_fast/) | DONE | 2 | 86 | 0 | 0 | 0 | 0 | 0.79 | 9.3 | vllm-omni custom_voices (engine) --stage-overrides {"0": {"gpu_memory_utilization": 0.40}} | {"TTS_RETRY_MAX": "2", "TTS_RETRY_ON": "suspect,engine_error,qc", "TTS_QC_TIMEOUT_S": "120"} + QC | 329 / 13986 |
| [P9_baseline_b8](P9_baseline_b8/) | DONE | 24 | 236 | 1 | 10 | 0 | 0 | 1.14 | 17.6 | qwen-tts baseline --max-batch 8 | off | 311 / 5498 |
| [P9_baseline_b1](P9_baseline_b1/) | DONE | 8 | 48 | 0 | 1 | 0 | 0 | 0.19 | 6.9 | qwen-tts baseline --max-batch 1 | off | 311 / 5498 |
| [P9_baseline_nocache](P9_baseline_nocache/) | DONE | 8 | 72 | 1 | 1 | 0 | 0 | 0.25 | 5.6 | qwen-tts baseline --max-batch 8 --no-prompt-cache | off | 311 / 5498 |
| [T0_prod](T0_prod/) | DONE | 8 | 688 | 0 | 3 | 0 | 0 | 1.42 | 4.6 | vllm-omni custom_voices (engine) | {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"} | 284 / 18800 |
| [T1_mnbt512](T1_mnbt512/) | DONE | 8 | 688 | 0 | 2 | 0 | 0 | 1.42 | 5.5 | vllm-omni T1_mnbt512 (engine) | {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"} | 281 / 18844 |
| [T2_ramp](T2_ramp/) | DONE | 8 | 688 | 0 | 0 | 0 | 0 | 1.41 | 5.7 | vllm-omni T2_ramp (engine) | {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"} | 278 / 19706 |
| [T3_adaptive](T3_adaptive/) | DONE | 8 | 688 | 1 | 1 | 0 | 0 | 1.42 | 5.8 | vllm-omni T3_adaptive (engine) | {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"} | 279 / 19270 |
| [T4_predgraphs](T4_predgraphs/) | DONE | 8 | 688 | 0 | 5 | 0 | 0 | 1.43 | 5.5 | vllm-omni T4_predgraphs (engine) | {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"} | 277 / 18810 |
| [T5_decode1](T5_decode1/) | DONE | 8 | 688 | 0 | 3 | 0 | 0 | 1.43 | 5.5 | vllm-omni T5_decode1 (engine) | {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"} | 278 / 18811 |
| [T6_ctx25](T6_ctx25/) | DONE | 8 | 688 | 0 | 1 | 0 | 0 | 1.42 | 5.5 | vllm-omni T6_ctx25 (engine) | {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"} | 282 / 18806 |
| [T7_mnbt512_ramp](T7_mnbt512_ramp/) | DONE | 8 | 688 | 0 | 2 | 0 | 0 | 1.42 | 5.8 | vllm-omni T7_mnbt512_ramp (engine) | {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"} | 284 / 19739 |
| [T8_mnbt512_adaptive](T8_mnbt512_adaptive/) | DONE | 8 | 688 | 0 | 4 | 0 | 0 | 1.44 | 5.9 | vllm-omni T8_mnbt512_adaptive (engine) | {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"} | 278 / 19311 |
| [00_first_engine_smoke](00_first_engine_smoke/) | no phase.json | 0 | 0 | 0 | 0 | – | – | 0.00 | 0 | – | off | – / – |
| [00_first_gateway_smoke](00_first_gateway_smoke/) | no phase.json | 0 | 0 | 0 | 0 | – | – | 0.00 | 0 | – | off | – / – |
| [01_probe_scaling_engine_direct](01_probe_scaling_engine_direct/) | no phase.json | 14 | 704 | 0 | 0 | – | – | 3.75 | 0 | – | off | – / – |
| [02_probe_gateway_urdu_c48](02_probe_gateway_urdu_c48/) | no phase.json | 1 | 96 | 0 | 0 | – | – | 0.59 | 0 | – | off | – / – |
| [03_ab_async_chunk](03_ab_async_chunk/) | no phase.json | 20 | 448 | 0 | 0 | – | – | 2.38 | 0 | – | off | – / – |
| [04_knob_verification](04_knob_verification/) | no phase.json | 0 | 0 | 0 | 0 | – | – | 0.00 | 0 | – | off | – / – |
| [05_eval_gpu_check](05_eval_gpu_check/) | no phase.json | 0 | 0 | 0 | 0 | – | – | 0.00 | 0 | – | off | – / – |
| [06_baseline_gpu_smoke](06_baseline_gpu_smoke/) | no phase.json | 0 | 0 | 0 | 0 | – | – | 0.00 | 0 | – | off | – / – |
| [10_production_verification](10_production_verification/) | no phase.json | 0 | 0 | 0 | 0 | – | – | 0.00 | 0 | – | off | – / – |
| [11_production_sim_guard](11_production_sim_guard/) | no phase.json | 6 | 480 | 0 | 1 | – | – | 1.01 | 0 | – | off | – / – |
| [12_failure_recovery](12_failure_recovery/) | no phase.json | 0 | 0 | 0 | 0 | – | – | 0.00 | 0 | – | off | – / – |
| [13_final_server](13_final_server/) | no phase.json | 16 | 834 | 0 | 0 | – | – | 4.13 | 0 | – | off | – / – |
| [P5_retry_study](P5_retry_study/) | no phase.json | 0 | 0 | 0 | 0 | – | – | 0.00 | 0 | – | off | – / – |

Not run yet: P1_screen_default_engine30 (optional), P1_screen_mrv2_engine30 (optional), X1_nsm_trump (optional), P8_quality_retry (optional), P9_baseline_avg (optional)

## P0_smoke: DONE

1 short request per voice: engine direct (inline, upload) non-stream + stream, and via the gateway  
- engine: vllm-omni default (engine), YAML sha256 4227f4e44bea982b
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P0_smoke/versions/`)
- gateway: {"TTS_RETRY_MAX": "0"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=93739) INFO 09-25 03:55:51 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 333 MiB, engine idle 19151 MiB, released after: True
- bench commands: 5 (exit codes 0, 0, 0, 0, 0); `P0_smoke/commands.sh`; duration 1.1 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [direct_trump_short_c1_n1_nonstream_inline](P0_smoke/direct_trump_short_c1_n1_nonstream_inline/) | trump | short | 1 | 1 |  | inline | 0 | 0 | 0.78 / 0.78 / 0.78 | – | 4 | 5.11 | 5.11 | 0 | 0.196 | 1.28 | 19455 (19122) |
| [direct_shehbaz_short_c1_n1_nonstream_inline](P0_smoke/direct_shehbaz_short_c1_n1_nonstream_inline/) | shehbaz | short | 1 | 1 |  | inline | 0 | 0 | 1.38 / 1.38 / 1.38 | – | 7.52 | 5.43 | 5.44 | 0 | 0.184 | 0.72 | 19452 (19119) |
| [direct_trump_short_c1_n1_stream_inline](P0_smoke/direct_trump_short_c1_n1_stream_inline/) | trump | short | 1 | 1 | y | inline | 0 | 0 | 0.65 / 0.65 / 0.65 | 0.12 / 0.12 / 0.12 | 3.2 | 4.95 | 4.95 | 0 | 0.202 | 1.55 | 19452 (19119) |
| [direct_shehbaz_short_c1_n1_stream_inline](P0_smoke/direct_shehbaz_short_c1_n1_stream_inline/) | shehbaz | short | 1 | 1 | y | inline | 0 | 0 | 1.54 / 1.54 / 1.54 | 0.12 / 0.12 / 0.12 | 8.32 | 5.4 | 5.4 | 0 | 0.185 | 0.65 | 19452 (19119) |
| [direct_trump_short_c1_n1_nonstream_upload](P0_smoke/direct_trump_short_c1_n1_nonstream_upload/) | trump | short | 1 | 1 |  | upload | 0 | 0 | 0.75 / 0.75 / 0.75 | – | 3.92 | 5.2 | 5.2 | 0 | 0.192 | 1.33 | 19450 (19117) |
| [direct_shehbaz_short_c1_n1_nonstream_upload](P0_smoke/direct_shehbaz_short_c1_n1_nonstream_upload/) | shehbaz | short | 1 | 1 |  | upload | 0 | 0 | 1.24 / 1.24 / 1.24 | – | 6.64 | 5.36 | 5.36 | 0 | 0.186 | 0.81 | 19450 (19117) |
| [gw_trump_short_c1_n1_nonstream_server](P0_smoke/gw_trump_short_c1_n1_nonstream_server/) | trump | short | 1 | 1 |  | server | 0 | 0 | 0.88 / 0.88 / 0.88 | – | 3.68 | 4.2 | 4.2 | 0 | 0.238 | 1.14 | 19458 (19125) |
| [gw_shehbaz_short_c1_n1_nonstream_server](P0_smoke/gw_shehbaz_short_c1_n1_nonstream_server/) | shehbaz | short | 1 | 1 |  | server | 0 | 0 | 1.42 / 1.42 / 1.42 | – | 7.68 | 5.42 | 5.43 | 0 | 0.184 | 0.71 | 19458 (19125) |
| [gw_trump_short_c1_n1_stream_server](P0_smoke/gw_trump_short_c1_n1_stream_server/) | trump | short | 1 | 1 | y | server | 0 | 0 | 0.69 / 0.69 / 0.69 | 0.11 / 0.11 / 0.11 | 3.52 | 5.1 | 5.1 | 0 | 0.196 | 1.45 | 19453 (19120) |
| [gw_shehbaz_short_c1_n1_stream_server](P0_smoke/gw_shehbaz_short_c1_n1_stream_server/) | shehbaz | short | 1 | 1 | y | server | 0 | 0 | 1.43 / 1.43 / 1.43 | 0.11 / 0.11 / 0.11 | 7.84 | 5.48 | 5.48 | 0 | 0.182 | 0.7 | 19456 (19123) |

## P0_knobs: DONE

knob verification on the engine: extra_params repetition_penalty/temperature -1 refused, the same values top-level ignored, non_streaming_mode 'x' and language 'Urdu' refused, max_new_tokens 40 ends in the codec-EOS error, the custom voices listed and usable (verify_knobs.py; takes in knobs/)  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P0_knobs/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 41; KV: (StageEngineCoreProc_stage0_replica0 pid=123331) INFO 09-25 04:15:31 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 329 MiB, engine idle 19147 MiB, released after: True
- knob check `request_fields` (engine): OK {'listed': 'listed', 'base_a': None, 'fails_extra_rp_neg': 'refused', 'fails_extra_temperature_neg': 'refused', 'fails_nsm_invalid': 'refused', 'fails_language_urdu': 'refused', 'fails_cap40': 'refused', 'succeeds_toplevel_rp_neg_ignored': 'accepted', 'succeeds_toplevel_temperature_neg_ignored': 'accepted', 'succeeds_custom_voice_avg': 'accepted'}
- bench commands: 0 (exit codes –); `P0_knobs/commands.sh`; duration 0.9 min

no bench_tts.py runs here (see the folder's own files)

## P1_screen_default: DONE

variant screen default (engine): both voices, medium, c=1,8,32 (n=8,16,32), non-stream  
- engine: vllm-omni default (engine), YAML sha256 4227f4e44bea982b
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P1_screen_default/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=95895) INFO 09-25 03:56:54 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 341 MiB, engine idle 19141 MiB, released after: True
- bench commands: 1 (exit codes 0); `P1_screen_default/commands.sh`; duration 1.8 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_medium_c1_n8_nonstream_inline](P1_screen_default/trump_medium_c1_n8_nonstream_inline/) | trump | medium | 1 | 8 |  | inline | 0 | 0 | 1.08 / 1.62 / 1.66 | – | 6.28 | 5.33 | 5.33 | 0 | 0.19 | 0.85 | 19148 (18807) |
| [trump_medium_c8_n16_nonstream_inline](P1_screen_default/trump_medium_c8_n16_nonstream_inline/) | trump | medium | 8 | 16 |  | inline | 0 | 0 | 2.56 / 3.02 / 3.15 | – | 6.14 | 16.26 | 16.19 | 0 | 0.435 | 2.65 | 19176 (18835) |
| [trump_medium_c32_n32_nonstream_inline](P1_screen_default/trump_medium_c32_n32_nonstream_inline/) | trump | medium | 32 | 32 |  | inline | 0 | 0 | 6.22 / 6.94 / 7.42 | – | 6.45 | 27.56 | 25.37 | 0 | 0.989 | 4.28 | 19458 (19117) |
| [shehbaz_medium_c1_n8_nonstream_inline](P1_screen_default/shehbaz_medium_c1_n8_nonstream_inline/) | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 2.26 / 2.62 / 2.69 | – | 10.85 | 5.49 | 5.49 | 0 | 0.184 | 0.51 | 19677 (19336) |
| [shehbaz_medium_c8_n16_nonstream_inline](P1_screen_default/shehbaz_medium_c8_n16_nonstream_inline/) | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 3.81 / 5.27 / 5.37 | – | 9.76 | 17.74 | 17.36 | 0 | 0.411 | 1.82 | 19678 (19337) |
| [shehbaz_medium_c32_n32_nonstream_inline](P1_screen_default/shehbaz_medium_c32_n32_nonstream_inline/) | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 8.47 / 9.52 / 9.91 | – | 9.42 | 30.29 | 27.68 | 0 | 0.925 | 3.22 | 19684 (19343) |

## P1_screen_no_async_chunk: DONE

variant screen no_async_chunk (engine): one confirming cell (shehbaz medium c=8 n=16; E03 measured it)  
- engine: vllm-omni no_async_chunk (engine), YAML sha256 dd57326b088f2dd0
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P1_screen_no_async_chunk/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=101018) INFO 09-25 03:58:45 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 333 MiB, engine idle 22773 MiB, released after: True
- bench commands: 1 (exit codes 0); `P1_screen_no_async_chunk/commands.sh`; duration 1.1 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [shehbaz_medium_c8_n16_nonstream_inline](P1_screen_no_async_chunk/shehbaz_medium_c8_n16_nonstream_inline/) | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 4.95 / 6.07 / 7.9 | – | 10.73 | 14.53 | 14.38 | 0 | 0.451 | 1.35 | 23102 (22769) |

## P1_screen_eager: DONE

variant screen eager (engine): both voices, medium, c=1,8,32 (n=8,16,32), non-stream  
- engine: vllm-omni eager (engine), YAML sha256 ac8049f28e5b6a53
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P1_screen_eager/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=102828) INFO 09-25 03:59:49 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 327 MiB, engine idle 16774 MiB, released after: True
- bench commands: 1 (exit codes 0); `P1_screen_eager/commands.sh`; duration 2.9 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_medium_c1_n8_nonstream_inline](P1_screen_eager/trump_medium_c1_n8_nonstream_inline/) | trump | medium | 1 | 8 |  | inline | 0 | 0 | 2.75 / 5.16 / 5.3 | – | 6.57 | 2 | 2 | 0 | 0.511 | 0.3 | 16788 (16461) |
| [trump_medium_c8_n16_nonstream_inline](P1_screen_eager/trump_medium_c8_n16_nonstream_inline/) | trump | medium | 8 | 16 |  | inline | 0 | 0 | 4.24 / 5.39 / 5.79 | – | 6.07 | 9.67 | 9.76 | 0 | 0.739 | 1.59 | 18837 (18510) |
| [trump_medium_c32_n32_nonstream_inline](P1_screen_eager/trump_medium_c32_n32_nonstream_inline/) | trump | medium | 32 | 32 |  | inline | 0 | 0 | 7.44 / 8.05 / 9.42 | – | 6.56 | 22 | 22.44 | 0 | 1.144 | 3.35 | 18976 (18649) |
| [shehbaz_medium_c1_n8_nonstream_inline](P1_screen_eager/shehbaz_medium_c1_n8_nonstream_inline/) | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 4.68 / 6.24 / 6.56 | – | 10.4 | 2.26 | 2.26 | 0 | 0.453 | 0.22 | 19291 (18964) |
| [shehbaz_medium_c8_n16_nonstream_inline](P1_screen_eager/shehbaz_medium_c8_n16_nonstream_inline/) | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 4.62 / 5.74 / 6.57 | – | 10.18 | 15.76 | 15.55 | 0 | 0.48 | 1.55 | 19293 (18966) |
| [shehbaz_medium_c32_n32_nonstream_inline](P1_screen_eager/shehbaz_medium_c32_n32_nonstream_inline/) | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 8.44 / 9.52 / 9.77 | – | 9.23 | 30.2 | 27.27 | 0 | 0.943 | 3.27 | 19454 (19127) |

## P1_screen_fp16_talker: failed

variant screen fp16_talker (engine): both voices, medium, c=1,8,32 (n=8,16,32), non-stream  
- engine: vllm-omni fp16_talker (engine), YAML sha256 f311877370962813
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 2, error lines 19; KV: (StageEngineCoreProc_stage0_replica0 pid=108415) INFO 09-25 04:02:59 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 321 MiB, engine idle – MiB, released after: True
- bench commands: 0 (exit codes –); `P1_screen_fp16_talker/commands.sh`; duration 2.9 min
- **error:** wait_ready.py failed (2): error: speech -> 500: b'{"error":{"message":"EngineCore encountered an issue. See stack trace (above) for the root cause.","type":"InternalServerError","param":null,"code":500,"request_id":"speech-831e1c93a3845181","error_stage_id":0}}'

no bench_tts.py runs here (see the folder's own files)

## P1_screen_fp32_talker: failed

variant screen fp32_talker (engine): both voices, medium, c=1,8,32 (n=8,16,32), non-stream  
- engine: vllm-omni fp32_talker (engine), YAML sha256 86934d637fb4b67d
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 2, error lines 19; KV: (StageEngineCoreProc_stage0_replica0 pid=110480) INFO 09-25 04:05:53 [kv_cache_utils.py:1869] GPU KV cache size: 39,664 tokens, Maximum concurrency for 4,096 tokens per request: 9.68x
- GPU 0: baseline 320 MiB, engine idle – MiB, released after: True
- bench commands: 0 (exit codes –); `P1_screen_fp32_talker/commands.sh`; duration 2 min
- **error:** wait_ready.py failed (2): error: speech -> 500: b'{"error":{"message":"EngineCore encountered an issue. See stack trace (above) for the root cause.","type":"InternalServerError","param":null,"code":500,"request_id":"speech-8866d241d6d080e7","error_stage_id":0}}'

no bench_tts.py runs here (see the folder's own files)

## P1_screen_seqs32: DONE

variant screen seqs32 (engine): both voices, medium, c=1,8,32 (n=8,16,32), non-stream  
- engine: vllm-omni seqs32 (engine), YAML sha256 54fb9bcc9caeda96
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P1_screen_seqs32/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=112021) INFO 09-25 04:07:47 [kv_cache_utils.py:1869] GPU KV cache size: 91,136 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 320 MiB, engine idle 18964 MiB, released after: True
- bench commands: 1 (exit codes 0); `P1_screen_seqs32/commands.sh`; duration 2.4 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_medium_c1_n8_nonstream_inline](P1_screen_seqs32/trump_medium_c1_n8_nonstream_inline/) | trump | medium | 1 | 8 |  | inline | 0 | 0 | 1.11 / 1.85 / 1.9 | – | 6.77 | 5.37 | 5.37 | 0 | 0.188 | 0.79 | 18964 (18644) |
| [trump_medium_c8_n16_nonstream_inline](P1_screen_seqs32/trump_medium_c8_n16_nonstream_inline/) | trump | medium | 8 | 16 |  | inline | 0 | 0 | 2.84 / 3.6 / 4.29 | – | 6.38 | 15.89 | 15.17 | 0 | 0.479 | 2.49 | 19008 (18688) |
| [trump_medium_c32_n32_nonstream_inline](P1_screen_seqs32/trump_medium_c32_n32_nonstream_inline/) | trump | medium | 32 | 32 |  | inline | 0 | 0 | 6.39 / 7.12 / 7.58 | – | 6.41 | 26.85 | 24.84 | 0 | 1.022 | 4.19 | 19280 (18960) |
| [shehbaz_medium_c1_n8_nonstream_inline](P1_screen_seqs32/shehbaz_medium_c1_n8_nonstream_inline/) | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 2.29 / 2.39 / 2.6 | – | 10.64 | 5.47 | 5.47 | 0 | 0.184 | 0.51 | 19496 (19176) |
| [shehbaz_medium_c8_n16_nonstream_inline](P1_screen_seqs32/shehbaz_medium_c8_n16_nonstream_inline/) | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 4.3 / 5.53 / 5.62 | – | 10.49 | 17.24 | 16.86 | 0 | 0.417 | 1.64 | 19496 (19176) |
| [shehbaz_medium_c32_n32_nonstream_inline](P1_screen_seqs32/shehbaz_medium_c32_n32_nonstream_inline/) | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 8.52 / 9.72 / 10.15 | – | 9.51 | 29.95 | 26.97 | 0 | 0.918 | 3.15 | 19632 (19312) |

## P1_screen_seqs128: DONE

variant screen seqs128 (engine): both voices, medium, c=1,8,32 (n=8,16,32), non-stream  
- engine: vllm-omni seqs128 (engine), YAML sha256 00dcbf17ee68986d
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P1_screen_seqs128/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=116498) INFO 09-25 04:10:14 [kv_cache_utils.py:1869] GPU KV cache size: 91,104 tokens, Maximum concurrency for 4,096 tokens per request: 22.24x
- GPU 0: baseline 318 MiB, engine idle 19722 MiB, released after: True
- bench commands: 1 (exit codes 0); `P1_screen_seqs128/commands.sh`; duration 2.8 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_medium_c1_n8_nonstream_inline](P1_screen_seqs128/trump_medium_c1_n8_nonstream_inline/) | trump | medium | 1 | 8 |  | inline | 0 | 0 | 1.14 / 1.69 / 1.96 | – | 6.69 | 5.35 | 5.35 | 0 | 0.189 | 0.8 | 19722 (19404) |
| [trump_medium_c8_n16_nonstream_inline](P1_screen_seqs128/trump_medium_c8_n16_nonstream_inline/) | trump | medium | 8 | 16 |  | inline | 0 | 0 | 2.83 / 3.99 / 4.13 | – | 6.42 | 15.02 | 14.96 | 0 | 0.476 | 2.34 | 19766 (19448) |
| [trump_medium_c32_n32_nonstream_inline](P1_screen_seqs128/trump_medium_c32_n32_nonstream_inline/) | trump | medium | 32 | 32 |  | inline | 0 | 0 | 6.59 / 7.22 / 7.54 | – | 6.47 | 27.28 | 24.92 | 0 | 1.01 | 4.22 | 20046 (19728) |
| [shehbaz_medium_c1_n8_nonstream_inline](P1_screen_seqs128/shehbaz_medium_c1_n8_nonstream_inline/) | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 1.99 / 2.65 / 2.84 | – | 10.63 | 5.42 | 5.42 | 0 | 0.187 | 0.51 | 20270 (19952) |
| [shehbaz_medium_c8_n16_nonstream_inline](P1_screen_seqs128/shehbaz_medium_c8_n16_nonstream_inline/) | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 3.88 / 4.71 / 5.45 | – | 9.71 | 18.03 | 17.23 | 0 | 0.418 | 1.86 | 20272 (19954) |
| [shehbaz_medium_c32_n32_nonstream_inline](P1_screen_seqs128/shehbaz_medium_c32_n32_nonstream_inline/) | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 8.64 / 9.53 / 9.82 | – | 9.35 | 30.46 | 27.37 | 0 | 0.922 | 3.26 | 20278 (19960) |

## P1_screen_decode8: failed

variant screen decode8 (engine): both voices, medium, c=1,8,32 (n=8,16,32), non-stream  
- engine: vllm-omni decode8 (engine), YAML sha256 0667d2f4fa463a22
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 93; KV: (StageEngineCoreProc_stage0_replica0 pid=121156) INFO 09-25 04:13:06 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 324 MiB, engine idle – MiB, released after: True
- bench commands: 0 (exit codes –); `P1_screen_decode8/commands.sh`; duration 1.7 min
- **error:** engine exited (1) before it was ready; see /home/vector/Documents/abdullah_workspace/qwen-server/tts-reference-voices/server/logs/engine_P1_screen_decode8.log

no bench_tts.py runs here (see the folder's own files)

## P1_screen_decode8_m045: failed

variant screen decode8_m045 (engine): both voices, medium, c=1,8,32 (n=8,16,32), non-stream  
- engine: vllm-omni decode8_m045 (engine), YAML sha256 a878d025dac1360a
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 79; KV: (StageEngineCoreProc_stage0_replica0 pid=124859) INFO 09-25 04:16:27 [kv_cache_utils.py:1869] GPU KV cache size: 58,032 tokens, Maximum concurrency for 4,096 tokens per request: 14.17x
- GPU 0: baseline 335 MiB, engine idle – MiB, released after: True
- bench commands: 0 (exit codes –); `P1_screen_decode8_m045/commands.sh`; duration 0.8 min
- **error:** engine exited (1) before it was ready; see /home/vector/Documents/abdullah_workspace/qwen-server/tts-reference-voices/server/logs/engine_P1_screen_decode8_m045.log

no bench_tts.py runs here (see the folder's own files)

## P1_screen_default_m045: DONE

variant screen default_m045 (engine): both voices, medium, c=1,8,32 (n=8,16,32), non-stream  
- engine: vllm-omni default_m045 (engine), YAML sha256 5d3588d548f281f8
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P1_screen_default_m045/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=125769) INFO 09-25 04:17:15 [kv_cache_utils.py:1869] GPU KV cache size: 58,032 tokens, Maximum concurrency for 4,096 tokens per request: 14.17x
- GPU 0: baseline 335 MiB, engine idle 15563 MiB, released after: True
- bench commands: 1 (exit codes 0); `P1_screen_default_m045/commands.sh`; duration 1.8 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_medium_c1_n8_nonstream_inline](P1_screen_default_m045/trump_medium_c1_n8_nonstream_inline/) | trump | medium | 1 | 8 |  | inline | 0 | 0 | 1.1 / 1.63 / 1.63 | – | 6.28 | 5.34 | 5.34 | 0 | 0.189 | 0.85 | 15563 (15228) |
| [trump_medium_c8_n16_nonstream_inline](P1_screen_default_m045/trump_medium_c8_n16_nonstream_inline/) | trump | medium | 8 | 16 |  | inline | 0 | 0 | 2.52 / 3.26 / 3.4 | – | 6.21 | 15.8 | 16.16 | 0 | 0.44 | 2.55 | 15605 (15270) |
| [trump_medium_c32_n32_nonstream_inline](P1_screen_default_m045/trump_medium_c32_n32_nonstream_inline/) | trump | medium | 32 | 32 |  | inline | 0 | 0 | 5.98 / 6.79 / 7.3 | – | 6.33 | 27.57 | 25.62 | 0 | 0.996 | 4.35 | 15929 (15594) |
| [shehbaz_medium_c1_n8_nonstream_inline](P1_screen_default_m045/shehbaz_medium_c1_n8_nonstream_inline/) | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 2.25 / 2.3 / 2.71 | – | 10.61 | 5.47 | 5.47 | 0 | 0.183 | 0.52 | 16061 (15726) |
| [shehbaz_medium_c8_n16_nonstream_inline](P1_screen_default_m045/shehbaz_medium_c8_n16_nonstream_inline/) | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 4.28 / 4.71 / 4.76 | – | 9.9 | 17.38 | 17.22 | 0 | 0.411 | 1.76 | 16061 (15726) |
| [shehbaz_medium_c32_n32_nonstream_inline](P1_screen_default_m045/shehbaz_medium_c32_n32_nonstream_inline/) | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 8.74 / 9.76 / 10.29 | – | 9.68 | 30.08 | 27.67 | 0 | 0.92 | 3.11 | 16061 (15726) |

## P1_screen_decode4g_m045: DONE

variant screen decode4g_m045 (engine): both voices, medium, c=1,8,32 (n=8,16,32), non-stream  
- engine: vllm-omni decode4g_m045 (engine), YAML sha256 1c588965d7b29218
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P1_screen_decode4g_m045/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=129998) INFO 09-25 04:19:43 [kv_cache_utils.py:1869] GPU KV cache size: 58,032 tokens, Maximum concurrency for 4,096 tokens per request: 14.17x
- GPU 0: baseline 335 MiB, engine idle 20262 MiB, released after: True
- bench commands: 1 (exit codes 0); `P1_screen_decode4g_m045/commands.sh`; duration 2.7 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_medium_c1_n8_nonstream_inline](P1_screen_decode4g_m045/trump_medium_c1_n8_nonstream_inline/) | trump | medium | 1 | 8 |  | inline | 0 | 0 | 1.22 / 1.79 / 1.91 | – | 6.86 | 5.31 | 5.31 | 0 | 0.19 | 0.77 | 20284 (19949) |
| [trump_medium_c8_n16_nonstream_inline](P1_screen_decode4g_m045/trump_medium_c8_n16_nonstream_inline/) | trump | medium | 8 | 16 |  | inline | 0 | 0 | 2.85 / 3.43 / 4 | – | 6.22 | 15.6 | 15.05 | 0 | 0.492 | 2.51 | 20328 (19993) |
| [trump_medium_c32_n32_nonstream_inline](P1_screen_decode4g_m045/trump_medium_c32_n32_nonstream_inline/) | trump | medium | 32 | 32 |  | inline | 0 | 0 | 6.49 / 6.92 / 7.38 | – | 6.34 | 27.29 | 25.23 | 0 | 0.999 | 4.3 | 20608 (20273) |
| [shehbaz_medium_c1_n8_nonstream_inline](P1_screen_decode4g_m045/shehbaz_medium_c1_n8_nonstream_inline/) | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 2.3 / 2.35 / 2.69 | – | 10.56 | 5.41 | 5.41 | 0 | 0.187 | 0.51 | 20829 (20494) |
| [shehbaz_medium_c8_n16_nonstream_inline](P1_screen_decode4g_m045/shehbaz_medium_c8_n16_nonstream_inline/) | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 4.08 / 4.86 / 5.09 | – | 9.79 | 17.52 | 17.36 | 0 | 0.416 | 1.79 | 20827 (20492) |
| [shehbaz_medium_c32_n32_nonstream_inline](P1_screen_decode4g_m045/shehbaz_medium_c32_n32_nonstream_inline/) | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 8.56 / 9.58 / 9.91 | – | 9.57 | 30.75 | 28.12 | 0 | 0.894 | 3.21 | 20832 (20497) |

## P2_matrix: DONE

main throughput/latency matrix: both voices x short/medium/long/xlong/xxlong x c=1,2,4,8,16,32, non-stream, engine direct with the gateway's sampling and length cap (n: short/medium max(8,2c), long max(4,c), xlong max(6,c), xxlong max(4,c))  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P2_matrix/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 32; KV: (StageEngineCoreProc_stage0_replica0 pid=134995) INFO 09-25 04:23:22 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 335 MiB, engine idle 19144 MiB, released after: –; kept for the next phase
- bench commands: 5 (exit codes 0, 0, 0, 0, 0); `P2_matrix/commands.sh`; duration 19.5 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_short_c1_n8_nonstream_inline](P2_matrix/trump_short_c1_n8_nonstream_inline/) | trump | short | 1 | 8 |  | inline | 0 | 0 | 0.79 / 1 / 1.01 | – | 3.61 | 5.01 | 5.01 | 0 | 0.202 | 1.39 | 19144 (18809) |
| [trump_short_c2_n8_nonstream_inline](P2_matrix/trump_short_c2_n8_nonstream_inline/) | trump | short | 2 | 8 |  | inline | 0 | 0 | 0.63 / 1.14 / 1.16 | – | 2.74 | 8.13 | 8.13 | 0 | 0.253 | 2.97 | 19147 (18812) |
| [trump_short_c4_n8_nonstream_inline](P2_matrix/trump_short_c4_n8_nonstream_inline/) | trump | short | 4 | 8 |  | inline | 0 | 0 | 0.89 / 1.21 / 1.39 | – | 3 | 10.64 | 10.64 | 0 | 0.355 | 3.55 | 19167 (18832) |
| [trump_short_c8_n16_nonstream_inline](P2_matrix/trump_short_c8_n16_nonstream_inline/) | trump | short | 8 | 16 |  | inline | 0 | 1 (0s/1l) | 1.36 / 2.31 / 2.86 | – | 3.01 | 13.39 | 12.64 | 0 | 0.533 | 4.45 | 19195 (18860) |
| [trump_short_c16_n32_nonstream_inline](P2_matrix/trump_short_c16_n32_nonstream_inline/) | trump | short | 16 | 32 |  | inline | 0 | 1 (1s/0l) | 2.4 / 3.99 / 4.49 | – | 2.89 | 16.09 | 14.77 | 0 | 0.912 | 5.57 | 19235 (18900) |
| [trump_short_c32_n64_nonstream_inline](P2_matrix/trump_short_c32_n64_nonstream_inline/) | trump | short | 32 | 64 |  | inline | 0 | 0 | 3.64 / 5.97 / 6.85 | – | 2.97 | 20.85 | 18.44 | 0 | 1.397 | 7.01 | 19463 (19128) |
| [shehbaz_short_c1_n8_nonstream_inline](P2_matrix/shehbaz_short_c1_n8_nonstream_inline/) | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 1.05 / 1.22 / 1.35 | – | 5.06 | 5.13 | 5.13 | 0 | 0.195 | 1.01 | 19675 (19340) |
| [shehbaz_short_c2_n8_nonstream_inline](P2_matrix/shehbaz_short_c2_n8_nonstream_inline/) | shehbaz | short | 2 | 8 |  | inline | 0 | 0 | 0.94 / 1.06 / 1.18 | – | 3.6 | 8.04 | 8.04 | 0 | 0.243 | 2.23 | 19670 (19335) |
| [shehbaz_short_c4_n8_nonstream_inline](P2_matrix/shehbaz_short_c4_n8_nonstream_inline/) | shehbaz | short | 4 | 8 |  | inline | 0 | 1 (0s/1l) | 1.48 / 1.84 / 2.26 | – | 5.14 | 11.38 | 11.38 | 0 | 0.301 | 2.21 | 19678 (19343) |
| [shehbaz_short_c8_n16_nonstream_inline](P2_matrix/shehbaz_short_c8_n16_nonstream_inline/) | shehbaz | short | 8 | 16 |  | inline | 0 | 1 (0s/1l) | 1.82 / 2.69 / 3.39 | – | 3.94 | 14.89 | 13.65 | 0 | 0.5 | 3.79 | 19678 (19343) |
| [shehbaz_short_c16_n32_nonstream_inline](P2_matrix/shehbaz_short_c16_n32_nonstream_inline/) | shehbaz | short | 16 | 32 |  | inline | 0 | 3 (0s/3l) | 2.68 / 4.79 / 5.88 | – | 4.36 | 19.59 | 17.77 | 0 | 0.753 | 4.49 | 19670 (19335) |
| [shehbaz_short_c32_n64_nonstream_inline](P2_matrix/shehbaz_short_c32_n64_nonstream_inline/) | shehbaz | short | 32 | 64 |  | inline | 0 | 3 (0s/3l) | 4.36 / 7.52 / 9.27 | – | 4.1 | 22.48 | 21.36 | 0 | 1.263 | 5.49 | 19811 (19476) |
| [trump_medium_c1_n8_nonstream_inline](P2_matrix/trump_medium_c1_n8_nonstream_inline/) | trump | medium | 1 | 8 |  | inline | 0 | 0 | 1.2 / 1.66 / 1.84 | – | 6.96 | 5.31 | 5.31 | 0 | 0.19 | 0.76 | 19810 (19475) |
| [trump_medium_c2_n8_nonstream_inline](P2_matrix/trump_medium_c2_n8_nonstream_inline/) | trump | medium | 2 | 8 |  | inline | 0 | 0 | 1.33 / 1.58 / 1.68 | – | 6.29 | 9.45 | 9.45 | 0 | 0.21 | 1.5 | 19802 (19467) |
| [trump_medium_c4_n8_nonstream_inline](P2_matrix/trump_medium_c4_n8_nonstream_inline/) | trump | medium | 4 | 8 |  | inline | 0 | 0 | 1.71 / 1.93 / 3.06 | – | 6.48 | 12.29 | 12.29 | 0 | 0.289 | 1.9 | 19802 (19467) |
| [trump_medium_c8_n16_nonstream_inline](P2_matrix/trump_medium_c8_n16_nonstream_inline/) | trump | medium | 8 | 16 |  | inline | 0 | 0 | 2.54 / 3.84 / 3.98 | – | 6.24 | 16.96 | 16.24 | 0 | 0.444 | 2.72 | 19810 (19475) |
| [trump_medium_c16_n32_nonstream_inline](P2_matrix/trump_medium_c16_n32_nonstream_inline/) | trump | medium | 16 | 32 |  | inline | 0 | 0 | 4.31 / 5.42 / 7.12 | – | 6.96 | 23.48 | 21.68 | 0 | 0.635 | 3.37 | 19818 (19483) |
| [trump_medium_c32_n64_nonstream_inline](P2_matrix/trump_medium_c32_n64_nonstream_inline/) | trump | medium | 32 | 64 |  | inline | 0 | 0 | 6.43 / 8.49 / 11.86 | – | 6.85 | 28.31 | 26.9 | 0 | 1.009 | 4.13 | 19811 (19476) |
| [shehbaz_medium_c1_n8_nonstream_inline](P2_matrix/shehbaz_medium_c1_n8_nonstream_inline/) | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 2.27 / 2.59 / 2.67 | – | 10.82 | 5.4 | 5.4 | 0 | 0.185 | 0.5 | 19813 (19478) |
| [shehbaz_medium_c2_n8_nonstream_inline](P2_matrix/shehbaz_medium_c2_n8_nonstream_inline/) | shehbaz | medium | 2 | 8 |  | inline | 0 | 0 | 2.07 / 2.44 / 2.93 | – | 10.26 | 9.05 | 9.06 | 0 | 0.202 | 0.88 | 19810 (19475) |
| [shehbaz_medium_c4_n8_nonstream_inline](P2_matrix/shehbaz_medium_c4_n8_nonstream_inline/) | shehbaz | medium | 4 | 8 |  | inline | 0 | 0 | 2.54 / 3 / 3.37 | – | 9.68 | 13.04 | 13.05 | 0 | 0.279 | 1.35 | 19805 (19470) |
| [shehbaz_medium_c8_n16_nonstream_inline](P2_matrix/shehbaz_medium_c8_n16_nonstream_inline/) | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 3.94 / 4.92 / 5.03 | – | 9.57 | 17.05 | 17.16 | 0 | 0.422 | 1.78 | 19805 (19470) |
| [shehbaz_medium_c16_n32_nonstream_inline](P2_matrix/shehbaz_medium_c16_n32_nonstream_inline/) | shehbaz | medium | 16 | 32 |  | inline | 0 | 0 | 5.63 / 7 / 7.4 | – | 9.5 | 23.87 | 22.07 | 0 | 0.612 | 2.51 | 19805 (19470) |
| [shehbaz_medium_c32_n64_nonstream_inline](P2_matrix/shehbaz_medium_c32_n64_nonstream_inline/) | shehbaz | medium | 32 | 64 |  | inline | 0 | 0 | 9.13 / 12.2 / 13.79 | – | 10.38 | 30.85 | 28.34 | 0 | 0.954 | 2.97 | 19948 (19613) |
| [trump_long_c1_n4_nonstream_inline](P2_matrix/trump_long_c1_n4_nonstream_inline/) | trump | long | 1 | 4 |  | inline | 0 | 0 | 3.03 / 3.05 / 3.05 | – | 15.28 | 5.48 | 5.48 | 0 | 0.183 | 0.36 | 19954 (19619) |
| [trump_long_c2_n4_nonstream_inline](P2_matrix/trump_long_c2_n4_nonstream_inline/) | trump | long | 2 | 4 |  | inline | 0 | 0 | 3.03 / 3.47 / 3.47 | – | 15.82 | 9.89 | 9.89 | 0 | 0.196 | 0.63 | 19942 (19607) |
| [trump_long_c4_n4_nonstream_inline](P2_matrix/trump_long_c4_n4_nonstream_inline/) | trump | long | 4 | 4 |  | inline | 0 | 0 | 4.23 / 4.26 / 4.26 | – | 15.66 | 14.68 | 14.68 | 0 | 0.264 | 0.94 | 19939 (19604) |
| [trump_long_c8_n8_nonstream_inline](P2_matrix/trump_long_c8_n8_nonstream_inline/) | trump | long | 8 | 8 |  | inline | 0 | 0 | 6.01 / 6.39 / 6.43 | – | 15.39 | 19.13 | 19.13 | 0 | 0.392 | 1.24 | 19941 (19606) |
| [trump_long_c16_n16_nonstream_inline](P2_matrix/trump_long_c16_n16_nonstream_inline/) | trump | long | 16 | 16 |  | inline | 0 | 0 | 9.1 / 9.88 / 10.03 | – | 16.45 | 26.23 | 24.59 | 0 | 0.555 | 1.59 | 19937 (19602) |
| [trump_long_c32_n32_nonstream_inline](P2_matrix/trump_long_c32_n32_nonstream_inline/) | trump | long | 32 | 32 |  | inline | 0 | 0 | 14 / 15.04 / 15.32 | – | 16.38 | 34.16 | 30.78 | 0 | 0.847 | 2.09 | 19940 (19605) |
| [shehbaz_long_c1_n4_nonstream_inline](P2_matrix/shehbaz_long_c1_n4_nonstream_inline/) | shehbaz | long | 1 | 4 |  | inline | 0 | 0 | 4.25 / 4.38 / 4.38 | – | 22.28 | 5.57 | 5.57 | 0 | 0.179 | 0.25 | 19928 (19593) |
| [shehbaz_long_c2_n4_nonstream_inline](P2_matrix/shehbaz_long_c2_n4_nonstream_inline/) | shehbaz | long | 2 | 4 |  | inline | 0 | 0 | 4.14 / 4.77 / 4.77 | – | 22.12 | 10.05 | 10.05 | 0 | 0.192 | 0.45 | 19928 (19593) |
| [shehbaz_long_c4_n4_nonstream_inline](P2_matrix/shehbaz_long_c4_n4_nonstream_inline/) | shehbaz | long | 4 | 4 |  | inline | 0 | 0 | 5.98 / 6.08 / 6.08 | – | 22.62 | 14.84 | 14.84 | 0 | 0.256 | 0.66 | 19928 (19593) |
| [shehbaz_long_c8_n8_nonstream_inline](P2_matrix/shehbaz_long_c8_n8_nonstream_inline/) | shehbaz | long | 8 | 8 |  | inline | 0 | 0 | 8.51 / 8.91 / 9 | – | 22.07 | 19.59 | 19.6 | 0 | 0.383 | 0.89 | 19928 (19593) |
| [shehbaz_long_c16_n16_nonstream_inline](P2_matrix/shehbaz_long_c16_n16_nonstream_inline/) | shehbaz | long | 16 | 16 |  | inline | 0 | 0 | 12.28 / 12.72 / 12.85 | – | 22.27 | 27.68 | 26 | 0 | 0.536 | 1.24 | 19928 (19593) |
| [shehbaz_long_c32_n32_nonstream_inline](P2_matrix/shehbaz_long_c32_n32_nonstream_inline/) | shehbaz | long | 32 | 32 |  | inline | 0 | 0 | 17.79 / 19.57 / 20.3 | – | 22.05 | 34.7 | 31.75 | 0 | 0.824 | 1.57 | 20072 (19737) |
| [trump_xlong_c1_n6_nonstream_inline](P2_matrix/trump_xlong_c1_n6_nonstream_inline/) | trump | xlong | 1 | 6 |  | inline | 0 | 0 | 5.52 / 5.84 / 6.31 | – | 32.24 | 5.63 | 5.63 | 0 | 0.178 | 0.17 | 20072 (19737) |
| [trump_xlong_c2_n6_nonstream_inline](P2_matrix/trump_xlong_c2_n6_nonstream_inline/) | trump | xlong | 2 | 6 |  | inline | 0 | 0 | 5.93 / 5.99 / 6.59 | – | 31.79 | 10.52 | 10.52 | 0 | 0.189 | 0.33 | 20072 (19737) |
| [trump_xlong_c4_n6_nonstream_inline](P2_matrix/trump_xlong_c4_n6_nonstream_inline/) | trump | xlong | 4 | 6 |  | inline | 0 | 0 | 7.48 / 7.73 / 8.12 | – | 31.36 | 13.49 | 13.49 | 0 | 0.251 | 0.43 | 20072 (19737) |
| [trump_xlong_c8_n8_nonstream_inline](P2_matrix/trump_xlong_c8_n8_nonstream_inline/) | trump | xlong | 8 | 8 |  | inline | 0 | 0 | 11.76 / 13.56 / 15.35 | – | 34.43 | 17.93 | 17.93 | 0 | 0.376 | 0.52 | 20072 (19737) |
| [trump_xlong_c16_n16_nonstream_inline](P2_matrix/trump_xlong_c16_n16_nonstream_inline/) | trump | xlong | 16 | 16 |  | inline | 0 | 0 | 16.44 / 17.66 / 17.77 | – | 31.62 | 28.46 | 26.59 | 0 | 0.523 | 0.9 | 20073 (19738) |
| [trump_xlong_c32_n32_nonstream_inline](P2_matrix/trump_xlong_c32_n32_nonstream_inline/) | trump | xlong | 32 | 32 |  | inline | 0 | 0 | 25.41 / 26.88 / 30.5 | – | 32.7 | 34.26 | 33.91 | 0 | 0.798 | 1.05 | 20072 (19737) |
| [shehbaz_xlong_c1_n6_nonstream_inline](P2_matrix/shehbaz_xlong_c1_n6_nonstream_inline/) | shehbaz | xlong | 1 | 6 |  | inline | 0 | 0 | 5.89 / 6.23 / 6.26 | – | 32.2 | 5.62 | 5.62 | 0 | 0.178 | 0.17 | 20072 (19737) |
| [shehbaz_xlong_c2_n6_nonstream_inline](P2_matrix/shehbaz_xlong_c2_n6_nonstream_inline/) | shehbaz | xlong | 2 | 6 |  | inline | 0 | 0 | 6.25 / 6.99 / 7.01 | – | 34.15 | 10.12 | 10.12 | 0 | 0.19 | 0.3 | 20072 (19737) |
| [shehbaz_xlong_c4_n6_nonstream_inline](P2_matrix/shehbaz_xlong_c4_n6_nonstream_inline/) | shehbaz | xlong | 4 | 6 |  | inline | 0 | 0 | 7.79 / 8.92 / 9.04 | – | 32.29 | 13.58 | 13.58 | 0 | 0.253 | 0.42 | 20072 (19737) |
| [shehbaz_xlong_c8_n8_nonstream_inline](P2_matrix/shehbaz_xlong_c8_n8_nonstream_inline/) | shehbaz | xlong | 8 | 8 |  | inline | 0 | 0 | 13.48 / 13.82 / 14.41 | – | 35.33 | 19.59 | 19.59 | 0 | 0.375 | 0.55 | 20072 (19737) |
| [shehbaz_xlong_c16_n16_nonstream_inline](P2_matrix/shehbaz_xlong_c16_n16_nonstream_inline/) | shehbaz | xlong | 16 | 16 |  | inline | 1 | 0 | 16.61 / 18 / 18.3 | – | 31.9 | 20.62 | 26.11 | 0 | 0.525 | 0.65 | 20070 (19735) |
| [shehbaz_xlong_c32_n32_nonstream_inline](P2_matrix/shehbaz_xlong_c32_n32_nonstream_inline/) | shehbaz | xlong | 32 | 32 |  | inline | 0 | 0 | 26.49 / 28.04 / 28.66 | – | 32.81 | 36.57 | 33.3 | 0 | 0.804 | 1.11 | 20070 (19735) |
| [trump_xxlong_c1_n4_nonstream_inline](P2_matrix/trump_xxlong_c1_n4_nonstream_inline/) | trump | xxlong | 1 | 4 |  | inline | 0 | 0 | 11.15 / 11.97 / 11.97 | – | 63.1 | 5.67 | 5.67 | 0 | 0.177 | 0.09 | 20070 (19735) |
| [trump_xxlong_c2_n4_nonstream_inline](P2_matrix/trump_xxlong_c2_n4_nonstream_inline/) | trump | xxlong | 2 | 4 |  | inline | 0 | 0 | 11.66 / 11.74 / 11.74 | – | 61.84 | 10.57 | 10.57 | 0 | 0.188 | 0.17 | 20070 (19735) |
| [trump_xxlong_c4_n4_nonstream_inline](P2_matrix/trump_xxlong_c4_n4_nonstream_inline/) | trump | xxlong | 4 | 4 |  | inline | 0 | 0 | 15.37 / 16.15 / 16.15 | – | 62.12 | 15.38 | 15.38 | 0 | 0.25 | 0.25 | 20070 (19735) |
| [trump_xxlong_c8_n8_nonstream_inline](P2_matrix/trump_xxlong_c8_n8_nonstream_inline/) | trump | xxlong | 8 | 8 |  | inline | 0 | 0 | 22.67 / 23.49 / 23.68 | – | 61.26 | 20.69 | 20.69 | 0 | 0.372 | 0.34 | 20070 (19735) |
| [trump_xxlong_c16_n16_nonstream_inline](P2_matrix/trump_xxlong_c16_n16_nonstream_inline/) | trump | xxlong | 16 | 16 |  | inline | 0 | 0 | 31.8 / 35.72 / 38.32 | – | 64.36 | 26.86 | 26.25 | 0 | 0.516 | 0.42 | 20070 (19735) |
| [trump_xxlong_c32_n32_nonstream_inline](P2_matrix/trump_xxlong_c32_n32_nonstream_inline/) | trump | xxlong | 32 | 32 |  | inline | 0 | 0 | 49.46 / 51.45 / 56 | – | 63.62 | 36.32 | 34.75 | 0 | 0.788 | 0.57 | 20072 (19737) |
| [shehbaz_xxlong_c1_n4_nonstream_inline](P2_matrix/shehbaz_xxlong_c1_n4_nonstream_inline/) | shehbaz | xxlong | 1 | 4 |  | inline | 4 | 0 | – | – | – | 0 | 0 | 0 | – | 0 | 20072 (19737) |
| [shehbaz_xxlong_c2_n4_nonstream_inline](P2_matrix/shehbaz_xxlong_c2_n4_nonstream_inline/) | shehbaz | xxlong | 2 | 4 |  | inline | 2 | 0 | 7.31 / 7.76 / 7.76 | – | 39.84 | 2.17 | 2.17 | 1 | 0.189 | 0.05 | 20071 (19736) |
| [shehbaz_xxlong_c4_n4_nonstream_inline](P2_matrix/shehbaz_xxlong_c4_n4_nonstream_inline/) | shehbaz | xxlong | 4 | 4 |  | inline | 1 | 0 | 10.87 / 11.23 / 11.23 | – | 43.57 | 5.37 | 5.37 | 0 | 0.251 | 0.12 | 20071 (19736) |
| [shehbaz_xxlong_c8_n8_nonstream_inline](P2_matrix/shehbaz_xxlong_c8_n8_nonstream_inline/) | shehbaz | xxlong | 8 | 8 |  | inline | 1 | 0 | 15.96 / 25.05 / 25.71 | – | 55.95 | 12.09 | 12.09 | 0 | 0.375 | 0.22 | 20071 (19736) |
| [shehbaz_xxlong_c16_n16_nonstream_inline](P2_matrix/shehbaz_xxlong_c16_n16_nonstream_inline/) | shehbaz | xxlong | 16 | 16 |  | inline | 10 | 1 (1s/0l) | 27.3 / 36.28 / 42.27 | – | 55.55 | 5.44 | 5.54 | 0 | 0.514 | 0.1 | 20071 (19736) |
| [shehbaz_xxlong_c32_n32_nonstream_inline](P2_matrix/shehbaz_xxlong_c32_n32_nonstream_inline/) | shehbaz | xxlong | 32 | 32 |  | inline | 13 | 1 (1s/0l) | 33.91 / 51.23 / 57.88 | – | 49.58 | 11.97 | 12.05 | 0 | 0.798 | 0.24 | 20259 (19924) |

## P2_high_c: DONE

c=48,64: short/medium (n=2c) and xlong at c=64 (n=64). The 91k-token KV cache holds 64 xxlong takes; the long pool at 48/64 was measured in E01  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P2_high_c/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 2; KV: (StageEngineCoreProc_stage0_replica0 pid=307319) INFO 09-25 08:09:49 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 329 MiB, engine idle 19129 MiB, released after: –; kept for the next phase
- bench commands: 2 (exit codes 0, 0); `P2_high_c/commands.sh`; duration 6.8 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_short_c48_n96_nonstream_inline](P2_high_c/trump_short_c48_n96_nonstream_inline/) | trump | short | 48 | 96 |  | inline | 0 | 1 (0s/1l) | 5.73 / 9.42 / 11.43 | – | 2.97 | 20.95 | 18.89 | 0 | 2.124 | 7.06 | 19769 (19440) |
| [trump_short_c64_n128_nonstream_inline](P2_high_c/trump_short_c64_n128_nonstream_inline/) | trump | short | 64 | 128 |  | inline | 0 | 2 (1s/1l) | 6.66 / 11.43 / 14.19 | – | 3.01 | 23.05 | 21.34 | 0 | 2.595 | 7.66 | 19849 (19520) |
| [trump_medium_c48_n96_nonstream_inline](P2_high_c/trump_medium_c48_n96_nonstream_inline/) | trump | medium | 48 | 96 |  | inline | 0 | 0 | 9.13 / 13.25 / 15.15 | – | 6.41 | 28.24 | 26.25 | 0 | 1.594 | 4.4 | 19849 (19520) |
| [trump_medium_c64_n128_nonstream_inline](P2_high_c/trump_medium_c64_n128_nonstream_inline/) | trump | medium | 64 | 128 |  | inline | 0 | 0 | 12.26 / 16.46 / 20.75 | – | 6.76 | 31.78 | 29.11 | 0 | 1.847 | 4.7 | 19883 (19554) |
| [shehbaz_short_c48_n96_nonstream_inline](P2_high_c/shehbaz_short_c48_n96_nonstream_inline/) | shehbaz | short | 48 | 96 |  | inline | 0 | 0 | 6.98 / 11.33 / 14.57 | – | 4.2 | 23.78 | 21.66 | 0 | 1.931 | 5.66 | 19889 (19560) |
| [shehbaz_short_c64_n128_nonstream_inline](P2_high_c/shehbaz_short_c64_n128_nonstream_inline/) | shehbaz | short | 64 | 128 |  | inline | 0 | 1 (0s/1l) | 7.79 / 13.11 / 16.27 | – | 4.05 | 24.72 | 22.99 | 0 | 2.393 | 6.11 | 20135 (19806) |
| [shehbaz_medium_c48_n96_nonstream_inline](P2_high_c/shehbaz_medium_c48_n96_nonstream_inline/) | shehbaz | medium | 48 | 96 |  | inline | 0 | 0 | 13.48 / 18.45 / 20.91 | – | 10.03 | 30.43 | 28.56 | 0 | 1.493 | 3.03 | 20135 (19806) |
| [shehbaz_medium_c64_n128_nonstream_inline](P2_high_c/shehbaz_medium_c64_n128_nonstream_inline/) | shehbaz | medium | 64 | 128 |  | inline | 0 | 0 | 15.72 / 21.91 / 27.79 | – | 9.9 | 34.15 | 32.22 | 0 | 1.754 | 3.45 | 20399 (20070) |
| [trump_xlong_c64_n64_nonstream_inline](P2_high_c/trump_xlong_c64_n64_nonstream_inline/) | trump | xlong | 64 | 64 |  | inline | 0 | 0 | 45.7 / 48.02 / 49.53 | – | 32.3 | 40.26 | 38.07 | 0 | 1.436 | 1.25 | 20397 (20068) |
| [shehbaz_xlong_c64_n64_nonstream_inline](P2_high_c/shehbaz_xlong_c64_n64_nonstream_inline/) | shehbaz | xlong | 64 | 64 |  | inline | 2 | 1 (1s/0l) | 47.83 / 51.88 / 55.27 | – | 34.16 | 34.52 | 36.3 | 0 | 1.433 | 1.01 | 20407 (20078) |

## P3_stream: DONE

streaming (stream_format audio): TTFA past the WAV header and total latency; short/xlong x c=1..32, xxlong x c=1,8; the same cells (n) as P2, so stream vs non-stream compare run for run  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P2_matrix
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P3_stream/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 160
- GPU 0: baseline 335 MiB, engine idle 19144 MiB, released after: True
- bench commands: 3 (exit codes 0, 0, 0); `P3_stream/commands.sh`; duration 8.7 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_short_c1_n8_stream_inline](P3_stream/trump_short_c1_n8_stream_inline/) | trump | short | 1 | 8 | y | inline | 0 | 0 | 0.73 / 0.99 / 1 | 0.12 / 0.13 / 0.14 | 3.62 | 5.01 | 5.01 | 0 | 0.204 | 1.38 | 20258 (19923) |
| [trump_short_c2_n8_stream_inline](P3_stream/trump_short_c2_n8_stream_inline/) | trump | short | 2 | 8 | y | inline | 0 | 0 | 0.55 / 1.08 / 1.25 | 0.17 / 0.19 / 0.19 | 2.66 | 7.85 | 7.85 | 0 | 0.258 | 2.95 | 20262 (19927) |
| [trump_short_c4_n8_stream_inline](P3_stream/trump_short_c4_n8_stream_inline/) | trump | short | 4 | 8 | y | inline | 0 | 0 | 0.91 / 1.23 / 1.41 | 0.36 / 0.36 / 0.36 | 2.87 | 10.17 | 10.17 | 0 | 0.376 | 3.54 | 20262 (19927) |
| [trump_short_c8_n16_stream_inline](P3_stream/trump_short_c8_n16_stream_inline/) | trump | short | 8 | 16 | y | inline | 0 | 0 | 1.45 / 2.62 / 3.25 | 0.43 / 0.66 / 0.66 | 3.16 | 13.87 | 12.37 | 0 | 0.513 | 4.39 | 20271 (19936) |
| [trump_short_c16_n32_stream_inline](P3_stream/trump_short_c16_n32_stream_inline/) | trump | short | 16 | 32 | y | inline | 0 | 0 | 2.31 / 3.74 / 4.42 | 0.81 / 1.26 / 1.26 | 2.94 | 16.74 | 15.6 | 0 | 0.857 | 5.7 | 20276 (19941) |
| [trump_short_c32_n64_stream_inline](P3_stream/trump_short_c32_n64_stream_inline/) | trump | short | 32 | 64 | y | inline | 0 | 0 | 3.76 / 6.41 / 7.14 | 1.77 / 2.46 / 2.47 | 3.01 | 20.64 | 18.52 | 0 | 1.434 | 6.86 | 20276 (19941) |
| [shehbaz_short_c1_n8_stream_inline](P3_stream/shehbaz_short_c1_n8_stream_inline/) | shehbaz | short | 1 | 8 | y | inline | 0 | 1 (0s/1l) | 1.06 / 1.31 / 1.54 | 0.12 / 0.12 / 0.13 | 5.29 | 5.15 | 5.15 | 0 | 0.197 | 0.97 | 20271 (19936) |
| [shehbaz_short_c2_n8_stream_inline](P3_stream/shehbaz_short_c2_n8_stream_inline/) | shehbaz | short | 2 | 8 | y | inline | 0 | 0 | 0.92 / 1.13 / 1.14 | 0.14 / 0.2 / 0.2 | 3.56 | 8.03 | 8.03 | 0 | 0.243 | 2.26 | 20266 (19931) |
| [shehbaz_short_c4_n8_stream_inline](P3_stream/shehbaz_short_c4_n8_stream_inline/) | shehbaz | short | 4 | 8 | y | inline | 0 | 1 (0s/1l) | 1.56 / 2.08 / 2.54 | 0.36 / 0.37 / 0.38 | 5.38 | 11.68 | 11.68 | 0 | 0.299 | 2.17 | 20266 (19931) |
| [shehbaz_short_c8_n16_stream_inline](P3_stream/shehbaz_short_c8_n16_stream_inline/) | shehbaz | short | 8 | 16 | y | inline | 0 | 0 | 1.91 / 2.9 / 3.24 | 0.37 / 0.69 / 0.7 | 4.06 | 14.68 | 14.06 | 0 | 0.506 | 3.61 | 20266 (19931) |
| [shehbaz_short_c16_n32_stream_inline](P3_stream/shehbaz_short_c16_n32_stream_inline/) | shehbaz | short | 16 | 32 | y | inline | 0 | 1 (0s/1l) | 2.61 / 4.43 / 5.75 | 0.46 / 1.3 / 1.31 | 4.19 | 19.16 | 17.07 | 0 | 0.762 | 4.58 | 20274 (19939) |
| [shehbaz_short_c32_n64_stream_inline](P3_stream/shehbaz_short_c32_n64_stream_inline/) | shehbaz | short | 32 | 64 | y | inline | 0 | 1 (0s/1l) | 4.43 / 7.41 / 9.02 | 1.02 / 2.53 / 2.55 | 4.1 | 22.57 | 21.37 | 0 | 1.272 | 5.51 | 20276 (19941) |
| [trump_xlong_c1_n6_stream_inline](P3_stream/trump_xlong_c1_n6_stream_inline/) | trump | xlong | 1 | 6 | y | inline | 0 | 0 | 5.52 / 5.97 / 6.01 | 0.12 / 0.12 / 0.12 | 31.59 | 5.6 | 5.6 | 0 | 0.178 | 0.18 | 20275 (19940) |
| [trump_xlong_c2_n6_stream_inline](P3_stream/trump_xlong_c2_n6_stream_inline/) | trump | xlong | 2 | 6 | y | inline | 0 | 0 | 5.96 / 6.43 / 6.58 | 0.13 / 0.2 / 0.2 | 32.03 | 10.12 | 10.12 | 0 | 0.191 | 0.32 | 20274 (19939) |
| [trump_xlong_c4_n6_stream_inline](P3_stream/trump_xlong_c4_n6_stream_inline/) | trump | xlong | 4 | 6 | y | inline | 0 | 0 | 7.44 / 7.9 / 8.2 | 0.35 / 0.36 / 0.36 | 31.28 | 13.19 | 13.2 | 0 | 0.254 | 0.42 | 20278 (19943) |
| [trump_xlong_c8_n8_stream_inline](P3_stream/trump_xlong_c8_n8_stream_inline/) | trump | xlong | 8 | 8 | y | inline | 0 | 0 | 11.34 / 13.4 / 15.18 | 0.65 / 0.66 / 0.66 | 33.22 | 17.49 | 17.49 | 0 | 0.379 | 0.53 | 20275 (19940) |
| [trump_xlong_c16_n16_stream_inline](P3_stream/trump_xlong_c16_n16_stream_inline/) | trump | xlong | 16 | 16 | y | inline | 0 | 0 | 16.81 / 17.83 / 18.04 | 1.24 / 1.25 / 1.25 | 31.8 | 28.16 | 26.52 | 0 | 0.527 | 0.89 | 20275 (19940) |
| [trump_xlong_c32_n32_stream_inline](P3_stream/trump_xlong_c32_n32_stream_inline/) | trump | xlong | 32 | 32 | y | inline | 0 | 0 | 25.63 / 27.81 / 31.04 | 2.42 / 2.44 / 2.44 | 32.98 | 33.95 | 33.04 | 0 | 0.81 | 1.03 | 20272 (19937) |
| [shehbaz_xlong_c1_n6_stream_inline](P3_stream/shehbaz_xlong_c1_n6_stream_inline/) | shehbaz | xlong | 1 | 6 | y | inline | 0 | 0 | 5.69 / 5.99 / 6.17 | 0.12 / 0.14 / 0.14 | 32.16 | 5.58 | 5.58 | 0 | 0.179 | 0.17 | 20274 (19939) |
| [shehbaz_xlong_c2_n6_stream_inline](P3_stream/shehbaz_xlong_c2_n6_stream_inline/) | shehbaz | xlong | 2 | 6 | y | inline | 1 | 0 | 5.91 / 6.44 / 6.44 | 0.16 / 0.22 / 0.22 | 31.9 | 6.67 | 6.68 | 0 | 0.191 | 0.21 | 20276 (19941) |
| [shehbaz_xlong_c4_n6_stream_inline](P3_stream/shehbaz_xlong_c4_n6_stream_inline/) | shehbaz | xlong | 4 | 6 | y | inline | 1 | 0 | 8.55 / 9.01 / 9.01 | 0.35 / 0.36 / 0.36 | 32.94 | 8.34 | 8.34 | 0 | 0.256 | 0.25 | 20280 (19945) |
| [shehbaz_xlong_c8_n8_stream_inline](P3_stream/shehbaz_xlong_c8_n8_stream_inline/) | shehbaz | xlong | 8 | 8 | y | inline | 0 | 0 | 13.1 / 14.12 / 15.04 | 0.69 / 0.7 / 0.71 | 35.73 | 18.99 | 18.99 | 0 | 0.381 | 0.53 | 20274 (19939) |
| [shehbaz_xlong_c16_n16_stream_inline](P3_stream/shehbaz_xlong_c16_n16_stream_inline/) | shehbaz | xlong | 16 | 16 | y | inline | 0 | 0 | 17.33 / 18.46 / 18.48 | 1.25 / 1.27 / 1.27 | 32.38 | 27.99 | 26.09 | 0 | 0.533 | 0.86 | 20274 (19939) |
| [shehbaz_xlong_c32_n32_stream_inline](P3_stream/shehbaz_xlong_c32_n32_stream_inline/) | shehbaz | xlong | 32 | 32 | y | inline | 2 | 0 | 27.2 / 29.07 / 30.48 | 2.53 / 2.56 / 2.58 | 33.89 | 29.8 | 32.76 | 0 | 0.808 | 0.88 | 20276 (19941) |
| [trump_xxlong_c1_n4_stream_inline](P3_stream/trump_xxlong_c1_n4_stream_inline/) | trump | xxlong | 1 | 4 | y | inline | 0 | 0 | 10.92 / 11.24 / 11.24 | 0.13 / 0.13 / 0.13 | 61.96 | 5.67 | 5.67 | 0 | 0.176 | 0.09 | 20262 (19927) |
| [trump_xxlong_c8_n8_stream_inline](P3_stream/trump_xxlong_c8_n8_stream_inline/) | trump | xxlong | 8 | 8 | y | inline | 0 | 0 | 23.26 / 23.76 / 23.76 | 0.64 / 0.64 / 0.64 | 62.35 | 20.98 | 20.98 | 0 | 0.374 | 0.34 | 20262 (19927) |
| [shehbaz_xxlong_c1_n4_stream_inline](P3_stream/shehbaz_xxlong_c1_n4_stream_inline/) | shehbaz | xxlong | 1 | 4 | y | inline | 1 | 2 (2s/0l) | 6.87 / 8.8 / 8.8 | 0.13 / 0.13 / 0.13 | 41.65 | 2.49 | 2.49 | 1 | 0.178 | 0.06 | 20262 (19927) |
| [shehbaz_xxlong_c8_n8_stream_inline](P3_stream/shehbaz_xxlong_c8_n8_stream_inline/) | shehbaz | xxlong | 8 | 8 | y | inline | 3 | 4 (4s/0l) | 14.84 / 26.46 / 26.46 | 0.68 / 0.69 / 0.69 | 48.43 | 5.23 | 5.24 | 1 | 0.375 | 0.11 | 20262 (19927) |

## P4_voice_cache: DONE

voice-prompt cache on/off, engine direct, fresh engine: upload (registered) vs inline vs nocache; short, c=1,8,32 (n=8,16,32), non-stream; streaming (TTFA) for inline vs nocache  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P4_voice_cache/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=214807) INFO 09-25 04:51:32 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 316 MiB, engine idle 19128 MiB, released after: –; kept for the next phase
- bench commands: 5 (exit codes 0, 0, 0, 0, 0); `P4_voice_cache/commands.sh`; duration 4.1 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_short_c1_n8_nonstream_upload](P4_voice_cache/trump_short_c1_n8_nonstream_upload/) | trump | short | 1 | 8 |  | upload | 0 | 1 (0s/1l) | 0.78 / 0.98 / 0.99 | – | 3.61 | 5.08 | 5.08 | 0 | 0.203 | 1.41 | 19128 (18812) |
| [trump_short_c8_n16_nonstream_upload](P4_voice_cache/trump_short_c8_n16_nonstream_upload/) | trump | short | 8 | 16 |  | upload | 0 | 0 | 1.35 / 2.56 / 2.78 | – | 2.77 | 12.86 | 11.42 | 0 | 0.573 | 4.63 | 19168 (18852) |
| [trump_short_c32_n32_nonstream_upload](P4_voice_cache/trump_short_c32_n32_nonstream_upload/) | trump | short | 32 | 32 |  | upload | 0 | 0 | 3.76 / 4.58 / 4.78 | – | 3.04 | 20.35 | 17.59 | 0 | 1.424 | 6.69 | 19474 (19158) |
| [shehbaz_short_c1_n8_nonstream_upload](P4_voice_cache/shehbaz_short_c1_n8_nonstream_upload/) | shehbaz | short | 1 | 8 |  | upload | 0 | 0 | 0.9 / 1.17 / 1.6 | – | 4.94 | 5.22 | 5.22 | 0 | 0.194 | 1.06 | 19604 (19288) |
| [shehbaz_short_c8_n16_nonstream_upload](P4_voice_cache/shehbaz_short_c8_n16_nonstream_upload/) | shehbaz | short | 8 | 16 |  | upload | 0 | 0 | 2.19 / 2.91 / 3.02 | – | 4.82 | 14.84 | 14.11 | 0 | 0.507 | 3.08 | 19604 (19288) |
| [shehbaz_short_c32_n32_nonstream_upload](P4_voice_cache/shehbaz_short_c32_n32_nonstream_upload/) | shehbaz | short | 32 | 32 |  | upload | 0 | 0 | 4.2 / 5.92 / 6.25 | – | 4.33 | 22.18 | 19.21 | 0 | 1.167 | 5.12 | 19832 (19516) |
| [trump_short_c1_n8_nonstream_inline](P4_voice_cache/trump_short_c1_n8_nonstream_inline/) | trump | short | 1 | 8 |  | inline | 0 | 1 (0s/1l) | 0.72 / 1.14 / 1.21 | – | 3.8 | 5.05 | 5.05 | 0 | 0.201 | 1.33 | 19832 (19516) |
| [trump_short_c8_n16_nonstream_inline](P4_voice_cache/trump_short_c8_n16_nonstream_inline/) | trump | short | 8 | 16 |  | inline | 0 | 0 | 1.17 / 2.56 / 2.67 | – | 2.79 | 12.75 | 11.72 | 0 | 0.596 | 4.56 | 19832 (19516) |
| [trump_short_c32_n32_nonstream_inline](P4_voice_cache/trump_short_c32_n32_nonstream_inline/) | trump | short | 32 | 32 |  | inline | 0 | 0 | 3.89 / 4.77 / 4.8 | – | 3.08 | 20.47 | 17.34 | 0 | 1.405 | 6.64 | 19832 (19516) |
| [shehbaz_short_c1_n8_nonstream_inline](P4_voice_cache/shehbaz_short_c1_n8_nonstream_inline/) | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 1.04 / 1.15 / 1.3 | – | 4.81 | 5.13 | 5.13 | 0 | 0.2 | 1.07 | 19832 (19516) |
| [shehbaz_short_c8_n16_nonstream_inline](P4_voice_cache/shehbaz_short_c8_n16_nonstream_inline/) | shehbaz | short | 8 | 16 |  | inline | 0 | 0 | 2.01 / 2.9 / 3.27 | – | 4.69 | 14.95 | 13.99 | 0 | 0.52 | 3.19 | 19830 (19514) |
| [shehbaz_short_c32_n32_nonstream_inline](P4_voice_cache/shehbaz_short_c32_n32_nonstream_inline/) | shehbaz | short | 32 | 32 |  | inline | 0 | 0 | 4.54 / 5.66 / 6.19 | – | 4.39 | 22.42 | 20.29 | 0 | 1.148 | 5.11 | 19830 (19514) |
| [trump_short_c1_n8_nonstream_nocache](P4_voice_cache/trump_short_c1_n8_nonstream_nocache/) | trump | short | 1 | 8 |  | nocache | 0 | 1 (0s/1l) | 0.86 / 1 / 1.07 | – | 3.48 | 4.58 | 4.58 | 0 | 0.228 | 1.32 | 19829 (19513) |
| [trump_short_c8_n16_nonstream_nocache](P4_voice_cache/trump_short_c8_n16_nonstream_nocache/) | trump | short | 8 | 16 |  | nocache | 0 | 0 | 1.82 / 2.78 / 3.63 | – | 2.87 | 10.36 | 9.44 | 0 | 0.689 | 3.61 | 19828 (19512) |
| [trump_short_c32_n32_nonstream_nocache](P4_voice_cache/trump_short_c32_n32_nonstream_nocache/) | trump | short | 32 | 32 |  | nocache | 0 | 1 (0s/1l) | 6.19 / 7.32 / 7.61 | – | 3.07 | 12.77 | 11.53 | 0 | 2.263 | 4.16 | 19830 (19514) |
| [shehbaz_short_c1_n8_nonstream_nocache](P4_voice_cache/shehbaz_short_c1_n8_nonstream_nocache/) | shehbaz | short | 1 | 8 |  | nocache | 0 | 0 | 1.15 / 1.22 / 1.48 | – | 5.13 | 4.85 | 4.85 | 0 | 0.206 | 0.94 | 19830 (19514) |
| [shehbaz_short_c8_n16_nonstream_nocache](P4_voice_cache/shehbaz_short_c8_n16_nonstream_nocache/) | shehbaz | short | 8 | 16 |  | nocache | 0 | 0 | 2.47 / 3.78 / 4.04 | – | 4.47 | 12.1 | 11.37 | 0 | 0.552 | 2.71 | 19830 (19514) |
| [shehbaz_short_c32_n32_nonstream_nocache](P4_voice_cache/shehbaz_short_c32_n32_nonstream_nocache/) | shehbaz | short | 32 | 32 |  | nocache | 0 | 0 | 7.35 / 9.13 / 9.75 | – | 4.39 | 14.22 | 12.78 | 0 | 1.937 | 3.24 | 19830 (19514) |
| [trump_short_c1_n8_stream_inline](P4_voice_cache/trump_short_c1_n8_stream_inline/) | trump | short | 1 | 8 | y | inline | 0 | 0 | 0.74 / 0.97 / 1.01 | 0.11 / 0.12 / 0.12 | 3.67 | 5.03 | 5.03 | 0 | 0.196 | 1.37 | 19828 (19512) |
| [trump_short_c8_n16_stream_inline](P4_voice_cache/trump_short_c8_n16_stream_inline/) | trump | short | 8 | 16 | y | inline | 0 | 0 | 1.42 / 2.46 / 2.85 | 0.5 / 0.65 / 0.65 | 2.88 | 12.59 | 11.15 | 0 | 0.588 | 4.37 | 19828 (19512) |
| [trump_short_c32_n32_stream_inline](P4_voice_cache/trump_short_c32_n32_stream_inline/) | trump | short | 32 | 32 | y | inline | 0 | 1 (0s/1l) | 3.73 / 4.65 / 4.83 | 2.35 / 2.37 / 2.38 | 3.05 | 20.17 | 17.37 | 0 | 1.339 | 6.61 | 19830 (19514) |
| [shehbaz_short_c1_n8_stream_inline](P4_voice_cache/shehbaz_short_c1_n8_stream_inline/) | shehbaz | short | 1 | 8 | y | inline | 0 | 0 | 1.01 / 1.29 / 1.59 | 0.12 / 0.12 / 0.13 | 5.29 | 5.22 | 5.22 | 0 | 0.191 | 0.99 | 19830 (19514) |
| [shehbaz_short_c8_n16_stream_inline](P4_voice_cache/shehbaz_short_c8_n16_stream_inline/) | shehbaz | short | 8 | 16 | y | inline | 0 | 0 | 2.1 / 3.12 / 3.54 | 0.32 / 0.69 / 0.69 | 4.46 | 14.58 | 13.52 | 0 | 0.517 | 3.27 | 19830 (19514) |
| [shehbaz_short_c32_n32_stream_inline](P4_voice_cache/shehbaz_short_c32_n32_stream_inline/) | shehbaz | short | 32 | 32 | y | inline | 0 | 0 | 4.88 / 5.71 / 6.37 | 2.48 / 2.52 / 2.53 | 4.29 | 21.38 | 19.39 | 0 | 1.205 | 4.98 | 19830 (19514) |
| [trump_short_c1_n8_stream_nocache](P4_voice_cache/trump_short_c1_n8_stream_nocache/) | trump | short | 1 | 8 | y | nocache | 0 | 0 | 0.79 / 1.02 / 1.07 | 0.27 / 0.29 / 0.29 | 3.4 | 4.53 | 4.53 | 0 | 0.229 | 1.33 | 19829 (19513) |
| [trump_short_c8_n16_stream_nocache](P4_voice_cache/trump_short_c8_n16_stream_nocache/) | trump | short | 8 | 16 | y | nocache | 0 | 1 (0s/1l) | 1.78 / 2.78 / 3.51 | 1.45 / 1.47 / 1.64 | 2.87 | 10.03 | 9.19 | 0 | 0.716 | 3.49 | 19828 (19512) |
| [trump_short_c32_n32_stream_nocache](P4_voice_cache/trump_short_c32_n32_stream_nocache/) | trump | short | 32 | 32 | y | nocache | 0 | 0 | 6.24 / 7.46 / 7.76 | 6.17 / 6.2 / 6.23 | 3.13 | 12.77 | 11.25 | 0 | 2.358 | 4.08 | 19830 (19514) |
| [shehbaz_short_c1_n8_stream_nocache](P4_voice_cache/shehbaz_short_c1_n8_stream_nocache/) | shehbaz | short | 1 | 8 | y | nocache | 0 | 0 | 1.04 / 1.25 / 1.65 | 0.31 / 0.32 / 0.34 | 5.19 | 4.82 | 4.82 | 0 | 0.209 | 0.93 | 19830 (19514) |
| [shehbaz_short_c8_n16_stream_nocache](P4_voice_cache/shehbaz_short_c8_n16_stream_nocache/) | shehbaz | short | 8 | 16 | y | nocache | 0 | 0 | 2.64 / 3.73 / 3.87 | 0.66 / 1.76 / 1.96 | 4.65 | 12.42 | 11.24 | 0 | 0.554 | 2.67 | 19830 (19514) |
| [shehbaz_short_c32_n32_stream_nocache](P4_voice_cache/shehbaz_short_c32_n32_stream_nocache/) | shehbaz | short | 32 | 32 | y | nocache | 0 | 0 | 7.43 / 9.07 / 9.64 | 7.34 / 7.36 / 7.41 | 4.37 | 14.34 | 12.88 | 0 | 1.969 | 3.28 | 19830 (19514) |

## P5_urdu_rp105: DONE

repetition_penalty 1.05 per request (extra_params): shehbaz 43 prompts x 6 unseeded takes (c=16); trump control 43 x 1. Compare settings by prompt  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P4_voice_cache
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P5_urdu_rp105/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 7
- GPU 0: baseline 316 MiB, engine idle 19128 MiB, released after: –; kept for the next phase
- knob check `rp_1.05` (engine): OK {'base_a': None, 'fails_extra_rp_neg': 'refused', 'succeeds_extra_rp_1.05': 'accepted'}
- bench commands: 2 (exit codes 0, 0); `P5_urdu_rp105/commands.sh`; duration 5.9 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline](P5_urdu_rp105/rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline/) | shehbaz | prompts | 16 | 258 |  | inline | 7 | 1 (1s/0l) | 17.62 / 19.59 / 23.02 | – | 33.03 | 27.65 | 28.24 | 0 | 0.537 | 0.84 | 19830 (19514) |
| [rp1.05_trump_prompts_c16_n43_nonstream_inline](P5_urdu_rp105/rp1.05_trump_prompts_c16_n43_nonstream_inline/) | trump | prompts | 16 | 43 |  | inline | 0 | 0 | 16.13 / 19.05 / 27.04 | – | 32.22 | 28.01 | 25.97 | 0 | 0.53 | 0.87 | 19829 (19513) |

## P5_urdu_rp110: DONE

repetition_penalty 1.10 per request (extra_params): shehbaz 43 prompts x 6 unseeded takes (c=16). Compare settings by prompt  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P4_voice_cache
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P5_urdu_rp110/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 8
- GPU 0: baseline 316 MiB, engine idle 19128 MiB, released after: –; kept for the next phase
- knob check `rp_1.10` (engine): OK {'base_a': None, 'fails_extra_rp_neg': 'refused', 'succeeds_extra_rp_1.10': 'accepted'}
- bench commands: 1 (exit codes 0); `P5_urdu_rp110/commands.sh`; duration 5.2 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline](P5_urdu_rp110/rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline/) | shehbaz | prompts | 16 | 258 |  | inline | 8 | 1 (1s/0l) | 17.77 / 20.01 / 23.22 | – | 33.33 | 27.33 | 27.49 | 0 | 0.537 | 0.82 | 19845 (19529) |

## P5_urdu_rp115: DONE

repetition_penalty 1.15 per request (extra_params): shehbaz 43 prompts x 6 unseeded takes (c=16). Compare settings by prompt  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P4_voice_cache
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P5_urdu_rp115/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 13
- GPU 0: baseline 316 MiB, engine idle 19128 MiB, released after: –; kept for the next phase
- knob check `rp_1.15` (engine): OK {'base_a': None, 'fails_extra_rp_neg': 'refused', 'succeeds_extra_rp_1.15': 'accepted'}
- bench commands: 1 (exit codes 0); `P5_urdu_rp115/commands.sh`; duration 5.3 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline](P5_urdu_rp115/rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline/) | shehbaz | prompts | 16 | 258 |  | inline | 13 | 0 | 17.64 / 19.7 / 22.22 | – | 33.14 | 26.12 | 26.19 | 0 | 0.537 | 0.79 | 19832 (19516) |

## P5_urdu_rp120: DONE

repetition_penalty 1.20 per request (extra_params): shehbaz 43 prompts x 6 unseeded takes (c=16); trump control 43 x 1. Compare settings by prompt  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P4_voice_cache
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P5_urdu_rp120/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 12
- GPU 0: baseline 316 MiB, engine idle 19128 MiB, released after: –; kept for the next phase
- knob check `rp_1.20` (engine): OK {'base_a': None, 'fails_extra_rp_neg': 'refused', 'succeeds_extra_rp_1.20': 'accepted'}
- bench commands: 2 (exit codes 0, 0); `P5_urdu_rp120/commands.sh`; duration 6.1 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline](P5_urdu_rp120/rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline/) | shehbaz | prompts | 16 | 258 |  | inline | 12 | 1 (1s/0l) | 17.75 / 19.74 / 21.96 | – | 33.13 | 26.4 | 26.15 | 0 | 0.536 | 0.8 | 19829 (19513) |
| [rp1.20_trump_prompts_c16_n43_nonstream_inline](P5_urdu_rp120/rp1.20_trump_prompts_c16_n43_nonstream_inline/) | trump | prompts | 16 | 43 |  | inline | 0 | 0 | 16.54 / 19.46 / 27.41 | – | 32.28 | 28.24 | 25.83 | 0 | 0.529 | 0.87 | 19829 (19513) |

## P6_auralis: DONE

Auralis Urdu pools short/medium/long: n=20 c=20 (their default) engine direct and via the gateway, plus a sweep c=1,4,8,16,32 (n=max(8,c))  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P4_voice_cache
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P6_auralis/versions/`)
- gateway: {"TTS_RETRY_MAX": "0"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0
- GPU 0: baseline 316 MiB, engine idle 19128 MiB, released after: True; kept for the next phase
- bench commands: 3 (exit codes 0, 0, 0); `P6_auralis/commands.sh`; duration 2.7 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [n20c20_shehbaz_short_c20_n20_nonstream_inline](P6_auralis/n20c20_shehbaz_short_c20_n20_nonstream_inline/) | shehbaz | short | 20 | 20 |  | inline | 0 | 0 | 3.19 / 3.43 / 3.47 | – | 3.36 | 19.25 | 17.1 | 0 | 0.963 | 5.74 | 19831 (19515) |
| [n20c20_shehbaz_medium_c20_n20_nonstream_inline](P6_auralis/n20c20_shehbaz_medium_c20_n20_nonstream_inline/) | shehbaz | medium | 20 | 20 |  | inline | 0 | 0 | 5.13 / 5.28 / 5.35 | – | 5.92 | 22.04 | 19.5 | 0 | 0.805 | 3.72 | 19829 (19513) |
| [n20c20_shehbaz_long_c20_n20_nonstream_inline](P6_auralis/n20c20_shehbaz_long_c20_n20_nonstream_inline/) | shehbaz | long | 20 | 20 |  | inline | 0 | 0 | 11.21 / 11.78 / 12.31 | – | 16.3 | 26.37 | 24.29 | 0 | 0.691 | 1.62 | 19828 (19512) |
| [sweep_shehbaz_short_c1_n8_nonstream_inline](P6_auralis/sweep_shehbaz_short_c1_n8_nonstream_inline/) | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 0.69 / 0.78 / 0.8 | – | 3.38 | 4.86 | 4.86 | 0 | 0.204 | 1.44 | 19826 (19510) |
| [sweep_shehbaz_short_c4_n8_nonstream_inline](P6_auralis/sweep_shehbaz_short_c4_n8_nonstream_inline/) | shehbaz | short | 4 | 8 |  | inline | 0 | 0 | 1.09 / 1.17 / 1.46 | – | 3.19 | 11.11 | 11.11 | 0 | 0.331 | 3.48 | 19826 (19510) |
| [sweep_shehbaz_short_c8_n8_nonstream_inline](P6_auralis/sweep_shehbaz_short_c8_n8_nonstream_inline/) | shehbaz | short | 8 | 8 |  | inline | 0 | 0 | 1.65 / 1.76 / 1.82 | – | 3.28 | 14.25 | 14.25 | 0 | 0.51 | 4.34 | 19826 (19510) |
| [sweep_shehbaz_short_c16_n16_nonstream_inline](P6_auralis/sweep_shehbaz_short_c16_n16_nonstream_inline/) | shehbaz | short | 16 | 16 |  | inline | 0 | 0 | 2.55 / 2.84 / 2.87 | – | 3.35 | 18.6 | 17.36 | 0 | 0.769 | 5.56 | 19828 (19512) |
| [sweep_shehbaz_short_c32_n32_nonstream_inline](P6_auralis/sweep_shehbaz_short_c32_n32_nonstream_inline/) | shehbaz | short | 32 | 32 |  | inline | 0 | 0 | 4.28 / 4.68 / 4.77 | – | 3.43 | 22.85 | 20.42 | 0 | 1.239 | 6.67 | 19828 (19512) |
| [sweep_shehbaz_medium_c1_n8_nonstream_inline](P6_auralis/sweep_shehbaz_medium_c1_n8_nonstream_inline/) | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 0.8 / 1.34 / 1.5 | – | 5.07 | 5.18 | 5.18 | 0 | 0.196 | 1.02 | 19829 (19513) |
| [sweep_shehbaz_medium_c4_n8_nonstream_inline](P6_auralis/sweep_shehbaz_medium_c4_n8_nonstream_inline/) | shehbaz | medium | 4 | 8 |  | inline | 0 | 0 | 1.97 / 2.24 / 2.25 | – | 6.68 | 13.8 | 13.81 | 0 | 0.283 | 2.07 | 19828 (19512) |
| [sweep_shehbaz_medium_c8_n8_nonstream_inline](P6_auralis/sweep_shehbaz_medium_c8_n8_nonstream_inline/) | shehbaz | medium | 8 | 8 |  | inline | 0 | 0 | 3.02 / 3.11 / 3.25 | – | 6.99 | 17.14 | 17.15 | 0 | 0.433 | 2.45 | 19828 (19512) |
| [sweep_shehbaz_medium_c16_n16_nonstream_inline](P6_auralis/sweep_shehbaz_medium_c16_n16_nonstream_inline/) | shehbaz | medium | 16 | 16 |  | inline | 0 | 0 | 4.45 / 4.83 / 5.04 | – | 7.2 | 22.61 | 21.74 | 0 | 0.626 | 3.14 | 19829 (19513) |
| [sweep_shehbaz_medium_c32_n32_nonstream_inline](P6_auralis/sweep_shehbaz_medium_c32_n32_nonstream_inline/) | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 7.14 / 7.8 / 7.94 | – | 7.38 | 29.72 | 26.81 | 0 | 0.981 | 4.03 | 19829 (19513) |
| [sweep_shehbaz_long_c1_n8_nonstream_inline](P6_auralis/sweep_shehbaz_long_c1_n8_nonstream_inline/) | shehbaz | long | 1 | 8 |  | inline | 0 | 0 | 2.95 / 3.36 / 3.61 | – | 16.31 | 5.55 | 5.55 | 0 | 0.18 | 0.34 | 19829 (19513) |
| [sweep_shehbaz_long_c4_n8_nonstream_inline](P6_auralis/sweep_shehbaz_long_c4_n8_nonstream_inline/) | shehbaz | long | 4 | 8 |  | inline | 0 | 0 | 4.35 / 4.65 / 4.76 | – | 16.39 | 14.38 | 14.38 | 0 | 0.262 | 0.88 | 19829 (19513) |
| [sweep_shehbaz_long_c8_n8_nonstream_inline](P6_auralis/sweep_shehbaz_long_c8_n8_nonstream_inline/) | shehbaz | long | 8 | 8 |  | inline | 0 | 0 | 6.57 / 7.15 / 7.58 | – | 17.13 | 18.07 | 18.08 | 0 | 0.391 | 1.06 | 19828 (19512) |
| [sweep_shehbaz_long_c16_n16_nonstream_inline](P6_auralis/sweep_shehbaz_long_c16_n16_nonstream_inline/) | shehbaz | long | 16 | 16 |  | inline | 0 | 0 | 8.75 / 9.38 / 9.77 | – | 15.76 | 25.7 | 24.63 | 0 | 0.55 | 1.63 | 19828 (19512) |
| [sweep_shehbaz_long_c32_n32_nonstream_inline](P6_auralis/sweep_shehbaz_long_c32_n32_nonstream_inline/) | shehbaz | long | 32 | 32 |  | inline | 0 | 0 | 13.97 / 14.84 / 15.24 | – | 16.2 | 33.86 | 30.9 | 0 | 0.848 | 2.09 | 19829 (19513) |
| [gw_n20c20_shehbaz_short_c20_n20_nonstream_server](P6_auralis/gw_n20c20_shehbaz_short_c20_n20_nonstream_server/) | shehbaz | short | 20 | 20 |  | server | 0 | 0 | 3.19 / 3.39 / 3.44 | – | 3.31 | 19.21 | 17.11 | 0 | 0.938 | 5.8 | 19829 (19513) |
| [gw_n20c20_shehbaz_medium_c20_n20_nonstream_server](P6_auralis/gw_n20c20_shehbaz_medium_c20_n20_nonstream_server/) | shehbaz | medium | 20 | 20 |  | server | 0 | 0 | 4.87 / 5.14 / 5.2 | – | 5.88 | 22.57 | 19.95 | 0 | 0.77 | 3.84 | 19828 (19512) |
| [gw_n20c20_shehbaz_long_c20_n20_nonstream_server](P6_auralis/gw_n20c20_shehbaz_long_c20_n20_nonstream_server/) | shehbaz | long | 20 | 20 |  | server | 0 | 0 | 11.16 / 11.59 / 12.31 | – | 16.06 | 26.08 | 24.28 | 0 | 0.689 | 1.62 | 19828 (19512) |

## P7_gateway: DONE

gateway overhead (short, c=1,16, n=8,32: engine direct vs gateway retries 0) and live retries (shehbaz long c=32 n=64, where E01 saw runaways: engine direct with the cap vs gateway retries 1)  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P4_voice_cache
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P7_gateway/versions/`)
- gateway: {"TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 1
- GPU 0: baseline 316 MiB, engine idle 19128 MiB, released after: True; kept for the next phase
- bench commands: 4 (exit codes 0, 0, 0, 0); `P7_gateway/commands.sh`; duration 2.5 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [direct_trump_short_c1_n8_nonstream_inline](P7_gateway/direct_trump_short_c1_n8_nonstream_inline/) | trump | short | 1 | 8 |  | inline | 0 | 1 (0s/1l) | 0.71 / 1 / 1.14 | – | 3.64 | 5.02 | 5.02 | 0 | 0.203 | 1.38 | 19829 (19513) |
| [direct_trump_short_c16_n32_nonstream_inline](P7_gateway/direct_trump_short_c16_n32_nonstream_inline/) | trump | short | 16 | 32 |  | inline | 0 | 1 (0s/1l) | 2.22 / 3.71 / 4.33 | – | 2.89 | 17.24 | 15.22 | 0 | 0.843 | 5.96 | 19829 (19513) |
| [direct_shehbaz_short_c1_n8_nonstream_inline](P7_gateway/direct_shehbaz_short_c1_n8_nonstream_inline/) | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 1 / 1.04 / 1.2 | – | 4.86 | 5.17 | 5.17 | 0 | 0.194 | 1.06 | 19829 (19513) |
| [direct_shehbaz_short_c16_n32_nonstream_inline](P7_gateway/direct_shehbaz_short_c16_n32_nonstream_inline/) | shehbaz | short | 16 | 32 |  | inline | 0 | 0 | 2.7 / 5.1 / 6.11 | – | 4.31 | 19.75 | 19.19 | 0 | 0.726 | 4.59 | 19829 (19513) |
| [gw_r0_trump_short_c1_n8_nonstream_server](P7_gateway/gw_r0_trump_short_c1_n8_nonstream_server/) | trump | short | 1 | 8 |  | server | 0 | 1 (0s/1l) | 0.71 / 1 / 1.05 | – | 3.49 | 5 | 5 | 0 | 0.212 | 1.43 | 19828 (19512) |
| [gw_r0_trump_short_c16_n32_nonstream_server](P7_gateway/gw_r0_trump_short_c16_n32_nonstream_server/) | trump | short | 16 | 32 |  | server | 0 | 0 | 2.15 / 3.58 / 4.4 | – | 2.95 | 17.85 | 15.94 | 0 | 0.859 | 6.05 | 19828 (19512) |
| [gw_r0_shehbaz_short_c1_n8_nonstream_server](P7_gateway/gw_r0_shehbaz_short_c1_n8_nonstream_server/) | shehbaz | short | 1 | 8 |  | server | 0 | 0 | 1.03 / 1.12 / 1.3 | – | 4.74 | 5.12 | 5.12 | 0 | 0.199 | 1.08 | 19828 (19512) |
| [gw_r0_shehbaz_short_c16_n32_nonstream_server](P7_gateway/gw_r0_shehbaz_short_c16_n32_nonstream_server/) | shehbaz | short | 16 | 32 |  | server | 0 | 0 | 2.73 / 4.36 / 5.56 | – | 4.25 | 20.36 | 18.92 | 0 | 0.732 | 4.8 | 19828 (19512) |
| [direct_shehbaz_long_c32_n64_nonstream_inline](P7_gateway/direct_shehbaz_long_c32_n64_nonstream_inline/) | shehbaz | long | 32 | 64 |  | inline | 0 | 0 | 18.51 / 20.83 / 21.74 | – | 22.22 | 36.13 | 32.85 | 0 | 0.85 | 1.63 | 19829 (19513) |
| [gw_r1_shehbaz_long_c32_n64_nonstream_server](P7_gateway/gw_r1_shehbaz_long_c32_n64_nonstream_server/) | shehbaz | long | 32 | 64 |  | server | 0 | 0 | 18.34 / 21.13 / 24.59 | – | 22.05 | 30.94 | 32.81 | 0 | 0.849 | 1.4 | 19829 (19513) |

## X1_nsm: DONE

non_streaming_mode=true (text not interleaved over the reference frames; source: serving_speech.py L2577 -> prompt_embeds_builder.py L952-963, Base default false): shehbaz 43 prompts x 1 take, vs P5_urdu_rp105  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P4_voice_cache
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `X1_nsm/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0
- GPU 0: baseline 316 MiB, engine idle 19128 MiB, released after: –; kept for the next phase
- knob check `non_streaming_mode` (engine): OK {'base_a': None, 'fails_nsm_invalid': 'refused', 'succeeds_nsm_true': 'accepted'}
- bench commands: 1 (exit codes 0); `X1_nsm/commands.sh`; duration 1 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [nsm_true_shehbaz_prompts_c16_n43_nonstream_inline](X1_nsm/nsm_true_shehbaz_prompts_c16_n43_nonstream_inline/) | shehbaz | prompts | 16 | 43 |  | inline | 0 | 0 | 18.7 / 21.54 / 25.12 | – | 35.17 | 26.57 | 24.39 | 0 | 0.553 | 0.76 | 19829 (19513) |

## X6_nsm_long_urdu: DONE

P2 found 31/68 shehbaz xxlong (~200 words, ~55 s) takes without EOS (hit the cap) vs 1/38 at xlong and 0 for English. Hypothesis: with non_streaming_mode=false the text beyond the reference is fed one token per frame (12.5/s) and Urdu needs ~3.2 tokens/word, so the feed barely stays ahead of the speech. Paired arms, same 43 xxlong texts, c=16: non_streaming_mode false (default) vs true; plus xlong true  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P2_high_c
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `X6_nsm_long_urdu/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 16
- GPU 0: baseline 329 MiB, engine idle 19129 MiB, released after: –; kept for the next phase
- knob check `non_streaming_mode` (engine): OK {'base_a': None, 'fails_nsm_invalid': 'refused', 'succeeds_nsm_true': 'accepted'}
- bench commands: 3 (exit codes 0, 0, 0); `X6_nsm_long_urdu/commands.sh`; duration 6.1 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [nsm_false_shehbaz_xxlong_c16_n43_nonstream_inline](X6_nsm_long_urdu/nsm_false_shehbaz_xxlong_c16_n43_nonstream_inline/) | shehbaz | xxlong | 16 | 43 |  | inline | 16 | 14 (14s/0l) | 21.73 / 40.27 / 53.66 | – | 53.21 | 9.8 | 10.07 | 14 | 0.527 | 0.18 | 20408 (20079) |
| [nsm_true_shehbaz_xxlong_c16_n43_nonstream_inline](X6_nsm_long_urdu/nsm_true_shehbaz_xxlong_c16_n43_nonstream_inline/) | shehbaz | xxlong | 16 | 43 |  | inline | 0 | 0 | 36.12 / 41.5 / 61.08 | – | 68.84 | 27.1 | 24.96 | 0 | 0.552 | 0.39 | 20407 (20078) |
| [nsm_true_trump_xxlong_c16_n43_nonstream_inline](X6_nsm_long_urdu/nsm_true_trump_xxlong_c16_n43_nonstream_inline/) | trump | xxlong | 16 | 43 |  | inline | 0 | 0 | 33.69 / 36.35 / 49.55 | – | 64.44 | 27.59 | 25.45 | 0 | 0.538 | 0.43 | 20406 (20077) |

## X7_split_off: DONE

gateway sentence splitting off (TTS_SPLIT_WORDS=0; parts run in parallel on free slots), retries 0: shehbaz + trump xxlong (~200 words), 43 texts each, c=8 -- failure rate, skips and latency of long texts with and without splitting (P2: 31/68 unsplit shehbaz xxlong takes hit the cap)  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P2_high_c
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `X7_split_off/versions/`)
- gateway: {"TTS_RETRY_MAX": "0", "TTS_SPLIT_WORDS": "0"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 18
- GPU 0: baseline 329 MiB, engine idle 19129 MiB, released after: True; kept for the next phase
- knob check `split_off` (gateway): OK {'base_a': None}
- bench commands: 2 (exit codes 0, 0); `X7_split_off/commands.sh`; duration 5.5 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [split_off_shehbaz_xxlong_c8_n43_nonstream_server](X7_split_off/split_off_shehbaz_xxlong_c8_n43_nonstream_server/) | shehbaz | xxlong | 8 | 43 |  | server | 18 | 16 (16s/0l) | 15.66 / 23.99 / 34.39 | – | 47.01 | 6.11 | 6.66 | 15 | 0.38 | 0.13 | 20406 (20077) |
| [split_off_trump_xxlong_c8_n43_nonstream_server](X7_split_off/split_off_trump_xxlong_c8_n43_nonstream_server/) | trump | xxlong | 8 | 43 |  | server | 0 | 0 | 23 / 25.59 / 33.55 | – | 62.66 | 20.54 | 20.04 | 0 | 0.377 | 0.33 | 20406 (20077) |

## X7_split_60: DONE

gateway sentence splitting 60 (TTS_SPLIT_WORDS=60; parts run in parallel on free slots), retries 0: shehbaz + trump xxlong (~200 words), 43 texts each, c=8 -- failure rate, skips and latency of long texts with and without splitting (P2: 31/68 unsplit shehbaz xxlong takes hit the cap)  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P2_high_c
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `X7_split_60/versions/`)
- gateway: {"TTS_RETRY_MAX": "0", "TTS_SPLIT_WORDS": "60"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0
- GPU 0: baseline 329 MiB, engine idle 19129 MiB, released after: True
- knob check `split_60` (gateway): OK {'base_a': None}
- bench commands: 2 (exit codes 0, 0); `X7_split_60/commands.sh`; duration 3.2 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [split_60_shehbaz_xxlong_c8_n43_nonstream_server](X7_split_60/split_60_shehbaz_xxlong_c8_n43_nonstream_server/) | shehbaz | xxlong | 8 | 43 |  | server | 0 | 0 | 16.83 / 18.81 / 21.11 | – | 70.63 | 31.95 | 31.71 | 0 | 0.236 | 0.45 | 20407 (20078) |
| [split_60_trump_xxlong_c8_n43_nonstream_server](X7_split_60/split_60_trump_xxlong_c8_n43_nonstream_server/) | trump | xxlong | 8 | 43 |  | server | 0 | 0 | 14.26 / 16.55 / 52.29 | – | 65.33 | 31.68 | 30.51 | 1 | 0.224 | 0.48 | 20406 (20077) |

## P5_urdu_nsm: DONE

non_streaming_mode=true at scale: shehbaz 43 prompts x 6 unseeded takes (c=16), rp 1.05, paired by prompt with P5_urdu_rp105 (X1 had 7.0% severe vs 15.5% in one take per prompt; this measures it with K=6 and feeds the retry simulation)  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P5_urdu_nsm/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 5; KV: (StageEngineCoreProc_stage0_replica0 pid=452686) INFO 09-25 11:15:07 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 325 MiB, engine idle 19128 MiB, released after: –; kept for the next phase
- knob check `non_streaming_mode` (engine): OK {'base_a': None, 'fails_nsm_invalid': 'refused', 'succeeds_nsm_true': 'accepted'}
- bench commands: 1 (exit codes 0); `P5_urdu_nsm/commands.sh`; duration 6.4 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [nsm_rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline](P5_urdu_nsm/nsm_rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline/) | shehbaz | prompts | 16 | 258 |  | inline | 5 | 0 | 19.7 / 22.22 / 24.69 | – | 35.29 | 26.93 | 26.92 | 0 | 0.564 | 0.76 | 19661 (19336) |

## X8_split_nsm: DONE

long Urdu (shehbaz xxlong, 43 texts, c=8) through the gateway with BOTH sentence splitting (60 words) and non_streaming_mode=true for Urdu; compare X6 nsm_true (16% severe) and X7 split_60 (23% severe)  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P5_urdu_nsm
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `X8_split_nsm/versions/`)
- gateway: {"TTS_RETRY_MAX": "0", "TTS_SPLIT_WORDS": "60", "TTS_NON_STREAMING_MODE_LANGS": "ur"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0
- GPU 0: baseline 325 MiB, engine idle 19128 MiB, released after: True
- knob check `split_nsm` (gateway): OK {'base_a': None}
- bench commands: 1 (exit codes 0); `X8_split_nsm/commands.sh`; duration 1.9 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [split60_nsm_shehbaz_xxlong_c8_n43_nonstream_server](X8_split_nsm/split60_nsm_shehbaz_xxlong_c8_n43_nonstream_server/) | shehbaz | xxlong | 8 | 43 |  | server | 0 | 0 | 18.88 / 21.96 / 24.07 | – | 75.48 | 30.56 | 30.3 | 0 | 0.256 | 0.4 | 20201 (19876) |

## X9_nsm_stream: DONE

does non_streaming_mode=true (whole text in the prefill) cost streaming TTFA? shehbaz short + xlong, streaming, c=1,8 (n=8), nsm true vs the default  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `X9_nsm_stream/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 20; KV: (StageEngineCoreProc_stage0_replica0 pid=470301) INFO 09-25 11:34:35 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 322 MiB, engine idle 19131 MiB, released after: True
- bench commands: 2 (exit codes 0, 0); `X9_nsm_stream/commands.sh`; duration 3.5 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [nsm_default_shehbaz_short_c1_n8_stream_inline](X9_nsm_stream/nsm_default_shehbaz_short_c1_n8_stream_inline/) | shehbaz | short | 1 | 8 | y | inline | 0 | 0 | 0.98 / 1.31 / 1.41 | 0.12 / 0.12 / 0.13 | 4.95 | 5.18 | 5.18 | 0 | 0.192 | 1.05 | 19434 (19112) |
| [nsm_default_shehbaz_short_c8_n8_stream_inline](X9_nsm_stream/nsm_default_shehbaz_short_c8_n8_stream_inline/) | shehbaz | short | 8 | 8 | y | inline | 0 | 0 | 1.84 / 2.05 / 2.12 | 0.68 / 0.69 / 0.69 | 3.57 | 13.44 | 13.44 | 0 | 0.472 | 3.76 | 19471 (19149) |
| [nsm_default_shehbaz_xlong_c1_n8_stream_inline](X9_nsm_stream/nsm_default_shehbaz_xlong_c1_n8_stream_inline/) | shehbaz | xlong | 1 | 8 | y | inline | 1 | 0 | 6.34 / 6.56 / 6.73 | 0.12 / 0.12 / 0.13 | 35.26 | 4.26 | 4.26 | 0 | 0.178 | 0.12 | 19472 (19150) |
| [nsm_default_shehbaz_xlong_c8_n8_stream_inline](X9_nsm_stream/nsm_default_shehbaz_xlong_c8_n8_stream_inline/) | shehbaz | xlong | 8 | 8 | y | inline | 0 | 0 | 12.74 / 13.11 / 13.93 | 0.68 / 0.68 / 0.69 | 33.6 | 19.3 | 19.3 | 0 | 0.379 | 0.57 | 19476 (19154) |
| [nsm_true_shehbaz_short_c1_n8_stream_inline](X9_nsm_stream/nsm_true_shehbaz_short_c1_n8_stream_inline/) | shehbaz | short | 1 | 8 | y | inline | 0 | 0 | 1.14 / 1.17 / 1.5 | 0.12 / 0.13 / 0.16 | 5.32 | 5.14 | 5.14 | 0 | 0.194 | 0.97 | 19476 (19154) |
| [nsm_true_shehbaz_short_c8_n8_stream_inline](X9_nsm_stream/nsm_true_shehbaz_short_c8_n8_stream_inline/) | shehbaz | short | 8 | 8 | y | inline | 0 | 0 | 1.88 / 2.18 / 2.32 | 0.73 / 0.74 / 0.74 | 3.85 | 13.29 | 13.29 | 0 | 0.501 | 3.45 | 19476 (19154) |
| [nsm_true_shehbaz_xlong_c1_n8_stream_inline](X9_nsm_stream/nsm_true_shehbaz_xlong_c1_n8_stream_inline/) | shehbaz | xlong | 1 | 8 | y | inline | 0 | 0 | 6.21 / 6.62 / 6.76 | 0.15 / 0.16 / 0.16 | 34.4 | 5.56 | 5.56 | 0 | 0.18 | 0.16 | 19476 (19154) |
| [nsm_true_shehbaz_xlong_c8_n8_stream_inline](X9_nsm_stream/nsm_true_shehbaz_xlong_c8_n8_stream_inline/) | shehbaz | xlong | 8 | 8 | y | inline | 0 | 0 | 14.55 / 14.8 / 15.3 | 0.86 / 0.86 / 0.86 | 36.89 | 19.28 | 19.28 | 0 | 0.389 | 0.52 | 19606 (19284) |

## X2_language: DONE

trump with language Auto instead of English: 43 prompts x 1 take, vs P5_urdu_rp105's trump control  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P4_voice_cache
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `X2_language/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0
- GPU 0: baseline 316 MiB, engine idle 19128 MiB, released after: –; kept for the next phase
- knob check `language` (engine): OK {'base_a': None, 'fails_urdu': 'refused', 'succeeds_auto': 'accepted'}
- bench commands: 1 (exit codes 0); `X2_language/commands.sh`; duration 0.9 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [lang_auto_trump_prompts_c16_n43_nonstream_inline](X2_language/lang_auto_trump_prompts_c16_n43_nonstream_inline/) | trump | prompts | 16 | 43 |  | inline | 0 | 0 | 16.71 / 19.09 / 26.06 | – | 32.52 | 27.96 | 25.9 | 0 | 0.53 | 0.86 | 19829 (19513) |

## X3_custom_voice: DONE

engine custom voices: shehbaz-avg (speaker embedding averaged over the clips + ICL) vs shehbaz-prompt (the reference's own embedding + ICL), 43 prompts x 1 take each (trump has one clip: -avg = -prompt in effect)  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P4_voice_cache
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `X3_custom_voice/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 3
- GPU 0: baseline 316 MiB, engine idle 19128 MiB, released after: –; kept for the next phase
- knob check `custom_voices` (engine): OK {'listed': 'listed', 'base_a': None, 'succeeds_avg': 'accepted'}
- bench commands: 2 (exit codes 0, 0); `X3_custom_voice/commands.sh`; duration 2.1 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [prompt_shehbaz_prompts_c16_n43_nonstream_server-prompt](X3_custom_voice/prompt_shehbaz_prompts_c16_n43_nonstream_server-prompt/) | shehbaz | prompts | 16 | 43 |  | server-prompt | 1 | 0 | 17.59 / 20.23 / 21.76 | – | 33.6 | 23.61 | 25.41 | 0 | 0.532 | 0.7 | 19829 (19513) |
| [avg_shehbaz_prompts_c16_n43_nonstream_server-avg](X3_custom_voice/avg_shehbaz_prompts_c16_n43_nonstream_server-avg/) | shehbaz | prompts | 16 | 43 |  | server-avg | 2 | 0 | 17.56 / 19.45 / 20.93 | – | 33.4 | 22.53 | 24.72 | 0 | 0.534 | 0.67 | 19829 (19513) |

## X4_length_cap: DONE

length cap on (the gateway's max_new_tokens) vs off (the engine's 12 x text-token cap + its built-in retry): shehbaz 43 prompts each, c=16  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P4_voice_cache
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `X4_length_cap/versions/`)
- gateway: off
- engine log: built-in runaway retries 5, preemption lines 0, error lines 2
- GPU 0: baseline 316 MiB, engine idle 19128 MiB, released after: –; kept for the next phase
- knob check `max_new_tokens` (engine): OK {'base_a': None, 'fails_cap40': 'refused'}
- bench commands: 2 (exit codes 0, 0); `X4_length_cap/commands.sh`; duration 3.8 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [cap_on_shehbaz_prompts_c16_n43_nonstream_inline](X4_length_cap/cap_on_shehbaz_prompts_c16_n43_nonstream_inline/) | shehbaz | prompts | 16 | 43 |  | inline | 1 | 0 | 17.31 / 19.48 / 28.02 | – | 33.63 | 26.73 | 24.46 | 0 | 0.533 | 0.79 | 19829 (19513) |
| [cap_off_shehbaz_prompts_c16_n43_nonstream_inline](X4_length_cap/cap_off_shehbaz_prompts_c16_n43_nonstream_inline/) | shehbaz | prompts | 16 | 43 |  | inline | 0 | 0 | 17.81 / 132.53 / 147.22 | – | 33.64 | 8.51 | 8.98 | 5 | 0.534 | 0.25 | 19829 (19513) |

## X5_mixed_voices: DONE

payload-leak guard (#4355): trump and shehbaz interleaved in one batch at c=16 (xlong n=16 per voice, short n=32 per voice); compare SIM with P2's single-voice runs; dup_audio counts identical PCM  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0, reused from P4_voice_cache
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `X5_mixed_voices/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0
- GPU 0: baseline 316 MiB, engine idle 19128 MiB, released after: True
- bench commands: 2 (exit codes 0, 0); `X5_mixed_voices/commands.sh`; duration 0.9 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [mix_trump+shehbaz_xlong_c16_n16_nonstream_inline](X5_mixed_voices/mix_trump+shehbaz_xlong_c16_n16_nonstream_inline/) | trump+shehbaz | xlong | 16 | 32 |  | inline | 0 | 0 | 17.38 / 19.72 / 21.62 | – | 33.08 | 28.52 | 26.35 | 0 | 0.532 | 0.86 | 19829 (19513) |
| [mix_trump+shehbaz_short_c16_n32_nonstream_inline](X5_mixed_voices/mix_trump+shehbaz_short_c16_n32_nonstream_inline/) | trump+shehbaz | short | 16 | 64 |  | inline | 0 | 1 (0s/1l) | 2.63 / 4.28 / 5.44 | – | 3.72 | 19.77 | 17.86 | 0 | 0.799 | 5.32 | 19829 (19513) |

## P8_quality_raw: DONE

quality before guardrails: 43 prompts per voice via the gateway, retries 0, QC off (c=16)  
- engine: vllm-omni custom_voices (engine) --stage-overrides {"0": {"gpu_memory_utilization": 0.45}}, YAML sha256 d9ac9b2ef1a6d2b0
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P8_quality_raw/versions/`)
- gateway: {"TTS_RETRY_MAX": "0"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 2; KV: (StageEngineCoreProc_stage0_replica0 pid=287688) INFO 09-25 05:32:06 [kv_cache_utils.py:1869] GPU KV cache size: 58,032 tokens, Maximum concurrency for 4,096 tokens per request: 14.17x
- GPU 0: baseline 311 MiB, engine idle 15540 MiB, released after: True; kept for the next phase
- knob check `raw_headers` (gateway): OK {'base_a': None}
- bench commands: 1 (exit codes 0); `P8_quality_raw/commands.sh`; duration 2.7 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [raw_trump_prompts_c16_n43_nonstream_server](P8_quality_raw/raw_trump_prompts_c16_n43_nonstream_server/) | trump | prompts | 16 | 43 |  | server | 0 | 0 | 16.5 / 19.29 / 26.45 | – | 32.72 | 28.1 | 25.99 | 0 | 0.528 | 0.86 | 15936 (15625) |
| [raw_shehbaz_prompts_c16_n43_nonstream_server](P8_quality_raw/raw_shehbaz_prompts_c16_n43_nonstream_server/) | shehbaz | prompts | 16 | 43 |  | server | 2 | 0 | 17.68 / 20.13 / 31.5 | – | 34.26 | 22.97 | 24.41 | 0 | 0.535 | 0.67 | 15937 (15626) |

## P8_quality_guard: DONE

quality after guardrails: the same prompts with retries (max 2 on suspect, engine error, QC fail) and the QC sidecar (ASR + SIM + audio checks) on the same GPU  
- engine: vllm-omni custom_voices (engine) --stage-overrides {"0": {"gpu_memory_utilization": 0.40}}, YAML sha256 d9ac9b2ef1a6d2b0
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P8_quality_guard/versions/`)
- gateway: {"TTS_RETRY_MAX": "2", "TTS_RETRY_ON": "suspect,engine_error,qc"}; QC sidecar on
- engine log: built-in runaway retries 0, preemption lines 0, error lines 2; KV: (StageEngineCoreProc_stage0_replica0 pid=341683) INFO 09-25 09:41:08 [kv_cache_utils.py:1869] GPU KV cache size: 47,008 tokens, Maximum concurrency for 4,096 tokens per request: 11.48x
- GPU 0: baseline 331 MiB, engine idle 14316 MiB, released after: True
- knob check `qc_consulted` (gateway): OK {'base_a': None}
- bench commands: 1 (exit codes 0); `P8_quality_guard/commands.sh`; duration 6.3 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [guard_trump_prompts_c16_n43_nonstream_server](P8_quality_guard/guard_trump_prompts_c16_n43_nonstream_server/) | trump | prompts | 16 | 43 |  | server | 0 | 0 | 41.88 / 50.06 / 56.21 | – | 32.24 | 10.63 | 10.26 | 0 | 1.31 | 0.33 | 19704 (19373) |
| [guard_shehbaz_prompts_c16_n43_nonstream_server](P8_quality_guard/guard_shehbaz_prompts_c16_n43_nonstream_server/) | shehbaz | prompts | 16 | 43 |  | server | 0 | 0 | 49.52 / 53.51 / 112.86 | – | 34.52 | 8.65 | 8.9 | 0 | 1.474 | 0.25 | 22201 (21870) |

## P8_quality_guard_fast: DONE

P8_quality_guard with a lighter online check: greedy Whisper (beam 1), 4 CTranslate2 workers, QC timeout 120 s. The beam-5 sidecar needed p50 24 s (en) / 58 s (ur) per take next to the engine at c=16 and most calls hit the 30 s gateway timeout  
- engine: vllm-omni custom_voices (engine) --stage-overrides {"0": {"gpu_memory_utilization": 0.40}}, YAML sha256 d9ac9b2ef1a6d2b0
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `P8_quality_guard_fast/versions/`)
- gateway: {"TTS_RETRY_MAX": "2", "TTS_RETRY_ON": "suspect,engine_error,qc", "TTS_QC_TIMEOUT_S": "120"}; QC sidecar on
- engine log: built-in runaway retries 0, preemption lines 0, error lines 5; KV: (StageEngineCoreProc_stage0_replica0 pid=353939) INFO 09-25 09:48:28 [kv_cache_utils.py:1869] GPU KV cache size: 47,008 tokens, Maximum concurrency for 4,096 tokens per request: 11.48x
- GPU 0: baseline 329 MiB, engine idle 14315 MiB, released after: True
- knob check `qc_consulted` (gateway): OK {'base_a': None}
- bench commands: 1 (exit codes 0); `P8_quality_guard_fast/commands.sh`; duration 9.3 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [guardfast_trump_prompts_c16_n43_nonstream_server](P8_quality_guard_fast/guardfast_trump_prompts_c16_n43_nonstream_server/) | trump | prompts | 16 | 43 |  | server | 0 | 0 | 36.2 / 54.2 / 63.46 | – | 32.15 | 12.47 | 11.98 | 0 | 1.101 | 0.39 | 20681 (20352) |
| [guardfast_shehbaz_prompts_c16_n43_nonstream_server](P8_quality_guard_fast/guardfast_shehbaz_prompts_c16_n43_nonstream_server/) | shehbaz | prompts | 16 | 43 |  | server | 0 | 0 | 125.74 / 188.25 / 269.4 | – | 34.01 | 3.86 | 3.74 | 0 | 3.643 | 0.11 | 22889 (22560) |

## P9_baseline_b8: DONE

qwen-tts baseline, max batch 8, prompt cache on: short + xlong c=1..16, xxlong c=1,8, both voices  
- engine: qwen-tts baseline --max-batch 8
- versions: torch 2.13.0, transformers 4.57.3, qwen_tts 0.1.1 (all packages: `P9_baseline_b8/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0
- GPU 0: baseline 311 MiB, engine idle 5809 MiB, released after: True
- bench commands: 3 (exit codes 0, 0, 0); `P9_baseline_b8/commands.sh`; duration 17.6 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_short_c1_n8_nonstream_inline](P9_baseline_b8/trump_short_c1_n8_nonstream_inline/) | trump | short | 1 | 8 |  | inline | 0 | 1 (0s/1l) | 2.27 / 3.35 / 3.37 | – | 3.53 | 1.56 | 1.56 | 0 | 0.641 | 0.44 | 5835 (5524) |
| [trump_short_c2_n8_nonstream_inline](P9_baseline_b8/trump_short_c2_n8_nonstream_inline/) | trump | short | 2 | 8 |  | inline | 0 | 0 | 3.2 / 3.56 / 3.56 | – | 2.71 | 2.16 | 2.16 | 0 | 0.945 | 0.8 | 7106 (6795) |
| [trump_short_c4_n8_nonstream_inline](P9_baseline_b8/trump_short_c4_n8_nonstream_inline/) | trump | short | 4 | 8 |  | inline | 0 | 1 (0s/1l) | 4.23 / 4.23 / 4.23 | – | 3.14 | 3.86 | 3.86 | 0 | 1.012 | 1.23 | 9919 (9608) |
| [trump_short_c8_n16_nonstream_inline](P9_baseline_b8/trump_short_c8_n16_nonstream_inline/) | trump | short | 8 | 16 |  | inline | 0 | 0 | 4.47 / 7.63 / 7.63 | – | 3.09 | 4.09 | 3.66 | 0 | 2.061 | 1.32 | 14990 (14679) |
| [trump_short_c16_n32_nonstream_inline](P9_baseline_b8/trump_short_c16_n32_nonstream_inline/) | trump | short | 16 | 32 |  | inline | 0 | 0 | 8.12 / 8.13 / 8.13 | – | 2.87 | 5.68 | 5.04 | 0 | 2.579 | 1.98 | 14991 (14680) |
| [shehbaz_short_c1_n8_nonstream_inline](P9_baseline_b8/shehbaz_short_c1_n8_nonstream_inline/) | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 3.14 / 3.52 / 4.52 | – | 4.74 | 1.62 | 1.62 | 0 | 0.621 | 0.34 | 15001 (14690) |
| [shehbaz_short_c2_n8_nonstream_inline](P9_baseline_b8/shehbaz_short_c2_n8_nonstream_inline/) | shehbaz | short | 2 | 8 |  | inline | 0 | 0 | 2.81 / 3.42 / 3.42 | – | 3.56 | 2.72 | 2.72 | 0 | 0.716 | 0.77 | 14993 (14682) |
| [shehbaz_short_c4_n8_nonstream_inline](P9_baseline_b8/shehbaz_short_c4_n8_nonstream_inline/) | shehbaz | short | 4 | 8 |  | inline | 0 | 0 | 5.67 / 5.67 / 5.67 | – | 5.37 | 4.3 | 4.3 | 0 | 0.876 | 0.8 | 14992 (14681) |
| [shehbaz_short_c8_n16_nonstream_inline](P9_baseline_b8/shehbaz_short_c8_n16_nonstream_inline/) | shehbaz | short | 8 | 16 |  | inline | 0 | 0 | 4.92 / 6.5 / 6.5 | – | 4.01 | 5.62 | 5.31 | 0 | 1.364 | 1.4 | 14993 (14682) |
| [shehbaz_short_c16_n32_nonstream_inline](P9_baseline_b8/shehbaz_short_c16_n32_nonstream_inline/) | shehbaz | short | 16 | 32 |  | inline | 0 | 0 | 11.09 / 13.47 / 13.52 | – | 4.26 | 5.91 | 5.24 | 0 | 2.829 | 1.39 | 15007 (14696) |
| [trump_xlong_c1_n4_nonstream_inline](P9_baseline_b8/trump_xlong_c1_n4_nonstream_inline/) | trump | xlong | 1 | 4 |  | inline | 0 | 0 | 19.64 / 20.46 / 20.46 | – | 33.58 | 1.72 | 1.72 | 0 | 0.582 | 0.05 | 15041 (14730) |
| [trump_xlong_c2_n4_nonstream_inline](P9_baseline_b8/trump_xlong_c2_n4_nonstream_inline/) | trump | xlong | 2 | 4 |  | inline | 0 | 0 | 21 / 21 / 21 | – | 31.58 | 3.18 | 3.18 | 0 | 0.635 | 0.1 | 15041 (14730) |
| [trump_xlong_c4_n4_nonstream_inline](P9_baseline_b8/trump_xlong_c4_n4_nonstream_inline/) | trump | xlong | 4 | 4 |  | inline | 0 | 0 | 20.64 / 20.64 / 20.64 | – | 31.8 | 6.16 | 6.16 | 0 | 0.665 | 0.19 | 15098 (14787) |
| [trump_xlong_c8_n8_nonstream_inline](P9_baseline_b8/trump_xlong_c8_n8_nonstream_inline/) | trump | xlong | 8 | 8 |  | inline | 0 | 0 | 22.75 / 22.76 / 22.76 | – | 31.4 | 11.03 | 11.03 | 0 | 0.748 | 0.35 | 18066 (17755) |
| [trump_xlong_c16_n16_nonstream_inline](P9_baseline_b8/trump_xlong_c16_n16_nonstream_inline/) | trump | xlong | 16 | 16 |  | inline | 0 | 0 | 56.18 / 78.52 / 78.53 | – | 32.77 | 6.68 | 6.31 | 0 | 1.778 | 0.2 | 18077 (17766) |
| [shehbaz_xlong_c1_n4_nonstream_inline](P9_baseline_b8/shehbaz_xlong_c1_n4_nonstream_inline/) | shehbaz | xlong | 1 | 4 |  | inline | 0 | 1 (1s/0l) | 19.13 / 19.55 / 19.55 | – | 26.14 | 1.7 | 1.7 | 0 | 0.591 | 0.06 | 18077 (17766) |
| [shehbaz_xlong_c2_n4_nonstream_inline](P9_baseline_b8/shehbaz_xlong_c2_n4_nonstream_inline/) | shehbaz | xlong | 2 | 4 |  | inline | 1 | 0 | 21.69 / 51.48 / 51.48 | – | 33.76 | 1.38 | 1.38 | 0 | 0.655 | 0.04 | 18077 (17766) |
| [shehbaz_xlong_c4_n4_nonstream_inline](P9_baseline_b8/shehbaz_xlong_c4_n4_nonstream_inline/) | shehbaz | xlong | 4 | 4 |  | inline | 0 | 0 | 20.52 / 20.52 / 20.52 | – | 32.88 | 6.41 | 6.41 | 0 | 0.619 | 0.19 | 18077 (17766) |
| [shehbaz_xlong_c8_n8_nonstream_inline](P9_baseline_b8/shehbaz_xlong_c8_n8_nonstream_inline/) | shehbaz | xlong | 8 | 8 |  | inline | 0 | 0 | 26.25 / 26.25 / 26.26 | – | 32.62 | 9.94 | 9.94 | 0 | 0.828 | 0.3 | 18130 (17819) |
| [shehbaz_xlong_c16_n16_nonstream_inline](P9_baseline_b8/shehbaz_xlong_c16_n16_nonstream_inline/) | shehbaz | xlong | 16 | 16 |  | inline | 0 | 1 (1s/0l) | 40.29 / 62.26 / 62.27 | – | 29.67 | 7.62 | 7.19 | 0 | 1.395 | 0.26 | 18133 (17822) |
| [trump_xxlong_c1_n2_nonstream_inline](P9_baseline_b8/trump_xxlong_c1_n2_nonstream_inline/) | trump | xxlong | 1 | 2 |  | inline | 0 | 0 | 35.26 / 40.96 / 40.96 | – | 65.12 | 1.71 | 1.71 | 0 | 0.584 | 0.03 | 18133 (17822) |
| [trump_xxlong_c8_n8_nonstream_inline](P9_baseline_b8/trump_xxlong_c8_n8_nonstream_inline/) | trump | xxlong | 8 | 8 |  | inline | 0 | 0 | 42.9 / 42.9 / 42.9 | – | 61.95 | 11.55 | 11.55 | 0 | 0.709 | 0.19 | 18437 (18126) |
| [shehbaz_xxlong_c1_n2_nonstream_inline](P9_baseline_b8/shehbaz_xxlong_c1_n2_nonstream_inline/) | shehbaz | xxlong | 1 | 2 |  | inline | 0 | 1 (0s/1l) | 28.55 / 94.92 / 94.92 | – | 104.52 | 1.69 | 1.69 | 0 | 0.585 | 0.02 | 18439 (18128) |
| [shehbaz_xxlong_c8_n8_nonstream_inline](P9_baseline_b8/shehbaz_xxlong_c8_n8_nonstream_inline/) | shehbaz | xxlong | 8 | 8 |  | inline | 0 | 5 (4s/1l) | 152.81 / 152.82 / 152.83 | – | 61.86 | 3.24 | 3.24 | 0 | 1.154 | 0.05 | 18651 (18340) |

## P9_baseline_b1: DONE

qwen-tts baseline, max batch 1 (requests queue): short + xlong at c=1,4  
- engine: qwen-tts baseline --max-batch 1
- versions: torch 2.13.0, transformers 4.57.3, qwen_tts 0.1.1 (all packages: `P9_baseline_b1/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0
- GPU 0: baseline 311 MiB, engine idle 5809 MiB, released after: True
- bench commands: 2 (exit codes 0, 0); `P9_baseline_b1/commands.sh`; duration 6.9 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_short_c1_n8_nonstream_inline](P9_baseline_b1/trump_short_c1_n8_nonstream_inline/) | trump | short | 1 | 8 |  | inline | 0 | 0 | 2.41 / 3.09 / 3.14 | – | 3.61 | 1.65 | 1.65 | 0 | 0.612 | 0.46 | 5815 (5504) |
| [trump_short_c4_n8_nonstream_inline](P9_baseline_b1/trump_short_c4_n8_nonstream_inline/) | trump | short | 4 | 8 |  | inline | 0 | 0 | 6.67 / 6.71 / 7.09 | – | 2.81 | 1.63 | 1.63 | 0 | 2.951 | 0.58 | 5817 (5506) |
| [shehbaz_short_c1_n8_nonstream_inline](P9_baseline_b1/shehbaz_short_c1_n8_nonstream_inline/) | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 2.96 / 3.21 / 4.12 | – | 4.73 | 1.66 | 1.66 | 0 | 0.603 | 0.35 | 5831 (5520) |
| [shehbaz_short_c4_n8_nonstream_inline](P9_baseline_b1/shehbaz_short_c4_n8_nonstream_inline/) | shehbaz | short | 4 | 8 |  | inline | 0 | 0 | 7.59 / 8.73 / 8.75 | – | 3.59 | 1.64 | 1.64 | 0 | 2.01 | 0.46 | 5831 (5520) |
| [trump_xlong_c1_n4_nonstream_inline](P9_baseline_b1/trump_xlong_c1_n4_nonstream_inline/) | trump | xlong | 1 | 4 |  | inline | 0 | 0 | 18.61 / 19.51 / 19.51 | – | 31.46 | 1.72 | 1.72 | 0 | 0.58 | 0.05 | 6323 (6012) |
| [trump_xlong_c4_n4_nonstream_inline](P9_baseline_b1/trump_xlong_c4_n4_nonstream_inline/) | trump | xlong | 4 | 4 |  | inline | 0 | 0 | 52.68 / 71.08 / 71.08 | – | 30.72 | 1.73 | 1.73 | 0 | 1.737 | 0.06 | 6323 (6012) |
| [shehbaz_xlong_c1_n4_nonstream_inline](P9_baseline_b1/shehbaz_xlong_c1_n4_nonstream_inline/) | shehbaz | xlong | 1 | 4 |  | inline | 0 | 1 (0s/1l) | 20.67 / 48.71 / 48.71 | – | 43.52 | 1.73 | 1.73 | 0 | 0.58 | 0.04 | 6323 (6012) |
| [shehbaz_xlong_c4_n4_nonstream_inline](P9_baseline_b1/shehbaz_xlong_c4_n4_nonstream_inline/) | shehbaz | xlong | 4 | 4 |  | inline | 0 | 0 | 58.34 / 75.38 / 75.38 | – | 32.52 | 1.73 | 1.73 | 0 | 1.792 | 0.05 | 6323 (6012) |

## P9_baseline_nocache: DONE

qwen-tts baseline, prompt cache off (reference re-encoded per request): short + xlong at c=1,8  
- engine: qwen-tts baseline --max-batch 8 --no-prompt-cache
- versions: torch 2.13.0, transformers 4.57.3, qwen_tts 0.1.1 (all packages: `P9_baseline_nocache/versions/`)
- gateway: off
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0
- GPU 0: baseline 311 MiB, engine idle 5809 MiB, released after: True
- bench commands: 2 (exit codes 0, 0); `P9_baseline_nocache/commands.sh`; duration 5.6 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trump_short_c1_n8_nonstream_inline](P9_baseline_nocache/trump_short_c1_n8_nonstream_inline/) | trump | short | 1 | 8 |  | inline | 0 | 1 (0s/1l) | 2.58 / 3.27 / 3.49 | – | 3.93 | 1.6 | 1.6 | 0 | 0.636 | 0.41 | 5817 (5506) |
| [trump_short_c8_n16_nonstream_inline](P9_baseline_nocache/trump_short_c8_n16_nonstream_inline/) | trump | short | 8 | 16 |  | inline | 0 | 0 | 4.53 / 5.61 / 5.61 | – | 2.83 | 4.47 | 3.95 | 0 | 2.191 | 1.58 | 14903 (14592) |
| [shehbaz_short_c1_n8_nonstream_inline](P9_baseline_nocache/shehbaz_short_c1_n8_nonstream_inline/) | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 3.06 / 3.75 / 4.33 | – | 4.83 | 1.61 | 1.61 | 0 | 0.624 | 0.33 | 14917 (14606) |
| [shehbaz_short_c8_n16_nonstream_inline](P9_baseline_nocache/shehbaz_short_c8_n16_nonstream_inline/) | shehbaz | short | 8 | 16 |  | inline | 0 | 0 | 4.39 / 10.36 / 10.37 | – | 4.52 | 4.94 | 4.45 | 0 | 1.504 | 1.09 | 14919 (14608) |
| [trump_xlong_c1_n4_nonstream_inline](P9_baseline_nocache/trump_xlong_c1_n4_nonstream_inline/) | trump | xlong | 1 | 4 |  | inline | 0 | 0 | 19.1 / 21.53 / 21.53 | – | 32.46 | 1.69 | 1.69 | 0 | 0.593 | 0.05 | 14966 (14655) |
| [trump_xlong_c8_n8_nonstream_inline](P9_baseline_nocache/trump_xlong_c8_n8_nonstream_inline/) | trump | xlong | 8 | 8 |  | inline | 0 | 0 | 21.4 / 21.41 / 21.41 | – | 31.13 | 11.63 | 11.63 | 0 | 0.688 | 0.37 | 18881 (18570) |
| [shehbaz_xlong_c1_n4_nonstream_inline](P9_baseline_nocache/shehbaz_xlong_c1_n4_nonstream_inline/) | shehbaz | xlong | 1 | 4 |  | inline | 0 | 0 | 17.87 / 17.88 / 17.88 | – | 28.98 | 1.68 | 1.68 | 0 | 0.597 | 0.06 | 18884 (18573) |
| [shehbaz_xlong_c8_n8_nonstream_inline](P9_baseline_nocache/shehbaz_xlong_c8_n8_nonstream_inline/) | shehbaz | xlong | 8 | 8 |  | inline | 1 | 0 | 53.57 / 74.25 / 74.25 | – | 32.15 | 3.03 | 3.03 | 0 | 1.849 | 0.09 | 19119 (18808) |

## T0_prod: DONE

TTFA / gapless start, Urdu streaming via the gateway: production engine (initial chunk 1 frame, then 25-frame chunks)  
- engine: vllm-omni custom_voices (engine), YAML sha256 d9ac9b2ef1a6d2b0
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `T0_prod/versions/`)
- gateway: {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=75136) INFO 09-28 16:11:36 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 284 MiB, engine idle 19084 MiB, released after: True
- bench commands: 1 (exit codes 0); `T0_prod/commands.sh`; duration 4.6 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ttfa_shehbaz_short_c1_n8_stream_server](T0_prod/ttfa_shehbaz_short_c1_n8_stream_server/) | shehbaz | short | 1 | 8 | y | server | 0 | 0 | 0.96 / 1.22 / 1.54 | 0.12 / 0.12 / 0.12 | 5.02 | 5.25 | 5.25 | 0 | 0.191 | 1.05 | 19389 (19105) |
| [ttfa_shehbaz_short_c8_n48_stream_server](T0_prod/ttfa_shehbaz_short_c8_n48_stream_server/) | shehbaz | short | 8 | 48 | y | server | 0 | 0 | 2 / 3.37 / 4.37 | 0.27 / 0.71 / 0.71 | 4.6 | 15.74 | 15.15 | 0 | 0.495 | 3.42 | 19444 (19160) |
| [ttfa_shehbaz_short_c16_n96_stream_server](T0_prod/ttfa_shehbaz_short_c16_n96_stream_server/) | shehbaz | short | 16 | 96 | y | server | 0 | 3 (0s/3l) | 3.09 / 4.84 / 6.23 | 0.41 / 1.4 / 1.4 | 4.33 | 20 | 19.04 | 0 | 0.777 | 4.62 | 19490 (19206) |
| [ttfa_shehbaz_short_c32_n192_stream_server](T0_prod/ttfa_shehbaz_short_c32_n192_stream_server/) | shehbaz | short | 32 | 192 | y | server | 0 | 0 | 4.9 / 8.05 / 10.2 | 0.74 / 2.65 / 2.65 | 4.22 | 24.2 | 22.72 | 0 | 1.272 | 5.74 | 19928 (19644) |
| [ttfa_shehbaz_medium_c1_n8_stream_server](T0_prod/ttfa_shehbaz_medium_c1_n8_stream_server/) | shehbaz | medium | 1 | 8 | y | server | 0 | 0 | 2.25 / 2.39 / 2.65 | 0.12 / 0.12 / 0.12 | 10.65 | 5.46 | 5.46 | 0 | 0.185 | 0.51 | 19922 (19638) |
| [ttfa_shehbaz_medium_c8_n48_stream_server](T0_prod/ttfa_shehbaz_medium_c8_n48_stream_server/) | shehbaz | medium | 8 | 48 | y | server | 0 | 0 | 4.17 / 5.08 / 6.76 | 0.25 / 0.74 / 0.74 | 10.19 | 18.61 | 17.85 | 0 | 0.423 | 1.83 | 19924 (19640) |
| [ttfa_shehbaz_medium_c16_n96_stream_server](T0_prod/ttfa_shehbaz_medium_c16_n96_stream_server/) | shehbaz | medium | 16 | 96 | y | server | 0 | 0 | 6.32 / 8.22 / 10.31 | 0.34 / 1.41 / 1.41 | 10.68 | 25.02 | 23.82 | 0 | 0.616 | 2.34 | 19920 (19636) |
| [ttfa_shehbaz_medium_c32_n192_stream_server](T0_prod/ttfa_shehbaz_medium_c32_n192_stream_server/) | shehbaz | medium | 32 | 192 | y | server | 0 | 0 | 9.91 / 12.76 / 16.65 | 0.6 / 2.75 / 2.75 | 10.51 | 31.45 | 29.89 | 0 | 0.986 | 2.99 | 19927 (19643) |

## T1_mnbt512: DONE

TTFA / gapless start, Urdu streaming via the gateway: stage-0 max_num_batched_tokens 512 (upstream 0.30 / high-concurrency value)  
- engine: vllm-omni T1_mnbt512 (engine), YAML sha256 f1c24797677456a4
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `T1_mnbt512/versions/`)
- gateway: {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=82299) INFO 09-28 16:16:28 [kv_cache_utils.py:1869] GPU KV cache size: 92,272 tokens, Maximum concurrency for 4,096 tokens per request: 22.53x
- GPU 0: baseline 281 MiB, engine idle 19125 MiB, released after: True
- bench commands: 1 (exit codes 0); `T1_mnbt512/commands.sh`; duration 5.5 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ttfa_shehbaz_short_c1_n8_stream_server](T1_mnbt512/ttfa_shehbaz_short_c1_n8_stream_server/) | shehbaz | short | 1 | 8 | y | server | 0 | 0 | 1.05 / 1.27 / 1.37 | 0.12 / 0.12 / 0.12 | 5.23 | 5.27 | 5.27 | 0 | 0.193 | 1.01 | 19431 (19150) |
| [ttfa_shehbaz_short_c8_n48_stream_server](T1_mnbt512/ttfa_shehbaz_short_c8_n48_stream_server/) | shehbaz | short | 8 | 48 | y | server | 0 | 0 | 2.25 / 3.35 / 4.14 | 0.28 / 0.45 / 1.04 | 4.54 | 14.93 | 14.26 | 0 | 0.498 | 3.29 | 19478 (19197) |
| [ttfa_shehbaz_short_c16_n96_stream_server](T1_mnbt512/ttfa_shehbaz_short_c16_n96_stream_server/) | shehbaz | short | 16 | 96 | y | server | 0 | 0 | 3.06 / 5.01 / 6.37 | 0.41 / 0.74 / 1.78 | 4.21 | 19.63 | 18.4 | 0 | 0.787 | 4.67 | 19524 (19243) |
| [ttfa_shehbaz_short_c32_n192_stream_server](T1_mnbt512/ttfa_shehbaz_short_c32_n192_stream_server/) | shehbaz | short | 32 | 192 | y | server | 0 | 1 (0s/1l) | 5.12 / 8.14 / 10.48 | 0.71 / 1.21 / 2.89 | 4.2 | 23.73 | 22.2 | 0 | 1.295 | 5.65 | 19612 (19331) |
| [ttfa_shehbaz_medium_c1_n8_stream_server](T1_mnbt512/ttfa_shehbaz_medium_c1_n8_stream_server/) | shehbaz | medium | 1 | 8 | y | server | 0 | 0 | 2.32 / 2.57 / 2.75 | 0.13 / 0.13 / 0.13 | 11.18 | 5.44 | 5.44 | 0 | 0.183 | 0.49 | 19615 (19334) |
| [ttfa_shehbaz_medium_c8_n48_stream_server](T1_mnbt512/ttfa_shehbaz_medium_c8_n48_stream_server/) | shehbaz | medium | 8 | 48 | y | server | 0 | 0 | 4.37 / 5.33 / 6.59 | 0.3 / 0.4 / 0.7 | 10.19 | 18.4 | 17.47 | 0 | 0.428 | 1.81 | 19620 (19339) |
| [ttfa_shehbaz_medium_c16_n96_stream_server](T1_mnbt512/ttfa_shehbaz_medium_c16_n96_stream_server/) | shehbaz | medium | 16 | 96 | y | server | 0 | 0 | 6.55 / 8.51 / 10.2 | 0.37 / 0.66 / 1.45 | 10.92 | 24.81 | 23.98 | 0 | 0.616 | 2.27 | 19621 (19340) |
| [ttfa_shehbaz_medium_c32_n192_stream_server](T1_mnbt512/ttfa_shehbaz_medium_c32_n192_stream_server/) | shehbaz | medium | 32 | 192 | y | server | 0 | 1 (0s/1l) | 10.16 / 13.23 / 15.79 | 0.57 / 1.23 / 3.13 | 10.53 | 30.95 | 29.51 | 0 | 0.997 | 2.94 | 19624 (19343) |

## T2_ramp: DONE

TTFA / gapless start, Urdu streaming via the gateway: codec_chunk_ramp 1,2,4,8,16,25 instead of 1 then 25  
- engine: vllm-omni T2_ramp (engine), YAML sha256 b4676a6c8bb07b53
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `T2_ramp/versions/`)
- gateway: {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=89921) INFO 09-28 16:22:00 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 278 MiB, engine idle 19984 MiB, released after: True
- bench commands: 1 (exit codes 0); `T2_ramp/commands.sh`; duration 5.7 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ttfa_shehbaz_short_c1_n8_stream_server](T2_ramp/ttfa_shehbaz_short_c1_n8_stream_server/) | shehbaz | short | 1 | 8 | y | server | 0 | 0 | 0.89 / 1.21 / 1.78 | 0.12 / 0.12 / 0.14 | 4.97 | 5.09 | 5.09 | 0 | 0.204 | 1.02 | 20289 (20011) |
| [ttfa_shehbaz_short_c8_n48_stream_server](T2_ramp/ttfa_shehbaz_short_c8_n48_stream_server/) | shehbaz | short | 8 | 48 | y | server | 0 | 0 | 2.18 / 3.42 / 4.51 | 0.31 / 0.99 / 0.99 | 4.48 | 14.1 | 13.47 | 0 | 0.546 | 3.15 | 20337 (20059) |
| [ttfa_shehbaz_short_c16_n96_stream_server](T2_ramp/ttfa_shehbaz_short_c16_n96_stream_server/) | shehbaz | short | 16 | 96 | y | server | 0 | 0 | 3.61 / 5.76 / 7.85 | 0.44 / 1.58 / 1.58 | 4.31 | 17.85 | 16.54 | 0 | 0.868 | 4.14 | 20533 (20255) |
| [ttfa_shehbaz_short_c32_n192_stream_server](T2_ramp/ttfa_shehbaz_short_c32_n192_stream_server/) | shehbaz | short | 32 | 192 | y | server | 0 | 0 | 5.55 / 8.96 / 11.78 | 1.04 / 2.88 / 2.89 | 4.22 | 21.14 | 19.53 | 0 | 1.484 | 5.01 | 20973 (20695) |
| [ttfa_shehbaz_medium_c1_n8_stream_server](T2_ramp/ttfa_shehbaz_medium_c1_n8_stream_server/) | shehbaz | medium | 1 | 8 | y | server | 0 | 0 | 2.21 / 2.74 / 2.78 | 0.13 / 0.13 / 0.14 | 11.14 | 5.38 | 5.38 | 0 | 0.186 | 0.48 | 20977 (20699) |
| [ttfa_shehbaz_medium_c8_n48_stream_server](T2_ramp/ttfa_shehbaz_medium_c8_n48_stream_server/) | shehbaz | medium | 8 | 48 | y | server | 0 | 0 | 4.46 / 5.44 / 6.06 | 0.24 / 0.78 / 0.78 | 10.22 | 17.55 | 16.73 | 0 | 0.445 | 1.72 | 20975 (20697) |
| [ttfa_shehbaz_medium_c16_n96_stream_server](T2_ramp/ttfa_shehbaz_medium_c16_n96_stream_server/) | shehbaz | medium | 16 | 96 | y | server | 0 | 0 | 6.78 / 8.89 / 9.94 | 0.35 / 1.43 / 1.53 | 10.84 | 23.8 | 22.64 | 0 | 0.648 | 2.2 | 20973 (20695) |
| [ttfa_shehbaz_medium_c32_n192_stream_server](T2_ramp/ttfa_shehbaz_medium_c32_n192_stream_server/) | shehbaz | medium | 32 | 192 | y | server | 0 | 0 | 10.79 / 13.95 / 15.89 | 0.68 / 2.86 / 3.23 | 10.32 | 29.44 | 27.53 | 0 | 1.064 | 2.85 | 21303 (21025) |

## T3_adaptive: DONE

TTFA / gapless start, Urdu streaming via the gateway: adaptive chunk sizes from buffer feedback (min 2 frames, 50 ms margin)  
- engine: vllm-omni T3_adaptive (engine), YAML sha256 90eed8635b5b0580
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `T3_adaptive/versions/`)
- gateway: {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 20; KV: (StageEngineCoreProc_stage0_replica0 pid=97444) INFO 09-28 16:27:44 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 279 MiB, engine idle 19549 MiB, released after: True
- bench commands: 1 (exit codes 0); `T3_adaptive/commands.sh`; duration 5.8 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ttfa_shehbaz_short_c1_n8_stream_server](T3_adaptive/ttfa_shehbaz_short_c1_n8_stream_server/) | shehbaz | short | 1 | 8 | y | server | 0 | 0 | 1.04 / 1.1 / 1.45 | 0.15 / 0.15 / 0.15 | 4.9 | 5.12 | 5.12 | 0 | 0.197 | 1.05 | 19866 (19587) |
| [ttfa_shehbaz_short_c8_n48_stream_server](T3_adaptive/ttfa_shehbaz_short_c8_n48_stream_server/) | shehbaz | short | 8 | 48 | y | server | 0 | 0 | 2.51 / 3.48 / 4.98 | 0.38 / 1.13 / 1.13 | 4.55 | 14.13 | 13.14 | 0 | 0.538 | 3.1 | 19908 (19629) |
| [ttfa_shehbaz_short_c16_n96_stream_server](T3_adaptive/ttfa_shehbaz_short_c16_n96_stream_server/) | shehbaz | short | 16 | 96 | y | server | 0 | 0 | 3.43 / 5.64 / 6.69 | 0.89 / 1.9 / 2.01 | 4.3 | 17.81 | 16.49 | 0 | 0.873 | 4.14 | 20041 (19762) |
| [ttfa_shehbaz_short_c32_n192_stream_server](T3_adaptive/ttfa_shehbaz_short_c32_n192_stream_server/) | shehbaz | short | 32 | 192 | y | server | 1 | 1 (0s/1l) | 5.76 / 8.4 / 11.3 | 2.11 / 3.33 / 3.57 | 4.23 | 21.03 | 19.32 | 1 | 1.427 | 4.97 | 20467 (20188) |
| [ttfa_shehbaz_medium_c1_n8_stream_server](T3_adaptive/ttfa_shehbaz_medium_c1_n8_stream_server/) | shehbaz | medium | 1 | 8 | y | server | 0 | 0 | 2.3 / 2.7 / 3.09 | 0.16 / 0.16 / 0.16 | 11.32 | 5.4 | 5.4 | 0 | 0.187 | 0.48 | 20470 (20191) |
| [ttfa_shehbaz_medium_c8_n48_stream_server](T3_adaptive/ttfa_shehbaz_medium_c8_n48_stream_server/) | shehbaz | medium | 8 | 48 | y | server | 0 | 0 | 4.39 / 5.64 / 6.45 | 0.35 / 0.92 / 0.92 | 10.11 | 17.25 | 16.33 | 0 | 0.451 | 1.71 | 20466 (20187) |
| [ttfa_shehbaz_medium_c16_n96_stream_server](T3_adaptive/ttfa_shehbaz_medium_c16_n96_stream_server/) | shehbaz | medium | 16 | 96 | y | server | 0 | 0 | 6.87 / 9.13 / 10.37 | 0.58 / 1.83 / 1.83 | 10.78 | 23.48 | 22.58 | 0 | 0.652 | 2.18 | 20469 (20190) |
| [ttfa_shehbaz_medium_c32_n192_stream_server](T3_adaptive/ttfa_shehbaz_medium_c32_n192_stream_server/) | shehbaz | medium | 32 | 192 | y | server | 0 | 0 | 10.73 / 14.07 / 16.88 | 0.99 / 3.4 / 3.72 | 10.5 | 29.32 | 27.87 | 0 | 1.058 | 2.79 | 20722 (20443) |

## T4_predgraphs: DONE

TTFA / gapless start, Urdu streaming via the gateway: code-predictor prefix CUDA graphs, batch buckets 8/16/32/64  
- engine: vllm-omni T4_predgraphs (engine), YAML sha256 294d79bab699ccdc
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `T4_predgraphs/versions/`)
- gateway: {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=104998) INFO 09-28 16:33:30 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 277 MiB, engine idle 19087 MiB, released after: True
- bench commands: 1 (exit codes 0); `T4_predgraphs/commands.sh`; duration 5.5 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ttfa_shehbaz_short_c1_n8_stream_server](T4_predgraphs/ttfa_shehbaz_short_c1_n8_stream_server/) | shehbaz | short | 1 | 8 | y | server | 0 | 0 | 1 / 1.27 / 1.42 | 0.12 / 0.12 / 0.12 | 5.12 | 5.24 | 5.24 | 0 | 0.193 | 1.02 | 19394 (19117) |
| [ttfa_shehbaz_short_c8_n48_stream_server](T4_predgraphs/ttfa_shehbaz_short_c8_n48_stream_server/) | shehbaz | short | 8 | 48 | y | server | 0 | 0 | 1.93 / 3.33 / 5.35 | 0.26 / 0.95 / 0.96 | 4.67 | 15.49 | 14.2 | 0 | 0.5 | 3.31 | 19442 (19165) |
| [ttfa_shehbaz_short_c16_n96_stream_server](T4_predgraphs/ttfa_shehbaz_short_c16_n96_stream_server/) | shehbaz | short | 16 | 96 | y | server | 0 | 1 (0s/1l) | 3 / 5.07 / 6.23 | 0.43 / 1.61 / 1.61 | 4.24 | 20.12 | 18.42 | 0 | 0.791 | 4.74 | 19491 (19214) |
| [ttfa_shehbaz_short_c32_n192_stream_server](T4_predgraphs/ttfa_shehbaz_short_c32_n192_stream_server/) | shehbaz | short | 32 | 192 | y | server | 0 | 4 (0s/4l) | 4.93 / 7.93 / 10.18 | 0.76 / 2.66 / 2.66 | 4.23 | 24.16 | 22.7 | 0 | 1.295 | 5.72 | 19926 (19649) |
| [ttfa_shehbaz_medium_c1_n8_stream_server](T4_predgraphs/ttfa_shehbaz_medium_c1_n8_stream_server/) | shehbaz | medium | 1 | 8 | y | server | 0 | 0 | 2.07 / 2.73 / 2.8 | 0.12 / 0.12 / 0.13 | 11.33 | 5.44 | 5.44 | 0 | 0.184 | 0.48 | 19926 (19649) |
| [ttfa_shehbaz_medium_c8_n48_stream_server](T4_predgraphs/ttfa_shehbaz_medium_c8_n48_stream_server/) | shehbaz | medium | 8 | 48 | y | server | 0 | 0 | 4.26 / 5.3 / 6.12 | 0.29 / 0.72 / 0.72 | 10.2 | 18.2 | 17.55 | 0 | 0.428 | 1.78 | 19924 (19647) |
| [ttfa_shehbaz_medium_c16_n96_stream_server](T4_predgraphs/ttfa_shehbaz_medium_c16_n96_stream_server/) | shehbaz | medium | 16 | 96 | y | server | 0 | 0 | 6.37 / 8.47 / 9.38 | 0.33 / 1.4 / 1.41 | 10.82 | 24.98 | 23.9 | 0 | 0.614 | 2.31 | 20121 (19844) |
| [ttfa_shehbaz_medium_c32_n192_stream_server](T4_predgraphs/ttfa_shehbaz_medium_c32_n192_stream_server/) | shehbaz | medium | 32 | 192 | y | server | 0 | 0 | 10.16 / 12.86 / 15.77 | 0.57 / 2.76 / 2.76 | 10.57 | 31.45 | 29.67 | 0 | 0.988 | 2.98 | 20326 (20049) |

## T5_decode1: DONE

TTFA / gapless start, Urdu streaming via the gateway: Code2Wav one stream per decode (upstream high-concurrency profile)  
- engine: vllm-omni T5_decode1 (engine), YAML sha256 1d4e8e0596355743
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `T5_decode1/versions/`)
- gateway: {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=112530) INFO 09-28 16:39:01 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 278 MiB, engine idle 19089 MiB, released after: True
- bench commands: 1 (exit codes 0); `T5_decode1/commands.sh`; duration 5.5 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ttfa_shehbaz_short_c1_n8_stream_server](T5_decode1/ttfa_shehbaz_short_c1_n8_stream_server/) | shehbaz | short | 1 | 8 | y | server | 0 | 0 | 0.92 / 1.54 / 1.59 | 0.12 / 0.12 / 0.12 | 5.49 | 5.25 | 5.25 | 0 | 0.194 | 0.96 | 19396 (19118) |
| [ttfa_shehbaz_short_c8_n48_stream_server](T5_decode1/ttfa_shehbaz_short_c8_n48_stream_server/) | shehbaz | short | 8 | 48 | y | server | 0 | 0 | 2.21 / 3.22 / 4.16 | 0.27 / 0.96 / 0.96 | 4.67 | 15.42 | 15.04 | 0 | 0.483 | 3.3 | 19443 (19165) |
| [ttfa_shehbaz_short_c16_n96_stream_server](T5_decode1/ttfa_shehbaz_short_c16_n96_stream_server/) | shehbaz | short | 16 | 96 | y | server | 0 | 1 (0s/1l) | 3.01 / 5.04 / 5.97 | 0.37 / 1.61 / 1.61 | 4.32 | 19.99 | 18.34 | 0 | 0.787 | 4.62 | 19493 (19215) |
| [ttfa_shehbaz_short_c32_n192_stream_server](T5_decode1/ttfa_shehbaz_short_c32_n192_stream_server/) | shehbaz | short | 32 | 192 | y | server | 0 | 2 (0s/2l) | 5.08 / 8.31 / 11.46 | 0.74 / 2.69 / 2.69 | 4.31 | 24.08 | 22.6 | 0 | 1.284 | 5.59 | 19937 (19659) |
| [ttfa_shehbaz_medium_c1_n8_stream_server](T5_decode1/ttfa_shehbaz_medium_c1_n8_stream_server/) | shehbaz | medium | 1 | 8 | y | server | 0 | 0 | 2.18 / 2.62 / 2.88 | 0.12 / 0.13 / 0.13 | 10.98 | 5.42 | 5.42 | 0 | 0.186 | 0.49 | 19939 (19661) |
| [ttfa_shehbaz_medium_c8_n48_stream_server](T5_decode1/ttfa_shehbaz_medium_c8_n48_stream_server/) | shehbaz | medium | 8 | 48 | y | server | 0 | 0 | 4.23 / 4.88 / 6.43 | 0.26 / 0.71 / 0.71 | 10.15 | 18.3 | 17.69 | 0 | 0.424 | 1.8 | 19928 (19650) |
| [ttfa_shehbaz_medium_c16_n96_stream_server](T5_decode1/ttfa_shehbaz_medium_c16_n96_stream_server/) | shehbaz | medium | 16 | 96 | y | server | 0 | 0 | 6.24 / 8.29 / 9.96 | 0.35 / 1.42 / 1.42 | 10.67 | 24.87 | 23.95 | 0 | 0.615 | 2.33 | 19940 (19662) |
| [ttfa_shehbaz_medium_c32_n192_stream_server](T5_decode1/ttfa_shehbaz_medium_c32_n192_stream_server/) | shehbaz | medium | 32 | 192 | y | server | 0 | 0 | 10.14 / 13.06 / 15.52 | 0.59 / 2.74 / 2.75 | 10.56 | 31.29 | 29.88 | 0 | 0.995 | 2.96 | 20251 (19973) |

## T6_ctx25: DONE

TTFA / gapless start, Urdu streaming via the gateway: Code2Wav left context 25 frames instead of 72 (cheaper decode; check quality)  
- engine: vllm-omni T6_ctx25 (engine), YAML sha256 6c77d5ddb917e043
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `T6_ctx25/versions/`)
- gateway: {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=120173) INFO 09-28 16:44:32 [kv_cache_utils.py:1869] GPU KV cache size: 91,120 tokens, Maximum concurrency for 4,096 tokens per request: 22.25x
- GPU 0: baseline 282 MiB, engine idle 19088 MiB, released after: True
- bench commands: 1 (exit codes 0); `T6_ctx25/commands.sh`; duration 5.5 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ttfa_shehbaz_short_c1_n8_stream_server](T6_ctx25/ttfa_shehbaz_short_c1_n8_stream_server/) | shehbaz | short | 1 | 8 | y | server | 0 | 0 | 1.01 / 1.26 / 1.43 | 0.12 / 0.12 / 0.12 | 5.12 | 5.22 | 5.22 | 0 | 0.193 | 1.02 | 19395 (19113) |
| [ttfa_shehbaz_short_c8_n48_stream_server](T6_ctx25/ttfa_shehbaz_short_c8_n48_stream_server/) | shehbaz | short | 8 | 48 | y | server | 0 | 0 | 2.18 / 3.29 / 4.98 | 0.29 / 0.96 / 0.96 | 4.74 | 15.65 | 14.59 | 0 | 0.492 | 3.3 | 19438 (19156) |
| [ttfa_shehbaz_short_c16_n96_stream_server](T6_ctx25/ttfa_shehbaz_short_c16_n96_stream_server/) | shehbaz | short | 16 | 96 | y | server | 0 | 1 (0s/1l) | 3.06 / 4.89 / 6.56 | 0.39 / 1.64 / 1.64 | 4.29 | 20.04 | 18.53 | 0 | 0.777 | 4.67 | 19488 (19206) |
| [ttfa_shehbaz_short_c32_n192_stream_server](T6_ctx25/ttfa_shehbaz_short_c32_n192_stream_server/) | shehbaz | short | 32 | 192 | y | server | 0 | 0 | 4.83 / 8.19 / 11 | 0.73 / 2.62 / 2.63 | 4.28 | 24.27 | 22.51 | 0 | 1.277 | 5.67 | 19901 (19619) |
| [ttfa_shehbaz_medium_c1_n8_stream_server](T6_ctx25/ttfa_shehbaz_medium_c1_n8_stream_server/) | shehbaz | medium | 1 | 8 | y | server | 0 | 0 | 2.23 / 2.55 / 2.65 | 0.12 / 0.12 / 0.13 | 10.82 | 5.43 | 5.43 | 0 | 0.186 | 0.5 | 19906 (19624) |
| [ttfa_shehbaz_medium_c8_n48_stream_server](T6_ctx25/ttfa_shehbaz_medium_c8_n48_stream_server/) | shehbaz | medium | 8 | 48 | y | server | 0 | 0 | 4.24 / 5.39 / 5.79 | 0.25 / 0.74 / 0.74 | 10.31 | 18.38 | 17.48 | 0 | 0.425 | 1.78 | 19899 (19617) |
| [ttfa_shehbaz_medium_c16_n96_stream_server](T6_ctx25/ttfa_shehbaz_medium_c16_n96_stream_server/) | shehbaz | medium | 16 | 96 | y | server | 0 | 0 | 6.38 / 8.31 / 10.06 | 0.34 / 1.42 / 1.42 | 10.76 | 25.01 | 24.01 | 0 | 0.614 | 2.32 | 19905 (19623) |
| [ttfa_shehbaz_medium_c32_n192_stream_server](T6_ctx25/ttfa_shehbaz_medium_c32_n192_stream_server/) | shehbaz | medium | 32 | 192 | y | server | 0 | 0 | 10.05 / 12.9 / 16.06 | 0.56 / 2.78 / 2.79 | 10.4 | 31.24 | 30.02 | 0 | 0.987 | 3 | 20131 (19849) |

## T7_mnbt512_ramp: DONE

TTFA / gapless start, Urdu streaming via the gateway: combined: 512-token prefill steps + chunk ramp 1,2,4,8,16,25  
- engine: vllm-omni T7_mnbt512_ramp (engine), YAML sha256 246982275dce38c2
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `T7_mnbt512_ramp/versions/`)
- gateway: {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=128964) INFO 09-28 16:51:07 [kv_cache_utils.py:1869] GPU KV cache size: 92,272 tokens, Maximum concurrency for 4,096 tokens per request: 22.53x
- GPU 0: baseline 284 MiB, engine idle 20023 MiB, released after: True
- bench commands: 1 (exit codes 0); `T7_mnbt512_ramp/commands.sh`; duration 5.8 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ttfa_shehbaz_short_c1_n8_stream_server](T7_mnbt512_ramp/ttfa_shehbaz_short_c1_n8_stream_server/) | shehbaz | short | 1 | 8 | y | server | 0 | 1 (0s/1l) | 1.15 / 1.29 / 1.56 | 0.12 / 0.12 / 0.13 | 5.37 | 5.15 | 5.15 | 0 | 0.196 | 0.96 | 20330 (20046) |
| [ttfa_shehbaz_short_c8_n48_stream_server](T7_mnbt512_ramp/ttfa_shehbaz_short_c8_n48_stream_server/) | shehbaz | short | 8 | 48 | y | server | 0 | 0 | 2.24 / 3.62 / 5.21 | 0.31 / 0.51 / 1.19 | 4.6 | 14.07 | 13.32 | 0 | 0.542 | 3.06 | 20378 (20094) |
| [ttfa_shehbaz_short_c16_n96_stream_server](T7_mnbt512_ramp/ttfa_shehbaz_short_c16_n96_stream_server/) | shehbaz | short | 16 | 96 | y | server | 0 | 0 | 3.52 / 5.54 / 6.7 | 0.46 / 0.79 / 2.16 | 4.22 | 17.6 | 16.31 | 0 | 0.877 | 4.17 | 20433 (20149) |
| [ttfa_shehbaz_short_c32_n192_stream_server](T7_mnbt512_ramp/ttfa_shehbaz_short_c32_n192_stream_server/) | shehbaz | short | 32 | 192 | y | server | 0 | 1 (0s/1l) | 5.69 / 9.31 / 12.7 | 0.83 / 1.39 / 3.62 | 4.29 | 21.17 | 19.32 | 0 | 1.462 | 4.94 | 20523 (20239) |
| [ttfa_shehbaz_medium_c1_n8_stream_server](T7_mnbt512_ramp/ttfa_shehbaz_medium_c1_n8_stream_server/) | shehbaz | medium | 1 | 8 | y | server | 0 | 0 | 2.33 / 2.53 / 2.58 | 0.13 / 0.13 / 0.13 | 10.77 | 5.38 | 5.38 | 0 | 0.185 | 0.5 | 20529 (20245) |
| [ttfa_shehbaz_medium_c8_n48_stream_server](T7_mnbt512_ramp/ttfa_shehbaz_medium_c8_n48_stream_server/) | shehbaz | medium | 8 | 48 | y | server | 0 | 0 | 4.39 / 5.6 / 6.17 | 0.29 / 0.4 / 0.85 | 10.25 | 17.57 | 16.81 | 0 | 0.447 | 1.71 | 20525 (20241) |
| [ttfa_shehbaz_medium_c16_n96_stream_server](T7_mnbt512_ramp/ttfa_shehbaz_medium_c16_n96_stream_server/) | shehbaz | medium | 16 | 96 | y | server | 0 | 0 | 6.82 / 8.65 / 10.15 | 0.4 / 0.7 / 1.75 | 10.65 | 23.31 | 22.39 | 0 | 0.657 | 2.19 | 20525 (20241) |
| [ttfa_shehbaz_medium_c32_n192_stream_server](T7_mnbt512_ramp/ttfa_shehbaz_medium_c32_n192_stream_server/) | shehbaz | medium | 32 | 192 | y | server | 0 | 0 | 11 / 14.85 / 16.75 | 0.63 / 1.41 / 3.87 | 10.47 | 28.96 | 27.49 | 0 | 1.071 | 2.76 | 20522 (20238) |

## T8_mnbt512_adaptive: DONE

TTFA / gapless start, Urdu streaming via the gateway: combined: 512-token prefill steps + adaptive chunks  
- engine: vllm-omni T8_mnbt512_adaptive (engine), YAML sha256 703cc87e96ba6b4d
- versions: vllm 0.28.0, vllm_omni 0.28.0, torch 2.13.0, transformers 5.14.1 (all packages: `T8_mnbt512_adaptive/versions/`)
- gateway: {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_SPLIT_WORDS": "60", "TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"}
- engine log: built-in runaway retries 0, preemption lines 0, error lines 0; KV: (StageEngineCoreProc_stage0_replica0 pid=136497) INFO 09-28 16:56:55 [kv_cache_utils.py:1869] GPU KV cache size: 92,272 tokens, Maximum concurrency for 4,096 tokens per request: 22.53x
- GPU 0: baseline 278 MiB, engine idle 19589 MiB, released after: True
- bench commands: 1 (exit codes 0); `T8_mnbt512_adaptive/commands.sh`; duration 5.9 min

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ttfa_shehbaz_short_c1_n8_stream_server](T8_mnbt512_adaptive/ttfa_shehbaz_short_c1_n8_stream_server/) | shehbaz | short | 1 | 8 | y | server | 0 | 0 | 0.92 / 1.16 / 1.3 | 0.15 / 0.15 / 0.15 | 4.95 | 5.15 | 5.15 | 0 | 0.194 | 1.04 | 19929 (19651) |
| [ttfa_shehbaz_short_c8_n48_stream_server](T8_mnbt512_adaptive/ttfa_shehbaz_short_c8_n48_stream_server/) | shehbaz | short | 8 | 48 | y | server | 0 | 1 (0s/1l) | 2.54 / 3.58 / 4.36 | 0.37 / 0.59 / 1.21 | 4.75 | 14.03 | 13.49 | 0 | 0.535 | 2.96 | 19979 (19701) |
| [ttfa_shehbaz_short_c16_n96_stream_server](T8_mnbt512_adaptive/ttfa_shehbaz_short_c16_n96_stream_server/) | shehbaz | short | 16 | 96 | y | server | 0 | 3 (0s/3l) | 3.64 / 5.64 / 7.21 | 0.73 / 1.02 / 2.22 | 4.35 | 17.9 | 16.46 | 0 | 0.878 | 4.12 | 20090 (19812) |
| [ttfa_shehbaz_short_c32_n192_stream_server](T8_mnbt512_adaptive/ttfa_shehbaz_short_c32_n192_stream_server/) | shehbaz | short | 32 | 192 | y | server | 0 | 0 | 5.62 / 8.75 / 12.07 | 1.24 / 1.91 / 3.84 | 4.28 | 21.78 | 20.18 | 0 | 1.419 | 5.09 | 20179 (19901) |
| [ttfa_shehbaz_medium_c1_n8_stream_server](T8_mnbt512_adaptive/ttfa_shehbaz_medium_c1_n8_stream_server/) | shehbaz | medium | 1 | 8 | y | server | 0 | 0 | 2.49 / 2.75 / 2.88 | 0.16 / 0.16 / 0.16 | 11.76 | 5.34 | 5.34 | 0 | 0.189 | 0.45 | 20200 (19922) |
| [ttfa_shehbaz_medium_c8_n48_stream_server](T8_mnbt512_adaptive/ttfa_shehbaz_medium_c8_n48_stream_server/) | shehbaz | medium | 8 | 48 | y | server | 0 | 0 | 4.55 / 5.67 / 6.37 | 0.4 / 0.54 / 0.9 | 10.3 | 17.32 | 16.35 | 0 | 0.454 | 1.68 | 20200 (19922) |
| [ttfa_shehbaz_medium_c16_n96_stream_server](T8_mnbt512_adaptive/ttfa_shehbaz_medium_c16_n96_stream_server/) | shehbaz | medium | 16 | 96 | y | server | 0 | 0 | 6.99 / 9.03 / 11.22 | 0.59 / 0.91 / 1.99 | 11.09 | 23.43 | 22.75 | 0 | 0.656 | 2.11 | 20203 (19925) |
| [ttfa_shehbaz_medium_c32_n192_stream_server](T8_mnbt512_adaptive/ttfa_shehbaz_medium_c32_n192_stream_server/) | shehbaz | medium | 32 | 192 | y | server | 0 | 0 | 10.83 / 14.59 / 17.45 | 0.99 / 1.58 / 4.32 | 10.5 | 28.8 | 27.32 | 0 | 1.071 | 2.74 | 20186 (19908) |

## 00_first_engine_smoke: no phase.json


no bench_tts.py runs here (see the folder's own files)

## 00_first_gateway_smoke: no phase.json


no bench_tts.py runs here (see the folder's own files)

## 01_probe_scaling_engine_direct: no phase.json


| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [probe_prod045_trump_long_c1_n8](01_probe_scaling_engine_direct/) | trump | long | 1 | 8 |  | – | 0 | 0 | 2.71 / 3.06 / 3.35 | – | – | 5.59 | – | – | 0.179 | 0.36 | 15925 |
| [probe_prod045_trump_long_c4_n8](01_probe_scaling_engine_direct/) | trump | long | 4 | 8 |  | – | 0 | 0 | 3.78 / 4.17 / 4.64 | – | – | 15.58 | – | – | 0.244 | 0.98 | 15923 |
| [probe_prod045_trump_long_c8_n16](01_probe_scaling_engine_direct/) | trump | long | 8 | 16 |  | – | 0 | 0 | 6.24 / 7 / 7.74 | – | – | 19.46 | – | – | 0.39 | 1.2 | 15923 |
| [probe_prod045_trump_long_c16_n32](01_probe_scaling_engine_direct/) | trump | long | 16 | 32 |  | – | 0 | 0 | 9 / 10.14 / 12.79 | – | – | 26.29 | – | – | 0.578 | 1.59 | 15975 |
| [probe_prod045_trump_long_c32_n64](01_probe_scaling_engine_direct/) | trump | long | 32 | 64 |  | – | 0 | 0 | 13.56 / 15.94 / 17.15 | – | – | 35.06 | – | – | 0.874 | 2.17 | 16203 |
| [probe_prod045_trump_long_c48_n96](01_probe_scaling_engine_direct/) | trump | long | 48 | 96 |  | – | 0 | 0 | 21.27 / 24.77 / 27.04 | – | – | 34.24 | – | – | 1.357 | 2.13 | 16475 |
| [probe_prod045_trump_long_c64_n128](01_probe_scaling_engine_direct/) | trump | long | 64 | 128 |  | – | 0 | 0 | 24.15 / 30.26 / 35.88 | – | – | 38.49 | – | – | 1.57 | 2.37 | 16752 |
| [probe_prod045_shehbaz_long_c1_n8](01_probe_scaling_engine_direct/) | shehbaz | long | 1 | 8 |  | – | 0 | 0 | 4.05 / 4.29 / 4.58 | – | – | 5.55 | – | – | 0.18 | 0.25 | 16749 |
| [probe_prod045_shehbaz_long_c4_n8](01_probe_scaling_engine_direct/) | shehbaz | long | 4 | 8 |  | – | 0 | 0 | 5.28 / 5.55 / 5.6 | – | – | 15.71 | – | – | 0.246 | 0.74 | 16750 |
| [probe_prod045_shehbaz_long_c8_n16](01_probe_scaling_engine_direct/) | shehbaz | long | 8 | 16 |  | – | 0 | 0 | 8.55 / 10.03 / 10.25 | – | – | 19.15 | – | – | 0.39 | 0.87 | 16748 |
| [probe_prod045_shehbaz_long_c16_n32](01_probe_scaling_engine_direct/) | shehbaz | long | 16 | 32 |  | – | 0 | 0 | 11.67 / 13.71 / 14.24 | – | – | 27.58 | – | – | 0.555 | 1.27 | 16749 |
| [probe_prod045_shehbaz_long_c32_n64](01_probe_scaling_engine_direct/) | shehbaz | long | 32 | 64 |  | – | 0 | 0 | 18.72 / 21.71 / 22.71 | – | – | 35.52 | – | – | 0.856 | 1.58 | 16753 |
| [probe_prod045_shehbaz_long_c48_n96](01_probe_scaling_engine_direct/) | shehbaz | long | 48 | 96 |  | – | 0 | 0 | 28.61 / 33.71 / 39.47 | – | – | 21.98 | – | – | 1.338 | 1 | 16753 |
| [probe_prod045_shehbaz_long_c64_n128](01_probe_scaling_engine_direct/) | shehbaz | long | 64 | 128 |  | – | 0 | 0 | 32.89 / 40.29 / 113.56 | – | – | 22.7 | – | – | 1.536 | 1.02 | 16966 |

## 02_probe_gateway_urdu_c48: no phase.json


| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [gw_retry1_cap_shehbaz_long_c48_n96](02_probe_gateway_urdu_c48/) | shehbaz | long | 48 | 96 |  | – | 0 | 0 | 23.83 / 35.7 / 40.81 | – | – | 34.34 | – | – | 1.049 | 1.54 | 16967 |

## 03_ab_async_chunk: no phase.json


| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [async_chunk/e03_async_trump_long_c1_n8](03_ab_async_chunk/async_chunk/) | trump | long | 1 | 8 |  | – | 0 | 0 | 3 / 3.12 / 3.21 | – | – | 5.55 | – | – | 0.18 | 0.34 | 19156 |
| [async_chunk/e03_async_trump_long_c8_n16](03_ab_async_chunk/async_chunk/) | trump | long | 8 | 16 |  | – | 0 | 0 | 6.5 / 6.79 / 7.16 | – | – | 19.01 | – | – | 0.401 | 1.18 | 19186 |
| [async_chunk/e03_async_trump_long_c32_n64](03_ab_async_chunk/async_chunk/) | trump | long | 32 | 64 |  | – | 0 | 0 | 13.97 / 16.97 / 17.99 | – | – | 34.48 | – | – | 0.88 | 2.13 | 19337 |
| [async_chunk/e03_async_stream_trump_long_c1_n8_stream](03_ab_async_chunk/async_chunk/) | trump | long | 1 | 8 | y | – | 0 | 0 | 2.89 / 3.07 / 3.53 | 0.12 / 0.14 / 0.14 | – | 5.54 | – | – | 0.181 | 0.35 | 19339 |
| [async_chunk/e03_async_stream_trump_long_c8_n16_stream](03_ab_async_chunk/async_chunk/) | trump | long | 8 | 16 | y | – | 0 | 0 | 6.12 / 7.46 / 7.73 | 0.33 / 0.65 / 0.65 | – | 18.95 | – | – | 0.396 | 1.18 | 19339 |
| [async_chunk/e03_async_shehbaz_long_c1_n8](03_ab_async_chunk/async_chunk/) | shehbaz | long | 1 | 8 |  | – | 0 | 0 | 4.05 / 4.78 / 4.88 | – | – | 5.49 | – | – | 0.182 | 0.24 | 19642 |
| [async_chunk/e03_async_shehbaz_long_c8_n16](03_ab_async_chunk/async_chunk/) | shehbaz | long | 8 | 16 |  | – | 0 | 0 | 8.7 / 10.23 / 10.37 | – | – | 18.3 | – | – | 0.402 | 0.81 | 19643 |
| [async_chunk/e03_async_shehbaz_long_c32_n64](03_ab_async_chunk/async_chunk/) | shehbaz | long | 32 | 64 |  | – | 0 | 0 | 18.76 / 21.89 / 24.19 | – | – | 21.6 | – | – | 0.871 | 0.98 | 19647 |
| [async_chunk/e03_async_stream_shehbaz_long_c1_n8_stream](03_ab_async_chunk/async_chunk/) | shehbaz | long | 1 | 8 | y | – | 0 | 0 | 4.22 / 4.64 / 4.76 | 0.14 / 0.14 / 0.14 | – | 5.43 | – | – | 0.184 | 0.23 | 19639 |
| [async_chunk/e03_async_stream_shehbaz_long_c8_n16_stream](03_ab_async_chunk/async_chunk/) | shehbaz | long | 8 | 16 | y | – | 0 | 0 | 9.13 / 9.64 / 9.8 | 0.42 / 0.73 / 0.74 | – | 19.07 | – | – | 0.397 | 0.84 | 19643 |
| [no_async_chunk/e03_noasync_trump_long_c1_n8](03_ab_async_chunk/no_async_chunk/) | trump | long | 1 | 8 |  | – | 0 | 0 | 3.06 / 3.38 / 3.38 | – | – | 5.26 | – | – | 0.19 | 0.33 | 22817 |
| [no_async_chunk/e03_noasync_trump_long_c8_n16](03_ab_async_chunk/no_async_chunk/) | trump | long | 8 | 16 |  | – | 0 | 0 | 7.28 / 8.02 / 8.02 | – | – | 16.51 | – | – | 0.427 | 1.04 | 22817 |
| [no_async_chunk/e03_noasync_trump_long_c32_n64](03_ab_async_chunk/no_async_chunk/) | trump | long | 32 | 64 |  | – | 0 | 0 | 15.92 / 19.85 / 20.47 | – | – | 28.56 | – | – | 0.931 | 1.78 | 22965 |
| [no_async_chunk/e03_noasync_stream_trump_long_c1_n8_stream](03_ab_async_chunk/no_async_chunk/) | trump | long | 1 | 8 | y | – | 0 | 0 | 3.45 / 3.52 / 3.63 | 3.45 / 3.52 / 3.63 | – | 4.96 | – | – | 0.203 | 0.31 | 22967 |
| [no_async_chunk/e03_noasync_stream_trump_long_c8_n16_stream](03_ab_async_chunk/no_async_chunk/) | trump | long | 8 | 16 | y | – | 0 | 0 | 7.24 / 7.99 / 7.99 | 7.24 / 7.98 / 7.99 | – | 16.27 | – | – | 0.431 | 1.02 | 22968 |
| [no_async_chunk/e03_noasync_shehbaz_long_c1_n8](03_ab_async_chunk/no_async_chunk/) | shehbaz | long | 1 | 8 |  | – | 0 | 0 | 4.49 / 4.91 / 4.92 | – | – | 4.9 | – | – | 0.205 | 0.22 | 23187 |
| [no_async_chunk/e03_noasync_shehbaz_long_c8_n16](03_ab_async_chunk/no_async_chunk/) | shehbaz | long | 8 | 16 |  | – | 0 | 0 | 9.69 / 11.32 / 11.35 | – | – | 17.14 | – | – | 0.428 | 0.76 | 23186 |
| [no_async_chunk/e03_noasync_shehbaz_long_c32_n64](03_ab_async_chunk/no_async_chunk/) | shehbaz | long | 32 | 64 |  | – | 0 | 0 | 21.81 / 24.04 / 25.9 | – | – | 18.38 | – | – | 0.947 | 0.84 | 23193 |
| [no_async_chunk/e03_noasync_stream_shehbaz_long_c1_n8_stream](03_ab_async_chunk/no_async_chunk/) | shehbaz | long | 1 | 8 | y | – | 0 | 0 | 4.53 / 4.96 / 5.57 | 4.53 / 4.96 / 5.57 | – | 4.91 | – | – | 0.203 | 0.23 | 23186 |
| [no_async_chunk/e03_noasync_stream_shehbaz_long_c8_n16_stream](03_ab_async_chunk/no_async_chunk/) | shehbaz | long | 8 | 16 | y | – | 0 | 0 | 9.56 / 10.93 / 11.04 | 9.56 / 10.93 / 11.04 | – | 16.28 | – | – | 0.442 | 0.73 | 23188 |

## 04_knob_verification: no phase.json


no bench_tts.py runs here (see the folder's own files)

## 05_eval_gpu_check: no phase.json


no bench_tts.py runs here (see the folder's own files)

## 06_baseline_gpu_smoke: no phase.json


no bench_tts.py runs here (see the folder's own files)

## 10_production_verification: no phase.json


no bench_tts.py runs here (see the folder's own files)

## 11_production_sim_guard: no phase.json


| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [prod_c1_trump_short_c1_n16_nonstream_server](11_production_sim_guard/prod_c1_trump_short_c1_n16_nonstream_server/) | trump | short | 1 | 16 |  | server | 0 | 0 | 0.67 / 1.03 / 1.12 | – | 3.1 | 4.77 | 4.8 | 0 | 0.221 | 1.54 | 20851 |
| [prod_c1_shehbaz_short_c1_n16_nonstream_server](11_production_sim_guard/prod_c1_shehbaz_short_c1_n16_nonstream_server/) | shehbaz | short | 1 | 16 |  | server | 0 | 0 | 0.95 / 1.34 / 1.44 | – | 4.66 | 5 | 5.01 | 0 | 0.201 | 1.07 | 20846 |
| [prod_c16_trump_short_c16_n320_nonstream_server](11_production_sim_guard/prod_c16_trump_short_c16_n320_nonstream_server/) | trump | short | 16 | 320 |  | server | 0 | 1 (0s/1l) | 2.42 / 4.36 / 5.25 | – | 2.96 | 17.41 | 16.96 | 0 | 0.9 | 5.88 | 20958 |
| [prod_c16_shehbaz_short_c16_n64_nonstream_server](11_production_sim_guard/prod_c16_shehbaz_short_c16_n64_nonstream_server/) | shehbaz | short | 16 | 64 |  | server | 0 | 0 | 3.38 / 5.94 / 6.6 | – | 4.78 | 19.33 | 18.27 | 0 | 0.8 | 4.04 | 21107 |
| [prod_c16_trump_xlong_c16_n32_nonstream_server](11_production_sim_guard/prod_c16_trump_xlong_c16_n32_nonstream_server/) | trump | xlong | 16 | 32 |  | server | 0 | 0 | 14.26 / 21.96 / 35.65 | – | 33.14 | 28.57 | 26.48 | 0 | 0.452 | 0.86 | 21232 |
| [prod_c16_shehbaz_xlong_c16_n32_nonstream_server](11_production_sim_guard/prod_c16_shehbaz_xlong_c16_n32_nonstream_server/) | shehbaz | xlong | 16 | 32 |  | server | 0 | 0 | 18.71 / 22.62 / 33.25 | – | 37.26 | 27.02 | 27.47 | 0 | 0.499 | 0.73 | 21811 |

## 12_failure_recovery: no phase.json


no bench_tts.py runs here (see the folder's own files)

## 13_final_server: no phase.json


| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [final_c1_trump_short_c1_n16_nonstream_server](13_final_server/final_c1_trump_short_c1_n16_nonstream_server/) | trump | short | 1 | 16 |  | server | 0 | 0 | 0.65 / 1.02 / 1.03 | – | 3.23 | 4.8 | 4.82 | 0 | 0.218 | 1.49 | 20736 |
| [final_c1_trump_short_c1_n16_stream_server](13_final_server/final_c1_trump_short_c1_n16_stream_server/) | trump | short | 1 | 16 | y | server | 0 | 0 | 0.61 / 0.98 / 1.06 | 0.11 / 0.11 / 0.12 | 3.16 | 4.98 | 5.01 | 0 | 0.205 | 1.58 | 20730 |
| [final_c16_trump_short_c16_n64_nonstream_server](13_final_server/final_c16_trump_short_c16_n64_nonstream_server/) | trump | short | 16 | 64 |  | server | 0 | 0 | 2.38 / 4.38 / 5.02 | – | 3.1 | 17.15 | 16.43 | 0 | 0.853 | 5.53 | 20843 |
| [final_c16_trump_medium_c16_n64_nonstream_server](13_final_server/final_c16_trump_medium_c16_n64_nonstream_server/) | trump | medium | 16 | 64 |  | server | 0 | 0 | 4.32 / 5.79 / 6.27 | – | 6.49 | 21.95 | 20.32 | 0 | 0.683 | 3.38 | 20884 |
| [final_c16_trump_long_c16_n43_nonstream_server](13_final_server/final_c16_trump_long_c16_n43_nonstream_server/) | trump | long | 16 | 43 |  | server | 0 | 0 | 9.46 / 11.14 / 11.64 | – | 15.94 | 24.6 | 23.09 | 0 | 0.589 | 1.54 | 20920 |
| [final_c16_trump_prompts_c16_n43_nonstream_server](13_final_server/final_c16_trump_prompts_c16_n43_nonstream_server/) | trump | prompts | 16 | 43 |  | server | 0 | 0 | 14.67 / 27.04 / 39.59 | – | 32.79 | 27.21 | 28.89 | 0 | 0.45 | 0.83 | 21004 |
| [final_c16_trump_xxlong_c16_n43_nonstream_server](13_final_server/final_c16_trump_xxlong_c16_n43_nonstream_server/) | trump | xxlong | 16 | 43 |  | server | 0 | 0 | 19.44 / 70.46 / 73 | – | 65.82 | 27.96 | 25.76 | 9 | 0.294 | 0.42 | 21155 |
| [final_c32_trump_medium_c32_n128_nonstream_server](13_final_server/final_c32_trump_medium_c32_n128_nonstream_server/) | trump | medium | 32 | 128 |  | server | 0 | 0 | 6.83 / 9.12 / 11.69 | – | 6.59 | 26.94 | 25.58 | 0 | 1.119 | 4.09 | 21151 |
| [final_c1_shehbaz_short_c1_n16_nonstream_server](13_final_server/final_c1_shehbaz_short_c1_n16_nonstream_server/) | shehbaz | short | 1 | 16 |  | server | 0 | 0 | 1.01 / 1.8 / 1.86 | – | 4.61 | 4.64 | 4.61 | 0 | 0.206 | 1.01 | 21152 |
| [final_c1_shehbaz_short_c1_n16_stream_server](13_final_server/final_c1_shehbaz_short_c1_n16_stream_server/) | shehbaz | short | 1 | 16 | y | server | 0 | 0 | 0.88 / 1.32 / 1.38 | 0.12 / 0.12 / 0.12 | 4.36 | 5.04 | 5.05 | 0 | 0.199 | 1.16 | 21153 |
| [final_c16_shehbaz_short_c16_n64_nonstream_server](13_final_server/final_c16_shehbaz_short_c16_n64_nonstream_server/) | shehbaz | short | 16 | 64 |  | server | 0 | 0 | 3.55 / 5.53 / 6.63 | – | 4.82 | 19.38 | 18 | 0 | 0.789 | 4.02 | 21154 |
| [final_c16_shehbaz_medium_c16_n64_nonstream_server](13_final_server/final_c16_shehbaz_medium_c16_n64_nonstream_server/) | shehbaz | medium | 16 | 64 |  | server | 0 | 0 | 6.66 / 8.43 / 9.62 | – | 10.35 | 23.1 | 22.28 | 0 | 0.656 | 2.23 | 21155 |
| [final_c16_shehbaz_long_c16_n43_nonstream_server](13_final_server/final_c16_shehbaz_long_c16_n43_nonstream_server/) | shehbaz | long | 16 | 43 |  | server | 0 | 0 | 14.06 / 17.13 / 18.89 | – | 23.67 | 24.26 | 22.23 | 0 | 0.58 | 1.03 | 21355 |
| [final_c16_shehbaz_prompts_c16_n43_nonstream_server](13_final_server/final_c16_shehbaz_prompts_c16_n43_nonstream_server/) | shehbaz | prompts | 16 | 43 |  | server | 0 | 0 | 18.48 / 21.96 / 57.09 | – | 37.63 | 28.34 | 26.16 | 1 | 0.499 | 0.75 | 22206 |
| [final_c16_shehbaz_xxlong_c16_n43_nonstream_server](13_final_server/final_c16_shehbaz_xxlong_c16_n43_nonstream_server/) | shehbaz | xxlong | 16 | 43 |  | server | 0 | 0 | 22.54 / 88.88 / 99.54 | – | 75.99 | 28.2 | 28.53 | 9 | 0.303 | 0.37 | 22501 |
| [final_c32_shehbaz_medium_c32_n128_nonstream_server](13_final_server/final_c32_shehbaz_medium_c32_n128_nonstream_server/) | shehbaz | medium | 32 | 128 |  | server | 0 | 0 | 10.63 / 13.47 / 16.35 | – | 10.67 | 29.11 | 27.37 | 0 | 1.05 | 2.73 | 22836 |

## P5_retry_study: no phase.json


no bench_tts.py runs here (see the folder's own files)
