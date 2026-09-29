# Experiment log

Machine for validation: `vector` (RTX 3090 24 GB shared with the production TTS service, which is paused for the
GPU stages). Full training runs are meant for a cloud GPU; the numbers here validate the pipeline, not a final model.

## V1: dataset derivation (2026-09-29)

`python -m qwen_train.derive` on the folders available here (the 300 h set is not compiled yet; same format):

| set | folders | speakers | kept | hours | dropped | eval / holdout |
|---|---|---|---|---|---|---|
| sample | audio_samples_dataset | 1 | 4,184 | 14.21 | 0 | 84 / – |
| f50 | female-data-50-hrs-preprocessed | 8 | 12,634 | 46.22 | 7 (not Urdu) | 237 / speaker-8 (820 utts, 2.94 h) |

Both are 22 kHz (sample: 74% stereo; f50: all stereo), 1.2-18.2 s per clip (p50 12.5-13.5 s), ~150-190 characters
per transcript. Only 3 of 14k transcripts contain digits; punctuation is Western "." "," with some "؟".
Note: in these folders the `speaker_name` column and the `wavs/speaker-N/` folder disagree (e.g. `wavs/speaker-5/`
labelled `@Speaker-1`); per the user, the column is the truth (`--speaker-from column`, the default).

## V2: audio QC (sample, 4,184 clips, `qwen_train.qc` audio measures, 3 s)

| measure | p10 | p50 | p90 | max |
|---|---|---|---|---|
| RMS dBFS | -27.2 | -20.3 | -14.6 | -10.7 |
| peak dBFS | -10.2 | -4.5 | -0.2 | 0.0 |
| clipped samples | 0 | 0 | 0 | 0.3% |
| leading silence s | 0 | 0 | 0.22 | 0.24 |
| trailing silence s | 0 | 0 | 0.16 | 0.24 |
| longest internal silence s | 0 | 0 | 0.42 | 0.48 |

Clean studio material: no clipping to speak of, no long pauses, tight edges. (Resampling to 24 kHz overshoots by up
to 2%, which prepare.py clips.)

## V3: transcript agreement (sample, Whisper large-v3, first 34 clips before the run OOMed next to production)

CER p10/p50/p90/max = 0.016 / 0.095 / 0.309 / 0.670, WER p50 0.233. Whisper's own error on correct transcripts of
accented Urdu is ~0.10, so the median is what a correct transcript looks like. The worst clip is a **label error**:
the transcript repeats a phrase ("تحصیل نصرتی میں چنا دال کے تحصیل نصرتی میں چنا دال کے لیے...") that the audio
says once. `qc --apply --max-cer 0.5` removes such rows. Full 300-clip run: see V8.

## V4: codec extraction (`qwen_train.prepare`, 12 Hz tokenizer + the model's speaker encoder, next to production)

| set | clips | time | rate | frames/s of audio | output |
|---|---|---|---|---|---|
| sample | 4,184 | 73 s | 57 clips/s | 12.54 | 37 MB (3 shards) |
| f50 | 12,634 | ~5 min | 36-70 clips/s (CPU contention) | 12.54 | 110 MB |

So the 300 h set (~100k clips) takes ~30-45 min on a 3090; the codes and x-vectors of 300 h are ~1 GB.

## V5: layout unit tests

`pytest -q tests` : 11 passed (layout positions for the x-vector, language-tag, instruct, ICL and streaming forms;
template slicing on Urdu text; collate padding; dataset reference pairing, epoch determinism, token-budget sampler).

## V6: alignment check on the pretrained model (`qwen_train.check_alignment`)

Teacher-forced next-frame prediction on real sample clips. "acc0" = top-1 accuracy of codebook 0 (2048-way),
"cp" = the code predictor on codebooks 1-15. CPU run, 4 clips (501 labels):

| variant | talker loss | acc0 | cp loss | cp acc (mean of 15) |
|---|---|---|---|---|
| our layout, x-vector only | 2.36 | **0.437** | 5.88 | 0.051 |
| our layout, in-context reference (another clip, same speaker) | 3.14 | 0.405 | 5.93 | 0.050 |
| our layout, streaming form, in-context | 3.15 | 0.413 | 5.96 | 0.051 |
| our layout, in-context + Urdu tag (row 2080, mean-initialised) | 3.15 | 0.411 | 5.93 | 0.050 |
| **official script's label shift** | 9.44 | 0.060 | 7.41 (= chance, ln 2048 = 7.62) | 0.012 |
| **official script's missing text projection** | 8.68 | 0.014 | 7.49 | 0.006 |
| copy test: in-context reference = the target itself | 2.35 | 0.583 | 4.47 | 0.165 |

The pretrained model predicts 41-44% of codebook-0 tokens exactly under our layout and 1-6% under the official
script's alignment (its code predictor is at chance level), so the official script trains something other than
what the model does at inference. The copy test shows the in-context reference is read (accuracy 0.41 → 0.58 when
the reference contains the answer). The 200-clip GPU run reproduces this (V7).

## V7: alignment check on the GPU, 200 clips (31,830 labelled positions, 7-11 s per variant)

| variant | talker loss | acc0 | cp loss | cp acc (mean / codebook 1) |
|---|---|---|---|---|
| our layout, x-vector only | 2.64 | **0.408** | 5.91 | 0.053 / 0.149 |
| our layout, in-context reference | 3.48 | 0.363 | 5.99 | 0.050 / 0.143 |
| our layout, streaming form, in-context | 3.52 | 0.356 | 6.02 | 0.049 / 0.138 |
| our layout, in-context + Urdu tag (row 2080) | 3.48 | 0.363 | 5.99 | 0.050 / 0.143 |
| official label shift | 9.21 | 0.056 | 7.33 | 0.015 / 0.036 |
| official missing text projection | 8.00 | 0.022 | 7.46 | 0.006 / 0.019 |
| copy test (reference = target) | 2.69 | 0.548 | 4.57 | 0.160 / 0.374 |

