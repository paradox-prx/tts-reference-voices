# Benchmark

`bench_tts.py` load-tests a Qwen3-TTS voice-clone server that uses vLLM-Omni's `/v1/audio/speech` request
shape (see `../NOTES.md`). It needs only `httpx`, and it was tested against a stub server, not a real GPU.

```bash
python bench/bench_tts.py --voice shehbaz --size short -n 32 -c 8
python bench/bench_tts.py --voice trump shehbaz --matrix                 # 4 sizes x concurrency 1,2,4,8,16,32
python bench/bench_tts.py --voice shehbaz --stream --size long --sweep 1,4,8,16
python bench/bench_tts.py --voice shehbaz --voice-mode upload ...        # register once, then send voice=<name>
python bench/bench_tts.py --voice shehbaz --param repetition_penalty=1.15 --size xlong -n 43 -c 8
python bench/bench_tts.py --voice shehbaz --pools other_pools.json ...   # someone else's sentence lists
```

**Sizes** come from `pools/{en,ur}.json`. Each size uses distinct strings, so a concurrency window never repeats
a text:

| size | length | speech |
|---|---|---|
| short | 1 sentence | a few seconds |
| medium | 20–45 words | ~8–15 s |
| long | 55–90 words | ~20–35 s |
| xlong | a full 80–170-word prompt | ~30–60 s |

**Per run** it records:
- latency p50/p90/p95/p99
- time to first audio (with `--stream`)
- throughput (audio seconds per wall second), req/s and per-request RTF
- error and `suspect` counts. `suspect` means the audio's length doesn't fit the word count: skipped text, a
  loop, or padding.
- peak GPU memory and mean utilisation, sampled from `nvidia-smi`

**Output** goes to `results/<timestamp>/`:
- `requests.jsonl`: every request, with its text
- `summary.csv` and `summary.md`
- `audio/`: the generated audio, unless `--no-audio`. Point a WER and similarity check at it.
