# server/eval: quality evaluation of Qwen3-TTS takes

Offline scoring of benchmark runs (WER / CER, speaker similarity, loop / skip / silence detectors, pace), the retry
policy study, calibration on the real reference clips, and the environment the QC sidecar (`server/qc`, package
`tts_qc`) shares. Every metric and verdict comes from one implementation, `server/qc/tts_qc`; the scripts here only
feed it files. Research behind the choices: `server/docs/research/eval-tooling.md` (31 findings).

Never publish generated audio. Score files hold transcripts and numbers only; they are written next to the run they
score (`results/.../scores.jsonl`), and `results/` is gitignored.

## Environment

One venv, `server/venvs/eval` (Python 3.12.6, pinned in `requirements-eval.txt`): torch 2.13.0 (CUDA 13.0 build),
transformers 5.17.0, faster-whisper 1.2.1, ctranslate2 4.8.2, jiwer 4.0.0, PyAV 18.1, soundfile, fastapi, uvicorn,
pytest, and nvidia-cublas-cu12 12.9.2.10 (+ nvidia-cuda-nvrtc-cu12, its dependency). Installed with uv hardlinks from
the uv cache. Always run through `run.sh`:

```bash
eval/run.sh <script.py | -m module> [args]     # venv python + LD_LIBRARY_PATH=<venv>/nvidia/cublas/lib + PYTHONPATH=server/qc
```

Why one venv and not two (ASR / SIM, as the research suggested): the sidecar must run Whisper and WavLM in one
process, in one CUDA context, on one decoded copy of each take (one HTTP call, one health check, no IPC). The only
conflict is the cuBLAS major version: torch cu130 links `libcublas.so.13` (from `nvidia/cu13/lib`, found by torch
itself), while ctranslate2 4.8.2 dlopens `libcublas.so.12` by soname and adds no search path on Linux. Different
sonames with versioned symbols (`cublasCreate_v2@@libcublas.so.12` / `@@libcublas.so.13`) coexist in one process.
Checked on CPU: both libraries `ctypes.CDLL`-loaded together, torch and ctranslate2 imported with the path set, both
mapped in `/proc/self/maps` (12.9.2 and 13.1.1). ctranslate2 resolves only 9 cuBLAS symbols (`cublasCreate_v2`,
`cublasDestroy_v2`, `cublasGemmEx`, `cublasGemmStridedBatchedEx`, `cublasGetMathMode`, `cublasGetProperty`,
`cublasSetStream_v2`, `cublasSgemmStridedBatched`, `cublasSgemm_v2`). Ubuntu's `libcublas12` package
(`/usr/lib/x86_64-linux-gnu/libcublas.so.12.2.5.6`, on the default loader path) exports all 9 too, so it is the
automatic fallback when the wheel is absent. The wheel keeps the venv self-contained and on the cuBLAS 12 line
ctranslate2's docs name. The GPU execution of both in one process is what `gpu_check.py` verifies (pending: the GPU
was busy with the engine while this was built).

Rebuild: see the header of `requirements-eval.txt`. Disk: the venv is ~5.0 GB counted on its own (hardlinked with
`~/.cache/uv`, so the cuBLAS 12 addition cost 1.13 GB of free space); the models 4.5 GB.

## Models (`server/models/eval`, gitignored; `fetch_models.py` downloads and verifies)

| dir | source (pinned revision) | sha256 | role |
|---|---|---|---|
| `faster-whisper-large-v3` | Systran/faster-whisper-large-v3 @ edaa852e (stock openai/whisper-large-v3 in CTranslate2) | `model.bin` 69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1 | ASR |
| `wavlm-base-plus-sv` | microsoft/wavlm-base-plus-sv @ feb593a6 | `pytorch_model.bin` e906bce2fa42fb497a1d1a9ecf81548adb7e03b12a5644e32d2f42f0d6500fad | SIM, Kaggle scale; the sidecar's default |
| `beatrice` | prj-beatrice/unispeech-wavlm-large-ecapa-tdnn-torch-native @ 13ad4fcc (seed-tts-eval WavLM-Large + ECAPA-TDNN) | `model.safetensors` 559b87088828b5f1bc5762d9746c08ef00ba4e5141b6897bebce1b77a58ae2b7 | SIM, seed-tts scale; primary offline |

`models/eval/SHA256SUMS` (`sha256sum -c`), `MANIFEST.json`; log `server/logs/eval_fetch_models.log` (all OK).
Never a Punjabi fine-tune: evals use stock Whisper large-v3.

## Scripts

