# higgs-gguf: Higgs TTS 3 weights as GGUF, loaded into vLLM-Omni

Experimental and self-contained. This folder converts `bosonai/higgs-tts-3-4b` (HF safetensors) to GGUF, holds the
converted weights, and has a harness that loads them into the stock vLLM-Omni 0.28 engine that higgs-studio runs
(`higgs-studio/engine/run_engine.sh`, used unchanged). Nothing outside this folder was modified: not higgs-studio,
not the engine venv, not the HF cache.

## Results (2026-10-09)

| question | answer |
|---|---|
| Does the conversion keep every tensor? | Yes. All 929 checkpoint tensors are kept. BF16 GGUF: bit-identical to the checkpoint. Q8_0 GGUF: 254 matrices quantised, relative RMS error median 0.39 %, max 0.60 % (`results/01_verify/`). |
| Does stock vLLM-Omni accept the GGUF? | **No.** vLLM 0.28 has no GGUF support at all; upstream removed the GGUF loader and GGUF quantisation. Pointing `engine.sh` at the GGUF dir fails with `Cannot find any model weights`, and `load_format: gguf` fails with ``Load format `gguf` is not supported`` (`results/03_stock_vllm_omni/`). |
| Does it load through the harness? | **Yes, both files.** The engine is healthy 40 s after launch (weights load in 6-7 s) and serves 26/26 voice-clone takes each, including an 8-way concurrent burst (`results/04_harness/`). |
| Is the BF16 GGUF really the same model? | Yes. The 10 sequential fixed-seed takes are **byte-identical WAVs** to the production engine on the original safetensors (`results/02_baseline_safetensors/`). |
| Q8_0 quality | No difference measurable at this sample size. On Urdu, WER was 8.6 % for Q8_0 vs 8.6 % for production and 6.5 % for BF16; on English, 0 % for both GGUFs (table below). |
| Does it save VRAM? | **No.** vLLM 0.28 has no GGML kernels, so the harness dequantises to bf16 at load. On the GPU the model is the same 7.61 GiB and stage 0 still takes 17.4 GiB. GGUF saves disk only (8.5 GB → 4.7 GB for Q8_0). |

## Quality (Whisper large-v3 WER, 26 takes per condition)

Same texts, same reference (callagent, 27 s Urdu), 2 runs x (5 sequential + 8 concurrent) per condition, scored on
CPU with `tts-reference-voices/server/eval/score_run.py` (manifest mode, no SIM). Tags were stripped from the
reference text.

| condition | lang | takes | corpus WER | mean CER | mean WER | takes WER>0.3 | `bad` (QC) | mean audio s |
|---|---|---|---|---|---|---|---|---|
| gguf_bf16 | all | 26 | 0.047 | 0.021 | 0.051 | 0 | 0 | 6.12 |
| gguf_q8_0 | all | 26 | 0.062 | 0.027 | 0.065 | 0 | 1 | 6.35 |
| safetensors | all | 26 | 0.110 | 0.073 | 0.121 | 3 | 3 | 8.35 |
| gguf_bf16 | en | 8 | 0.000 | 0.000 | 0.000 | 0 | 0 | 5.33 |
| gguf_q8_0 | en | 8 | 0.000 | 0.000 | 0.000 | 0 | 0 | 5.12 |
| safetensors | en | 8 | 0.172 | 0.132 | 0.172 | 2 | 2 | 11.56 |
| gguf_bf16 | ur | 18 | 0.065 | 0.031 | 0.074 | 0 | 0 | 6.47 |
| gguf_q8_0 | ur | 18 | 0.086 | 0.039 | 0.093 | 0 | 1 | 6.90 |
| safetensors | ur | 18 | 0.086 | 0.047 | 0.099 | 1 | 1 | 6.93 |

Read this as "no regression visible", not as a ranking. The production row is worse only because of sampling
luck: one concurrent take ran on to 58 s, and Higgs does that now and then on any weights. Sampling is not
reproducible under batching, so 26 takes cannot separate conditions within a few WER points. A real Q8_0
quality verdict needs a few hundred takes (`bench/bench_tts.py` as in the Higgs benchmark) and a native-speaker listen.

## Layout

```
higgs_gguf/            shared package
  names.py             checkpoint name <-> GGUF name (llama.cpp names for the Qwen3 backbone: token_embd, blk.N.attn_q,
                       ffn_gate, ...; audio_embd / audio_head; the codec under codec.* abbreviated to fit 63 bytes)
  quant.py             per-tensor GGML type policy
  reader.py            GGUF -> checkpoint-named torch tensors (Q8_0 torch fast path, gguf-py for other types)
  vllm_loader.py       vLLM model loader `higgs_gguf`
harness/sitecustomize.py   registers `higgs_gguf` in every vLLM process (inert unless HIGGS_GGUF_HARNESS=1)
deploy/higgs_gguf_3090_32.yaml       production profile (higgs_3090_32.yaml) + `load_format: higgs_gguf` per stage
deploy/stock_load_format_gguf.yaml   production profile + vLLM's own `load_format: gguf` (rejection test only)
scripts/
  convert_higgs_to_gguf.py   safetensors -> GGUF (bf16 | q8_0 | q5_1 | q5_0 | q4_1 | q4_0)
  verify_gguf.py             tensor-by-tensor check against the checkpoint
  gguf_model_dir.py          re-create config/tokenizer files from a lone .gguf (they are embedded in its metadata)
  run_gguf_engine.sh         start the engine on a GGUF via higgs-studio's run_engine.sh + the harness (port 8096)
  test_stock_vllm_omni.sh    does unmodified vLLM-Omni accept the GGUF? (records how it fails)
  run_load_test.sh           start on a GGUF, record loader lines + VRAM, run smoke_tts.py twice, stop
  smoke_tts.py               fixed-seed voice-clone takes (5 sequential + 8 concurrent), WAVs + numbers
  summarise_quality.py       WER table from results/05_quality/scores.jsonl
weights/higgs-tts-3-4b-BF16/   model.gguf (7.9 GiB) + config/tokenizer files + conversion.json
weights/higgs-tts-3-4b-Q8_0/   model.gguf (4.4 GiB) + config/tokenizer files + conversion.json
results/                       one folder per experiment; every take's WAV is kept
```

