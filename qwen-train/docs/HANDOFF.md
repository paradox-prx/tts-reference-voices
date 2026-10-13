# Handoff: Qwen3-TTS Urdu fine-tuning pipeline

For the next Claude Code session (or engineer) that has to set this up on a fresh GPU box and run it. Read this file
top to bottom, then `README.md`, then `docs/EXPERIMENTS.md` (every validation number) and `docs/RESEARCH.md` (why the
trainer is our own and not the official script). Everything is marked **VERIFIED** (run on the dev box, numbers in
EXPERIMENTS.md) or **UNVERIFIED** (reasoned or estimated, never run).

Written 2026-10-13. Dev box: `vector` (1x RTX 3090 24 GB, shared with a production TTS service). Real training is meant
for a rented cloud GPU (RunPod).

---

## 0. TL;DR

- **What:** fine-tune `Qwen/Qwen3-TTS-12Hz-1.7B-Base` on studio Urdu (multi-speaker) so that voice cloning with a
  reference clip speaks Urdu natively instead of with a foreign accent. Result is a normal model directory that
  vLLM-Omni 0.28 serves unchanged.
- **Pipeline:** `derive` (manifest) -> `qc` (audio checks) -> `prepare` (codec codes + x-vectors) -> `check_alignment`
  (gate) -> `train` -> `synth_eval` + `score` -> `export` -> serve.
- **Why our own trainer:** the official `finetuning/` scripts have three verified bugs and are single-speaker
  (RESEARCH.md §2). Do not "simplify" back to them.
- **State:** pipeline validated end to end on 14 h and 46 h samples (smoke training, serving check). **No full run has
  been done.** The real dataset (see §3) was compiled on another PC and is being packaged for upload.
- **First real run:** `configs/full_24gb.yaml` (24 GB cards) or `configs/full_80gb.yaml` (40-80 GB) on the compiled
  data. Cheapest sensible hardware: one RTX 4090 24 GB (~$0.34/h community cloud, ~11-12 h for 300 h x 4 epochs).

---

## 1. How the model and the trainer work (the parts you must not break)

Qwen3-TTS-12Hz-1.7B-Base = a 28-layer Qwen3 **talker** (2048 hidden) predicting codebook 0 of a 16-codebook 12.5 Hz
codec, a 5-layer **code predictor** filling codebooks 1-15 from the talker's hidden state, a frozen ECAPA **speaker
encoder** (2048-d x-vector from a 24 kHz mel) and the **Code2Wav** decoder. Urdu is not one of its ten pre-training
languages.

- **Language tag.** Language is a codec-channel token; prefix `[think, think_bos, LANG, think_eos]`, or the "Auto" form
  `[nothink, think_bos, think_eos]`. Row **2080** of the codec embedding is untrained in the Base checkpoint; we use it
  as the `urdu` tag, initialised from the mean of the ten language rows. The exported `config.json` carries
  `"urdu": 2080` in `codec_language_id`, so vLLM-Omni serves `language: Urdu` with no code change.
- **Two prompt forms** are used by the production server, so training mixes both (`configs/*.yaml`): 70% in-context
  (another clip of the same speaker, 3-20 s, as reference text + codes) and 30% x-vector only; 80% with the Urdu tag,
  20% Auto. Non-streaming layout (`non_streaming_mode=true`), which is what the server sends for Urdu.