| script | what |
|---|---|
| `score_run.py` | score bench result dirs -> `scores.jsonl`, `scores_summary.json`, `scores_summary.md` next to each `requests.jsonl` (resumable, multi-worker, `--rejudge` for new thresholds without models); `--manifest` for clip lists |
| `retry_sim.py` | retry-policy table (retry R = 0..3, best-of-N) with prompt-bootstrap CIs from K takes per prompt -> `retry_sim.json` / `.md` next to `scores.jsonl`; `--combine DIR` pairs settings by prompt |
| `takes.py` | how rows group into settings / prompts / takes (no seeds) and map engine voice names to repo voices |
| `sim_eval.py` | SIM calibration on the reference clips, both models -> `calibration/sim_calibration_<device>.json` |
| `make_synth.py` | rebuild the synthetic failure clips (`lab/synth/`, gitignored) and `calibration/*_manifest.jsonl` |
| `calibration_report.py` | ours vs the research's recorded numbers; synthetic-failure detection -> `calibration/summary_<tag>.json` |
| `gpu_check.py` | ASR fp16 + WavLM on the GPU in one process: timings, memory, loaded cuBLAS -> `calibration/gpu_check_<device>.json` |
| `qc_latency.py` | per-call latency of a running sidecar -> JSON |
| `fetch_models.py` | download + sha256-verify the models |
| `stats.py` | Wilson CI, bootstrap, describe (shared) |
| `lab/` | the research's original scripts and CPU calibration records (superseded by the above; kept as the record) |

### Scoring a benchmark phase

Takes are unseeded: on vLLM-Omni 0.28 a seed does not reproduce a take, so K takes of a prompt are K independent
requests (bench rows `take` 0..K-1, `seed` null) and settings pair by prompt. Grouping (`takes.py`): a setting is a
bench run + the voice as the engine knows it (`trump-avg` and `trump-prompt` are different settings); a prompt is the
repo voice + prompt id (else pool text index, else a hash of the text). Engine voice names (`<id>-avg`,
`<id>-prompt`, content-addressed `<id>-<sha10>`) are scored against `voices/<id>` (SIM references, pace, language).

```bash
# 1. generate K takes per prompt (bench_tts.py, no --seed)
python bench/bench_tts.py --voice shehbaz --size prompts --takes 6 -c 8 --tag P5_rp110 ...
# 2. score (GPU when free; add CUDA_VISIBLE_DEVICES= ... --device cpu --workers 1 otherwise)
server/eval/run.sh server/eval/score_run.py results/P5_rp110 --device cuda --workers 4
# 3. retry policy, per run and paired across settings (by prompt)
server/eval/run.sh server/eval/retry_sim.py results/P5_rp110
server/eval/run.sh server/eval/retry_sim.py results/P5_rp1* --combine results/P5_retry --baseline rp105
# re-judge after changing thresholds (no models, seconds):
server/eval/run.sh server/eval/score_run.py results/P5_rp110 --rejudge --thresholds my_thresholds.json
```

`score_run.py` options: `--device cuda|cpu`, `--workers N` (parallel takes = CTranslate2 workers sharing one copy of
the weights), `--cpu-threads`, `--asr-compute float16|int8_float16|int8`, `--beam 5`, `--sim large,base`,
`--gate-sim base` (production's model), `--bad-sim large`, `--setting run|tag|params|dir` (summary groups, always
split by voice), `--no-asr`, `--no-pace`, `--lid` (also store Whisper's
p(ur)/p(hi)/p(en)), `--limit`, `--force`, `--rejudge`, `--thresholds '{"gate": {...}, "bad": {...}}'` (JSON file).

ASR settings (fixed, part of the metric): faster-whisper large-v3, float16 on GPU / int8 on CPU, beam 5, language
forced to `en` / `ur`, `condition_on_previous_text=False`, `vad_filter=False`, `word_timestamps=True`, sequential
long-form decoding, default temperature fallback. Audio reaches Whisper through the same PyAV resampler as
`faster_whisper.decode_audio` (tested equal), whether it comes from a WAV file or the sidecar's PCM.

Text normalization: English uses Whisper's `EnglishTextNormalizer` (vendored, `tts_qc/whisper_normalizers`) on both
sides; Urdu uses `tts_qc.textnorm.UrduNormalizer` (NFKC, hamza/yeh/kaf/heh folding, digits, no diacritics,
punctuation -> space). Not Whisper's BasicTextNormalizer, which splits Urdu words at diacritics.

## Metrics and verdicts

Per take (`tts_qc/scorer.py`; letters = `str.isalnum` count, as in the gateway and `calibration/pace.json`):