Every Python script runs on the engine venv's interpreter, which already has `gguf` 0.19, torch and safetensors:
`PY=../tts-reference-voices/server/venvs/engine/bin/python`.

## Usage

```bash
PY=../tts-reference-voices/server/venvs/engine/bin/python
$PY -I scripts/convert_higgs_to_gguf.py --outtype q8_0            # -> weights/higgs-tts-3-4b-Q8_0/
$PY -I scripts/verify_gguf.py weights/higgs-tts-3-4b-Q8_0/model.gguf

# the engine needs the whole GPU: take production down for the test, bring it back afterwards
systemctl --user stop higgs-engine-watchdog.timer higgs-engine
scripts/run_gguf_engine.sh weights/higgs-tts-3-4b-Q8_0            # serves the same API on 127.0.0.1:8096
#   or: scripts/run_load_test.sh weights/higgs-tts-3-4b-Q8_0 04_harness/q8_0
systemctl --user start higgs-engine higgs-engine-watchdog.timer
```

## How the harness works

1. **Loader.** `higgs_gguf.vllm_loader.HiggsGGUFModelLoader` is a vLLM `BaseModelLoader`. It reads the GGUF,
   dequantises each tensor to the model dtype (bf16), renames it to its checkpoint name using the map stored in the
   file, and streams it into the model's own `load_weights`. The Higgs model code, the API server and the deploy
   settings stay stock. Stage 1 (Code2Wav) only gets the 528 codec tensors, so it does not dequantise the 4B backbone.
   If any parameter is left uninitialised, the loader raises an error.
2. **Registration.** vLLM-Omni spawns the API server and each stage as fresh processes, so the loader must be
   registered in each one. `harness/sitecustomize.py` is put on `PYTHONPATH` by `run_gguf_engine.sh`. It is gated
   by `HIGGS_GGUF_HARNESS=1` and calls `register_model_loader("higgs_gguf")` right after
   `vllm.model_executor.model_loader` is imported. Nothing is installed into the shared engine venv.
3. **Model dir.** `config.json`, `tokenizer.json`, `tokenizer_config.json` and `chat_template.jinja` sit next to
   `model.gguf`. They are also embedded in the GGUF metadata (`higgs.hf.*`), so a lone `.gguf` can be turned back
   into a model dir with `gguf_model_dir.py`. `run_gguf_engine.sh` refuses a dir that also contains safetensors, so
   a test can never silently load the original weights.

## GGUF format notes

- `general.architecture = higgs-tts3`, with llama.cpp-style hyper-parameter keys (`higgs-tts3.block_count`,
  `.embedding_length`, `.attention.head_count_kv`, `.rope.freq_base`, ...) and `general.file_type`.
- Tensor map: `higgs.tensor_map.gguf` / `higgs.tensor_map.hf`, two aligned string arrays. Readers use this map
  rather than re-deriving the abbreviations.
- Tied heads: in this checkpoint, `tied.head.text_head.weight` and `tied.head.modality_heads.0.weight` are
  bit-identical copies of the text and audio embeddings. They are stored once and listed in `higgs.alias.hf` /
  `higgs.alias.src`, and the reader re-emits them, which saves 0.8 GB. (Boson's `model.safetensors.index.json`
  leaves both heads out, but the safetensors file contains them, and vLLM reads the file. The converter therefore
  reads the file's keys, not the index.)
- Quantisation policy (`--outtype q8_0`): the 252 block projections plus `token_embd` use Q8_0.
  `audio_embd` / `audio_head` stay BF16 (use `--quantize-audio` for Q8_0), the codec stays BF16, and 1-D tensors
  are F32. For 4/5-bit outtypes, `token_embd` stays Q8_0. gguf-py can only quantise Q8_0/Q5_x/Q4_x (no k-quants);
  `llama-quantize` from llama.cpp could make Q4_K etc., and the reader loads any type gguf-py can dequantise.
- **llama.cpp itself cannot run this file.** The `higgs-tts3` architecture (Qwen3 backbone + 8-codebook audio
  head with a delay pattern + codec decoder) is not implemented in llama.cpp. The backbone tensors follow
  llama.cpp's naming, so a future ggml port could use them directly.

## Caveats

- **Licence:** Boson's research / non-commercial licence applies to these converted files exactly as it does to
  the originals (recorded in `general.license`).
- **No VRAM saving** in vLLM 0.28 (see above). Getting one would mean GGML dequant-matmul kernels in vLLM, i.e. the
  out-of-tree GGUF plugin that upstream moved GGUF support to. That plugin does not know this architecture either.
- Disk: about 7.5 GB was free after converting, so only the BF16 and Q8_0 files exist. `--outtype q5_0` etc. work
  but were not run.
