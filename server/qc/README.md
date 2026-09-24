# tts_qc: quality-check sidecar for Qwen3-TTS takes

A small FastAPI service next to the gateway. For each non-streaming take the gateway posts the PCM and the input
text; the sidecar runs Whisper large-v3 (ASR), WavLM speaker similarity and waveform checks, and answers pass/fail
with reason codes. The gateway retries a failing take (fresh sampling) and keeps the best take
(`server/gateway/tts_gateway/quality.py`). QC is advisory: when the sidecar is down or slow the gateway keeps the take
(fail open).

The same code scores benchmark runs offline (`server/eval/score_run.py`), so production verdicts and offline numbers
come from one implementation. Metric definitions, thresholds and calibration: `server/eval/README.md` and
`tts_qc/policy.py`.

## Run

```bash
cd server/qc
../eval/run.sh -m tts_qc                                   # 127.0.0.1:8092, cuda, Whisper fp16 + wavlm-base-plus-sv
TTS_QC_DEVICE=cpu ../eval/run.sh -m tts_qc                 # CPU: Whisper int8 (~0.7 s per second of Urdu audio)
TTS_QC_ASR=0 ../eval/run.sh -m tts_qc                      # SIM + audio checks only (cheap)
```

`eval/run.sh` runs `venvs/eval/bin/python` with the venv's cuBLAS 12 on `LD_LIBRARY_PATH` (ctranslate2 needs
`libcublas.so.12`; torch brings its own `libcublas.so.13`) and `server/qc` on `PYTHONPATH`. Startup loads the models
and embeds every voice's references (prompt clip + held-out clips) in a worker thread; `/health` answers 503 until
then (CPU: ~25 s; the models are local, nothing is downloaded).

Gateway side: `TTS_QC_URL=http://127.0.0.1:8092` (optional `TTS_QC_CHECKS=asr,sim,audio`, `TTS_QC_TIMEOUT_S=30`).

## Configuration (environment)

| variable | default | meaning |
|---|---|---|
| `TTS_QC_HOST` / `TTS_QC_PORT` | `127.0.0.1` / `8092` | bind address |
| `TTS_QC_DEVICE` | `cuda` | `cuda` or `cpu` (both models) |
| `TTS_QC_DEVICE_INDEX` | `0` | GPU index (as the process sees it) |
| `TTS_QC_ASR` | `1` | Whisper checks on/off |
| `TTS_QC_SIM` | `1` | speaker similarity on/off |
| `TTS_QC_ASR_COMPUTE` | `float16` (cuda) / `int8` (cpu) | CTranslate2 compute type (`float16`, `int8_float16`, `int8`) |
| `TTS_QC_BEAM` | `5` | beam size |
| `TTS_QC_WORKERS` | `2` | CTranslate2 workers (replicas sharing one copy of the weights) |
| `TTS_QC_CPU_THREADS` | `8` | threads per CT2 worker and for torch, on CPU |
| `TTS_QC_SIM_MODEL` | `base` | `base` = microsoft/wavlm-base-plus-sv (the Kaggle 0.97 scale, cheap); `large` = WavLM-Large+ECAPA (seed-tts scale) |
| `TTS_QC_VOICES_DIR` | `<repo>/voices` | voices/<id>/references/{qwen3-tts.wav,references.json}, clips, voice.json |
| `TTS_QC_MODELS_DIR` | `server/models/eval` | from `server/eval/fetch_models.py` (sha256-verified) |
| `TTS_QC_PACE_FILE` | `server/calibration/pace.json` | expected s/letter per voice (shared with the gateway and bench) |
| `TTS_QC_MAX_SECONDS` | `300` | longest take accepted |
| `TTS_QC_LOG_LEVEL` / `TTS_QC_TZ` | `INFO` / `Asia/Karachi` | JSON log lines on stdout, local-time ISO timestamps with offset |
| `TTS_QC_<THRESHOLD>` | see `policy.GATE` | any gate threshold, e.g. `TTS_QC_CER_NOSPACE_UR=0.12`, `TTS_QC_SIM_LONG_BASE=0.9`, `TTS_QC_PAUSE_S=2.5` |

## API

`GET /health` -> `200 {"status": "ok", "asr": true, "sim": true, "device": "cuda", "sim_model": "base", "voices": [...],
"version": "0.1.0"}` once loaded; `503 {"status": "loading" | "error", "error": ..., "device": ...}` before (or if
loading failed).

`POST /v1/qc`

```json
{"request_id": "abc", "voice": "shehbaz", "lang": "ur", "text": "...", "sample_rate": 24000,
 "pcm_b64": "<base64 PCM16 LE mono>", "checks": ["asr", "sim", "audio"]}
```

- `voice`: a repo voice id, or `""` for an inline reference (SIM and the pace check are skipped). Engine variants
  (`trump-avg`, `shehbaz-prompt`, content-addressed `<id>-<sha10>`) are judged against `voices/<id>`.
- `lang`: `en` | `ur` | `und` (`und`: no ASR checks, since there is no normalizer or forced language for it).
- `checks`: optional subset; default = every check this server has enabled (`TTS_QC_ASR`, `TTS_QC_SIM`).

-> `200 {"pass": bool, "reasons": [str], "metrics": {...}, "ms": {"asr", "sim", "audio", "total"}}`;
`400` bad input (validation, base64, odd byte count, empty, longer than `TTS_QC_MAX_SECONDS`), `404` unknown voice,
`503` still loading, `500` scoring error (the gateway treats every non-200 as a QC error and keeps the take).

`reasons` are `<metric><op><threshold>` codes: `cer_nospace>0.15`, `wer>0.2`, `char_ratio<0.85`, `char_ratio>1.15`,
`del_run>=4` (en: `>=3`), `ins_run>=4`, `repeat_excess>=4`, `token_run>=3`, `char_run>=1`, `long_word>2.5`,
`word_gap>2`, `unaligned_tail>3`, `pause>2`, `lead_sil>1`, `trail_sil>1.5`, `speech_ratio<0.6`, `no_speech`, `pace<0.6`,
`pace>1.8`, `sim<0.88` (the threshold shown is the one applied). `metrics` holds every number behind them
(`asr_text`, `wer`, `cer`, `cer_nospace`, `char_ratio`, `del_run`, ..., `sim_prompt_base`, `sim_heldout_base`,
`sim_speech_s`, `duration_s`, `lead_sil_s`, `trail_sil_s`, `max_internal_sil_s`, `speech_ratio`, `pace_ratio`, ...)
and `checks` (the checks actually run).

## Tests

```bash
cd server/qc
../eval/run.sh -m pytest -q tests -m 'not slow'   # decision logic, detectors, API contract (fake scorer): ~1 s
../eval/run.sh -m pytest -q tests                 # + the real models on CPU over HTTP: ~1 min
```

The tests force CPU (`CUDA_VISIBLE_DEVICES=""`) unless `TTS_QC_TEST_GPU=1`.