| metric | definition |
|---|---|
| `wer`, `cer` | word / character error rate of the normalized transcript vs the normalized input (jiwer 4) |
| `cer_nospace` | CER with all spaces removed: Urdu word segmentation varies (صورتحال / صورت حال) |
| `char_ratio` | transcript letters / input letters (normalized): < 1 skipped text, > 1 loop or filler |
| `del_run`, `ins_run` | longest run of consecutive deleted / inserted words in the alignment |
| `repeat_excess` | max over n-grams (n = 1..4) of (count in transcript - count in input) x n |
| `token_run`, `char_runs` | longest run of one repeated word; letters repeated >= 4 times ('آآآآ'); each vs the input's own |
| `max_word_s`, `max_word_voiced` | longest word timestamp and its voiced share (a loop the ASR swallowed into one word) |
| `max_gap_s`, `max_gap_voiced` | longest stretch before / between words that no word covers, and its voiced share (a loop the ASR skipped) |
| `unaligned_tail_s` | audio after the last ASR word |
| `seg_max_cr` | largest Whisper segment compression ratio (zlib on UTF-8 bytes; Urdu runs higher than English) |
| `script_arabic` | Arabic-script share of the transcript's letters (`_ref`: of the input) |
| `lead_sil_s`, `trail_sil_s`, `max_internal_sil_s`, `speech_ratio` | energy VAD, 20 ms frames, speech = RMS above max(-60 dBFS, p95 - 35 dB) |
| `pace_ratio` | (duration / input letters) / the voice's expected s/letter (`server/calibration/pace.json`: trump 0.0795, shehbaz 0.088) |
| `sim_prompt_<m>` | cosine(take, `voices/<id>/references/qwen3-tts.wav`) with model m = `large` (WavLM-Large+ECAPA) or `base` (wavlm-base-plus-sv); both 16 kHz, leading / trailing silence trimmed |
| `sim_heldout_<m>` | cosine(take, centroid of the voice's clips not in the prompt): shehbaz 02-06; none for trump (his one clip is the prompt) |
| `sim_speech_s` | seconds embedded (after the trim): SIM verdicts use duration buckets |

Verdicts (`tts_qc/policy.py`; reason codes `<metric><op><threshold>`):

- **gate**: what production computes per non-streaming take (gateway pace band + sidecar checks), SIM model `base`.
  A failing take is retried (fresh sampling; seeds do not reproduce on vLLM-Omni 0.28).
- **bad**: an offline label for evaluating the gate and the retry policy: stricter thresholds, the *other* SIM model
  (`large`, plus the held-out centroid) and two extra detectors. It shares the ASR with the gate, so it is a proxy;
  human labels (`retry_sim.py --labels`) are the real oracle.

| check | gate (online) | bad (offline) | basis |
|---|---|---|---|
| Urdu `cer_nospace` | > 0.15 | > 0.10 | real clips corpus 2-4 %, worst clip ~9 % |
| English `wer` | > 0.20 | > 0.10 | Kaggle good takes < 1 %; NOTES re-roll rule 0.22 |
| `char_ratio` | < 0.85 or > 1.15 | < 0.90 or > 1.10 | research proposal |
| `del_run` | >= 4 (ur), >= 3 (en) | >= 3 | research proposal |
| `ins_run` / `repeat_excess` | >= 4 / >= 4 | >= 3 / >= 3 | research proposal |
| `token_run` / `char_run` (beyond input) | >= 3 / >= 1 | same | research proposal |
| `long_word` | > 2.5 s and > 80 % voiced | > 2.0 s | real 1.0-2.2 s; Urdu loops 4.9-5.5 s at 98-99 % |
| `word_gap` | > 2.0 s and > 50 % voiced | > 1.5 s | real: voiced gaps <= 0.68 s, one 2.52 s joint pause at 36 %; English 3 x 3 s loop 9.0 s at 97 % |
| `unaligned_tail` | > 3 s | > 2 s | real 0.09-0.49 s; 6 s tails 6.4 s |
| `pause` (internal silence) | > 2.0 s | same | real <= 1.5 s |
| `trail_sil` / `lead_sil` | > 1.5 s / > 1.0 s | same | research proposal |
| `speech_ratio` | < 0.6 | same | research proposal |
| `pace` | < 0.6 or > 1.8 (= gateway `TTS_SUSPECT_BAND`) | < 0.7 or > 1.5 | pace.json |
| SIM (`sim_prompt`) | base: < 0.88 (>= 5 s), < 0.85 (2-5 s) | large: < 0.50 (>= 5 s), < 0.40 (2-5 s), also held-out | calibration below |
| SIM under 2 s of speech | no verdict | no verdict | a 2 s crop loses ~0.2 (large) |
| `cr` (compression ratio) | - | > 2.4 | Whisper's own threshold; real Urdu <= 1.8, loops 14-18 |
| `script_drift` (Urdu) | - | Arabic share > 10 points below the input's | Hindi/Urdu LID confusion |

Every threshold is a starting point from the research (findings 17, 21, 26) and the Kaggle notes. Recalibrate on the
first scored batch of good takes (about their 1st percentile), then `--rejudge`. Sidecar overrides:
`TTS_QC_<FIELD>` (e.g. `TTS_QC_CER_NOSPACE_UR=0.12`).

Summaries (`scores_summary.json`, per bench run and `ALL`): means / medians / p10 / p90 of every metric, corpus WER /
CER / CER-nospace (total edits / total reference length), gate-fail and bad rates with 95 % Wilson CIs, the bad
rate of first takes (no guardrail) and of gate-passing takes (guardrail with unlimited retries), gate recall /
precision / false-reject rate against `bad`, reason counts, and a per-prompt table. `retry_sim.py` adds the bad rate
after R = 0..3 retries and best-of-N with prompt-bootstrap CIs, attempts and extra compute.

## Calibration (CPU)

All on this box's CPU (int8 Whisper, fp32 WavLM, 8 threads) on 2026-09-25 while the TTS engine was running, so the
speeds are pessimistic. Files in `calibration/` (small, committable; no audio). Research values in brackets
(eval-tooling.md, measured 2026-09-24 with torchaudio resampling; `lab/*.jsonl`).

**Real clips** (`refs_cpu_int8.scores.jsonl`, `--no-pace` since human clips are not TTS output; 8 shehbaz clips, the
2 prompt references, trump_01): all 11 pass the gate and none is `bad`.

- Urdu, 8 shehbaz clips, corpus: WER 12.4 %, CER 3.38 %, **CER-nospace 3.66 %** [13.1 / 3.5 / 3.8 %]; per clip WER
  0-28.6 %, CER-nospace 0-8.6 % (shehbaz_07). The one difference: shehbaz_02 now comes back exact (research: نہائیت
  for نہایت). The shehbaz prompt reference (qwen3-tts.wav): WER 13.2 %, CER-nospace 5.2 %.
- English trump_01: WER 1.7 %, CER-nospace 0.35 %; trump prompt reference WER 0.
- Whisper LID p(ur) on the Urdu clips 0.745-0.996 [0.718-0.996], p(hi) up to 0.10 (shehbaz_07).
- Detector ranges over the 11 clips (the margins under the thresholds): longest internal pause 0.02-1.50 s (1.48 s
  shehbaz_08, 1.50 s shehbaz prompt), leading silence <= 0.04 s, trailing <= 0.08 s, speech ratio 0.71-0.99, longest
  word 1.0-2.22 s, longest inter-word gap 0.68 s at 85 % voiced (trump prompt) / 2.52 s at 36 % voiced (a joint pause in the
  shehbaz prompt), unaligned tail 0.09-0.49 s, compression ratio 1.17-1.79, char ratio 0.966-1.004, deletion /
  insertion run <= 1, repeat excess <= 1.

**Synthetic failures** (`synth_cpu_int8.scores.jsonl`, `make_synth.py`): 8/8 fail the gate, each with its expected
reason(s):

| case | gate reasons | key numbers [research] |
|---|---|---|
| ur_trail_silence6s | trail_sil>1.5, unaligned_tail>3 | trailing 6.0 s, tail 6.42 s [6.0, 6.43] |
| ur_trail_noise6s | unaligned_tail>3 | tail 6.42 s [6.43]; the -50 dBFS noise counts as voiced |
| ur_syllable_loop12 | long_word>2.5 | transcript unchanged (CER-ns 1.5 %); longest word 4.64 s, 100 % voiced [5.52 s, 99 %] |
| ur_phrase_loop3 | long_word>2.5 | transcript unchanged; longest word 4.86 s, 99 % voiced [4.90 s, 98 %] |
| ur_truncated60 | cer_nospace>0.15, char_ratio<0.85, del_run>=4 | CER-ns 0.385, char ratio 0.646, deletion run 7 [same] |
| ur_gap4s | pause>2 | pause 4.06 s; longest word 5.24 s but 23 % voiced, so not a loop [3.98 s; 5.24 s, 26 %] |
| en_phrase_loop3 | word_gap>2 | transcript unchanged (WER 0), a 9.04 s gap between two words, 97 % voiced [research splice: WER 0.35, insertion run 21] |
| en_truncated70 | wer>0.2, char_ratio<0.85, del_run>=3 | WER 0.367, char ratio 0.66, deletion run 21 [same] |

So Whisper can hide a loop in English too, not only in Urdu: depending on the splice it writes the repeats out
(research), or it skips them and leaves a voiced hole in the word timestamps (here). `word_gap` covers the latter;
`long_word` covers Urdu, where the ASR stretches one word over the loop instead.

**Speaker similarity** (`sim_calibration_cpu.json`, `sim_eval.py`):

| | WavLM-Large+ECAPA (`large`) | wavlm-base-plus-sv (`base`) |
|---|---|---|
| shehbaz held-out clips (02-06) vs prompt | 0.896-0.940 [0.896-0.939] | 0.977-0.991 |
| shehbaz in-prompt clips (01, 07, 08) vs prompt | 0.869-0.948 | 0.975-0.993 |
| held-out leave-one-out vs held-out centroid | 0.926-0.951 [0.927-0.951] | 0.986-0.994 |
| prompt vs held-out centroid | 0.952 [0.952] | 0.992 |
| trump half vs half | 0.907 [0.908] | 0.993 [0.994] |
| cross-speaker (trump vs shehbaz) | 0.102-0.175 [0.106-0.182] | 0.746-0.798 [0.746-0.799] |
| shehbaz_02 first 2 / 3 / 5 s / full vs prompt | 0.674 / 0.730 / 0.804 / 0.901 [0.676 / 0.733 / 0.807 / 0.903] | 0.950 / 0.951 / 0.970 / 0.984 [2 s: 0.951] |
| gap: lowest same-speaker minus highest cross-speaker | 0.694 | 0.177 |
| speed (8 threads, shared CPU) | 7.2 x realtime [15] | 21.4 x realtime [37.8] |

Same-speaker real audio sits far above the gate thresholds (large 0.50, base 0.88) and cross-speaker far below, but
TTS output scores lower than same-session real audio (seed-tts human ground truth 0.73 on large; Qwen3-TTS reports
0.775 English), so the SIM thresholds must be recalibrated on real takes before they are trusted. base's range is
compressed: its 0.177 same-vs-cross gap is a quarter of large's.

**Sidecar latency on CPU** (`qc_latency_cpu_ur10s.json`; sidecar over HTTP, int8 Whisper + base SIM, 1 CT2 worker
x 8 threads, shared CPU): 10.21 s Urdu clip, 5 calls after 1 warm-up: wall p50 5.61 s (mean 5.37, 4.19-6.36 s);
server ASR 5.29 s (median), SIM 0.35 s, audio checks 4 ms. A 10.0 s English crop (`qc_latency_cpu_en10s.json`):
wall p50 7.40 s (ASR 6.94 s, SIM 0.46 s). About 0.5-0.7 s per second of audio: too slow for online QC at production
concurrency on CPU. GPU fp16 numbers are pending `gpu_check.py` / `qc_latency.py` on the GPU.

**One process, CPU** (`gpu_check_cpu.json`): torch cu130 + ctranslate2 import together, both cuBLAS libraries mapped
(`libcublas.so.12` 12.9.2 from the venv wheel, `libcublas.so.13` 13.1.1 from torch); models load in 23.7 s (Whisper
2.5 s; base 1.4 s + references 5.6 s; large 0.1 s + references 14.1 s); one 10.21 s clip with both SIM models scored
in 8.0-8.8 s (ASR 6.3-7.0 s, SIM 1.7-1.8 s).

Rebuild everything here (CPU, ~8 min):

```bash
export CUDA_VISIBLE_DEVICES=
eval/run.sh eval/make_synth.py
eval/run.sh eval/score_run.py --manifest eval/calibration/refs_manifest.jsonl --out eval/calibration/refs_cpu_int8.scores.jsonl --device cpu --workers 1 --no-pace --lid --force
eval/run.sh eval/score_run.py --manifest eval/calibration/synth_manifest.jsonl --out eval/calibration/synth_cpu_int8.scores.jsonl --device cpu --workers 1 --no-pace --force
eval/run.sh eval/sim_eval.py --device cpu
eval/run.sh eval/calibration_report.py
eval/run.sh eval/gpu_check.py --device cpu --workers 1
```

On the GPU (when it is free): `eval/run.sh eval/gpu_check.py` (writes `calibration/gpu_check_cuda.json`), then the
same score_run / sim_eval commands with `--device cuda` and `--out` / tag `cuda_fp16` for the fp16-vs-int8 check.