- **Layout** (`qwen_train/layout.py`) mirrors `generate()` / `generate_icl_prompt()` position by position. Labels are the
  next frame's codebook 0; the code predictor is trained from the hidden state that *predicted* each frame, as at
  inference. **`check_alignment.py` is the gate:** it must print `layout matches inference` on the real data before any
  training run (VERIFIED on the pretrained model: acc0 0.41 for our layout vs 0.06 for the official script's shift).
- **What trains:** talker, code predictor, codec embedding, text projection (1,605M of 1,929M params). Frozen: speaker
  encoder and the 152k x 2048 Qwen text embedding. `mode: lora` (r=64) is the fallback if the full fine-tune hurts
  cloning of unseen voices.
- **Precision:** `bf16` + Kahan-summation AdamW (`torch-optimi`) on 24 GB; `fp32-master` + bf16 autocast on 40-80 GB.
  Plain bf16 AdamW silently loses small updates at lr <= 1e-5: never "fix" this by removing optimi.
- **Pinned versions** (`requirements.txt`): `qwen-tts==0.1.1`, `transformers==4.57.3`, `peft==0.21.1`,
  `torch-optimi==0.3.3`, Python 3.12. We keep the `qwen-tts` package untouched and replace only layout + loss.

## 2. Setup on a fresh GPU box (RunPod)

Needs: Ubuntu, NVIDIA driver with CUDA >= 12.x, Python 3.12, `ffmpeg`, `git`. Use a **network volume** mounted at
`/workspace` (survives pod stops; it is also what the S3 API uploads to).

```bash
cd /workspace
git clone <this repo> qwen-train && cd qwen-train
export HF_HOME=/workspace/hf_cache          # keep the models on the volume, not the container disk
bash setup.sh                                # .venv, torch (cu128 default), requirements, downloads both models (~9 GB)
#   other CUDA build:  TORCH_INDEX=https://download.pytorch.org/whl/cu130 bash setup.sh
source .venv/bin/activate
pytest -q tests                              # 11 tests, CPU only
python -m qwen_train.derive --help
```
Sizes: `data/<name>/codes` ~1 GB for 300 h; a full checkpoint 3.4 GB; with `save_optimizer: true` each checkpoint also
holds optimizer state (**UNVERIFIED**, expect roughly +10 GB). `keep_last: 2` -> provision **>= 100 GB** of volume
(dataset FLAC + models + codes + checkpoints). Run long jobs inside `tmux`/`nohup`; pods get preempted, so always
train with `--resume` available (§5).

Gotchas hit before:
- **GPU memory is exclusive.** On the dev box the production service must be stopped first (`scripts/gpu_window*.sh`
  do that and restart it). On a rented pod there is nothing else, but a stray `python` still holds the card.
- **Orphaned vLLM workers** hold ~19 GB after a killed engine: kill the whole process group (`serve_check.sh` does).
- `faster-whisper` downloads Whisper large-v3 (~3 GB) on first use; `microsoft/wavlm-base-plus-sv` for similarity.
- `export` needs `tokenizer_config.json` etc. in the checkpoint; this is fixed in `model_utils.save_checkpoint`
  (`--copy-tokenizer` bundles the speech tokenizer so the directory can leave the machine).

## 3. The data

### 3.1 Format derive.py expects

```
<folder>/
  *_cleaned.csv         audio_file|text|speaker_name    pipe-separated, UTF-8, paths relative to <folder>
  wavs/<speaker>/*.{wav,flac,mp3,ogg,m4a}   any sample rate / channels (resampled to 24 kHz mono on the fly)
```
`--csv-glob` picks which CSVs are read (default `*_cleaned.csv`). Text is normalised by `qwen_train/text.py` (NFKC,
digits spelled out in Urdu, whitespace/punctuation tidied) and **the same function must be applied to text sent to the
fine-tuned model at serving time**.

### 3.2 The compiled dataset (current plan)

The user's Urdu set lives on another PC as two tune runs, each with train + eval CSVs (VERIFIED by that PC's session):
`1st_tune_run_dataset/{metadata_train,metadata_eval}.csv` (19,922 + 1,049 rows) and
`2nd_tune_run_dataset/...` (11,863 + 625), 33,459 rows, ~187 h, 21 speaker labels, paths like `wavs/<name>_chunkN.wav`
relative to each run folder. Two label spellings of the same person exist (`anila-ahsan` / `anila_ahsan`).
`flagged_forced_cuts.csv` files are QA logs, not metadata.

That PC's Claude was given a prompt (kept in this repo's chat history, summarised here) to: merge the four CSVs into one
`metadata_cleaned.csv` with resolved paths and canonical lowercase speaker names, convert audio to mono FLAC (keep
rate if <= 24 kHz, else 24 kHz), lay it out as `urdu_pkg/wavs/<speaker>/<run>__<stem>.flac`, pack `wavs/` into
~1.5 GB uncompressed tar shards (`shards/urdu_wavs_NNN.tar`, FLAC is already compressed so zip gains nothing), write
`SHA256SUMS`/`MANIFEST.json`, and an `upload_runpod.sh` (AWS CLI against the RunPod S3-compatible API) plus an
`extract_on_pod.sh`.

RunPod S3 upload, for reference (**UNVERIFIED** on this account): endpoint `https://s3api-<DATACENTER>.runpod.io`,
region = datacenter id (e.g. `EU-RO-1`), bucket = the network volume id, S3 API keys created in the RunPod console:

```bash
export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...        # never commit these
aws s3 cp shards/urdu_wavs_000.tar s3://$VOLUME_ID/urdu_pkg/shards/ \
    --endpoint-url https://s3api-$DC.runpod.io --region $DC
```
Then on the pod:
```bash
cd /workspace/urdu_pkg && sha256sum -c SHA256SUMS
mkdir -p wavs && for f in shards/*.tar; do tar -xf "$f" -C /workspace/urdu_pkg; done
wc -l metadata_cleaned.csv
```

### 3.3 Speaker labels: read this before trusting them

