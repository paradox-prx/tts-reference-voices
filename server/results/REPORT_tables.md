# Tables for REPORT.md

Generated 2026-09-28T13:16:32+05:00 from `/home/vector/Documents/abdullah_workspace/qwen-server/tts-reference-voices/server/results` by `server/bench/collect.py`. Latency and TTFA in seconds (p50 / p90 / p99); TTFA is the first audio byte past the WAV header (streaming runs only); x realtime = audio seconds per wall second over the run (aggregate); x realtime p90-wall = audio finished by the time 90% of the requests had finished over that time (one runaway cannot dominate it); stragglers = requests slower than 3x the run's median latency; RTF = latency / audio seconds per request; GPU peak is nvidia-smi memory.used of the benchmark GPU during the run, in brackets minus the idle baseline before the engine started (desktop and other tenants). Suspects: takes whose pace is outside 0.6-1.8x the voice's expected s/letter (s = too short, l = too long).

## P0_smoke

Config: vllm-omni default (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| direct_trump_short_c1_n1_nonstream_inline | trump | short | 1 | 1 |  | inline | 0 | 0 | 0.78 / 0.78 / 0.78 | – | 4 | 5.11 | 5.11 | 0 | 0.196 | 1.28 | 19455 (19122) |
| direct_shehbaz_short_c1_n1_nonstream_inline | shehbaz | short | 1 | 1 |  | inline | 0 | 0 | 1.38 / 1.38 / 1.38 | – | 7.52 | 5.43 | 5.44 | 0 | 0.184 | 0.72 | 19452 (19119) |
| direct_trump_short_c1_n1_stream_inline | trump | short | 1 | 1 | y | inline | 0 | 0 | 0.65 / 0.65 / 0.65 | 0.12 / 0.12 / 0.12 | 3.2 | 4.95 | 4.95 | 0 | 0.202 | 1.55 | 19452 (19119) |
| direct_shehbaz_short_c1_n1_stream_inline | shehbaz | short | 1 | 1 | y | inline | 0 | 0 | 1.54 / 1.54 / 1.54 | 0.12 / 0.12 / 0.12 | 8.32 | 5.4 | 5.4 | 0 | 0.185 | 0.65 | 19452 (19119) |
| direct_trump_short_c1_n1_nonstream_upload | trump | short | 1 | 1 |  | upload | 0 | 0 | 0.75 / 0.75 / 0.75 | – | 3.92 | 5.2 | 5.2 | 0 | 0.192 | 1.33 | 19450 (19117) |
| direct_shehbaz_short_c1_n1_nonstream_upload | shehbaz | short | 1 | 1 |  | upload | 0 | 0 | 1.24 / 1.24 / 1.24 | – | 6.64 | 5.36 | 5.36 | 0 | 0.186 | 0.81 | 19450 (19117) |
| gw_trump_short_c1_n1_nonstream_server | trump | short | 1 | 1 |  | server | 0 | 0 | 0.88 / 0.88 / 0.88 | – | 3.68 | 4.2 | 4.2 | 0 | 0.238 | 1.14 | 19458 (19125) |
| gw_shehbaz_short_c1_n1_nonstream_server | shehbaz | short | 1 | 1 |  | server | 0 | 0 | 1.42 / 1.42 / 1.42 | – | 7.68 | 5.42 | 5.43 | 0 | 0.184 | 0.71 | 19458 (19125) |
| gw_trump_short_c1_n1_stream_server | trump | short | 1 | 1 | y | server | 0 | 0 | 0.69 / 0.69 / 0.69 | 0.11 / 0.11 / 0.11 | 3.52 | 5.1 | 5.1 | 0 | 0.196 | 1.45 | 19453 (19120) |
| gw_shehbaz_short_c1_n1_stream_server | shehbaz | short | 1 | 1 | y | server | 0 | 0 | 1.43 / 1.43 / 1.43 | 0.11 / 0.11 / 0.11 | 7.84 | 5.48 | 5.48 | 0 | 0.182 | 0.7 | 19456 (19123) |

## P1_screen_default

Config: vllm-omni default (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_medium_c1_n8_nonstream_inline | trump | medium | 1 | 8 |  | inline | 0 | 0 | 1.08 / 1.62 / 1.66 | – | 6.28 | 5.33 | 5.33 | 0 | 0.19 | 0.85 | 19148 (18807) |
| trump_medium_c8_n16_nonstream_inline | trump | medium | 8 | 16 |  | inline | 0 | 0 | 2.56 / 3.02 / 3.15 | – | 6.14 | 16.26 | 16.19 | 0 | 0.435 | 2.65 | 19176 (18835) |
| trump_medium_c32_n32_nonstream_inline | trump | medium | 32 | 32 |  | inline | 0 | 0 | 6.22 / 6.94 / 7.42 | – | 6.45 | 27.56 | 25.37 | 0 | 0.989 | 4.28 | 19458 (19117) |
| shehbaz_medium_c1_n8_nonstream_inline | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 2.26 / 2.62 / 2.69 | – | 10.85 | 5.49 | 5.49 | 0 | 0.184 | 0.51 | 19677 (19336) |
| shehbaz_medium_c8_n16_nonstream_inline | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 3.81 / 5.27 / 5.37 | – | 9.76 | 17.74 | 17.36 | 0 | 0.411 | 1.82 | 19678 (19337) |
| shehbaz_medium_c32_n32_nonstream_inline | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 8.47 / 9.52 / 9.91 | – | 9.42 | 30.29 | 27.68 | 0 | 0.925 | 3.22 | 19684 (19343) |

**aggregate x realtime** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 5.49 | 17.74 | 30.29 |
| trump medium | 5.33 | 16.26 | 27.56 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 5.49 | 17.36 | 27.68 |
| trump medium | 5.33 | 16.19 | 25.37 |

**req/s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 0.51 | 1.82 | 3.22 |
| trump medium | 0.85 | 2.65 | 4.28 |

**latency p50 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 2.26 | 3.81 | 8.47 |
| trump medium | 1.08 | 2.56 | 6.22 |

**latency p90 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 2.62 | 5.27 | 9.52 |
| trump medium | 1.62 | 3.02 | 6.94 |

**per-request RTF p50** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 0.184 | 0.411 | 0.925 |
| trump medium | 0.19 | 0.435 | 0.989 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 19336 | 19337 | 19343 |
| trump medium | 18807 | 18835 | 19117 |

## P1_screen_no_async_chunk

Config: vllm-omni no_async_chunk (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| shehbaz_medium_c8_n16_nonstream_inline | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 4.95 / 6.07 / 7.9 | – | 10.73 | 14.53 | 14.38 | 0 | 0.451 | 1.35 | 23102 (22769) |

## P1_screen_eager

Config: vllm-omni eager (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_medium_c1_n8_nonstream_inline | trump | medium | 1 | 8 |  | inline | 0 | 0 | 2.75 / 5.16 / 5.3 | – | 6.57 | 2 | 2 | 0 | 0.511 | 0.3 | 16788 (16461) |
| trump_medium_c8_n16_nonstream_inline | trump | medium | 8 | 16 |  | inline | 0 | 0 | 4.24 / 5.39 / 5.79 | – | 6.07 | 9.67 | 9.76 | 0 | 0.739 | 1.59 | 18837 (18510) |
| trump_medium_c32_n32_nonstream_inline | trump | medium | 32 | 32 |  | inline | 0 | 0 | 7.44 / 8.05 / 9.42 | – | 6.56 | 22 | 22.44 | 0 | 1.144 | 3.35 | 18976 (18649) |
| shehbaz_medium_c1_n8_nonstream_inline | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 4.68 / 6.24 / 6.56 | – | 10.4 | 2.26 | 2.26 | 0 | 0.453 | 0.22 | 19291 (18964) |
| shehbaz_medium_c8_n16_nonstream_inline | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 4.62 / 5.74 / 6.57 | – | 10.18 | 15.76 | 15.55 | 0 | 0.48 | 1.55 | 19293 (18966) |
| shehbaz_medium_c32_n32_nonstream_inline | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 8.44 / 9.52 / 9.77 | – | 9.23 | 30.2 | 27.27 | 0 | 0.943 | 3.27 | 19454 (19127) |

**aggregate x realtime** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 2.26 | 15.76 | 30.2 |
| trump medium | 2 | 9.67 | 22 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 2.26 | 15.55 | 27.27 |
| trump medium | 2 | 9.76 | 22.44 |

**req/s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 0.22 | 1.55 | 3.27 |
| trump medium | 0.3 | 1.59 | 3.35 |

**latency p50 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 4.68 | 4.62 | 8.44 |
| trump medium | 2.75 | 4.24 | 7.44 |

**latency p90 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 6.24 | 5.74 | 9.52 |
| trump medium | 5.16 | 5.39 | 8.05 |

**per-request RTF p50** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 0.453 | 0.48 | 0.943 |
| trump medium | 0.511 | 0.739 | 1.144 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 18964 | 18966 | 19127 |
| trump medium | 16461 | 18510 | 18649 |

## P1_screen_seqs32

Config: vllm-omni seqs32 (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_medium_c1_n8_nonstream_inline | trump | medium | 1 | 8 |  | inline | 0 | 0 | 1.11 / 1.85 / 1.9 | – | 6.77 | 5.37 | 5.37 | 0 | 0.188 | 0.79 | 18964 (18644) |
| trump_medium_c8_n16_nonstream_inline | trump | medium | 8 | 16 |  | inline | 0 | 0 | 2.84 / 3.6 / 4.29 | – | 6.38 | 15.89 | 15.17 | 0 | 0.479 | 2.49 | 19008 (18688) |
| trump_medium_c32_n32_nonstream_inline | trump | medium | 32 | 32 |  | inline | 0 | 0 | 6.39 / 7.12 / 7.58 | – | 6.41 | 26.85 | 24.84 | 0 | 1.022 | 4.19 | 19280 (18960) |
| shehbaz_medium_c1_n8_nonstream_inline | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 2.29 / 2.39 / 2.6 | – | 10.64 | 5.47 | 5.47 | 0 | 0.184 | 0.51 | 19496 (19176) |
| shehbaz_medium_c8_n16_nonstream_inline | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 4.3 / 5.53 / 5.62 | – | 10.49 | 17.24 | 16.86 | 0 | 0.417 | 1.64 | 19496 (19176) |
| shehbaz_medium_c32_n32_nonstream_inline | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 8.52 / 9.72 / 10.15 | – | 9.51 | 29.95 | 26.97 | 0 | 0.918 | 3.15 | 19632 (19312) |

**aggregate x realtime** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 5.47 | 17.24 | 29.95 |
| trump medium | 5.37 | 15.89 | 26.85 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 5.47 | 16.86 | 26.97 |
| trump medium | 5.37 | 15.17 | 24.84 |

**req/s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 0.51 | 1.64 | 3.15 |
| trump medium | 0.79 | 2.49 | 4.19 |

**latency p50 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 2.29 | 4.3 | 8.52 |
| trump medium | 1.11 | 2.84 | 6.39 |

**latency p90 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 2.39 | 5.53 | 9.72 |
| trump medium | 1.85 | 3.6 | 7.12 |

**per-request RTF p50** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 0.184 | 0.417 | 0.918 |
| trump medium | 0.188 | 0.479 | 1.022 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 19176 | 19176 | 19312 |
| trump medium | 18644 | 18688 | 18960 |

## P1_screen_seqs128

Config: vllm-omni seqs128 (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_medium_c1_n8_nonstream_inline | trump | medium | 1 | 8 |  | inline | 0 | 0 | 1.14 / 1.69 / 1.96 | – | 6.69 | 5.35 | 5.35 | 0 | 0.189 | 0.8 | 19722 (19404) |
| trump_medium_c8_n16_nonstream_inline | trump | medium | 8 | 16 |  | inline | 0 | 0 | 2.83 / 3.99 / 4.13 | – | 6.42 | 15.02 | 14.96 | 0 | 0.476 | 2.34 | 19766 (19448) |
| trump_medium_c32_n32_nonstream_inline | trump | medium | 32 | 32 |  | inline | 0 | 0 | 6.59 / 7.22 / 7.54 | – | 6.47 | 27.28 | 24.92 | 0 | 1.01 | 4.22 | 20046 (19728) |
| shehbaz_medium_c1_n8_nonstream_inline | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 1.99 / 2.65 / 2.84 | – | 10.63 | 5.42 | 5.42 | 0 | 0.187 | 0.51 | 20270 (19952) |
| shehbaz_medium_c8_n16_nonstream_inline | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 3.88 / 4.71 / 5.45 | – | 9.71 | 18.03 | 17.23 | 0 | 0.418 | 1.86 | 20272 (19954) |
| shehbaz_medium_c32_n32_nonstream_inline | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 8.64 / 9.53 / 9.82 | – | 9.35 | 30.46 | 27.37 | 0 | 0.922 | 3.26 | 20278 (19960) |

**aggregate x realtime** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 5.42 | 18.03 | 30.46 |
| trump medium | 5.35 | 15.02 | 27.28 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 5.42 | 17.23 | 27.37 |
| trump medium | 5.35 | 14.96 | 24.92 |

**req/s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 0.51 | 1.86 | 3.26 |
| trump medium | 0.8 | 2.34 | 4.22 |

**latency p50 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 1.99 | 3.88 | 8.64 |
| trump medium | 1.14 | 2.83 | 6.59 |

**latency p90 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 2.65 | 4.71 | 9.53 |
| trump medium | 1.69 | 3.99 | 7.22 |

**per-request RTF p50** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 0.187 | 0.418 | 0.922 |
| trump medium | 0.189 | 0.476 | 1.01 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 19952 | 19954 | 19960 |
| trump medium | 19404 | 19448 | 19728 |

## P1_screen_default_m045

Config: vllm-omni default_m045 (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_medium_c1_n8_nonstream_inline | trump | medium | 1 | 8 |  | inline | 0 | 0 | 1.1 / 1.63 / 1.63 | – | 6.28 | 5.34 | 5.34 | 0 | 0.189 | 0.85 | 15563 (15228) |
| trump_medium_c8_n16_nonstream_inline | trump | medium | 8 | 16 |  | inline | 0 | 0 | 2.52 / 3.26 / 3.4 | – | 6.21 | 15.8 | 16.16 | 0 | 0.44 | 2.55 | 15605 (15270) |
| trump_medium_c32_n32_nonstream_inline | trump | medium | 32 | 32 |  | inline | 0 | 0 | 5.98 / 6.79 / 7.3 | – | 6.33 | 27.57 | 25.62 | 0 | 0.996 | 4.35 | 15929 (15594) |
| shehbaz_medium_c1_n8_nonstream_inline | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 2.25 / 2.3 / 2.71 | – | 10.61 | 5.47 | 5.47 | 0 | 0.183 | 0.52 | 16061 (15726) |
| shehbaz_medium_c8_n16_nonstream_inline | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 4.28 / 4.71 / 4.76 | – | 9.9 | 17.38 | 17.22 | 0 | 0.411 | 1.76 | 16061 (15726) |
| shehbaz_medium_c32_n32_nonstream_inline | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 8.74 / 9.76 / 10.29 | – | 9.68 | 30.08 | 27.67 | 0 | 0.92 | 3.11 | 16061 (15726) |

**aggregate x realtime** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 5.47 | 17.38 | 30.08 |
| trump medium | 5.34 | 15.8 | 27.57 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 5.47 | 17.22 | 27.67 |
| trump medium | 5.34 | 16.16 | 25.62 |

**req/s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 0.52 | 1.76 | 3.11 |
| trump medium | 0.85 | 2.55 | 4.35 |

**latency p50 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 2.25 | 4.28 | 8.74 |
| trump medium | 1.1 | 2.52 | 5.98 |

**latency p90 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 2.3 | 4.71 | 9.76 |
| trump medium | 1.63 | 3.26 | 6.79 |

**per-request RTF p50** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 0.183 | 0.411 | 0.92 |
| trump medium | 0.189 | 0.44 | 0.996 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 15726 | 15726 | 15726 |
| trump medium | 15228 | 15270 | 15594 |

## P1_screen_decode4g_m045

Config: vllm-omni decode4g_m045 (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_medium_c1_n8_nonstream_inline | trump | medium | 1 | 8 |  | inline | 0 | 0 | 1.22 / 1.79 / 1.91 | – | 6.86 | 5.31 | 5.31 | 0 | 0.19 | 0.77 | 20284 (19949) |
| trump_medium_c8_n16_nonstream_inline | trump | medium | 8 | 16 |  | inline | 0 | 0 | 2.85 / 3.43 / 4 | – | 6.22 | 15.6 | 15.05 | 0 | 0.492 | 2.51 | 20328 (19993) |
| trump_medium_c32_n32_nonstream_inline | trump | medium | 32 | 32 |  | inline | 0 | 0 | 6.49 / 6.92 / 7.38 | – | 6.34 | 27.29 | 25.23 | 0 | 0.999 | 4.3 | 20608 (20273) |
| shehbaz_medium_c1_n8_nonstream_inline | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 2.3 / 2.35 / 2.69 | – | 10.56 | 5.41 | 5.41 | 0 | 0.187 | 0.51 | 20829 (20494) |
| shehbaz_medium_c8_n16_nonstream_inline | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 4.08 / 4.86 / 5.09 | – | 9.79 | 17.52 | 17.36 | 0 | 0.416 | 1.79 | 20827 (20492) |
| shehbaz_medium_c32_n32_nonstream_inline | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 8.56 / 9.58 / 9.91 | – | 9.57 | 30.75 | 28.12 | 0 | 0.894 | 3.21 | 20832 (20497) |

**aggregate x realtime** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 5.41 | 17.52 | 30.75 |
| trump medium | 5.31 | 15.6 | 27.29 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 5.41 | 17.36 | 28.12 |
| trump medium | 5.31 | 15.05 | 25.23 |

**req/s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 0.51 | 1.79 | 3.21 |
| trump medium | 0.77 | 2.51 | 4.3 |

**latency p50 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 2.3 | 4.08 | 8.56 |
| trump medium | 1.22 | 2.85 | 6.49 |

**latency p90 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 2.35 | 4.86 | 9.58 |
| trump medium | 1.79 | 3.43 | 6.92 |

**per-request RTF p50** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 0.187 | 0.416 | 0.894 |
| trump medium | 0.19 | 0.492 | 0.999 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz medium | 20494 | 20492 | 20497 |
| trump medium | 19949 | 19993 | 20273 |

## P2_matrix

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_short_c1_n8_nonstream_inline | trump | short | 1 | 8 |  | inline | 0 | 0 | 0.79 / 1 / 1.01 | – | 3.61 | 5.01 | 5.01 | 0 | 0.202 | 1.39 | 19144 (18809) |
| trump_short_c2_n8_nonstream_inline | trump | short | 2 | 8 |  | inline | 0 | 0 | 0.63 / 1.14 / 1.16 | – | 2.74 | 8.13 | 8.13 | 0 | 0.253 | 2.97 | 19147 (18812) |
| trump_short_c4_n8_nonstream_inline | trump | short | 4 | 8 |  | inline | 0 | 0 | 0.89 / 1.21 / 1.39 | – | 3 | 10.64 | 10.64 | 0 | 0.355 | 3.55 | 19167 (18832) |
| trump_short_c8_n16_nonstream_inline | trump | short | 8 | 16 |  | inline | 0 | 1 (0s/1l) | 1.36 / 2.31 / 2.86 | – | 3.01 | 13.39 | 12.64 | 0 | 0.533 | 4.45 | 19195 (18860) |
| trump_short_c16_n32_nonstream_inline | trump | short | 16 | 32 |  | inline | 0 | 1 (1s/0l) | 2.4 / 3.99 / 4.49 | – | 2.89 | 16.09 | 14.77 | 0 | 0.912 | 5.57 | 19235 (18900) |
| trump_short_c32_n64_nonstream_inline | trump | short | 32 | 64 |  | inline | 0 | 0 | 3.64 / 5.97 / 6.85 | – | 2.97 | 20.85 | 18.44 | 0 | 1.397 | 7.01 | 19463 (19128) |
| shehbaz_short_c1_n8_nonstream_inline | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 1.05 / 1.22 / 1.35 | – | 5.06 | 5.13 | 5.13 | 0 | 0.195 | 1.01 | 19675 (19340) |
| shehbaz_short_c2_n8_nonstream_inline | shehbaz | short | 2 | 8 |  | inline | 0 | 0 | 0.94 / 1.06 / 1.18 | – | 3.6 | 8.04 | 8.04 | 0 | 0.243 | 2.23 | 19670 (19335) |
| shehbaz_short_c4_n8_nonstream_inline | shehbaz | short | 4 | 8 |  | inline | 0 | 1 (0s/1l) | 1.48 / 1.84 / 2.26 | – | 5.14 | 11.38 | 11.38 | 0 | 0.301 | 2.21 | 19678 (19343) |
| shehbaz_short_c8_n16_nonstream_inline | shehbaz | short | 8 | 16 |  | inline | 0 | 1 (0s/1l) | 1.82 / 2.69 / 3.39 | – | 3.94 | 14.89 | 13.65 | 0 | 0.5 | 3.79 | 19678 (19343) |
| shehbaz_short_c16_n32_nonstream_inline | shehbaz | short | 16 | 32 |  | inline | 0 | 3 (0s/3l) | 2.68 / 4.79 / 5.88 | – | 4.36 | 19.59 | 17.77 | 0 | 0.753 | 4.49 | 19670 (19335) |
| shehbaz_short_c32_n64_nonstream_inline | shehbaz | short | 32 | 64 |  | inline | 0 | 3 (0s/3l) | 4.36 / 7.52 / 9.27 | – | 4.1 | 22.48 | 21.36 | 0 | 1.263 | 5.49 | 19811 (19476) |
| trump_medium_c1_n8_nonstream_inline | trump | medium | 1 | 8 |  | inline | 0 | 0 | 1.2 / 1.66 / 1.84 | – | 6.96 | 5.31 | 5.31 | 0 | 0.19 | 0.76 | 19810 (19475) |
| trump_medium_c2_n8_nonstream_inline | trump | medium | 2 | 8 |  | inline | 0 | 0 | 1.33 / 1.58 / 1.68 | – | 6.29 | 9.45 | 9.45 | 0 | 0.21 | 1.5 | 19802 (19467) |
| trump_medium_c4_n8_nonstream_inline | trump | medium | 4 | 8 |  | inline | 0 | 0 | 1.71 / 1.93 / 3.06 | – | 6.48 | 12.29 | 12.29 | 0 | 0.289 | 1.9 | 19802 (19467) |
| trump_medium_c8_n16_nonstream_inline | trump | medium | 8 | 16 |  | inline | 0 | 0 | 2.54 / 3.84 / 3.98 | – | 6.24 | 16.96 | 16.24 | 0 | 0.444 | 2.72 | 19810 (19475) |
| trump_medium_c16_n32_nonstream_inline | trump | medium | 16 | 32 |  | inline | 0 | 0 | 4.31 / 5.42 / 7.12 | – | 6.96 | 23.48 | 21.68 | 0 | 0.635 | 3.37 | 19818 (19483) |
| trump_medium_c32_n64_nonstream_inline | trump | medium | 32 | 64 |  | inline | 0 | 0 | 6.43 / 8.49 / 11.86 | – | 6.85 | 28.31 | 26.9 | 0 | 1.009 | 4.13 | 19811 (19476) |
| shehbaz_medium_c1_n8_nonstream_inline | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 2.27 / 2.59 / 2.67 | – | 10.82 | 5.4 | 5.4 | 0 | 0.185 | 0.5 | 19813 (19478) |
| shehbaz_medium_c2_n8_nonstream_inline | shehbaz | medium | 2 | 8 |  | inline | 0 | 0 | 2.07 / 2.44 / 2.93 | – | 10.26 | 9.05 | 9.06 | 0 | 0.202 | 0.88 | 19810 (19475) |
| shehbaz_medium_c4_n8_nonstream_inline | shehbaz | medium | 4 | 8 |  | inline | 0 | 0 | 2.54 / 3 / 3.37 | – | 9.68 | 13.04 | 13.05 | 0 | 0.279 | 1.35 | 19805 (19470) |
| shehbaz_medium_c8_n16_nonstream_inline | shehbaz | medium | 8 | 16 |  | inline | 0 | 0 | 3.94 / 4.92 / 5.03 | – | 9.57 | 17.05 | 17.16 | 0 | 0.422 | 1.78 | 19805 (19470) |
| shehbaz_medium_c16_n32_nonstream_inline | shehbaz | medium | 16 | 32 |  | inline | 0 | 0 | 5.63 / 7 / 7.4 | – | 9.5 | 23.87 | 22.07 | 0 | 0.612 | 2.51 | 19805 (19470) |
| shehbaz_medium_c32_n64_nonstream_inline | shehbaz | medium | 32 | 64 |  | inline | 0 | 0 | 9.13 / 12.2 / 13.79 | – | 10.38 | 30.85 | 28.34 | 0 | 0.954 | 2.97 | 19948 (19613) |
| trump_long_c1_n4_nonstream_inline | trump | long | 1 | 4 |  | inline | 0 | 0 | 3.03 / 3.05 / 3.05 | – | 15.28 | 5.48 | 5.48 | 0 | 0.183 | 0.36 | 19954 (19619) |
| trump_long_c2_n4_nonstream_inline | trump | long | 2 | 4 |  | inline | 0 | 0 | 3.03 / 3.47 / 3.47 | – | 15.82 | 9.89 | 9.89 | 0 | 0.196 | 0.63 | 19942 (19607) |
| trump_long_c4_n4_nonstream_inline | trump | long | 4 | 4 |  | inline | 0 | 0 | 4.23 / 4.26 / 4.26 | – | 15.66 | 14.68 | 14.68 | 0 | 0.264 | 0.94 | 19939 (19604) |
| trump_long_c8_n8_nonstream_inline | trump | long | 8 | 8 |  | inline | 0 | 0 | 6.01 / 6.39 / 6.43 | – | 15.39 | 19.13 | 19.13 | 0 | 0.392 | 1.24 | 19941 (19606) |
| trump_long_c16_n16_nonstream_inline | trump | long | 16 | 16 |  | inline | 0 | 0 | 9.1 / 9.88 / 10.03 | – | 16.45 | 26.23 | 24.59 | 0 | 0.555 | 1.59 | 19937 (19602) |
| trump_long_c32_n32_nonstream_inline | trump | long | 32 | 32 |  | inline | 0 | 0 | 14 / 15.04 / 15.32 | – | 16.38 | 34.16 | 30.78 | 0 | 0.847 | 2.09 | 19940 (19605) |
| shehbaz_long_c1_n4_nonstream_inline | shehbaz | long | 1 | 4 |  | inline | 0 | 0 | 4.25 / 4.38 / 4.38 | – | 22.28 | 5.57 | 5.57 | 0 | 0.179 | 0.25 | 19928 (19593) |
| shehbaz_long_c2_n4_nonstream_inline | shehbaz | long | 2 | 4 |  | inline | 0 | 0 | 4.14 / 4.77 / 4.77 | – | 22.12 | 10.05 | 10.05 | 0 | 0.192 | 0.45 | 19928 (19593) |
| shehbaz_long_c4_n4_nonstream_inline | shehbaz | long | 4 | 4 |  | inline | 0 | 0 | 5.98 / 6.08 / 6.08 | – | 22.62 | 14.84 | 14.84 | 0 | 0.256 | 0.66 | 19928 (19593) |
| shehbaz_long_c8_n8_nonstream_inline | shehbaz | long | 8 | 8 |  | inline | 0 | 0 | 8.51 / 8.91 / 9 | – | 22.07 | 19.59 | 19.6 | 0 | 0.383 | 0.89 | 19928 (19593) |
| shehbaz_long_c16_n16_nonstream_inline | shehbaz | long | 16 | 16 |  | inline | 0 | 0 | 12.28 / 12.72 / 12.85 | – | 22.27 | 27.68 | 26 | 0 | 0.536 | 1.24 | 19928 (19593) |
| shehbaz_long_c32_n32_nonstream_inline | shehbaz | long | 32 | 32 |  | inline | 0 | 0 | 17.79 / 19.57 / 20.3 | – | 22.05 | 34.7 | 31.75 | 0 | 0.824 | 1.57 | 20072 (19737) |
| trump_xlong_c1_n6_nonstream_inline | trump | xlong | 1 | 6 |  | inline | 0 | 0 | 5.52 / 5.84 / 6.31 | – | 32.24 | 5.63 | 5.63 | 0 | 0.178 | 0.17 | 20072 (19737) |
| trump_xlong_c2_n6_nonstream_inline | trump | xlong | 2 | 6 |  | inline | 0 | 0 | 5.93 / 5.99 / 6.59 | – | 31.79 | 10.52 | 10.52 | 0 | 0.189 | 0.33 | 20072 (19737) |
| trump_xlong_c4_n6_nonstream_inline | trump | xlong | 4 | 6 |  | inline | 0 | 0 | 7.48 / 7.73 / 8.12 | – | 31.36 | 13.49 | 13.49 | 0 | 0.251 | 0.43 | 20072 (19737) |
| trump_xlong_c8_n8_nonstream_inline | trump | xlong | 8 | 8 |  | inline | 0 | 0 | 11.76 / 13.56 / 15.35 | – | 34.43 | 17.93 | 17.93 | 0 | 0.376 | 0.52 | 20072 (19737) |
| trump_xlong_c16_n16_nonstream_inline | trump | xlong | 16 | 16 |  | inline | 0 | 0 | 16.44 / 17.66 / 17.77 | – | 31.62 | 28.46 | 26.59 | 0 | 0.523 | 0.9 | 20073 (19738) |
| trump_xlong_c32_n32_nonstream_inline | trump | xlong | 32 | 32 |  | inline | 0 | 0 | 25.41 / 26.88 / 30.5 | – | 32.7 | 34.26 | 33.91 | 0 | 0.798 | 1.05 | 20072 (19737) |
| shehbaz_xlong_c1_n6_nonstream_inline | shehbaz | xlong | 1 | 6 |  | inline | 0 | 0 | 5.89 / 6.23 / 6.26 | – | 32.2 | 5.62 | 5.62 | 0 | 0.178 | 0.17 | 20072 (19737) |
| shehbaz_xlong_c2_n6_nonstream_inline | shehbaz | xlong | 2 | 6 |  | inline | 0 | 0 | 6.25 / 6.99 / 7.01 | – | 34.15 | 10.12 | 10.12 | 0 | 0.19 | 0.3 | 20072 (19737) |
| shehbaz_xlong_c4_n6_nonstream_inline | shehbaz | xlong | 4 | 6 |  | inline | 0 | 0 | 7.79 / 8.92 / 9.04 | – | 32.29 | 13.58 | 13.58 | 0 | 0.253 | 0.42 | 20072 (19737) |
| shehbaz_xlong_c8_n8_nonstream_inline | shehbaz | xlong | 8 | 8 |  | inline | 0 | 0 | 13.48 / 13.82 / 14.41 | – | 35.33 | 19.59 | 19.59 | 0 | 0.375 | 0.55 | 20072 (19737) |
| shehbaz_xlong_c16_n16_nonstream_inline | shehbaz | xlong | 16 | 16 |  | inline | 1 | 0 | 16.61 / 18 / 18.3 | – | 31.9 | 20.62 | 26.11 | 0 | 0.525 | 0.65 | 20070 (19735) |
| shehbaz_xlong_c32_n32_nonstream_inline | shehbaz | xlong | 32 | 32 |  | inline | 0 | 0 | 26.49 / 28.04 / 28.66 | – | 32.81 | 36.57 | 33.3 | 0 | 0.804 | 1.11 | 20070 (19735) |
| trump_xxlong_c1_n4_nonstream_inline | trump | xxlong | 1 | 4 |  | inline | 0 | 0 | 11.15 / 11.97 / 11.97 | – | 63.1 | 5.67 | 5.67 | 0 | 0.177 | 0.09 | 20070 (19735) |
| trump_xxlong_c2_n4_nonstream_inline | trump | xxlong | 2 | 4 |  | inline | 0 | 0 | 11.66 / 11.74 / 11.74 | – | 61.84 | 10.57 | 10.57 | 0 | 0.188 | 0.17 | 20070 (19735) |
| trump_xxlong_c4_n4_nonstream_inline | trump | xxlong | 4 | 4 |  | inline | 0 | 0 | 15.37 / 16.15 / 16.15 | – | 62.12 | 15.38 | 15.38 | 0 | 0.25 | 0.25 | 20070 (19735) |
| trump_xxlong_c8_n8_nonstream_inline | trump | xxlong | 8 | 8 |  | inline | 0 | 0 | 22.67 / 23.49 / 23.68 | – | 61.26 | 20.69 | 20.69 | 0 | 0.372 | 0.34 | 20070 (19735) |
| trump_xxlong_c16_n16_nonstream_inline | trump | xxlong | 16 | 16 |  | inline | 0 | 0 | 31.8 / 35.72 / 38.32 | – | 64.36 | 26.86 | 26.25 | 0 | 0.516 | 0.42 | 20070 (19735) |
| trump_xxlong_c32_n32_nonstream_inline | trump | xxlong | 32 | 32 |  | inline | 0 | 0 | 49.46 / 51.45 / 56 | – | 63.62 | 36.32 | 34.75 | 0 | 0.788 | 0.57 | 20072 (19737) |
| shehbaz_xxlong_c1_n4_nonstream_inline | shehbaz | xxlong | 1 | 4 |  | inline | 4 | 0 | – | – | – | 0 | 0 | 0 | – | 0 | 20072 (19737) |
| shehbaz_xxlong_c2_n4_nonstream_inline | shehbaz | xxlong | 2 | 4 |  | inline | 2 | 0 | 7.31 / 7.76 / 7.76 | – | 39.84 | 2.17 | 2.17 | 1 | 0.189 | 0.05 | 20071 (19736) |
| shehbaz_xxlong_c4_n4_nonstream_inline | shehbaz | xxlong | 4 | 4 |  | inline | 1 | 0 | 10.87 / 11.23 / 11.23 | – | 43.57 | 5.37 | 5.37 | 0 | 0.251 | 0.12 | 20071 (19736) |
| shehbaz_xxlong_c8_n8_nonstream_inline | shehbaz | xxlong | 8 | 8 |  | inline | 1 | 0 | 15.96 / 25.05 / 25.71 | – | 55.95 | 12.09 | 12.09 | 0 | 0.375 | 0.22 | 20071 (19736) |
| shehbaz_xxlong_c16_n16_nonstream_inline | shehbaz | xxlong | 16 | 16 |  | inline | 10 | 1 (1s/0l) | 27.3 / 36.28 / 42.27 | – | 55.55 | 5.44 | 5.54 | 0 | 0.514 | 0.1 | 20071 (19736) |
| shehbaz_xxlong_c32_n32_nonstream_inline | shehbaz | xxlong | 32 | 32 |  | inline | 13 | 1 (1s/0l) | 33.91 / 51.23 / 57.88 | – | 49.58 | 11.97 | 12.05 | 0 | 0.798 | 0.24 | 20259 (19924) |

**aggregate x realtime** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz long | 5.57 | 10.05 | 14.84 | 19.59 | 27.68 | 34.7 |
| shehbaz medium | 5.4 | 9.05 | 13.04 | 17.05 | 23.87 | 30.85 |
| shehbaz short | 5.13 | 8.04 | 11.38 | 14.89 | 19.59 | 22.48 |
| shehbaz xlong | 5.62 | 10.12 | 13.58 | 19.59 | 20.62 | 36.57 |
| shehbaz xxlong | 0 | 2.17 | 5.37 | 12.09 | 5.44 | 11.97 |
| trump long | 5.48 | 9.89 | 14.68 | 19.13 | 26.23 | 34.16 |
| trump medium | 5.31 | 9.45 | 12.29 | 16.96 | 23.48 | 28.31 |
| trump short | 5.01 | 8.13 | 10.64 | 13.39 | 16.09 | 20.85 |
| trump xlong | 5.63 | 10.52 | 13.49 | 17.93 | 28.46 | 34.26 |
| trump xxlong | 5.67 | 10.57 | 15.38 | 20.69 | 26.86 | 36.32 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz long | 5.57 | 10.05 | 14.84 | 19.6 | 26 | 31.75 |
| shehbaz medium | 5.4 | 9.06 | 13.05 | 17.16 | 22.07 | 28.34 |
| shehbaz short | 5.13 | 8.04 | 11.38 | 13.65 | 17.77 | 21.36 |
| shehbaz xlong | 5.62 | 10.12 | 13.58 | 19.59 | 26.11 | 33.3 |
| shehbaz xxlong | 0 | 2.17 | 5.37 | 12.09 | 5.54 | 12.05 |
| trump long | 5.48 | 9.89 | 14.68 | 19.13 | 24.59 | 30.78 |
| trump medium | 5.31 | 9.45 | 12.29 | 16.24 | 21.68 | 26.9 |
| trump short | 5.01 | 8.13 | 10.64 | 12.64 | 14.77 | 18.44 |
| trump xlong | 5.63 | 10.52 | 13.49 | 17.93 | 26.59 | 33.91 |
| trump xxlong | 5.67 | 10.57 | 15.38 | 20.69 | 26.25 | 34.75 |

**req/s** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz long | 0.25 | 0.45 | 0.66 | 0.89 | 1.24 | 1.57 |
| shehbaz medium | 0.5 | 0.88 | 1.35 | 1.78 | 2.51 | 2.97 |
| shehbaz short | 1.01 | 2.23 | 2.21 | 3.79 | 4.49 | 5.49 |
| shehbaz xlong | 0.17 | 0.3 | 0.42 | 0.55 | 0.65 | 1.11 |
| shehbaz xxlong | 0 | 0.05 | 0.12 | 0.22 | 0.1 | 0.24 |
| trump long | 0.36 | 0.63 | 0.94 | 1.24 | 1.59 | 2.09 |
| trump medium | 0.76 | 1.5 | 1.9 | 2.72 | 3.37 | 4.13 |
| trump short | 1.39 | 2.97 | 3.55 | 4.45 | 5.57 | 7.01 |
| trump xlong | 0.17 | 0.33 | 0.43 | 0.52 | 0.9 | 1.05 |
| trump xxlong | 0.09 | 0.17 | 0.25 | 0.34 | 0.42 | 0.57 |

**latency p50 s** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz long | 4.25 | 4.14 | 5.98 | 8.51 | 12.28 | 17.79 |
| shehbaz medium | 2.27 | 2.07 | 2.54 | 3.94 | 5.63 | 9.13 |
| shehbaz short | 1.05 | 0.94 | 1.48 | 1.82 | 2.68 | 4.36 |
| shehbaz xlong | 5.89 | 6.25 | 7.79 | 13.48 | 16.61 | 26.49 |
| shehbaz xxlong | – | 7.31 | 10.87 | 15.96 | 27.3 | 33.91 |
| trump long | 3.03 | 3.03 | 4.23 | 6.01 | 9.1 | 14 |
| trump medium | 1.2 | 1.33 | 1.71 | 2.54 | 4.31 | 6.43 |
| trump short | 0.79 | 0.63 | 0.89 | 1.36 | 2.4 | 3.64 |
| trump xlong | 5.52 | 5.93 | 7.48 | 11.76 | 16.44 | 25.41 |
| trump xxlong | 11.15 | 11.66 | 15.37 | 22.67 | 31.8 | 49.46 |

**latency p90 s** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz long | 4.38 | 4.77 | 6.08 | 8.91 | 12.72 | 19.57 |
| shehbaz medium | 2.59 | 2.44 | 3 | 4.92 | 7 | 12.2 |
| shehbaz short | 1.22 | 1.06 | 1.84 | 2.69 | 4.79 | 7.52 |
| shehbaz xlong | 6.23 | 6.99 | 8.92 | 13.82 | 18 | 28.04 |
| shehbaz xxlong | – | 7.76 | 11.23 | 25.05 | 36.28 | 51.23 |
| trump long | 3.05 | 3.47 | 4.26 | 6.39 | 9.88 | 15.04 |
| trump medium | 1.66 | 1.58 | 1.93 | 3.84 | 5.42 | 8.49 |
| trump short | 1 | 1.14 | 1.21 | 2.31 | 3.99 | 5.97 |
| trump xlong | 5.84 | 5.99 | 7.73 | 13.56 | 17.66 | 26.88 |
| trump xxlong | 11.97 | 11.74 | 16.15 | 23.49 | 35.72 | 51.45 |

**per-request RTF p50** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz long | 0.179 | 0.192 | 0.256 | 0.383 | 0.536 | 0.824 |
| shehbaz medium | 0.185 | 0.202 | 0.279 | 0.422 | 0.612 | 0.954 |
| shehbaz short | 0.195 | 0.243 | 0.301 | 0.5 | 0.753 | 1.263 |
| shehbaz xlong | 0.178 | 0.19 | 0.253 | 0.375 | 0.525 | 0.804 |
| shehbaz xxlong | – | 0.189 | 0.251 | 0.375 | 0.514 | 0.798 |
| trump long | 0.183 | 0.196 | 0.264 | 0.392 | 0.555 | 0.847 |
| trump medium | 0.19 | 0.21 | 0.289 | 0.444 | 0.635 | 1.009 |
| trump short | 0.202 | 0.253 | 0.355 | 0.533 | 0.912 | 1.397 |
| trump xlong | 0.178 | 0.189 | 0.251 | 0.376 | 0.523 | 0.798 |
| trump xxlong | 0.177 | 0.188 | 0.25 | 0.372 | 0.516 | 0.788 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz long | 19593 | 19593 | 19593 | 19593 | 19593 | 19737 |
| shehbaz medium | 19478 | 19475 | 19470 | 19470 | 19470 | 19613 |
| shehbaz short | 19340 | 19335 | 19343 | 19343 | 19335 | 19476 |
| shehbaz xlong | 19737 | 19737 | 19737 | 19737 | 19735 | 19735 |
| shehbaz xxlong | 19737 | 19736 | 19736 | 19736 | 19736 | 19924 |
| trump long | 19619 | 19607 | 19604 | 19606 | 19602 | 19605 |
| trump medium | 19475 | 19467 | 19467 | 19475 | 19483 | 19476 |
| trump short | 18809 | 18812 | 18832 | 18860 | 18900 | 19128 |
| trump xlong | 19737 | 19737 | 19737 | 19737 | 19738 | 19737 |
| trump xxlong | 19735 | 19735 | 19735 | 19735 | 19735 | 19737 |

## P2_high_c

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_short_c48_n96_nonstream_inline | trump | short | 48 | 96 |  | inline | 0 | 1 (0s/1l) | 5.73 / 9.42 / 11.43 | – | 2.97 | 20.95 | 18.89 | 0 | 2.124 | 7.06 | 19769 (19440) |
| trump_short_c64_n128_nonstream_inline | trump | short | 64 | 128 |  | inline | 0 | 2 (1s/1l) | 6.66 / 11.43 / 14.19 | – | 3.01 | 23.05 | 21.34 | 0 | 2.595 | 7.66 | 19849 (19520) |
| trump_medium_c48_n96_nonstream_inline | trump | medium | 48 | 96 |  | inline | 0 | 0 | 9.13 / 13.25 / 15.15 | – | 6.41 | 28.24 | 26.25 | 0 | 1.594 | 4.4 | 19849 (19520) |
| trump_medium_c64_n128_nonstream_inline | trump | medium | 64 | 128 |  | inline | 0 | 0 | 12.26 / 16.46 / 20.75 | – | 6.76 | 31.78 | 29.11 | 0 | 1.847 | 4.7 | 19883 (19554) |
| shehbaz_short_c48_n96_nonstream_inline | shehbaz | short | 48 | 96 |  | inline | 0 | 0 | 6.98 / 11.33 / 14.57 | – | 4.2 | 23.78 | 21.66 | 0 | 1.931 | 5.66 | 19889 (19560) |
| shehbaz_short_c64_n128_nonstream_inline | shehbaz | short | 64 | 128 |  | inline | 0 | 1 (0s/1l) | 7.79 / 13.11 / 16.27 | – | 4.05 | 24.72 | 22.99 | 0 | 2.393 | 6.11 | 20135 (19806) |
| shehbaz_medium_c48_n96_nonstream_inline | shehbaz | medium | 48 | 96 |  | inline | 0 | 0 | 13.48 / 18.45 / 20.91 | – | 10.03 | 30.43 | 28.56 | 0 | 1.493 | 3.03 | 20135 (19806) |
| shehbaz_medium_c64_n128_nonstream_inline | shehbaz | medium | 64 | 128 |  | inline | 0 | 0 | 15.72 / 21.91 / 27.79 | – | 9.9 | 34.15 | 32.22 | 0 | 1.754 | 3.45 | 20399 (20070) |
| trump_xlong_c64_n64_nonstream_inline | trump | xlong | 64 | 64 |  | inline | 0 | 0 | 45.7 / 48.02 / 49.53 | – | 32.3 | 40.26 | 38.07 | 0 | 1.436 | 1.25 | 20397 (20068) |
| shehbaz_xlong_c64_n64_nonstream_inline | shehbaz | xlong | 64 | 64 |  | inline | 2 | 1 (1s/0l) | 47.83 / 51.88 / 55.27 | – | 34.16 | 34.52 | 36.3 | 0 | 1.433 | 1.01 | 20407 (20078) |

**aggregate x realtime** by concurrency

| series | c=48 | c=64 |
|---|---|---|
| shehbaz medium | 30.43 | 34.15 |
| shehbaz short | 23.78 | 24.72 |
| trump medium | 28.24 | 31.78 |
| trump short | 20.95 | 23.05 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=48 | c=64 |
|---|---|---|
| shehbaz medium | 28.56 | 32.22 |
| shehbaz short | 21.66 | 22.99 |
| trump medium | 26.25 | 29.11 |
| trump short | 18.89 | 21.34 |

**req/s** by concurrency

| series | c=48 | c=64 |
|---|---|---|
| shehbaz medium | 3.03 | 3.45 |
| shehbaz short | 5.66 | 6.11 |
| trump medium | 4.4 | 4.7 |
| trump short | 7.06 | 7.66 |

**latency p50 s** by concurrency

| series | c=48 | c=64 |
|---|---|---|
| shehbaz medium | 13.48 | 15.72 |
| shehbaz short | 6.98 | 7.79 |
| trump medium | 9.13 | 12.26 |
| trump short | 5.73 | 6.66 |

**latency p90 s** by concurrency

| series | c=48 | c=64 |
|---|---|---|
| shehbaz medium | 18.45 | 21.91 |
| shehbaz short | 11.33 | 13.11 |
| trump medium | 13.25 | 16.46 |
| trump short | 9.42 | 11.43 |

**per-request RTF p50** by concurrency

| series | c=48 | c=64 |
|---|---|---|
| shehbaz medium | 1.493 | 1.754 |
| shehbaz short | 1.931 | 2.393 |
| trump medium | 1.594 | 1.847 |
| trump short | 2.124 | 2.595 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=48 | c=64 |
|---|---|---|
| shehbaz medium | 19806 | 20070 |
| shehbaz short | 19560 | 19806 |
| trump medium | 19520 | 19554 |
| trump short | 19440 | 19520 |

## P3_stream

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_short_c1_n8_stream_inline | trump | short | 1 | 8 | y | inline | 0 | 0 | 0.73 / 0.99 / 1 | 0.12 / 0.13 / 0.14 | 3.62 | 5.01 | 5.01 | 0 | 0.204 | 1.38 | 20258 (19923) |
| trump_short_c2_n8_stream_inline | trump | short | 2 | 8 | y | inline | 0 | 0 | 0.55 / 1.08 / 1.25 | 0.17 / 0.19 / 0.19 | 2.66 | 7.85 | 7.85 | 0 | 0.258 | 2.95 | 20262 (19927) |
| trump_short_c4_n8_stream_inline | trump | short | 4 | 8 | y | inline | 0 | 0 | 0.91 / 1.23 / 1.41 | 0.36 / 0.36 / 0.36 | 2.87 | 10.17 | 10.17 | 0 | 0.376 | 3.54 | 20262 (19927) |
| trump_short_c8_n16_stream_inline | trump | short | 8 | 16 | y | inline | 0 | 0 | 1.45 / 2.62 / 3.25 | 0.43 / 0.66 / 0.66 | 3.16 | 13.87 | 12.37 | 0 | 0.513 | 4.39 | 20271 (19936) |
| trump_short_c16_n32_stream_inline | trump | short | 16 | 32 | y | inline | 0 | 0 | 2.31 / 3.74 / 4.42 | 0.81 / 1.26 / 1.26 | 2.94 | 16.74 | 15.6 | 0 | 0.857 | 5.7 | 20276 (19941) |
| trump_short_c32_n64_stream_inline | trump | short | 32 | 64 | y | inline | 0 | 0 | 3.76 / 6.41 / 7.14 | 1.77 / 2.46 / 2.47 | 3.01 | 20.64 | 18.52 | 0 | 1.434 | 6.86 | 20276 (19941) |
| shehbaz_short_c1_n8_stream_inline | shehbaz | short | 1 | 8 | y | inline | 0 | 1 (0s/1l) | 1.06 / 1.31 / 1.54 | 0.12 / 0.12 / 0.13 | 5.29 | 5.15 | 5.15 | 0 | 0.197 | 0.97 | 20271 (19936) |
| shehbaz_short_c2_n8_stream_inline | shehbaz | short | 2 | 8 | y | inline | 0 | 0 | 0.92 / 1.13 / 1.14 | 0.14 / 0.2 / 0.2 | 3.56 | 8.03 | 8.03 | 0 | 0.243 | 2.26 | 20266 (19931) |
| shehbaz_short_c4_n8_stream_inline | shehbaz | short | 4 | 8 | y | inline | 0 | 1 (0s/1l) | 1.56 / 2.08 / 2.54 | 0.36 / 0.37 / 0.38 | 5.38 | 11.68 | 11.68 | 0 | 0.299 | 2.17 | 20266 (19931) |
| shehbaz_short_c8_n16_stream_inline | shehbaz | short | 8 | 16 | y | inline | 0 | 0 | 1.91 / 2.9 / 3.24 | 0.37 / 0.69 / 0.7 | 4.06 | 14.68 | 14.06 | 0 | 0.506 | 3.61 | 20266 (19931) |
| shehbaz_short_c16_n32_stream_inline | shehbaz | short | 16 | 32 | y | inline | 0 | 1 (0s/1l) | 2.61 / 4.43 / 5.75 | 0.46 / 1.3 / 1.31 | 4.19 | 19.16 | 17.07 | 0 | 0.762 | 4.58 | 20274 (19939) |
| shehbaz_short_c32_n64_stream_inline | shehbaz | short | 32 | 64 | y | inline | 0 | 1 (0s/1l) | 4.43 / 7.41 / 9.02 | 1.02 / 2.53 / 2.55 | 4.1 | 22.57 | 21.37 | 0 | 1.272 | 5.51 | 20276 (19941) |
| trump_xlong_c1_n6_stream_inline | trump | xlong | 1 | 6 | y | inline | 0 | 0 | 5.52 / 5.97 / 6.01 | 0.12 / 0.12 / 0.12 | 31.59 | 5.6 | 5.6 | 0 | 0.178 | 0.18 | 20275 (19940) |
| trump_xlong_c2_n6_stream_inline | trump | xlong | 2 | 6 | y | inline | 0 | 0 | 5.96 / 6.43 / 6.58 | 0.13 / 0.2 / 0.2 | 32.03 | 10.12 | 10.12 | 0 | 0.191 | 0.32 | 20274 (19939) |
| trump_xlong_c4_n6_stream_inline | trump | xlong | 4 | 6 | y | inline | 0 | 0 | 7.44 / 7.9 / 8.2 | 0.35 / 0.36 / 0.36 | 31.28 | 13.19 | 13.2 | 0 | 0.254 | 0.42 | 20278 (19943) |
| trump_xlong_c8_n8_stream_inline | trump | xlong | 8 | 8 | y | inline | 0 | 0 | 11.34 / 13.4 / 15.18 | 0.65 / 0.66 / 0.66 | 33.22 | 17.49 | 17.49 | 0 | 0.379 | 0.53 | 20275 (19940) |
| trump_xlong_c16_n16_stream_inline | trump | xlong | 16 | 16 | y | inline | 0 | 0 | 16.81 / 17.83 / 18.04 | 1.24 / 1.25 / 1.25 | 31.8 | 28.16 | 26.52 | 0 | 0.527 | 0.89 | 20275 (19940) |
| trump_xlong_c32_n32_stream_inline | trump | xlong | 32 | 32 | y | inline | 0 | 0 | 25.63 / 27.81 / 31.04 | 2.42 / 2.44 / 2.44 | 32.98 | 33.95 | 33.04 | 0 | 0.81 | 1.03 | 20272 (19937) |
| shehbaz_xlong_c1_n6_stream_inline | shehbaz | xlong | 1 | 6 | y | inline | 0 | 0 | 5.69 / 5.99 / 6.17 | 0.12 / 0.14 / 0.14 | 32.16 | 5.58 | 5.58 | 0 | 0.179 | 0.17 | 20274 (19939) |
| shehbaz_xlong_c2_n6_stream_inline | shehbaz | xlong | 2 | 6 | y | inline | 1 | 0 | 5.91 / 6.44 / 6.44 | 0.16 / 0.22 / 0.22 | 31.9 | 6.67 | 6.68 | 0 | 0.191 | 0.21 | 20276 (19941) |
| shehbaz_xlong_c4_n6_stream_inline | shehbaz | xlong | 4 | 6 | y | inline | 1 | 0 | 8.55 / 9.01 / 9.01 | 0.35 / 0.36 / 0.36 | 32.94 | 8.34 | 8.34 | 0 | 0.256 | 0.25 | 20280 (19945) |
| shehbaz_xlong_c8_n8_stream_inline | shehbaz | xlong | 8 | 8 | y | inline | 0 | 0 | 13.1 / 14.12 / 15.04 | 0.69 / 0.7 / 0.71 | 35.73 | 18.99 | 18.99 | 0 | 0.381 | 0.53 | 20274 (19939) |
| shehbaz_xlong_c16_n16_stream_inline | shehbaz | xlong | 16 | 16 | y | inline | 0 | 0 | 17.33 / 18.46 / 18.48 | 1.25 / 1.27 / 1.27 | 32.38 | 27.99 | 26.09 | 0 | 0.533 | 0.86 | 20274 (19939) |
| shehbaz_xlong_c32_n32_stream_inline | shehbaz | xlong | 32 | 32 | y | inline | 2 | 0 | 27.2 / 29.07 / 30.48 | 2.53 / 2.56 / 2.58 | 33.89 | 29.8 | 32.76 | 0 | 0.808 | 0.88 | 20276 (19941) |
| trump_xxlong_c1_n4_stream_inline | trump | xxlong | 1 | 4 | y | inline | 0 | 0 | 10.92 / 11.24 / 11.24 | 0.13 / 0.13 / 0.13 | 61.96 | 5.67 | 5.67 | 0 | 0.176 | 0.09 | 20262 (19927) |
| trump_xxlong_c8_n8_stream_inline | trump | xxlong | 8 | 8 | y | inline | 0 | 0 | 23.26 / 23.76 / 23.76 | 0.64 / 0.64 / 0.64 | 62.35 | 20.98 | 20.98 | 0 | 0.374 | 0.34 | 20262 (19927) |
| shehbaz_xxlong_c1_n4_stream_inline | shehbaz | xxlong | 1 | 4 | y | inline | 1 | 2 (2s/0l) | 6.87 / 8.8 / 8.8 | 0.13 / 0.13 / 0.13 | 41.65 | 2.49 | 2.49 | 1 | 0.178 | 0.06 | 20262 (19927) |
| shehbaz_xxlong_c8_n8_stream_inline | shehbaz | xxlong | 8 | 8 | y | inline | 3 | 4 (4s/0l) | 14.84 / 26.46 / 26.46 | 0.68 / 0.69 / 0.69 | 48.43 | 5.23 | 5.24 | 1 | 0.375 | 0.11 | 20262 (19927) |

**aggregate x realtime** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz short stream | 5.15 | 8.03 | 11.68 | 14.68 | 19.16 | 22.57 |
| shehbaz xlong stream | 5.58 | 6.67 | 8.34 | 18.99 | 27.99 | 29.8 |
| shehbaz xxlong stream | 2.49 |  |  | 5.23 |  |  |
| trump short stream | 5.01 | 7.85 | 10.17 | 13.87 | 16.74 | 20.64 |
| trump xlong stream | 5.6 | 10.12 | 13.19 | 17.49 | 28.16 | 33.95 |
| trump xxlong stream | 5.67 |  |  | 20.98 |  |  |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz short stream | 5.15 | 8.03 | 11.68 | 14.06 | 17.07 | 21.37 |
| shehbaz xlong stream | 5.58 | 6.68 | 8.34 | 18.99 | 26.09 | 32.76 |
| shehbaz xxlong stream | 2.49 |  |  | 5.24 |  |  |
| trump short stream | 5.01 | 7.85 | 10.17 | 12.37 | 15.6 | 18.52 |
| trump xlong stream | 5.6 | 10.12 | 13.2 | 17.49 | 26.52 | 33.04 |
| trump xxlong stream | 5.67 |  |  | 20.98 |  |  |

**req/s** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz short stream | 0.97 | 2.26 | 2.17 | 3.61 | 4.58 | 5.51 |
| shehbaz xlong stream | 0.17 | 0.21 | 0.25 | 0.53 | 0.86 | 0.88 |
| shehbaz xxlong stream | 0.06 |  |  | 0.11 |  |  |
| trump short stream | 1.38 | 2.95 | 3.54 | 4.39 | 5.7 | 6.86 |
| trump xlong stream | 0.18 | 0.32 | 0.42 | 0.53 | 0.89 | 1.03 |
| trump xxlong stream | 0.09 |  |  | 0.34 |  |  |

**latency p50 s** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz short stream | 1.06 | 0.92 | 1.56 | 1.91 | 2.61 | 4.43 |
| shehbaz xlong stream | 5.69 | 5.91 | 8.55 | 13.1 | 17.33 | 27.2 |
| shehbaz xxlong stream | 6.87 |  |  | 14.84 |  |  |
| trump short stream | 0.73 | 0.55 | 0.91 | 1.45 | 2.31 | 3.76 |
| trump xlong stream | 5.52 | 5.96 | 7.44 | 11.34 | 16.81 | 25.63 |
| trump xxlong stream | 10.92 |  |  | 23.26 |  |  |

**latency p90 s** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz short stream | 1.31 | 1.13 | 2.08 | 2.9 | 4.43 | 7.41 |
| shehbaz xlong stream | 5.99 | 6.44 | 9.01 | 14.12 | 18.46 | 29.07 |
| shehbaz xxlong stream | 8.8 |  |  | 26.46 |  |  |
| trump short stream | 0.99 | 1.08 | 1.23 | 2.62 | 3.74 | 6.41 |
| trump xlong stream | 5.97 | 6.43 | 7.9 | 13.4 | 17.83 | 27.81 |
| trump xxlong stream | 11.24 |  |  | 23.76 |  |  |

**per-request RTF p50** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz short stream | 0.197 | 0.243 | 0.299 | 0.506 | 0.762 | 1.272 |
| shehbaz xlong stream | 0.179 | 0.191 | 0.256 | 0.381 | 0.533 | 0.808 |
| shehbaz xxlong stream | 0.178 |  |  | 0.375 |  |  |
| trump short stream | 0.204 | 0.258 | 0.376 | 0.513 | 0.857 | 1.434 |
| trump xlong stream | 0.178 | 0.191 | 0.254 | 0.379 | 0.527 | 0.81 |
| trump xxlong stream | 0.176 |  |  | 0.374 |  |  |

**TTFA p50 s** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz short stream | 0.12 | 0.14 | 0.36 | 0.37 | 0.46 | 1.02 |
| shehbaz xlong stream | 0.12 | 0.16 | 0.35 | 0.69 | 1.25 | 2.53 |
| shehbaz xxlong stream | 0.13 |  |  | 0.68 |  |  |
| trump short stream | 0.12 | 0.17 | 0.36 | 0.43 | 0.81 | 1.77 |
| trump xlong stream | 0.12 | 0.13 | 0.35 | 0.65 | 1.24 | 2.42 |
| trump xxlong stream | 0.13 |  |  | 0.64 |  |  |

**TTFA p90 s** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz short stream | 0.12 | 0.2 | 0.37 | 0.69 | 1.3 | 2.53 |
| shehbaz xlong stream | 0.14 | 0.22 | 0.36 | 0.7 | 1.27 | 2.56 |
| shehbaz xxlong stream | 0.13 |  |  | 0.69 |  |  |
| trump short stream | 0.13 | 0.19 | 0.36 | 0.66 | 1.26 | 2.46 |
| trump xlong stream | 0.12 | 0.2 | 0.36 | 0.66 | 1.25 | 2.44 |
| trump xxlong stream | 0.13 |  |  | 0.64 |  |  |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| shehbaz short stream | 19936 | 19931 | 19931 | 19931 | 19939 | 19941 |
| shehbaz xlong stream | 19939 | 19941 | 19945 | 19939 | 19939 | 19941 |
| shehbaz xxlong stream | 19927 |  |  | 19927 |  |  |
| trump short stream | 19923 | 19927 | 19927 | 19936 | 19941 | 19941 |
| trump xlong stream | 19940 | 19939 | 19943 | 19940 | 19940 | 19937 |
| trump xxlong stream | 19927 |  |  | 19927 |  |  |

## P4_voice_cache

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_short_c1_n8_nonstream_upload | trump | short | 1 | 8 |  | upload | 0 | 1 (0s/1l) | 0.78 / 0.98 / 0.99 | – | 3.61 | 5.08 | 5.08 | 0 | 0.203 | 1.41 | 19128 (18812) |
| trump_short_c8_n16_nonstream_upload | trump | short | 8 | 16 |  | upload | 0 | 0 | 1.35 / 2.56 / 2.78 | – | 2.77 | 12.86 | 11.42 | 0 | 0.573 | 4.63 | 19168 (18852) |
| trump_short_c32_n32_nonstream_upload | trump | short | 32 | 32 |  | upload | 0 | 0 | 3.76 / 4.58 / 4.78 | – | 3.04 | 20.35 | 17.59 | 0 | 1.424 | 6.69 | 19474 (19158) |
| shehbaz_short_c1_n8_nonstream_upload | shehbaz | short | 1 | 8 |  | upload | 0 | 0 | 0.9 / 1.17 / 1.6 | – | 4.94 | 5.22 | 5.22 | 0 | 0.194 | 1.06 | 19604 (19288) |
| shehbaz_short_c8_n16_nonstream_upload | shehbaz | short | 8 | 16 |  | upload | 0 | 0 | 2.19 / 2.91 / 3.02 | – | 4.82 | 14.84 | 14.11 | 0 | 0.507 | 3.08 | 19604 (19288) |
| shehbaz_short_c32_n32_nonstream_upload | shehbaz | short | 32 | 32 |  | upload | 0 | 0 | 4.2 / 5.92 / 6.25 | – | 4.33 | 22.18 | 19.21 | 0 | 1.167 | 5.12 | 19832 (19516) |
| trump_short_c1_n8_nonstream_inline | trump | short | 1 | 8 |  | inline | 0 | 1 (0s/1l) | 0.72 / 1.14 / 1.21 | – | 3.8 | 5.05 | 5.05 | 0 | 0.201 | 1.33 | 19832 (19516) |
| trump_short_c8_n16_nonstream_inline | trump | short | 8 | 16 |  | inline | 0 | 0 | 1.17 / 2.56 / 2.67 | – | 2.79 | 12.75 | 11.72 | 0 | 0.596 | 4.56 | 19832 (19516) |
| trump_short_c32_n32_nonstream_inline | trump | short | 32 | 32 |  | inline | 0 | 0 | 3.89 / 4.77 / 4.8 | – | 3.08 | 20.47 | 17.34 | 0 | 1.405 | 6.64 | 19832 (19516) |
| shehbaz_short_c1_n8_nonstream_inline | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 1.04 / 1.15 / 1.3 | – | 4.81 | 5.13 | 5.13 | 0 | 0.2 | 1.07 | 19832 (19516) |
| shehbaz_short_c8_n16_nonstream_inline | shehbaz | short | 8 | 16 |  | inline | 0 | 0 | 2.01 / 2.9 / 3.27 | – | 4.69 | 14.95 | 13.99 | 0 | 0.52 | 3.19 | 19830 (19514) |
| shehbaz_short_c32_n32_nonstream_inline | shehbaz | short | 32 | 32 |  | inline | 0 | 0 | 4.54 / 5.66 / 6.19 | – | 4.39 | 22.42 | 20.29 | 0 | 1.148 | 5.11 | 19830 (19514) |
| trump_short_c1_n8_nonstream_nocache | trump | short | 1 | 8 |  | nocache | 0 | 1 (0s/1l) | 0.86 / 1 / 1.07 | – | 3.48 | 4.58 | 4.58 | 0 | 0.228 | 1.32 | 19829 (19513) |
| trump_short_c8_n16_nonstream_nocache | trump | short | 8 | 16 |  | nocache | 0 | 0 | 1.82 / 2.78 / 3.63 | – | 2.87 | 10.36 | 9.44 | 0 | 0.689 | 3.61 | 19828 (19512) |
| trump_short_c32_n32_nonstream_nocache | trump | short | 32 | 32 |  | nocache | 0 | 1 (0s/1l) | 6.19 / 7.32 / 7.61 | – | 3.07 | 12.77 | 11.53 | 0 | 2.263 | 4.16 | 19830 (19514) |
| shehbaz_short_c1_n8_nonstream_nocache | shehbaz | short | 1 | 8 |  | nocache | 0 | 0 | 1.15 / 1.22 / 1.48 | – | 5.13 | 4.85 | 4.85 | 0 | 0.206 | 0.94 | 19830 (19514) |
| shehbaz_short_c8_n16_nonstream_nocache | shehbaz | short | 8 | 16 |  | nocache | 0 | 0 | 2.47 / 3.78 / 4.04 | – | 4.47 | 12.1 | 11.37 | 0 | 0.552 | 2.71 | 19830 (19514) |
| shehbaz_short_c32_n32_nonstream_nocache | shehbaz | short | 32 | 32 |  | nocache | 0 | 0 | 7.35 / 9.13 / 9.75 | – | 4.39 | 14.22 | 12.78 | 0 | 1.937 | 3.24 | 19830 (19514) |
| trump_short_c1_n8_stream_inline | trump | short | 1 | 8 | y | inline | 0 | 0 | 0.74 / 0.97 / 1.01 | 0.11 / 0.12 / 0.12 | 3.67 | 5.03 | 5.03 | 0 | 0.196 | 1.37 | 19828 (19512) |
| trump_short_c8_n16_stream_inline | trump | short | 8 | 16 | y | inline | 0 | 0 | 1.42 / 2.46 / 2.85 | 0.5 / 0.65 / 0.65 | 2.88 | 12.59 | 11.15 | 0 | 0.588 | 4.37 | 19828 (19512) |
| trump_short_c32_n32_stream_inline | trump | short | 32 | 32 | y | inline | 0 | 1 (0s/1l) | 3.73 / 4.65 / 4.83 | 2.35 / 2.37 / 2.38 | 3.05 | 20.17 | 17.37 | 0 | 1.339 | 6.61 | 19830 (19514) |
| shehbaz_short_c1_n8_stream_inline | shehbaz | short | 1 | 8 | y | inline | 0 | 0 | 1.01 / 1.29 / 1.59 | 0.12 / 0.12 / 0.13 | 5.29 | 5.22 | 5.22 | 0 | 0.191 | 0.99 | 19830 (19514) |
| shehbaz_short_c8_n16_stream_inline | shehbaz | short | 8 | 16 | y | inline | 0 | 0 | 2.1 / 3.12 / 3.54 | 0.32 / 0.69 / 0.69 | 4.46 | 14.58 | 13.52 | 0 | 0.517 | 3.27 | 19830 (19514) |
| shehbaz_short_c32_n32_stream_inline | shehbaz | short | 32 | 32 | y | inline | 0 | 0 | 4.88 / 5.71 / 6.37 | 2.48 / 2.52 / 2.53 | 4.29 | 21.38 | 19.39 | 0 | 1.205 | 4.98 | 19830 (19514) |
| trump_short_c1_n8_stream_nocache | trump | short | 1 | 8 | y | nocache | 0 | 0 | 0.79 / 1.02 / 1.07 | 0.27 / 0.29 / 0.29 | 3.4 | 4.53 | 4.53 | 0 | 0.229 | 1.33 | 19829 (19513) |
| trump_short_c8_n16_stream_nocache | trump | short | 8 | 16 | y | nocache | 0 | 1 (0s/1l) | 1.78 / 2.78 / 3.51 | 1.45 / 1.47 / 1.64 | 2.87 | 10.03 | 9.19 | 0 | 0.716 | 3.49 | 19828 (19512) |
| trump_short_c32_n32_stream_nocache | trump | short | 32 | 32 | y | nocache | 0 | 0 | 6.24 / 7.46 / 7.76 | 6.17 / 6.2 / 6.23 | 3.13 | 12.77 | 11.25 | 0 | 2.358 | 4.08 | 19830 (19514) |
| shehbaz_short_c1_n8_stream_nocache | shehbaz | short | 1 | 8 | y | nocache | 0 | 0 | 1.04 / 1.25 / 1.65 | 0.31 / 0.32 / 0.34 | 5.19 | 4.82 | 4.82 | 0 | 0.209 | 0.93 | 19830 (19514) |
| shehbaz_short_c8_n16_stream_nocache | shehbaz | short | 8 | 16 | y | nocache | 0 | 0 | 2.64 / 3.73 / 3.87 | 0.66 / 1.76 / 1.96 | 4.65 | 12.42 | 11.24 | 0 | 0.554 | 2.67 | 19830 (19514) |
| shehbaz_short_c32_n32_stream_nocache | shehbaz | short | 32 | 32 | y | nocache | 0 | 0 | 7.43 / 9.07 / 9.64 | 7.34 / 7.36 / 7.41 | 4.37 | 14.34 | 12.88 | 0 | 1.969 | 3.28 | 19830 (19514) |

**aggregate x realtime** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz short | 5.13 | 14.95 | 22.42 |
| shehbaz short nocache | 4.85 | 12.1 | 14.22 |
| shehbaz short upload | 5.22 | 14.84 | 22.18 |
| shehbaz short stream | 5.22 | 14.58 | 21.38 |
| shehbaz short stream nocache | 4.82 | 12.42 | 14.34 |
| trump short | 5.05 | 12.75 | 20.47 |
| trump short nocache | 4.58 | 10.36 | 12.77 |
| trump short upload | 5.08 | 12.86 | 20.35 |
| trump short stream | 5.03 | 12.59 | 20.17 |
| trump short stream nocache | 4.53 | 10.03 | 12.77 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz short | 5.13 | 13.99 | 20.29 |
| shehbaz short nocache | 4.85 | 11.37 | 12.78 |
| shehbaz short upload | 5.22 | 14.11 | 19.21 |
| shehbaz short stream | 5.22 | 13.52 | 19.39 |
| shehbaz short stream nocache | 4.82 | 11.24 | 12.88 |
| trump short | 5.05 | 11.72 | 17.34 |
| trump short nocache | 4.58 | 9.44 | 11.53 |
| trump short upload | 5.08 | 11.42 | 17.59 |
| trump short stream | 5.03 | 11.15 | 17.37 |
| trump short stream nocache | 4.53 | 9.19 | 11.25 |

**req/s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz short | 1.07 | 3.19 | 5.11 |
| shehbaz short nocache | 0.94 | 2.71 | 3.24 |
| shehbaz short upload | 1.06 | 3.08 | 5.12 |
| shehbaz short stream | 0.99 | 3.27 | 4.98 |
| shehbaz short stream nocache | 0.93 | 2.67 | 3.28 |
| trump short | 1.33 | 4.56 | 6.64 |
| trump short nocache | 1.32 | 3.61 | 4.16 |
| trump short upload | 1.41 | 4.63 | 6.69 |
| trump short stream | 1.37 | 4.37 | 6.61 |
| trump short stream nocache | 1.33 | 3.49 | 4.08 |

**latency p50 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz short | 1.04 | 2.01 | 4.54 |
| shehbaz short nocache | 1.15 | 2.47 | 7.35 |
| shehbaz short upload | 0.9 | 2.19 | 4.2 |
| shehbaz short stream | 1.01 | 2.1 | 4.88 |
| shehbaz short stream nocache | 1.04 | 2.64 | 7.43 |
| trump short | 0.72 | 1.17 | 3.89 |
| trump short nocache | 0.86 | 1.82 | 6.19 |
| trump short upload | 0.78 | 1.35 | 3.76 |
| trump short stream | 0.74 | 1.42 | 3.73 |
| trump short stream nocache | 0.79 | 1.78 | 6.24 |

**latency p90 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz short | 1.15 | 2.9 | 5.66 |
| shehbaz short nocache | 1.22 | 3.78 | 9.13 |
| shehbaz short upload | 1.17 | 2.91 | 5.92 |
| shehbaz short stream | 1.29 | 3.12 | 5.71 |
| shehbaz short stream nocache | 1.25 | 3.73 | 9.07 |
| trump short | 1.14 | 2.56 | 4.77 |
| trump short nocache | 1 | 2.78 | 7.32 |
| trump short upload | 0.98 | 2.56 | 4.58 |
| trump short stream | 0.97 | 2.46 | 4.65 |
| trump short stream nocache | 1.02 | 2.78 | 7.46 |

**per-request RTF p50** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz short | 0.2 | 0.52 | 1.148 |
| shehbaz short nocache | 0.206 | 0.552 | 1.937 |
| shehbaz short upload | 0.194 | 0.507 | 1.167 |
| shehbaz short stream | 0.191 | 0.517 | 1.205 |
| shehbaz short stream nocache | 0.209 | 0.554 | 1.969 |
| trump short | 0.201 | 0.596 | 1.405 |
| trump short nocache | 0.228 | 0.689 | 2.263 |
| trump short upload | 0.203 | 0.573 | 1.424 |
| trump short stream | 0.196 | 0.588 | 1.339 |
| trump short stream nocache | 0.229 | 0.716 | 2.358 |

**TTFA p50 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz short stream | 0.12 | 0.32 | 2.48 |
| shehbaz short stream nocache | 0.31 | 0.66 | 7.34 |
| trump short stream | 0.11 | 0.5 | 2.35 |
| trump short stream nocache | 0.27 | 1.45 | 6.17 |

**TTFA p90 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz short stream | 0.12 | 0.69 | 2.52 |
| shehbaz short stream nocache | 0.32 | 1.76 | 7.36 |
| trump short stream | 0.12 | 0.65 | 2.37 |
| trump short stream nocache | 0.29 | 1.47 | 6.2 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| shehbaz short | 19516 | 19514 | 19514 |
| shehbaz short nocache | 19514 | 19514 | 19514 |
| shehbaz short upload | 19288 | 19288 | 19516 |
| shehbaz short stream | 19514 | 19514 | 19514 |
| shehbaz short stream nocache | 19514 | 19514 | 19514 |
| trump short | 19516 | 19516 | 19516 |
| trump short nocache | 19513 | 19512 | 19514 |
| trump short upload | 18812 | 18852 | 19158 |
| trump short stream | 19512 | 19512 | 19514 |
| trump short stream nocache | 19513 | 19512 | 19514 |

## P5_urdu_rp105

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline | shehbaz | prompts | 16 | 258 |  | inline | 7 | 1 (1s/0l) | 17.62 / 19.59 / 23.02 | – | 33.03 | 27.65 | 28.24 | 0 | 0.537 | 0.84 | 19830 (19514) |
| rp1.05_trump_prompts_c16_n43_nonstream_inline | trump | prompts | 16 | 43 |  | inline | 0 | 0 | 16.13 / 19.05 / 27.04 | – | 32.22 | 28.01 | 25.97 | 0 | 0.53 | 0.87 | 19829 (19513) |

## P5_urdu_rp110

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline | shehbaz | prompts | 16 | 258 |  | inline | 8 | 1 (1s/0l) | 17.77 / 20.01 / 23.22 | – | 33.33 | 27.33 | 27.49 | 0 | 0.537 | 0.82 | 19845 (19529) |

## P5_urdu_rp115

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline | shehbaz | prompts | 16 | 258 |  | inline | 13 | 0 | 17.64 / 19.7 / 22.22 | – | 33.14 | 26.12 | 26.19 | 0 | 0.537 | 0.79 | 19832 (19516) |

## P5_urdu_rp120

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline | shehbaz | prompts | 16 | 258 |  | inline | 12 | 1 (1s/0l) | 17.75 / 19.74 / 21.96 | – | 33.13 | 26.4 | 26.15 | 0 | 0.536 | 0.8 | 19829 (19513) |
| rp1.20_trump_prompts_c16_n43_nonstream_inline | trump | prompts | 16 | 43 |  | inline | 0 | 0 | 16.54 / 19.46 / 27.41 | – | 32.28 | 28.24 | 25.83 | 0 | 0.529 | 0.87 | 19829 (19513) |

## P6_auralis

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n20c20_shehbaz_short_c20_n20_nonstream_inline | shehbaz | short | 20 | 20 |  | inline | 0 | 0 | 3.19 / 3.43 / 3.47 | – | 3.36 | 19.25 | 17.1 | 0 | 0.963 | 5.74 | 19831 (19515) |
| n20c20_shehbaz_medium_c20_n20_nonstream_inline | shehbaz | medium | 20 | 20 |  | inline | 0 | 0 | 5.13 / 5.28 / 5.35 | – | 5.92 | 22.04 | 19.5 | 0 | 0.805 | 3.72 | 19829 (19513) |
| n20c20_shehbaz_long_c20_n20_nonstream_inline | shehbaz | long | 20 | 20 |  | inline | 0 | 0 | 11.21 / 11.78 / 12.31 | – | 16.3 | 26.37 | 24.29 | 0 | 0.691 | 1.62 | 19828 (19512) |
| sweep_shehbaz_short_c1_n8_nonstream_inline | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 0.69 / 0.78 / 0.8 | – | 3.38 | 4.86 | 4.86 | 0 | 0.204 | 1.44 | 19826 (19510) |
| sweep_shehbaz_short_c4_n8_nonstream_inline | shehbaz | short | 4 | 8 |  | inline | 0 | 0 | 1.09 / 1.17 / 1.46 | – | 3.19 | 11.11 | 11.11 | 0 | 0.331 | 3.48 | 19826 (19510) |
| sweep_shehbaz_short_c8_n8_nonstream_inline | shehbaz | short | 8 | 8 |  | inline | 0 | 0 | 1.65 / 1.76 / 1.82 | – | 3.28 | 14.25 | 14.25 | 0 | 0.51 | 4.34 | 19826 (19510) |
| sweep_shehbaz_short_c16_n16_nonstream_inline | shehbaz | short | 16 | 16 |  | inline | 0 | 0 | 2.55 / 2.84 / 2.87 | – | 3.35 | 18.6 | 17.36 | 0 | 0.769 | 5.56 | 19828 (19512) |
| sweep_shehbaz_short_c32_n32_nonstream_inline | shehbaz | short | 32 | 32 |  | inline | 0 | 0 | 4.28 / 4.68 / 4.77 | – | 3.43 | 22.85 | 20.42 | 0 | 1.239 | 6.67 | 19828 (19512) |
| sweep_shehbaz_medium_c1_n8_nonstream_inline | shehbaz | medium | 1 | 8 |  | inline | 0 | 0 | 0.8 / 1.34 / 1.5 | – | 5.07 | 5.18 | 5.18 | 0 | 0.196 | 1.02 | 19829 (19513) |
| sweep_shehbaz_medium_c4_n8_nonstream_inline | shehbaz | medium | 4 | 8 |  | inline | 0 | 0 | 1.97 / 2.24 / 2.25 | – | 6.68 | 13.8 | 13.81 | 0 | 0.283 | 2.07 | 19828 (19512) |
| sweep_shehbaz_medium_c8_n8_nonstream_inline | shehbaz | medium | 8 | 8 |  | inline | 0 | 0 | 3.02 / 3.11 / 3.25 | – | 6.99 | 17.14 | 17.15 | 0 | 0.433 | 2.45 | 19828 (19512) |
| sweep_shehbaz_medium_c16_n16_nonstream_inline | shehbaz | medium | 16 | 16 |  | inline | 0 | 0 | 4.45 / 4.83 / 5.04 | – | 7.2 | 22.61 | 21.74 | 0 | 0.626 | 3.14 | 19829 (19513) |
| sweep_shehbaz_medium_c32_n32_nonstream_inline | shehbaz | medium | 32 | 32 |  | inline | 0 | 0 | 7.14 / 7.8 / 7.94 | – | 7.38 | 29.72 | 26.81 | 0 | 0.981 | 4.03 | 19829 (19513) |
| sweep_shehbaz_long_c1_n8_nonstream_inline | shehbaz | long | 1 | 8 |  | inline | 0 | 0 | 2.95 / 3.36 / 3.61 | – | 16.31 | 5.55 | 5.55 | 0 | 0.18 | 0.34 | 19829 (19513) |
| sweep_shehbaz_long_c4_n8_nonstream_inline | shehbaz | long | 4 | 8 |  | inline | 0 | 0 | 4.35 / 4.65 / 4.76 | – | 16.39 | 14.38 | 14.38 | 0 | 0.262 | 0.88 | 19829 (19513) |
| sweep_shehbaz_long_c8_n8_nonstream_inline | shehbaz | long | 8 | 8 |  | inline | 0 | 0 | 6.57 / 7.15 / 7.58 | – | 17.13 | 18.07 | 18.08 | 0 | 0.391 | 1.06 | 19828 (19512) |
| sweep_shehbaz_long_c16_n16_nonstream_inline | shehbaz | long | 16 | 16 |  | inline | 0 | 0 | 8.75 / 9.38 / 9.77 | – | 15.76 | 25.7 | 24.63 | 0 | 0.55 | 1.63 | 19828 (19512) |
| sweep_shehbaz_long_c32_n32_nonstream_inline | shehbaz | long | 32 | 32 |  | inline | 0 | 0 | 13.97 / 14.84 / 15.24 | – | 16.2 | 33.86 | 30.9 | 0 | 0.848 | 2.09 | 19829 (19513) |
| gw_n20c20_shehbaz_short_c20_n20_nonstream_server | shehbaz | short | 20 | 20 |  | server | 0 | 0 | 3.19 / 3.39 / 3.44 | – | 3.31 | 19.21 | 17.11 | 0 | 0.938 | 5.8 | 19829 (19513) |
| gw_n20c20_shehbaz_medium_c20_n20_nonstream_server | shehbaz | medium | 20 | 20 |  | server | 0 | 0 | 4.87 / 5.14 / 5.2 | – | 5.88 | 22.57 | 19.95 | 0 | 0.77 | 3.84 | 19828 (19512) |
| gw_n20c20_shehbaz_long_c20_n20_nonstream_server | shehbaz | long | 20 | 20 |  | server | 0 | 0 | 11.16 / 11.59 / 12.31 | – | 16.06 | 26.08 | 24.28 | 0 | 0.689 | 1.62 | 19828 (19512) |

**aggregate x realtime** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|
| sweep shehbaz long | 5.55 | 14.38 | 18.07 | 25.7 | 33.86 |
| sweep shehbaz medium | 5.18 | 13.8 | 17.14 | 22.61 | 29.72 |
| sweep shehbaz short | 4.86 | 11.11 | 14.25 | 18.6 | 22.85 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|
| sweep shehbaz long | 5.55 | 14.38 | 18.08 | 24.63 | 30.9 |
| sweep shehbaz medium | 5.18 | 13.81 | 17.15 | 21.74 | 26.81 |
| sweep shehbaz short | 4.86 | 11.11 | 14.25 | 17.36 | 20.42 |

**req/s** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|
| sweep shehbaz long | 0.34 | 0.88 | 1.06 | 1.63 | 2.09 |
| sweep shehbaz medium | 1.02 | 2.07 | 2.45 | 3.14 | 4.03 |
| sweep shehbaz short | 1.44 | 3.48 | 4.34 | 5.56 | 6.67 |

**latency p50 s** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|
| sweep shehbaz long | 2.95 | 4.35 | 6.57 | 8.75 | 13.97 |
| sweep shehbaz medium | 0.8 | 1.97 | 3.02 | 4.45 | 7.14 |
| sweep shehbaz short | 0.69 | 1.09 | 1.65 | 2.55 | 4.28 |

**latency p90 s** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|
| sweep shehbaz long | 3.36 | 4.65 | 7.15 | 9.38 | 14.84 |
| sweep shehbaz medium | 1.34 | 2.24 | 3.11 | 4.83 | 7.8 |
| sweep shehbaz short | 0.78 | 1.17 | 1.76 | 2.84 | 4.68 |

**per-request RTF p50** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|
| sweep shehbaz long | 0.18 | 0.262 | 0.391 | 0.55 | 0.848 |
| sweep shehbaz medium | 0.196 | 0.283 | 0.433 | 0.626 | 0.981 |
| sweep shehbaz short | 0.204 | 0.331 | 0.51 | 0.769 | 1.239 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|
| sweep shehbaz long | 19513 | 19513 | 19512 | 19512 | 19513 |
| sweep shehbaz medium | 19513 | 19512 | 19512 | 19513 | 19513 |
| sweep shehbaz short | 19510 | 19510 | 19510 | 19512 | 19512 |

## P7_gateway

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| direct_trump_short_c1_n8_nonstream_inline | trump | short | 1 | 8 |  | inline | 0 | 1 (0s/1l) | 0.71 / 1 / 1.14 | – | 3.64 | 5.02 | 5.02 | 0 | 0.203 | 1.38 | 19829 (19513) |
| direct_trump_short_c16_n32_nonstream_inline | trump | short | 16 | 32 |  | inline | 0 | 1 (0s/1l) | 2.22 / 3.71 / 4.33 | – | 2.89 | 17.24 | 15.22 | 0 | 0.843 | 5.96 | 19829 (19513) |
| direct_shehbaz_short_c1_n8_nonstream_inline | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 1 / 1.04 / 1.2 | – | 4.86 | 5.17 | 5.17 | 0 | 0.194 | 1.06 | 19829 (19513) |
| direct_shehbaz_short_c16_n32_nonstream_inline | shehbaz | short | 16 | 32 |  | inline | 0 | 0 | 2.7 / 5.1 / 6.11 | – | 4.31 | 19.75 | 19.19 | 0 | 0.726 | 4.59 | 19829 (19513) |
| gw_r0_trump_short_c1_n8_nonstream_server | trump | short | 1 | 8 |  | server | 0 | 1 (0s/1l) | 0.71 / 1 / 1.05 | – | 3.49 | 5 | 5 | 0 | 0.212 | 1.43 | 19828 (19512) |
| gw_r0_trump_short_c16_n32_nonstream_server | trump | short | 16 | 32 |  | server | 0 | 0 | 2.15 / 3.58 / 4.4 | – | 2.95 | 17.85 | 15.94 | 0 | 0.859 | 6.05 | 19828 (19512) |
| gw_r0_shehbaz_short_c1_n8_nonstream_server | shehbaz | short | 1 | 8 |  | server | 0 | 0 | 1.03 / 1.12 / 1.3 | – | 4.74 | 5.12 | 5.12 | 0 | 0.199 | 1.08 | 19828 (19512) |
| gw_r0_shehbaz_short_c16_n32_nonstream_server | shehbaz | short | 16 | 32 |  | server | 0 | 0 | 2.73 / 4.36 / 5.56 | – | 4.25 | 20.36 | 18.92 | 0 | 0.732 | 4.8 | 19828 (19512) |
| direct_shehbaz_long_c32_n64_nonstream_inline | shehbaz | long | 32 | 64 |  | inline | 0 | 0 | 18.51 / 20.83 / 21.74 | – | 22.22 | 36.13 | 32.85 | 0 | 0.85 | 1.63 | 19829 (19513) |
| gw_r1_shehbaz_long_c32_n64_nonstream_server | shehbaz | long | 32 | 64 |  | server | 0 | 0 | 18.34 / 21.13 / 24.59 | – | 22.05 | 30.94 | 32.81 | 0 | 0.849 | 1.4 | 19829 (19513) |

**aggregate x realtime** by concurrency

| series | c=1 | c=16 |
|---|---|---|
| direct shehbaz short | 5.17 | 19.75 |
| direct trump short | 5.02 | 17.24 |
| gw_r0 shehbaz short server | 5.12 | 20.36 |
| gw_r0 trump short server | 5 | 17.85 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=16 |
|---|---|---|
| direct shehbaz short | 5.17 | 19.19 |
| direct trump short | 5.02 | 15.22 |
| gw_r0 shehbaz short server | 5.12 | 18.92 |
| gw_r0 trump short server | 5 | 15.94 |

**req/s** by concurrency

| series | c=1 | c=16 |
|---|---|---|
| direct shehbaz short | 1.06 | 4.59 |
| direct trump short | 1.38 | 5.96 |
| gw_r0 shehbaz short server | 1.08 | 4.8 |
| gw_r0 trump short server | 1.43 | 6.05 |

**latency p50 s** by concurrency

| series | c=1 | c=16 |
|---|---|---|
| direct shehbaz short | 1 | 2.7 |
| direct trump short | 0.71 | 2.22 |
| gw_r0 shehbaz short server | 1.03 | 2.73 |
| gw_r0 trump short server | 0.71 | 2.15 |

**latency p90 s** by concurrency

| series | c=1 | c=16 |
|---|---|---|
| direct shehbaz short | 1.04 | 5.1 |
| direct trump short | 1 | 3.71 |
| gw_r0 shehbaz short server | 1.12 | 4.36 |
| gw_r0 trump short server | 1 | 3.58 |

**per-request RTF p50** by concurrency

| series | c=1 | c=16 |
|---|---|---|
| direct shehbaz short | 0.194 | 0.726 |
| direct trump short | 0.203 | 0.843 |
| gw_r0 shehbaz short server | 0.199 | 0.732 |
| gw_r0 trump short server | 0.212 | 0.859 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=16 |
|---|---|---|
| direct shehbaz short | 19513 | 19513 |
| direct trump short | 19513 | 19513 |
| gw_r0 shehbaz short server | 19512 | 19512 |
| gw_r0 trump short server | 19512 | 19512 |

## X1_nsm

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nsm_true_shehbaz_prompts_c16_n43_nonstream_inline | shehbaz | prompts | 16 | 43 |  | inline | 0 | 0 | 18.7 / 21.54 / 25.12 | – | 35.17 | 26.57 | 24.39 | 0 | 0.553 | 0.76 | 19829 (19513) |

## X6_nsm_long_urdu

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nsm_false_shehbaz_xxlong_c16_n43_nonstream_inline | shehbaz | xxlong | 16 | 43 |  | inline | 16 | 14 (14s/0l) | 21.73 / 40.27 / 53.66 | – | 53.21 | 9.8 | 10.07 | 14 | 0.527 | 0.18 | 20408 (20079) |
| nsm_true_shehbaz_xxlong_c16_n43_nonstream_inline | shehbaz | xxlong | 16 | 43 |  | inline | 0 | 0 | 36.12 / 41.5 / 61.08 | – | 68.84 | 27.1 | 24.96 | 0 | 0.552 | 0.39 | 20407 (20078) |
| nsm_true_trump_xxlong_c16_n43_nonstream_inline | trump | xxlong | 16 | 43 |  | inline | 0 | 0 | 33.69 / 36.35 / 49.55 | – | 64.44 | 27.59 | 25.45 | 0 | 0.538 | 0.43 | 20406 (20077) |

## X7_split_off

Config: vllm-omni custom_voices (engine); gateway {"TTS_RETRY_MAX": "0", "TTS_SPLIT_WORDS": "0"}

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| split_off_shehbaz_xxlong_c8_n43_nonstream_server | shehbaz | xxlong | 8 | 43 |  | server | 18 | 16 (16s/0l) | 15.66 / 23.99 / 34.39 | – | 47.01 | 6.11 | 6.66 | 15 | 0.38 | 0.13 | 20406 (20077) |
| split_off_trump_xxlong_c8_n43_nonstream_server | trump | xxlong | 8 | 43 |  | server | 0 | 0 | 23 / 25.59 / 33.55 | – | 62.66 | 20.54 | 20.04 | 0 | 0.377 | 0.33 | 20406 (20077) |

## X7_split_60

Config: vllm-omni custom_voices (engine); gateway {"TTS_RETRY_MAX": "0", "TTS_SPLIT_WORDS": "60"}

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| split_60_shehbaz_xxlong_c8_n43_nonstream_server | shehbaz | xxlong | 8 | 43 |  | server | 0 | 0 | 16.83 / 18.81 / 21.11 | – | 70.63 | 31.95 | 31.71 | 0 | 0.236 | 0.45 | 20407 (20078) |
| split_60_trump_xxlong_c8_n43_nonstream_server | trump | xxlong | 8 | 43 |  | server | 0 | 0 | 14.26 / 16.55 / 52.29 | – | 65.33 | 31.68 | 30.51 | 1 | 0.224 | 0.48 | 20406 (20077) |

## P5_urdu_nsm

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nsm_rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline | shehbaz | prompts | 16 | 258 |  | inline | 5 | 0 | 19.7 / 22.22 / 24.69 | – | 35.29 | 26.93 | 26.92 | 0 | 0.564 | 0.76 | 19661 (19336) |

## X8_split_nsm

Config: vllm-omni custom_voices (engine); gateway {"TTS_NON_STREAMING_MODE_LANGS": "ur", "TTS_RETRY_MAX": "0", "TTS_SPLIT_WORDS": "60"}

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| split60_nsm_shehbaz_xxlong_c8_n43_nonstream_server | shehbaz | xxlong | 8 | 43 |  | server | 0 | 0 | 18.88 / 21.96 / 24.07 | – | 75.48 | 30.56 | 30.3 | 0 | 0.256 | 0.4 | 20201 (19876) |

## X9_nsm_stream

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nsm_default_shehbaz_short_c1_n8_stream_inline | shehbaz | short | 1 | 8 | y | inline | 0 | 0 | 0.98 / 1.31 / 1.41 | 0.12 / 0.12 / 0.13 | 4.95 | 5.18 | 5.18 | 0 | 0.192 | 1.05 | 19434 (19112) |
| nsm_default_shehbaz_short_c8_n8_stream_inline | shehbaz | short | 8 | 8 | y | inline | 0 | 0 | 1.84 / 2.05 / 2.12 | 0.68 / 0.69 / 0.69 | 3.57 | 13.44 | 13.44 | 0 | 0.472 | 3.76 | 19471 (19149) |
| nsm_default_shehbaz_xlong_c1_n8_stream_inline | shehbaz | xlong | 1 | 8 | y | inline | 1 | 0 | 6.34 / 6.56 / 6.73 | 0.12 / 0.12 / 0.13 | 35.26 | 4.26 | 4.26 | 0 | 0.178 | 0.12 | 19472 (19150) |
| nsm_default_shehbaz_xlong_c8_n8_stream_inline | shehbaz | xlong | 8 | 8 | y | inline | 0 | 0 | 12.74 / 13.11 / 13.93 | 0.68 / 0.68 / 0.69 | 33.6 | 19.3 | 19.3 | 0 | 0.379 | 0.57 | 19476 (19154) |
| nsm_true_shehbaz_short_c1_n8_stream_inline | shehbaz | short | 1 | 8 | y | inline | 0 | 0 | 1.14 / 1.17 / 1.5 | 0.12 / 0.13 / 0.16 | 5.32 | 5.14 | 5.14 | 0 | 0.194 | 0.97 | 19476 (19154) |
| nsm_true_shehbaz_short_c8_n8_stream_inline | shehbaz | short | 8 | 8 | y | inline | 0 | 0 | 1.88 / 2.18 / 2.32 | 0.73 / 0.74 / 0.74 | 3.85 | 13.29 | 13.29 | 0 | 0.501 | 3.45 | 19476 (19154) |
| nsm_true_shehbaz_xlong_c1_n8_stream_inline | shehbaz | xlong | 1 | 8 | y | inline | 0 | 0 | 6.21 / 6.62 / 6.76 | 0.15 / 0.16 / 0.16 | 34.4 | 5.56 | 5.56 | 0 | 0.18 | 0.16 | 19476 (19154) |
| nsm_true_shehbaz_xlong_c8_n8_stream_inline | shehbaz | xlong | 8 | 8 | y | inline | 0 | 0 | 14.55 / 14.8 / 15.3 | 0.86 / 0.86 / 0.86 | 36.89 | 19.28 | 19.28 | 0 | 0.389 | 0.52 | 19606 (19284) |

**aggregate x realtime** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| nsm_default shehbaz short stream | 5.18 | 13.44 |
| nsm_default shehbaz xlong stream | 4.26 | 19.3 |
| nsm_true shehbaz short stream | 5.14 | 13.29 |
| nsm_true shehbaz xlong stream | 5.56 | 19.28 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| nsm_default shehbaz short stream | 5.18 | 13.44 |
| nsm_default shehbaz xlong stream | 4.26 | 19.3 |
| nsm_true shehbaz short stream | 5.14 | 13.29 |
| nsm_true shehbaz xlong stream | 5.56 | 19.28 |

**req/s** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| nsm_default shehbaz short stream | 1.05 | 3.76 |
| nsm_default shehbaz xlong stream | 0.12 | 0.57 |
| nsm_true shehbaz short stream | 0.97 | 3.45 |
| nsm_true shehbaz xlong stream | 0.16 | 0.52 |

**latency p50 s** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| nsm_default shehbaz short stream | 0.98 | 1.84 |
| nsm_default shehbaz xlong stream | 6.34 | 12.74 |
| nsm_true shehbaz short stream | 1.14 | 1.88 |
| nsm_true shehbaz xlong stream | 6.21 | 14.55 |

**latency p90 s** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| nsm_default shehbaz short stream | 1.31 | 2.05 |
| nsm_default shehbaz xlong stream | 6.56 | 13.11 |
| nsm_true shehbaz short stream | 1.17 | 2.18 |
| nsm_true shehbaz xlong stream | 6.62 | 14.8 |

**per-request RTF p50** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| nsm_default shehbaz short stream | 0.192 | 0.472 |
| nsm_default shehbaz xlong stream | 0.178 | 0.379 |
| nsm_true shehbaz short stream | 0.194 | 0.501 |
| nsm_true shehbaz xlong stream | 0.18 | 0.389 |

**TTFA p50 s** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| nsm_default shehbaz short stream | 0.12 | 0.68 |
| nsm_default shehbaz xlong stream | 0.12 | 0.68 |
| nsm_true shehbaz short stream | 0.12 | 0.73 |
| nsm_true shehbaz xlong stream | 0.15 | 0.86 |

**TTFA p90 s** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| nsm_default shehbaz short stream | 0.12 | 0.69 |
| nsm_default shehbaz xlong stream | 0.12 | 0.68 |
| nsm_true shehbaz short stream | 0.13 | 0.74 |
| nsm_true shehbaz xlong stream | 0.16 | 0.86 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| nsm_default shehbaz short stream | 19112 | 19149 |
| nsm_default shehbaz xlong stream | 19150 | 19154 |
| nsm_true shehbaz short stream | 19154 | 19154 |
| nsm_true shehbaz xlong stream | 19154 | 19284 |

## X2_language

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lang_auto_trump_prompts_c16_n43_nonstream_inline | trump | prompts | 16 | 43 |  | inline | 0 | 0 | 16.71 / 19.09 / 26.06 | – | 32.52 | 27.96 | 25.9 | 0 | 0.53 | 0.86 | 19829 (19513) |

## X3_custom_voice

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| prompt_shehbaz_prompts_c16_n43_nonstream_server-prompt | shehbaz | prompts | 16 | 43 |  | server-prompt | 1 | 0 | 17.59 / 20.23 / 21.76 | – | 33.6 | 23.61 | 25.41 | 0 | 0.532 | 0.7 | 19829 (19513) |
| avg_shehbaz_prompts_c16_n43_nonstream_server-avg | shehbaz | prompts | 16 | 43 |  | server-avg | 2 | 0 | 17.56 / 19.45 / 20.93 | – | 33.4 | 22.53 | 24.72 | 0 | 0.534 | 0.67 | 19829 (19513) |

## X4_length_cap

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cap_on_shehbaz_prompts_c16_n43_nonstream_inline | shehbaz | prompts | 16 | 43 |  | inline | 1 | 0 | 17.31 / 19.48 / 28.02 | – | 33.63 | 26.73 | 24.46 | 0 | 0.533 | 0.79 | 19829 (19513) |
| cap_off_shehbaz_prompts_c16_n43_nonstream_inline | shehbaz | prompts | 16 | 43 |  | inline | 0 | 0 | 17.81 / 132.53 / 147.22 | – | 33.64 | 8.51 | 8.98 | 5 | 0.534 | 0.25 | 19829 (19513) |

## X5_mixed_voices

Config: vllm-omni custom_voices (engine)

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mix_trump+shehbaz_xlong_c16_n16_nonstream_inline | trump+shehbaz | xlong | 16 | 32 |  | inline | 0 | 0 | 17.38 / 19.72 / 21.62 | – | 33.08 | 28.52 | 26.35 | 0 | 0.532 | 0.86 | 19829 (19513) |
| mix_trump+shehbaz_short_c16_n32_nonstream_inline | trump+shehbaz | short | 16 | 64 |  | inline | 0 | 1 (0s/1l) | 2.63 / 4.28 / 5.44 | – | 3.72 | 19.77 | 17.86 | 0 | 0.799 | 5.32 | 19829 (19513) |

## P8_quality_raw

Config: vllm-omni custom_voices (engine) --stage-overrides {"0": {"gpu_memory_utilization": 0.45}}; gateway {"TTS_RETRY_MAX": "0"}

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| raw_trump_prompts_c16_n43_nonstream_server | trump | prompts | 16 | 43 |  | server | 0 | 0 | 16.5 / 19.29 / 26.45 | – | 32.72 | 28.1 | 25.99 | 0 | 0.528 | 0.86 | 15936 (15625) |
| raw_shehbaz_prompts_c16_n43_nonstream_server | shehbaz | prompts | 16 | 43 |  | server | 2 | 0 | 17.68 / 20.13 / 31.5 | – | 34.26 | 22.97 | 24.41 | 0 | 0.535 | 0.67 | 15937 (15626) |

## P8_quality_guard

Config: vllm-omni custom_voices (engine) --stage-overrides {"0": {"gpu_memory_utilization": 0.40}}; gateway {"TTS_RETRY_MAX": "2", "TTS_RETRY_ON": "suspect,engine_error,qc"} + QC

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| guard_trump_prompts_c16_n43_nonstream_server | trump | prompts | 16 | 43 |  | server | 0 | 0 | 41.88 / 50.06 / 56.21 | – | 32.24 | 10.63 | 10.26 | 0 | 1.31 | 0.33 | 19704 (19373) |
| guard_shehbaz_prompts_c16_n43_nonstream_server | shehbaz | prompts | 16 | 43 |  | server | 0 | 0 | 49.52 / 53.51 / 112.86 | – | 34.52 | 8.65 | 8.9 | 0 | 1.474 | 0.25 | 22201 (21870) |

## P8_quality_guard_fast

Config: vllm-omni custom_voices (engine) --stage-overrides {"0": {"gpu_memory_utilization": 0.40}}; gateway {"TTS_QC_TIMEOUT_S": "120", "TTS_RETRY_MAX": "2", "TTS_RETRY_ON": "suspect,engine_error,qc"} + QC

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| guardfast_trump_prompts_c16_n43_nonstream_server | trump | prompts | 16 | 43 |  | server | 0 | 0 | 36.2 / 54.2 / 63.46 | – | 32.15 | 12.47 | 11.98 | 0 | 1.101 | 0.39 | 20681 (20352) |
| guardfast_shehbaz_prompts_c16_n43_nonstream_server | shehbaz | prompts | 16 | 43 |  | server | 0 | 0 | 125.74 / 188.25 / 269.4 | – | 34.01 | 3.86 | 3.74 | 0 | 3.643 | 0.11 | 22889 (22560) |

## P9_baseline_b8

Config: qwen-tts baseline --max-batch 8

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_short_c1_n8_nonstream_inline | trump | short | 1 | 8 |  | inline | 0 | 1 (0s/1l) | 2.27 / 3.35 / 3.37 | – | 3.53 | 1.56 | 1.56 | 0 | 0.641 | 0.44 | 5835 (5524) |
| trump_short_c2_n8_nonstream_inline | trump | short | 2 | 8 |  | inline | 0 | 0 | 3.2 / 3.56 / 3.56 | – | 2.71 | 2.16 | 2.16 | 0 | 0.945 | 0.8 | 7106 (6795) |
| trump_short_c4_n8_nonstream_inline | trump | short | 4 | 8 |  | inline | 0 | 1 (0s/1l) | 4.23 / 4.23 / 4.23 | – | 3.14 | 3.86 | 3.86 | 0 | 1.012 | 1.23 | 9919 (9608) |
| trump_short_c8_n16_nonstream_inline | trump | short | 8 | 16 |  | inline | 0 | 0 | 4.47 / 7.63 / 7.63 | – | 3.09 | 4.09 | 3.66 | 0 | 2.061 | 1.32 | 14990 (14679) |
| trump_short_c16_n32_nonstream_inline | trump | short | 16 | 32 |  | inline | 0 | 0 | 8.12 / 8.13 / 8.13 | – | 2.87 | 5.68 | 5.04 | 0 | 2.579 | 1.98 | 14991 (14680) |
| shehbaz_short_c1_n8_nonstream_inline | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 3.14 / 3.52 / 4.52 | – | 4.74 | 1.62 | 1.62 | 0 | 0.621 | 0.34 | 15001 (14690) |
| shehbaz_short_c2_n8_nonstream_inline | shehbaz | short | 2 | 8 |  | inline | 0 | 0 | 2.81 / 3.42 / 3.42 | – | 3.56 | 2.72 | 2.72 | 0 | 0.716 | 0.77 | 14993 (14682) |
| shehbaz_short_c4_n8_nonstream_inline | shehbaz | short | 4 | 8 |  | inline | 0 | 0 | 5.67 / 5.67 / 5.67 | – | 5.37 | 4.3 | 4.3 | 0 | 0.876 | 0.8 | 14992 (14681) |
| shehbaz_short_c8_n16_nonstream_inline | shehbaz | short | 8 | 16 |  | inline | 0 | 0 | 4.92 / 6.5 / 6.5 | – | 4.01 | 5.62 | 5.31 | 0 | 1.364 | 1.4 | 14993 (14682) |
| shehbaz_short_c16_n32_nonstream_inline | shehbaz | short | 16 | 32 |  | inline | 0 | 0 | 11.09 / 13.47 / 13.52 | – | 4.26 | 5.91 | 5.24 | 0 | 2.829 | 1.39 | 15007 (14696) |
| trump_xlong_c1_n4_nonstream_inline | trump | xlong | 1 | 4 |  | inline | 0 | 0 | 19.64 / 20.46 / 20.46 | – | 33.58 | 1.72 | 1.72 | 0 | 0.582 | 0.05 | 15041 (14730) |
| trump_xlong_c2_n4_nonstream_inline | trump | xlong | 2 | 4 |  | inline | 0 | 0 | 21 / 21 / 21 | – | 31.58 | 3.18 | 3.18 | 0 | 0.635 | 0.1 | 15041 (14730) |
| trump_xlong_c4_n4_nonstream_inline | trump | xlong | 4 | 4 |  | inline | 0 | 0 | 20.64 / 20.64 / 20.64 | – | 31.8 | 6.16 | 6.16 | 0 | 0.665 | 0.19 | 15098 (14787) |
| trump_xlong_c8_n8_nonstream_inline | trump | xlong | 8 | 8 |  | inline | 0 | 0 | 22.75 / 22.76 / 22.76 | – | 31.4 | 11.03 | 11.03 | 0 | 0.748 | 0.35 | 18066 (17755) |
| trump_xlong_c16_n16_nonstream_inline | trump | xlong | 16 | 16 |  | inline | 0 | 0 | 56.18 / 78.52 / 78.53 | – | 32.77 | 6.68 | 6.31 | 0 | 1.778 | 0.2 | 18077 (17766) |
| shehbaz_xlong_c1_n4_nonstream_inline | shehbaz | xlong | 1 | 4 |  | inline | 0 | 1 (1s/0l) | 19.13 / 19.55 / 19.55 | – | 26.14 | 1.7 | 1.7 | 0 | 0.591 | 0.06 | 18077 (17766) |
| shehbaz_xlong_c2_n4_nonstream_inline | shehbaz | xlong | 2 | 4 |  | inline | 1 | 0 | 21.69 / 51.48 / 51.48 | – | 33.76 | 1.38 | 1.38 | 0 | 0.655 | 0.04 | 18077 (17766) |
| shehbaz_xlong_c4_n4_nonstream_inline | shehbaz | xlong | 4 | 4 |  | inline | 0 | 0 | 20.52 / 20.52 / 20.52 | – | 32.88 | 6.41 | 6.41 | 0 | 0.619 | 0.19 | 18077 (17766) |
| shehbaz_xlong_c8_n8_nonstream_inline | shehbaz | xlong | 8 | 8 |  | inline | 0 | 0 | 26.25 / 26.25 / 26.26 | – | 32.62 | 9.94 | 9.94 | 0 | 0.828 | 0.3 | 18130 (17819) |
| shehbaz_xlong_c16_n16_nonstream_inline | shehbaz | xlong | 16 | 16 |  | inline | 0 | 1 (1s/0l) | 40.29 / 62.26 / 62.27 | – | 29.67 | 7.62 | 7.19 | 0 | 1.395 | 0.26 | 18133 (17822) |
| trump_xxlong_c1_n2_nonstream_inline | trump | xxlong | 1 | 2 |  | inline | 0 | 0 | 35.26 / 40.96 / 40.96 | – | 65.12 | 1.71 | 1.71 | 0 | 0.584 | 0.03 | 18133 (17822) |
| trump_xxlong_c8_n8_nonstream_inline | trump | xxlong | 8 | 8 |  | inline | 0 | 0 | 42.9 / 42.9 / 42.9 | – | 61.95 | 11.55 | 11.55 | 0 | 0.709 | 0.19 | 18437 (18126) |
| shehbaz_xxlong_c1_n2_nonstream_inline | shehbaz | xxlong | 1 | 2 |  | inline | 0 | 1 (0s/1l) | 28.55 / 94.92 / 94.92 | – | 104.52 | 1.69 | 1.69 | 0 | 0.585 | 0.02 | 18439 (18128) |
| shehbaz_xxlong_c8_n8_nonstream_inline | shehbaz | xxlong | 8 | 8 |  | inline | 0 | 5 (4s/1l) | 152.81 / 152.82 / 152.83 | – | 61.86 | 3.24 | 3.24 | 0 | 1.154 | 0.05 | 18651 (18340) |

**aggregate x realtime** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 |
|---|---|---|---|---|---|
| shehbaz short | 1.62 | 2.72 | 4.3 | 5.62 | 5.91 |
| shehbaz xlong | 1.7 | 1.38 | 6.41 | 9.94 | 7.62 |
| shehbaz xxlong | 1.69 |  |  | 3.24 |  |
| trump short | 1.56 | 2.16 | 3.86 | 4.09 | 5.68 |
| trump xlong | 1.72 | 3.18 | 6.16 | 11.03 | 6.68 |
| trump xxlong | 1.71 |  |  | 11.55 |  |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 |
|---|---|---|---|---|---|
| shehbaz short | 1.62 | 2.72 | 4.3 | 5.31 | 5.24 |
| shehbaz xlong | 1.7 | 1.38 | 6.41 | 9.94 | 7.19 |
| shehbaz xxlong | 1.69 |  |  | 3.24 |  |
| trump short | 1.56 | 2.16 | 3.86 | 3.66 | 5.04 |
| trump xlong | 1.72 | 3.18 | 6.16 | 11.03 | 6.31 |
| trump xxlong | 1.71 |  |  | 11.55 |  |

**req/s** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 |
|---|---|---|---|---|---|
| shehbaz short | 0.34 | 0.77 | 0.8 | 1.4 | 1.39 |
| shehbaz xlong | 0.06 | 0.04 | 0.19 | 0.3 | 0.26 |
| shehbaz xxlong | 0.02 |  |  | 0.05 |  |
| trump short | 0.44 | 0.8 | 1.23 | 1.32 | 1.98 |
| trump xlong | 0.05 | 0.1 | 0.19 | 0.35 | 0.2 |
| trump xxlong | 0.03 |  |  | 0.19 |  |

**latency p50 s** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 |
|---|---|---|---|---|---|
| shehbaz short | 3.14 | 2.81 | 5.67 | 4.92 | 11.09 |
| shehbaz xlong | 19.13 | 21.69 | 20.52 | 26.25 | 40.29 |
| shehbaz xxlong | 28.55 |  |  | 152.81 |  |
| trump short | 2.27 | 3.2 | 4.23 | 4.47 | 8.12 |
| trump xlong | 19.64 | 21 | 20.64 | 22.75 | 56.18 |
| trump xxlong | 35.26 |  |  | 42.9 |  |

**latency p90 s** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 |
|---|---|---|---|---|---|
| shehbaz short | 3.52 | 3.42 | 5.67 | 6.5 | 13.47 |
| shehbaz xlong | 19.55 | 51.48 | 20.52 | 26.25 | 62.26 |
| shehbaz xxlong | 94.92 |  |  | 152.82 |  |
| trump short | 3.35 | 3.56 | 4.23 | 7.63 | 8.13 |
| trump xlong | 20.46 | 21 | 20.64 | 22.76 | 78.52 |
| trump xxlong | 40.96 |  |  | 42.9 |  |

**per-request RTF p50** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 |
|---|---|---|---|---|---|
| shehbaz short | 0.621 | 0.716 | 0.876 | 1.364 | 2.829 |
| shehbaz xlong | 0.591 | 0.655 | 0.619 | 0.828 | 1.395 |
| shehbaz xxlong | 0.585 |  |  | 1.154 |  |
| trump short | 0.641 | 0.945 | 1.012 | 2.061 | 2.579 |
| trump xlong | 0.582 | 0.635 | 0.665 | 0.748 | 1.778 |
| trump xxlong | 0.584 |  |  | 0.709 |  |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=2 | c=4 | c=8 | c=16 |
|---|---|---|---|---|---|
| shehbaz short | 14690 | 14682 | 14681 | 14682 | 14696 |
| shehbaz xlong | 17766 | 17766 | 17766 | 17819 | 17822 |
| shehbaz xxlong | 18128 |  |  | 18340 |  |
| trump short | 5524 | 6795 | 9608 | 14679 | 14680 |
| trump xlong | 14730 | 14730 | 14787 | 17755 | 17766 |
| trump xxlong | 17822 |  |  | 18126 |  |

## P9_baseline_b1

Config: qwen-tts baseline --max-batch 1

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_short_c1_n8_nonstream_inline | trump | short | 1 | 8 |  | inline | 0 | 0 | 2.41 / 3.09 / 3.14 | – | 3.61 | 1.65 | 1.65 | 0 | 0.612 | 0.46 | 5815 (5504) |
| trump_short_c4_n8_nonstream_inline | trump | short | 4 | 8 |  | inline | 0 | 0 | 6.67 / 6.71 / 7.09 | – | 2.81 | 1.63 | 1.63 | 0 | 2.951 | 0.58 | 5817 (5506) |
| shehbaz_short_c1_n8_nonstream_inline | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 2.96 / 3.21 / 4.12 | – | 4.73 | 1.66 | 1.66 | 0 | 0.603 | 0.35 | 5831 (5520) |
| shehbaz_short_c4_n8_nonstream_inline | shehbaz | short | 4 | 8 |  | inline | 0 | 0 | 7.59 / 8.73 / 8.75 | – | 3.59 | 1.64 | 1.64 | 0 | 2.01 | 0.46 | 5831 (5520) |
| trump_xlong_c1_n4_nonstream_inline | trump | xlong | 1 | 4 |  | inline | 0 | 0 | 18.61 / 19.51 / 19.51 | – | 31.46 | 1.72 | 1.72 | 0 | 0.58 | 0.05 | 6323 (6012) |
| trump_xlong_c4_n4_nonstream_inline | trump | xlong | 4 | 4 |  | inline | 0 | 0 | 52.68 / 71.08 / 71.08 | – | 30.72 | 1.73 | 1.73 | 0 | 1.737 | 0.06 | 6323 (6012) |
| shehbaz_xlong_c1_n4_nonstream_inline | shehbaz | xlong | 1 | 4 |  | inline | 0 | 1 (0s/1l) | 20.67 / 48.71 / 48.71 | – | 43.52 | 1.73 | 1.73 | 0 | 0.58 | 0.04 | 6323 (6012) |
| shehbaz_xlong_c4_n4_nonstream_inline | shehbaz | xlong | 4 | 4 |  | inline | 0 | 0 | 58.34 / 75.38 / 75.38 | – | 32.52 | 1.73 | 1.73 | 0 | 1.792 | 0.05 | 6323 (6012) |

**aggregate x realtime** by concurrency

| series | c=1 | c=4 |
|---|---|---|
| shehbaz short | 1.66 | 1.64 |
| shehbaz xlong | 1.73 | 1.73 |
| trump short | 1.65 | 1.63 |
| trump xlong | 1.72 | 1.73 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=4 |
|---|---|---|
| shehbaz short | 1.66 | 1.64 |
| shehbaz xlong | 1.73 | 1.73 |
| trump short | 1.65 | 1.63 |
| trump xlong | 1.72 | 1.73 |

**req/s** by concurrency

| series | c=1 | c=4 |
|---|---|---|
| shehbaz short | 0.35 | 0.46 |
| shehbaz xlong | 0.04 | 0.05 |
| trump short | 0.46 | 0.58 |
| trump xlong | 0.05 | 0.06 |

**latency p50 s** by concurrency

| series | c=1 | c=4 |
|---|---|---|
| shehbaz short | 2.96 | 7.59 |
| shehbaz xlong | 20.67 | 58.34 |
| trump short | 2.41 | 6.67 |
| trump xlong | 18.61 | 52.68 |

**latency p90 s** by concurrency

| series | c=1 | c=4 |
|---|---|---|
| shehbaz short | 3.21 | 8.73 |
| shehbaz xlong | 48.71 | 75.38 |
| trump short | 3.09 | 6.71 |
| trump xlong | 19.51 | 71.08 |

**per-request RTF p50** by concurrency

| series | c=1 | c=4 |
|---|---|---|
| shehbaz short | 0.603 | 2.01 |
| shehbaz xlong | 0.58 | 1.792 |
| trump short | 0.612 | 2.951 |
| trump xlong | 0.58 | 1.737 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=4 |
|---|---|---|
| shehbaz short | 5520 | 5520 |
| shehbaz xlong | 6012 | 6012 |
| trump short | 5504 | 5506 |
| trump xlong | 6012 | 6012 |

## P9_baseline_nocache

Config: qwen-tts baseline --max-batch 8 --no-prompt-cache

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_short_c1_n8_nonstream_inline | trump | short | 1 | 8 |  | inline | 0 | 1 (0s/1l) | 2.58 / 3.27 / 3.49 | – | 3.93 | 1.6 | 1.6 | 0 | 0.636 | 0.41 | 5817 (5506) |
| trump_short_c8_n16_nonstream_inline | trump | short | 8 | 16 |  | inline | 0 | 0 | 4.53 / 5.61 / 5.61 | – | 2.83 | 4.47 | 3.95 | 0 | 2.191 | 1.58 | 14903 (14592) |
| shehbaz_short_c1_n8_nonstream_inline | shehbaz | short | 1 | 8 |  | inline | 0 | 0 | 3.06 / 3.75 / 4.33 | – | 4.83 | 1.61 | 1.61 | 0 | 0.624 | 0.33 | 14917 (14606) |
| shehbaz_short_c8_n16_nonstream_inline | shehbaz | short | 8 | 16 |  | inline | 0 | 0 | 4.39 / 10.36 / 10.37 | – | 4.52 | 4.94 | 4.45 | 0 | 1.504 | 1.09 | 14919 (14608) |
| trump_xlong_c1_n4_nonstream_inline | trump | xlong | 1 | 4 |  | inline | 0 | 0 | 19.1 / 21.53 / 21.53 | – | 32.46 | 1.69 | 1.69 | 0 | 0.593 | 0.05 | 14966 (14655) |
| trump_xlong_c8_n8_nonstream_inline | trump | xlong | 8 | 8 |  | inline | 0 | 0 | 21.4 / 21.41 / 21.41 | – | 31.13 | 11.63 | 11.63 | 0 | 0.688 | 0.37 | 18881 (18570) |
| shehbaz_xlong_c1_n4_nonstream_inline | shehbaz | xlong | 1 | 4 |  | inline | 0 | 0 | 17.87 / 17.88 / 17.88 | – | 28.98 | 1.68 | 1.68 | 0 | 0.597 | 0.06 | 18884 (18573) |
| shehbaz_xlong_c8_n8_nonstream_inline | shehbaz | xlong | 8 | 8 |  | inline | 1 | 0 | 53.57 / 74.25 / 74.25 | – | 32.15 | 3.03 | 3.03 | 0 | 1.849 | 0.09 | 19119 (18808) |

**aggregate x realtime** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| shehbaz short | 1.61 | 4.94 |
| shehbaz xlong | 1.68 | 3.03 |
| trump short | 1.6 | 4.47 |
| trump xlong | 1.69 | 11.63 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| shehbaz short | 1.61 | 4.45 |
| shehbaz xlong | 1.68 | 3.03 |
| trump short | 1.6 | 3.95 |
| trump xlong | 1.69 | 11.63 |

**req/s** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| shehbaz short | 0.33 | 1.09 |
| shehbaz xlong | 0.06 | 0.09 |
| trump short | 0.41 | 1.58 |
| trump xlong | 0.05 | 0.37 |

**latency p50 s** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| shehbaz short | 3.06 | 4.39 |
| shehbaz xlong | 17.87 | 53.57 |
| trump short | 2.58 | 4.53 |
| trump xlong | 19.1 | 21.4 |

**latency p90 s** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| shehbaz short | 3.75 | 10.36 |
| shehbaz xlong | 17.88 | 74.25 |
| trump short | 3.27 | 5.61 |
| trump xlong | 21.53 | 21.41 |

**per-request RTF p50** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| shehbaz short | 0.624 | 1.504 |
| shehbaz xlong | 0.597 | 1.849 |
| trump short | 0.636 | 2.191 |
| trump xlong | 0.593 | 0.688 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=8 |
|---|---|---|
| shehbaz short | 14606 | 14608 |
| shehbaz xlong | 18573 | 18808 |
| trump short | 5506 | 14592 |
| trump xlong | 14655 | 18570 |

## 01_probe_scaling_engine_direct

Config: 

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| probe_prod045_trump_long_c1_n8 | trump | long | 1 | 8 |  | – | 0 | 0 | 2.71 / 3.06 / 3.35 | – | – | 5.59 | – | – | 0.179 | 0.36 | 15925 |
| probe_prod045_trump_long_c4_n8 | trump | long | 4 | 8 |  | – | 0 | 0 | 3.78 / 4.17 / 4.64 | – | – | 15.58 | – | – | 0.244 | 0.98 | 15923 |
| probe_prod045_trump_long_c8_n16 | trump | long | 8 | 16 |  | – | 0 | 0 | 6.24 / 7 / 7.74 | – | – | 19.46 | – | – | 0.39 | 1.2 | 15923 |
| probe_prod045_trump_long_c16_n32 | trump | long | 16 | 32 |  | – | 0 | 0 | 9 / 10.14 / 12.79 | – | – | 26.29 | – | – | 0.578 | 1.59 | 15975 |
| probe_prod045_trump_long_c32_n64 | trump | long | 32 | 64 |  | – | 0 | 0 | 13.56 / 15.94 / 17.15 | – | – | 35.06 | – | – | 0.874 | 2.17 | 16203 |
| probe_prod045_trump_long_c48_n96 | trump | long | 48 | 96 |  | – | 0 | 0 | 21.27 / 24.77 / 27.04 | – | – | 34.24 | – | – | 1.357 | 2.13 | 16475 |
| probe_prod045_trump_long_c64_n128 | trump | long | 64 | 128 |  | – | 0 | 0 | 24.15 / 30.26 / 35.88 | – | – | 38.49 | – | – | 1.57 | 2.37 | 16752 |
| probe_prod045_shehbaz_long_c1_n8 | shehbaz | long | 1 | 8 |  | – | 0 | 0 | 4.05 / 4.29 / 4.58 | – | – | 5.55 | – | – | 0.18 | 0.25 | 16749 |
| probe_prod045_shehbaz_long_c4_n8 | shehbaz | long | 4 | 8 |  | – | 0 | 0 | 5.28 / 5.55 / 5.6 | – | – | 15.71 | – | – | 0.246 | 0.74 | 16750 |
| probe_prod045_shehbaz_long_c8_n16 | shehbaz | long | 8 | 16 |  | – | 0 | 0 | 8.55 / 10.03 / 10.25 | – | – | 19.15 | – | – | 0.39 | 0.87 | 16748 |
| probe_prod045_shehbaz_long_c16_n32 | shehbaz | long | 16 | 32 |  | – | 0 | 0 | 11.67 / 13.71 / 14.24 | – | – | 27.58 | – | – | 0.555 | 1.27 | 16749 |
| probe_prod045_shehbaz_long_c32_n64 | shehbaz | long | 32 | 64 |  | – | 0 | 0 | 18.72 / 21.71 / 22.71 | – | – | 35.52 | – | – | 0.856 | 1.58 | 16753 |
| probe_prod045_shehbaz_long_c48_n96 | shehbaz | long | 48 | 96 |  | – | 0 | 0 | 28.61 / 33.71 / 39.47 | – | – | 21.98 | – | – | 1.338 | 1 | 16753 |
| probe_prod045_shehbaz_long_c64_n128 | shehbaz | long | 64 | 128 |  | – | 0 | 0 | 32.89 / 40.29 / 113.56 | – | – | 22.7 | – | – | 1.536 | 1.02 | 16966 |

**aggregate x realtime** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 | c=48 | c=64 |
|---|---|---|---|---|---|---|---|
| probe_prod045 shehbaz long | 5.55 | 15.71 | 19.15 | 27.58 | 35.52 | 21.98 | 22.7 |
| probe_prod045 trump long | 5.59 | 15.58 | 19.46 | 26.29 | 35.06 | 34.24 | 38.49 |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 | c=48 | c=64 |
|---|---|---|---|---|---|---|---|
| probe_prod045 shehbaz long | – | – | – | – | – | – | – |
| probe_prod045 trump long | – | – | – | – | – | – | – |

**req/s** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 | c=48 | c=64 |
|---|---|---|---|---|---|---|---|
| probe_prod045 shehbaz long | 0.25 | 0.74 | 0.87 | 1.27 | 1.58 | 1 | 1.02 |
| probe_prod045 trump long | 0.36 | 0.98 | 1.2 | 1.59 | 2.17 | 2.13 | 2.37 |

**latency p50 s** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 | c=48 | c=64 |
|---|---|---|---|---|---|---|---|
| probe_prod045 shehbaz long | 4.05 | 5.28 | 8.55 | 11.67 | 18.72 | 28.61 | 32.89 |
| probe_prod045 trump long | 2.71 | 3.78 | 6.24 | 9 | 13.56 | 21.27 | 24.15 |

**latency p90 s** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 | c=48 | c=64 |
|---|---|---|---|---|---|---|---|
| probe_prod045 shehbaz long | 4.29 | 5.55 | 10.03 | 13.71 | 21.71 | 33.71 | 40.29 |
| probe_prod045 trump long | 3.06 | 4.17 | 7 | 10.14 | 15.94 | 24.77 | 30.26 |

**per-request RTF p50** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 | c=48 | c=64 |
|---|---|---|---|---|---|---|---|
| probe_prod045 shehbaz long | 0.18 | 0.246 | 0.39 | 0.555 | 0.856 | 1.338 | 1.536 |
| probe_prod045 trump long | 0.179 | 0.244 | 0.39 | 0.578 | 0.874 | 1.357 | 1.57 |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=4 | c=8 | c=16 | c=32 | c=48 | c=64 |
|---|---|---|---|---|---|---|---|
| probe_prod045 shehbaz long | – | – | – | – | – | – | – |
| probe_prod045 trump long | – | – | – | – | – | – | – |

## 02_probe_gateway_urdu_c48

Config: 

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gw_retry1_cap_shehbaz_long_c48_n96 | shehbaz | long | 48 | 96 |  | – | 0 | 0 | 23.83 / 35.7 / 40.81 | – | – | 34.34 | – | – | 1.049 | 1.54 | 16967 |

## 03_ab_async_chunk

Config: 

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| async_chunk/e03_async_trump_long_c1_n8 | trump | long | 1 | 8 |  | – | 0 | 0 | 3 / 3.12 / 3.21 | – | – | 5.55 | – | – | 0.18 | 0.34 | 19156 |
| async_chunk/e03_async_trump_long_c8_n16 | trump | long | 8 | 16 |  | – | 0 | 0 | 6.5 / 6.79 / 7.16 | – | – | 19.01 | – | – | 0.401 | 1.18 | 19186 |
| async_chunk/e03_async_trump_long_c32_n64 | trump | long | 32 | 64 |  | – | 0 | 0 | 13.97 / 16.97 / 17.99 | – | – | 34.48 | – | – | 0.88 | 2.13 | 19337 |
| async_chunk/e03_async_stream_trump_long_c1_n8_stream | trump | long | 1 | 8 | y | – | 0 | 0 | 2.89 / 3.07 / 3.53 | 0.12 / 0.14 / 0.14 | – | 5.54 | – | – | 0.181 | 0.35 | 19339 |
| async_chunk/e03_async_stream_trump_long_c8_n16_stream | trump | long | 8 | 16 | y | – | 0 | 0 | 6.12 / 7.46 / 7.73 | 0.33 / 0.65 / 0.65 | – | 18.95 | – | – | 0.396 | 1.18 | 19339 |
| async_chunk/e03_async_shehbaz_long_c1_n8 | shehbaz | long | 1 | 8 |  | – | 0 | 0 | 4.05 / 4.78 / 4.88 | – | – | 5.49 | – | – | 0.182 | 0.24 | 19642 |
| async_chunk/e03_async_shehbaz_long_c8_n16 | shehbaz | long | 8 | 16 |  | – | 0 | 0 | 8.7 / 10.23 / 10.37 | – | – | 18.3 | – | – | 0.402 | 0.81 | 19643 |
| async_chunk/e03_async_shehbaz_long_c32_n64 | shehbaz | long | 32 | 64 |  | – | 0 | 0 | 18.76 / 21.89 / 24.19 | – | – | 21.6 | – | – | 0.871 | 0.98 | 19647 |
| async_chunk/e03_async_stream_shehbaz_long_c1_n8_stream | shehbaz | long | 1 | 8 | y | – | 0 | 0 | 4.22 / 4.64 / 4.76 | 0.14 / 0.14 / 0.14 | – | 5.43 | – | – | 0.184 | 0.23 | 19639 |
| async_chunk/e03_async_stream_shehbaz_long_c8_n16_stream | shehbaz | long | 8 | 16 | y | – | 0 | 0 | 9.13 / 9.64 / 9.8 | 0.42 / 0.73 / 0.74 | – | 19.07 | – | – | 0.397 | 0.84 | 19643 |
| no_async_chunk/e03_noasync_trump_long_c1_n8 | trump | long | 1 | 8 |  | – | 0 | 0 | 3.06 / 3.38 / 3.38 | – | – | 5.26 | – | – | 0.19 | 0.33 | 22817 |
| no_async_chunk/e03_noasync_trump_long_c8_n16 | trump | long | 8 | 16 |  | – | 0 | 0 | 7.28 / 8.02 / 8.02 | – | – | 16.51 | – | – | 0.427 | 1.04 | 22817 |
| no_async_chunk/e03_noasync_trump_long_c32_n64 | trump | long | 32 | 64 |  | – | 0 | 0 | 15.92 / 19.85 / 20.47 | – | – | 28.56 | – | – | 0.931 | 1.78 | 22965 |
| no_async_chunk/e03_noasync_stream_trump_long_c1_n8_stream | trump | long | 1 | 8 | y | – | 0 | 0 | 3.45 / 3.52 / 3.63 | 3.45 / 3.52 / 3.63 | – | 4.96 | – | – | 0.203 | 0.31 | 22967 |
| no_async_chunk/e03_noasync_stream_trump_long_c8_n16_stream | trump | long | 8 | 16 | y | – | 0 | 0 | 7.24 / 7.99 / 7.99 | 7.24 / 7.98 / 7.99 | – | 16.27 | – | – | 0.431 | 1.02 | 22968 |
| no_async_chunk/e03_noasync_shehbaz_long_c1_n8 | shehbaz | long | 1 | 8 |  | – | 0 | 0 | 4.49 / 4.91 / 4.92 | – | – | 4.9 | – | – | 0.205 | 0.22 | 23187 |
| no_async_chunk/e03_noasync_shehbaz_long_c8_n16 | shehbaz | long | 8 | 16 |  | – | 0 | 0 | 9.69 / 11.32 / 11.35 | – | – | 17.14 | – | – | 0.428 | 0.76 | 23186 |
| no_async_chunk/e03_noasync_shehbaz_long_c32_n64 | shehbaz | long | 32 | 64 |  | – | 0 | 0 | 21.81 / 24.04 / 25.9 | – | – | 18.38 | – | – | 0.947 | 0.84 | 23193 |
| no_async_chunk/e03_noasync_stream_shehbaz_long_c1_n8_stream | shehbaz | long | 1 | 8 | y | – | 0 | 0 | 4.53 / 4.96 / 5.57 | 4.53 / 4.96 / 5.57 | – | 4.91 | – | – | 0.203 | 0.23 | 23186 |
| no_async_chunk/e03_noasync_stream_shehbaz_long_c8_n16_stream | shehbaz | long | 8 | 16 | y | – | 0 | 0 | 9.56 / 10.93 / 11.04 | 9.56 / 10.93 / 11.04 | – | 16.28 | – | – | 0.442 | 0.73 | 23188 |

**aggregate x realtime** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| e03_async shehbaz long | 5.49 | 18.3 | 21.6 |
| e03_async trump long | 5.55 | 19.01 | 34.48 |
| e03_async_stream shehbaz long stream | 5.43 | 19.07 |  |
| e03_async_stream trump long stream | 5.54 | 18.95 |  |
| e03_noasync shehbaz long | 4.9 | 17.14 | 18.38 |
| e03_noasync trump long | 5.26 | 16.51 | 28.56 |
| e03_noasync_stream shehbaz long stream | 4.91 | 16.28 |  |
| e03_noasync_stream trump long stream | 4.96 | 16.27 |  |

**x realtime over the first 90% of finished requests (straggler-robust)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| e03_async shehbaz long | – | – | – |
| e03_async trump long | – | – | – |
| e03_async_stream shehbaz long stream | – | – |  |
| e03_async_stream trump long stream | – | – |  |
| e03_noasync shehbaz long | – | – | – |
| e03_noasync trump long | – | – | – |
| e03_noasync_stream shehbaz long stream | – | – |  |
| e03_noasync_stream trump long stream | – | – |  |

**req/s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| e03_async shehbaz long | 0.24 | 0.81 | 0.98 |
| e03_async trump long | 0.34 | 1.18 | 2.13 |
| e03_async_stream shehbaz long stream | 0.23 | 0.84 |  |
| e03_async_stream trump long stream | 0.35 | 1.18 |  |
| e03_noasync shehbaz long | 0.22 | 0.76 | 0.84 |
| e03_noasync trump long | 0.33 | 1.04 | 1.78 |
| e03_noasync_stream shehbaz long stream | 0.23 | 0.73 |  |
| e03_noasync_stream trump long stream | 0.31 | 1.02 |  |

**latency p50 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| e03_async shehbaz long | 4.05 | 8.7 | 18.76 |
| e03_async trump long | 3 | 6.5 | 13.97 |
| e03_async_stream shehbaz long stream | 4.22 | 9.13 |  |
| e03_async_stream trump long stream | 2.89 | 6.12 |  |
| e03_noasync shehbaz long | 4.49 | 9.69 | 21.81 |
| e03_noasync trump long | 3.06 | 7.28 | 15.92 |
| e03_noasync_stream shehbaz long stream | 4.53 | 9.56 |  |
| e03_noasync_stream trump long stream | 3.45 | 7.24 |  |

**latency p90 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| e03_async shehbaz long | 4.78 | 10.23 | 21.89 |
| e03_async trump long | 3.12 | 6.79 | 16.97 |
| e03_async_stream shehbaz long stream | 4.64 | 9.64 |  |
| e03_async_stream trump long stream | 3.07 | 7.46 |  |
| e03_noasync shehbaz long | 4.91 | 11.32 | 24.04 |
| e03_noasync trump long | 3.38 | 8.02 | 19.85 |
| e03_noasync_stream shehbaz long stream | 4.96 | 10.93 |  |
| e03_noasync_stream trump long stream | 3.52 | 7.99 |  |

**per-request RTF p50** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| e03_async shehbaz long | 0.182 | 0.402 | 0.871 |
| e03_async trump long | 0.18 | 0.401 | 0.88 |
| e03_async_stream shehbaz long stream | 0.184 | 0.397 |  |
| e03_async_stream trump long stream | 0.181 | 0.396 |  |
| e03_noasync shehbaz long | 0.205 | 0.428 | 0.947 |
| e03_noasync trump long | 0.19 | 0.427 | 0.931 |
| e03_noasync_stream shehbaz long stream | 0.203 | 0.442 |  |
| e03_noasync_stream trump long stream | 0.203 | 0.431 |  |

**TTFA p50 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| e03_async_stream shehbaz long stream | 0.14 | 0.42 |  |
| e03_async_stream trump long stream | 0.12 | 0.33 |  |
| e03_noasync_stream shehbaz long stream | 4.53 | 9.56 |  |
| e03_noasync_stream trump long stream | 3.45 | 7.24 |  |

**TTFA p90 s** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| e03_async_stream shehbaz long stream | 0.14 | 0.73 |  |
| e03_async_stream trump long stream | 0.14 | 0.65 |  |
| e03_noasync_stream shehbaz long stream | 4.96 | 10.93 |  |
| e03_noasync_stream trump long stream | 3.52 | 7.98 |  |

**engine GPU MiB (peak - idle baseline)** by concurrency

| series | c=1 | c=8 | c=32 |
|---|---|---|---|
| e03_async shehbaz long | – | – | – |
| e03_async trump long | – | – | – |
| e03_async_stream shehbaz long stream | – | – |  |
| e03_async_stream trump long stream | – | – |  |
| e03_noasync shehbaz long | – | – | – |
| e03_noasync trump long | – | – | – |
| e03_noasync_stream shehbaz long stream | – | – |  |
| e03_noasync_stream trump long stream | – | – |  |

## 11_production_sim_guard

Config: 

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| prod_c1_trump_short_c1_n16_nonstream_server | trump | short | 1 | 16 |  | server | 0 | 0 | 0.67 / 1.03 / 1.12 | – | 3.1 | 4.77 | 4.8 | 0 | 0.221 | 1.54 | 20851 |
| prod_c1_shehbaz_short_c1_n16_nonstream_server | shehbaz | short | 1 | 16 |  | server | 0 | 0 | 0.95 / 1.34 / 1.44 | – | 4.66 | 5 | 5.01 | 0 | 0.201 | 1.07 | 20846 |
| prod_c16_trump_short_c16_n320_nonstream_server | trump | short | 16 | 320 |  | server | 0 | 1 (0s/1l) | 2.42 / 4.36 / 5.25 | – | 2.96 | 17.41 | 16.96 | 0 | 0.9 | 5.88 | 20958 |
| prod_c16_shehbaz_short_c16_n64_nonstream_server | shehbaz | short | 16 | 64 |  | server | 0 | 0 | 3.38 / 5.94 / 6.6 | – | 4.78 | 19.33 | 18.27 | 0 | 0.8 | 4.04 | 21107 |
| prod_c16_trump_xlong_c16_n32_nonstream_server | trump | xlong | 16 | 32 |  | server | 0 | 0 | 14.26 / 21.96 / 35.65 | – | 33.14 | 28.57 | 26.48 | 0 | 0.452 | 0.86 | 21232 |
| prod_c16_shehbaz_xlong_c16_n32_nonstream_server | shehbaz | xlong | 16 | 32 |  | server | 0 | 0 | 18.71 / 22.62 / 33.25 | – | 37.26 | 27.02 | 27.47 | 0 | 0.499 | 0.73 | 21811 |

## 13_final_server

Config: 

| run | voice | size | c | n | stream | voice mode | errors | suspects | latency p50/p90/p99 s | TTFA p50/p90/p99 s | audio s/req | x realtime | x realtime p90-wall | stragglers | RTF p50 | req/s | GPU peak MiB (engine) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final_c1_trump_short_c1_n16_nonstream_server | trump | short | 1 | 16 |  | server | 0 | 0 | 0.65 / 1.02 / 1.03 | – | 3.23 | 4.8 | 4.82 | 0 | 0.218 | 1.49 | 20736 |
| final_c1_trump_short_c1_n16_stream_server | trump | short | 1 | 16 | y | server | 0 | 0 | 0.61 / 0.98 / 1.06 | 0.11 / 0.11 / 0.12 | 3.16 | 4.98 | 5.01 | 0 | 0.205 | 1.58 | 20730 |
| final_c16_trump_short_c16_n64_nonstream_server | trump | short | 16 | 64 |  | server | 0 | 0 | 2.38 / 4.38 / 5.02 | – | 3.1 | 17.15 | 16.43 | 0 | 0.853 | 5.53 | 20843 |
| final_c16_trump_medium_c16_n64_nonstream_server | trump | medium | 16 | 64 |  | server | 0 | 0 | 4.32 / 5.79 / 6.27 | – | 6.49 | 21.95 | 20.32 | 0 | 0.683 | 3.38 | 20884 |
| final_c16_trump_long_c16_n43_nonstream_server | trump | long | 16 | 43 |  | server | 0 | 0 | 9.46 / 11.14 / 11.64 | – | 15.94 | 24.6 | 23.09 | 0 | 0.589 | 1.54 | 20920 |
| final_c16_trump_prompts_c16_n43_nonstream_server | trump | prompts | 16 | 43 |  | server | 0 | 0 | 14.67 / 27.04 / 39.59 | – | 32.79 | 27.21 | 28.89 | 0 | 0.45 | 0.83 | 21004 |
| final_c16_trump_xxlong_c16_n43_nonstream_server | trump | xxlong | 16 | 43 |  | server | 0 | 0 | 19.44 / 70.46 / 73 | – | 65.82 | 27.96 | 25.76 | 9 | 0.294 | 0.42 | 21155 |
| final_c32_trump_medium_c32_n128_nonstream_server | trump | medium | 32 | 128 |  | server | 0 | 0 | 6.83 / 9.12 / 11.69 | – | 6.59 | 26.94 | 25.58 | 0 | 1.119 | 4.09 | 21151 |
| final_c1_shehbaz_short_c1_n16_nonstream_server | shehbaz | short | 1 | 16 |  | server | 0 | 0 | 1.01 / 1.8 / 1.86 | – | 4.61 | 4.64 | 4.61 | 0 | 0.206 | 1.01 | 21152 |
| final_c1_shehbaz_short_c1_n16_stream_server | shehbaz | short | 1 | 16 | y | server | 0 | 0 | 0.88 / 1.32 / 1.38 | 0.12 / 0.12 / 0.12 | 4.36 | 5.04 | 5.05 | 0 | 0.199 | 1.16 | 21153 |
| final_c16_shehbaz_short_c16_n64_nonstream_server | shehbaz | short | 16 | 64 |  | server | 0 | 0 | 3.55 / 5.53 / 6.63 | – | 4.82 | 19.38 | 18 | 0 | 0.789 | 4.02 | 21154 |
| final_c16_shehbaz_medium_c16_n64_nonstream_server | shehbaz | medium | 16 | 64 |  | server | 0 | 0 | 6.66 / 8.43 / 9.62 | – | 10.35 | 23.1 | 22.28 | 0 | 0.656 | 2.23 | 21155 |
| final_c16_shehbaz_long_c16_n43_nonstream_server | shehbaz | long | 16 | 43 |  | server | 0 | 0 | 14.06 / 17.13 / 18.89 | – | 23.67 | 24.26 | 22.23 | 0 | 0.58 | 1.03 | 21355 |
| final_c16_shehbaz_prompts_c16_n43_nonstream_server | shehbaz | prompts | 16 | 43 |  | server | 0 | 0 | 18.48 / 21.96 / 57.09 | – | 37.63 | 28.34 | 26.16 | 1 | 0.499 | 0.75 | 22206 |
| final_c16_shehbaz_xxlong_c16_n43_nonstream_server | shehbaz | xxlong | 16 | 43 |  | server | 0 | 0 | 22.54 / 88.88 / 99.54 | – | 75.99 | 28.2 | 28.53 | 9 | 0.303 | 0.37 | 22501 |
| final_c32_shehbaz_medium_c32_n128_nonstream_server | shehbaz | medium | 32 | 128 |  | server | 0 | 0 | 10.63 / 13.47 / 16.35 | – | 10.67 | 29.11 | 27.37 | 0 | 1.05 | 2.73 | 22836 |

