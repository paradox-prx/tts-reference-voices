# XTTS / Auralis baseline (as provided by the user, 2026-09-24)

Source: the Auralis README "Performance" section (full detail in
/home/serveradmin/services/xtts_optimized/auralis_new_architecture/docs/OPTIMIZATION_WRITEUP.md).
Measured on an **RTX 3090 24 GB** (the same GPU model as this box), **Pashto model**, full proxy stack, 20 concurrent,
with `benchmark_tts.py` (not the Urdu pools of `benchmark_tts_urdu_new.py`).

| Metric | Before | After |
|---|---|---|
| Single request | 1.46 s | 0.32 s |
| 20 concurrent, ~3 s clips | – | p50 0.52 s |
| 20 concurrent, ~5 s clips (burst) | mean 2.46 s | mean 0.73 s, p99 0.90 s |
| 20 concurrent sustained (200 reqs) | mean ~3.2 s, p99 5.7 s | mean 0.86 s, p99 1.2 s |
| Aggregate throughput | ~28x realtime | ~110x realtime |
| GPU utilization under load | low (CPU-bound) | 67 % avg / 96 % peak |

Auralis Urdu request settings in benchmark_tts_urdu_new.py: temperature 0.4, top_k 50, top_p 0.85,
repetition_penalty 2.0, length_penalty 1.0, enhance_speech, voice_key registry, n=20, c=20 by default.

Lessons from that work that carry over to any autoregressive TTS server: CUDA graphs for decode, multi-step
scheduling, repetition penalty on GPU, a voice-key registry instead of ~1 MB of base64 per request, micro-batched
vocoder decoding, no per-request empty_cache()/synchronize(), WAV encoding off the event loop, uvloop, and checking the
CPU governor and GPU clocks before trusting numbers (./diagnose_perf.sh).