On the earlier folders, voice analysis (V13 in EXPERIMENTS.md) showed `speaker_name` and the `wavs/speaker-N/` folder
disagree, the same woman appears under several labels, and one "single speaker" folder holds 26 different voices. The
**user's decision was: trust the `speaker_name` column** (the default `--speaker-from column`). Nothing was re-tagged.
If you want to check the new set, `qwen_train.speakers embed` / `cluster` re-tag by voice (WavLM-Large + ECAPA, ~40
voices found on the old data) and `derive --speaker-map assignments.jsonl` applies it, but that is the user's call.
It matters for two reasons: the "same-speaker reference" for in-context training is picked by label, and the held-out
speaker must be a different *person*, not just a different label.

### 3.4 Transcripts

The transcripts (Gemini multimodal / Whisper made by the user) are **better than stock Whisper** on this data: Whisper
was wrong in 5 of 6 disagreements (collapses real repetitions, hallucinates). So `qc --apply` filters by audio checks +
per-speaker pace only. **Do not add a Whisper-CER filter by default.**

## 4. Pipeline run, step by step

Use `<name>` = `urdu`; `/workspace/urdu_pkg` is the extracted package. All commands run from the repo root with the
venv active.

```bash
# 1. manifest. One speaker is held out entirely (never trained; scored for unseen-speaker similarity). Pick a
#    speaker with >= ~1 h; `speakers.csv` in the package lists them. The script also carves a small eval split.
python -m qwen_train.derive --name urdu --out data/urdu --folder /workspace/urdu_pkg \
    --csv-glob '*_cleaned.csv' --holdout-speakers <speaker>
#    useful knobs: --min-dur 0.8 --max-dur 30 --min-chars 3 --max-chars 500 --eval-frac 0.02 --allow-sr 22050,24000

# 2. audio QC (free; add --asr large-v3 only as a diagnostic) and drop outliers
python -m qwen_train.qc --manifest data/urdu/manifest.jsonl --device cuda --apply
#    -> data/urdu/manifest_qc.jsonl (+ dropped_qc.jsonl). data.py automatically prefers manifest_qc.jsonl when it exists.

# 3. codec codes + x-vectors (~60 clips/s on a 3090; ~100k clips in 30-45 min); resumable by shard
python -m qwen_train.prepare --manifest data/urdu/manifest.jsonl --out data/urdu/codes --device cuda

# 4. GATE: must print "layout matches inference"
python -m qwen_train.check_alignment --data data/urdu --n 200 --language-id 2080 --copy-test

# 5. train
python -m qwen_train.train --config configs/full_24gb.yaml --set data_dir=data/urdu --set out_dir=runs/urdu_a
#    resume after a preemption:
python -m qwen_train.train --config configs/full_24gb.yaml --set data_dir=data/urdu --set out_dir=runs/urdu_a \
    --resume runs/urdu_a/latest
#    tensorboard --logdir runs/urdu_a

# 6. evaluate a checkpoint (every eval_every steps by hand, or at the end)
python -m qwen_train.synth_eval --model runs/urdu_a/latest --data data/urdu --refs configs/eval_refs.json \
    --language urdu --per-speaker 20 --out runs/urdu_a/eval_latest
python -m qwen_train.score --synth runs/urdu_a/eval_latest/synth.jsonl --score-gt

# 7. export a movable model directory and bring it home
python -m qwen_train.export --checkpoint runs/urdu_a/latest --out export/qwen3-tts-urdu-a --copy-tokenizer
tar -cf urdu_a.tar -C export qwen3-tts-urdu-a     # ~3.4 GB + tokenizer; download via the S3 API or runpodctl
```

Note on step 2 -> 3: `prepare` runs on the full `manifest.jsonl` (codes for every clip, which is fine); training and
`check_alignment` load `data/urdu` and pick `manifest_qc.jsonl` automatically (`data.py:71`), so QC drops apply at train time.

`configs/eval_refs.json` lists external reference voices (a Urdu speaker and an English speaker) with fixed sentences, so
every checkpoint is scored on an unseen Urdu voice and on English retention. Its `audio` paths are absolute paths on the
dev box: **edit them** to clips available on the pod, or drop that file from the command.

## 5. Configs and what to tune

| config | for | notes |
|---|---|---|
| `full_24gb.yaml` | RTX 3090/4090/A5000 | bf16 + Kahan AdamW, `max_tokens 8000`, `grad_accum 4`, lr 5e-6, 4 epochs |
| `full_80gb.yaml` | A100/H100/L40S | fp32 master, `max_tokens 24000`, `max_batch 24`, `grad_accum 1` |
| `lora_24gb.yaml` | fallback | r=64 adapters; use if full FT degrades cloning of unseen voices |
| `smoke.yaml` | 30-step check | what was used for the VERIFIED smoke run |

Set any key with `--set key=value` (dotted for nesting). Shared settings: cosine schedule, warmup 500, `cp_weight 0.3`,
`clip 1.0`, `eval_every 500`, `save_every 2000`, `keep_last 2`, `save_optimizer true`, `grad_checkpointing true`.