Verdict printed by the script: "layout matches inference". The Urdu tag row, initialised from the mean of the ten
language rows, changes nothing before training (identical to the Auto form to 3 decimals), which is the intended
neutral start.

## V8: smoke training (f50, full fine-tune, bf16 + Kahan AdamW, RTX 3090)

`configs/smoke.yaml` with `data_dir=data/f50`: 1,605.5M trainable of 1,928.7M parameters (speaker encoder and the
Qwen text embedding frozen), gradient checkpointing, ≤6,000 tokens per micro-batch (≈6 clips), accumulation 2.

| step | loss | talker | cp | acc0 | cp acc | grad norm | tok/s | peak VRAM |
|---|---|---|---|---|---|---|---|---|
| 5 | 4.09 | 2.50 | 5.32 | 0.453 | 0.094 | 18.6 | 2,036 | 18.8 GB |
| 15 | 3.62 | 2.09 | 5.10 | 0.429 | 0.102 | 16.8 | 2,082 | 19.1 GB |
| 30 | 3.26 | 1.75 | 5.02 | 0.500 | 0.107 | 11.1 | 2,043 | 19.4 GB |

Held-out (eval split, teacher-forced): step 15 talker 1.916 / acc0 0.473, step 30 talker 1.720 / acc0 0.506.
Checkpoint written as a model directory (3.4 GB) in 0.03 h. At ~2,040 tokens/s a 300 h epoch (~35M tokens with
references) is ~4.8 h on this card; an A100/H100 should be 3-5x faster. Memory leaves ~4 GB headroom on 24 GB.

## V9: transcript agreement, 300 clips (Whisper large-v3 fp16, beam 1, GPU)

CER p10/p50/p90/p95/max = 0.035 / 0.094 / 0.271 / 0.375 / 0.745; WER p50 0.239. 6 of 300 (2%) exceed CER 0.5
and 26 (8.7%) exceed 0.3. The >0.5 rows are label errors of the kind found in V3 (duplicated phrases, missing
sentences); `qc --apply --max-cer 0.5` removes them. Audio measures of the same 300 clips match V2.

## V10: serving check (vLLM-Omni 0.28.0, the production engine script, on the smoke checkpoint)

`bash serve_check.sh runs/smoke/latest 8093`: the exported directory (config with `"urdu": 2080` in
`codec_language_id`, `tts_model_type: base`, full weights incl. the speaker encoder, speech tokenizer linked) loaded
and was ready after 105 s (the same as the base model). Three Urdu and three English voice-clone requests with
inline reference clips, `non_streaming_mode=true`, all 200 OK:

| voice | n | ok | latency p50 / p90 | audio per request | x realtime | GPU |
|---|---|---|---|---|---|---|
| shehbaz (Urdu) | 3 | 3 | 0.60 / 1.46 s | 4.3 s | 5.1 | 19.3 GB |
| trump (English) | 3 | 3 | 0.80 / 1.17 s | 4.3 s | 5.1 | 19.3 GB |

Identical speed to the production model (REPORT §4). The first attempt failed because the export had skipped
`tokenizer_config.json` (fixed in model_utils.save_checkpoint; the file list is now generation/preprocessor/tokenizer
configs + vocab + merges). The later `score` stage of this window ran out of GPU memory because the engine had not
released the card yet; scoring was redone on CPU (V11).

## V11: baseline of the pretrained model (what the fine-tune has to beat)

`synth_eval` with the pretrained Base model, voice clone with an in-context reference (another clip of the same
speaker, `non_streaming_mode`, language Auto): 3 clips per f50 eval speaker (7 speakers), 3 of the held-out speaker-8,
4 Urdu sentences on the Shehbaz reference and 3 English on the Trump reference. 31/31 generated, 9.0 s per clip
through the HF generator. Scored with Whisper large-v3 (beam 5, fp16, GPU) and WavLM-base-plus-sv similarity to the
real recording of the same speaker; the ground-truth recordings were transcribed the same way (gt).

| set | clips | CER mean / median | gt CER mean / median | WER median | SIM mean | pace | severe (CER > 0.5) |
|---|---|---|---|---|---|---|---|
| f50 eval (seen speakers) | 21 | 0.172 / 0.144 | 0.068 / 0.030 | 0.35 | 0.956 | 0.98 | 4.8% (1) |
| f50 holdout speaker-8 (unseen) | 3 | 0.287 / 0.197 | 0.138 / 0.054 | 0.38 | 0.969 | 0.94 | 33% (1) |
| external: Shehbaz (ur) + Trump (en) | 7 | 0.114 / 0.122 | – | 0.22 | 0.939 | – | 0 |
| all | 31 | 0.170 / 0.144 | 0.077 / 0.038 | 0.36 | 0.954 | 0.97 | 6.5% (2) |

Reading: on these speakers the pretrained model's Urdu is 2.5-5x further from the transcript than the real
recordings are (Whisper's own error on the real clips is 0.03-0.05 median), with 1 in 15 clips severely wrong,
while the timbre already matches (SIM 0.95-0.97, real same-speaker pairs score ≥ 0.975 on this scale). The fine-tune's
job is the first column; the third column must not fall. Numbers are noisy at 3 clips per speaker: the real
evaluation uses `--per-speaker 20`.

## Incident: orphaned engine workers

The first `serve_check.sh` killed only the engine's parent process; its two vLLM stage workers survived, held 19 GB,
made the scoring OOM and the production engine fail to start after the window. Fixed: the engine now runs in its own
process group, the trap kills the group and waits until the card is released. The orphans were killed by PID.
