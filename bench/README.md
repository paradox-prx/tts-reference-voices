# Benchmark

`bench_tts.py` load-tests a Qwen3-TTS voice-clone server that speaks vLLM-Omni's `/v1/audio/speech` request shape
(see `../NOTES.md`): the vLLM-Omni engine itself, our gateway (`server/gateway`), or the plain qwen-tts baseline
(`server/baseline`). It needs only `httpx` (run it with `server/venvs/gateway/bin/python`). `python bench/bench_tts.py
--help` lists every flag. The full benchmark plan (engine variants, matrix, streaming, cache, quality, baseline) is run
phase by phase by `server/bench/run_plan.py`; see its `--help` and `server/bench/plan.py`.

```bash
python bench/bench_tts.py --voice shehbaz --size short -n 32 -c 8
python bench/bench_tts.py --voice trump shehbaz --size xlong --sweep 1,2,4,8,16,32 --n-rule 6:1   # n = max(6, c)
python bench/bench_tts.py --voice shehbaz --stream --size short xlong xxlong --sweep 1,4,8,16
python bench/bench_tts.py --voice trump shehbaz --voice-mode server --url http://127.0.0.1:8090   # through the gateway
python bench/bench_tts.py --voice shehbaz --voice-mode upload ...          # register once, then send voice=<name>
python bench/bench_tts.py --voice shehbaz --voice-mode nocache ...         # every reference new: caches defeated
python bench/bench_tts.py --voice shehbaz --voice-mode server --voice-name '{voice}-avg' ...   # engine custom voice
python bench/bench_tts.py --voice shehbaz --size prompts --takes 6 -c 16 \
    --extra-param repetition_penalty=1.15 --max-new-tokens auto            # 43 prompts x 6 takes
python bench/bench_tts.py --voice trump shehbaz --mix --size xlong -n 16 -c 16   # both voices in one batch
python bench/bench_tts.py --voice shehbaz --pools bench/pools/auralis_ur.json --size short medium long -n 20 -c 20
python bench/bench_tts.py --voice shehbaz --size xxlong --sweep 1,8 --estimate   # requests + audio seconds, sends nothing
```

## Sizes

From `pools/{en,ur}.json` (and `../benchmarks/<set>.json` for `prompts`). Speech durations at the calibrated pace
(`server/calibration/pace.json`: trump 0.0795, shehbaz 0.088 s per letter).

| size | text | speech en / ur | the user's size |
|---|---|---|---|
| short | 1 sentence (5-25 words) | ~3 s / ~3 s | short (1 sentence) |
| medium | 20-45 words | ~7.5 s / ~7.5 s | |
| long | 55-69 words | ~18 s / ~18 s | |
| xlong | one benchmark prompt (82-165 words) | ~37 s / ~28 s | medium (~30 s) |
| xxlong | two consecutive prompts joined (167-321 words) | ~73 s / ~56 s | long (~60 s) |
| prompts | the 43 prompts of `benchmarks/trump_en.json` / `shehbaz_ur.json` in order, with their ids | as xlong | quality runs |

A run never repeats a string while the pool is large enough, and the runs of one command continue through the list
(use `--n-rule MIN:MULT[:MAX]` rather than `-n` so a sweep keeps sending distinct texts).

## Requests

- **Voice modes** (`--voice-mode`): `inline` (reference clip as a `data:` URL + transcript in every request),
  `upload` (`POST /v1/audio/voices` once, then `voice=<name>`), `server` (only `voice=<name>`: the gateway's voice ids,
  or engine custom voices with `--voice-name '{voice}-avg'`), `nocache` (inline, but one PCM sample's least significant
  bit is flipped per request, so vLLM-Omni's two reference caches, keyed by sha1 of the data URL and of the decoded
  samples, miss every time).
- **Engine-direct fields:** vLLM-Omni silently ignores top-level `temperature`/`top_k`/`top_p`/`repetition_penalty`.
  Send sampling with `--extra-param K=V` (merged into `extra_params`; `repetition_penalty` needs `server/engine/patches`),
  other top-level fields with `--param K=V` (JSON value, e.g. `non_streaming_mode=true`; `null` removes a field),
  `--language English|Auto|none`, and `--max-new-tokens auto|N` (`auto` = the gateway's length cap). Through the
  gateway, sampling fields and `retries` are top-level `--param`s.
- **Seeds:** don't. On vLLM-Omni 0.28 a seed does not reproduce even sequentially at c=1 (server/docs/EXPERIMENTS.md E04), it serialises the code predictor of the whole batch and disables the engine's built-in retry. Repeat unseeded takes with `--takes K` (rows carry `take` and `prompt_id`) and compare settings by prompt. `run_plan.py` refuses `--seed`.

## What it measures

Per request: latency, time to first audio past the WAV header (`--stream`), audio seconds, RTF, seconds per letter
and the pace ratio against the voice's expected pace, every `x-*` response header (gateway retries, suspect, QC,
engine/queue ms; engine token counts), the request fields sent, a PCM hash. `suspect` = pace outside 0.6-1.8x the
voice's expected seconds per letter (`too_short`: skipped or cut-off text; `too_long`: loop, filler, padding). It is
only a first screen: ASR and audio checks (`server/eval`, the gateway's QC sidecar) catch the rest.

Per run: latency p50/p90/p95/p99, TTFA p50/p90/p99, audio seconds per request, aggregate x realtime, per-request RTF,
req/s, errors (by kind), suspects, duplicate audio, gateway retries and QC verdicts, pace-ratio percentiles, peak GPU
memory and mean utilisation (`--gpus`, sampled with nvidia-smi every 500 ms; it includes other tenants of that GPU).

## Output

`--out DIR` (default `results/<timestamp>/`; `run_plan.py` uses `server/results/<phase>/`), one folder per run, named
for it: `<tag>_<voice>_<size>_c<c>_n<n>[_k<takes>][_s<seed>]_<stream|nonstream>_<voice mode>`.

```
DIR/<run>/audio/*.wav            every take, rewritten as a clean RIFF with a LIST/INFO "AI-generated" comment
DIR/<run>/requests.jsonl         that run's requests (`file` relative to <run>/); requests.partial.jsonl while running
DIR/<run>/summary.json           that run's numbers + the full config of the invocation that made it
DIR/requests.jsonl               every request of every run (`file` relative to DIR)
DIR/summary.csv|md|json          one row per run; summary.json also keeps every invocation's config
```

`results/` is gitignored. **The audio is AI-generated: never publish it.** When scoring with
`server/eval/score_run.py`, point it at one phase or run folder at a time: a phase folder and its run folders both hold
a `requests.jsonl`, so a recursive search from `results/` would score every take twice.