- **OOM on 24 GB:** lower `max_tokens` (e.g. 6000), keep `grad_checkpointing: true`, keep `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
  Smoke run peak was 19.4 GB at `max_tokens 6000`, ~4 GB headroom.
- **Throughput (VERIFIED, 3090):** ~2,040 tokens/s. A 300 h epoch is ~35M tokens (references double the load), so
  ~4.8 h/epoch; the 187 h set is ~3 h/epoch. A100/H100 estimated 3-5x faster (**UNVERIFIED**).
- **Learning rate:** 5e-6 is a reasoned choice (others used 2e-6 with the buggy script); no sweep has been run. Watch
  for the known failure "speech gets faster every epoch" (that was the label-shift bug; it should not occur here).
- **Cloning degradation levers**, in order: fewer epochs, lower lr, LoRA, more speakers (diversity matters more than
  more hours of the same voices).

### Cost on RunPod (Community Cloud, prices change; checked 2026-10)
One 24 GB GPU for 300 h x 4 epochs: A5000 $0.16/h ~25 h ~$4; 3090 $0.22/h ~20 h ~$4.50; **4090 $0.34/h ~11-12 h ~$4
(recommended)**; A100 80 GB $1.19/h ~5-7 h ~$7-8 (use `full_80gb.yaml`). Add a network volume (~$0.07/GB-month).

## 6. Acceptance: how to know the fine-tune worked

Baseline of the pretrained model (V11, 31 clips, Whisper large-v3 + WavLM similarity): CER mean 0.170 on seen
speakers' Urdu (ground-truth recordings score 0.077), severe failures (CER > 0.5) 6.5%, SIM 0.954. A checkpoint is good if:
1. CER on the eval set approaches the ground-truth row (target < ~0.10 with `--per-speaker 20`);
2. SIM stays >= ~0.95 (timbre must not get worse) on seen **and** the held-out speaker;
3. the external Urdu voice (unseen speaker) and the English reference stay close to baseline (CER ~0.11-0.12, SIM ~0.94);
4. severe-failure rate falls from 6.5%;
5. a listening check by a native Urdu speaker. Metrics use a Whisper that is itself accented on Urdu: it is a
   comparison tool, not an absolute score.

## 7. Serving the result

`serve_check.sh runs/<x>/latest [port]` starts the **production engine script of the `tts-reference-voices` repo
(vLLM-Omni 0.28 + vLLM 0.28, engine venv with the PR #7065 patch, `VLLM_USE_FLASHINFER_SAMPLER=0`)** on the checkpoint, sends
Urdu and English clone requests, prints timings and stops (VERIFIED on the smoke checkpoint: ready after 105 s, same
speed as the base model). It expects that repo as a sibling folder (`TTS_REPO`), which a fresh RunPod pod will not have.
**Recommended:** do not install vLLM-Omni on the training pod; export, download, and serve at home (`TTS_ENGINE_MODEL=<dir>`).
At request time send `language: Urdu` and run the text through `qwen_train.text.normalize_urdu`.

## 8. Decisions already made (do not re-litigate)

- Trust the CSV `speaker_name` column and the user's own `*_cleaned.csv` transcripts; no Whisper-CER filtering.
- Full fine-tune on a cloud GPU, not the dev box; voice cloning first, **VoiceDesign as experiment 2** (the trainer has
  the instruct layout, `instruct_field`; no public recipe exists; how much design ability survives is unknown).
- Our trainer, not the official scripts. LoRA only as a fallback.

## 9. Open items / not done

- No full run yet; no learning-rate sweep; checkpoint/optimizer sizes on a real run unmeasured.
- The new dataset's speaker labels were never voice-checked (§3.3); the held-out speaker has to be chosen.
- Pashto/Sindhi/Punjabi etc. are out of scope here (that is the Higgs project, a different repo).
- No native-speaker listening review of any output exists yet.
- Licence: Qwen3-TTS models are Apache-2.0 per their model cards (**UNVERIFIED here**; check before commercial use).

## 10. Repo map

```
qwen_train/   derive qc prepare speakers layout data model_utils train check_alignment synth_eval score export text
configs/      full_24gb full_80gb lora_24gb smoke eval_refs.json
scripts/      gpu_window*.sh spk_*window.sh   (dev-box helpers: pause prod units, run GPU stages, restart)
tests/        test_layout.py test_data.py     (pytest -q tests)
docs/         RESEARCH.md EXPERIMENTS.md HANDOFF.md (this file)
setup.sh serve_check.sh requirements.txt
data/ runs/   gitignored (datasets, codes, checkpoints, evals)
```
Commit identity used on this project: Abdullah Ashfaq <voxatechh@gmail.com>. Scan for secrets before every push; label
AI-generated audio when publishing it.
