# qwen-train: fine-tuning Qwen3-TTS for Urdu voice cloning

A portable pipeline that takes dataset folders in the XTTS layout (`wavs/speaker-N/*.wav` + `audio_file|text|speaker_name`
CSVs), derives and checks a training set, extracts codec codes, fine-tunes `Qwen/Qwen3-TTS-12Hz-1.7B-Base` in the
same prompt format the production server uses (in-context voice cloning with a reference clip, plus an explicit
`Urdu` language tag), evaluates it against held-out and unseen speakers, and exports a checkpoint that vLLM-Omni
serves as-is.

Why not the official `finetuning/` scripts: they are single-speaker and train a different layout from inference
(three verified bugs: doubly shifted talker labels, misaligned code-predictor labels, text embeddings without the
projection). Details and sources in [docs/RESEARCH.md](docs/RESEARCH.md); every validation number is in
[docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

## Setup (fresh GPU box)

```bash
bash setup.sh                       # .venv with torch + qwen-tts 0.1.1 + peft + optimi; downloads the two models
source .venv/bin/activate
```
Python 3.12, one NVIDIA GPU. 24 GB is enough for the full fine-tune (`configs/full_24gb.yaml`); 40-80 GB cards use
`configs/full_80gb.yaml` (bigger batches, fp32 master weights). The evaluation needs faster-whisper (Whisper large-v3
is downloaded on first use, ~3 GB) and `microsoft/wavlm-base-plus-sv`.

## Pipeline

```bash
# 1. manifest from one or more dataset folders (speaker from the speaker_name column; one speaker held out)
python -m qwen_train.derive --name urdu300 --out data/urdu300 \
    --folder /data/set1 --folder /data/set2 --csv-glob '*_cleaned.csv' --holdout-speakers speaker-8

# 2. quality checks: audio measurements for every clip, Whisper agreement with the transcript; --apply drops outliers
python -m qwen_train.qc --manifest data/urdu300/manifest.jsonl --asr large-v3 --device cuda --apply

# 3. codec codes (12.5 Hz x 16 codebooks) and speaker embeddings, ~60 clips/s on a 3090
python -m qwen_train.prepare --manifest data/urdu300/manifest.jsonl --out data/urdu300/codes

# 4. prove the layout matches inference on this data (must print "layout matches inference")
python -m qwen_train.check_alignment --data data/urdu300 --n 200 --language-id 2080 --copy-test

# 5. train (resumable; checkpoints are servable model directories)
python -m qwen_train.train --config configs/full_24gb.yaml --set data_dir=data/urdu300 --set out_dir=runs/urdu_a
python -m qwen_train.train --config configs/full_24gb.yaml --set out_dir=runs/urdu_a --resume runs/urdu_a/latest

# 6. evaluate a checkpoint: clone held-out/unseen speakers, score intelligibility and similarity
python -m qwen_train.synth_eval --model runs/urdu_a/latest --data data/urdu300 --refs configs/eval_refs.json \
    --language urdu --out runs/urdu_a/eval_latest
python -m qwen_train.score --synth runs/urdu_a/eval_latest/synth.jsonl --score-gt

# 7. serve it (on the production box: the same engine script the service uses)
bash serve_check.sh runs/urdu_a/latest
```
`configs/eval_refs.json` holds external reference voices (the server's Shehbaz and Trump clips) and fixed sentences,
so every checkpoint is scored on an unseen Urdu speaker and on English retention.

## What the trainer does

- **Layout** (`qwen_train/layout.py`): role tokens, the codec prefix (`[think, think_bos, urdu, think_eos]` or the
  Auto form), the speaker embedding slot, then `[reference text, target text, eos]` over codec pads, `bos`, the
  reference frames and the target frames (non-streaming form, what the server sends for Urdu). Streaming form and the
  VoiceDesign instruct form are supported too. Labels are the next frame's codebook 0; the code predictor is trained
  from the hidden state that predicted each frame, as at inference.
- **Data mix** (`configs/*.yaml`): 70% of examples carry an in-context reference (another clip of the same speaker,
  3-20 s), 30% the x-vector only; 80% carry the language tag, 20% the Auto form.
- **Trainable parameters**: the talker, code predictor, codec embedding and text projection; the speaker encoder and
  the 152k x 2048 Qwen text embedding stay frozen. `mode: lora` trains r=64 adapters instead.
- **Precision**: bf16 weights with Kahan-summation AdamW (`torch-optimi`) on 24 GB cards; fp32 master weights with
  bf16 autocast on bigger cards.
- **Checkpoints**: full HF directories (config with the Urdu tag, speaker encoder included, speech tokenizer
  symlinked; `export.py --copy-tokenizer` bundles it), `trainer_state.json`, optional `optimizer.pt`.

## Data format expected by derive.py

```
<folder>/
  *_cleaned.csv        audio_file|text|speaker_name      (or audio,text[,language] with speaker = wavs/<speaker>/)
  wavs/speaker-N/*.wav  any sample rate / channels (resampled to 24 kHz mono on the fly)
```
Text is normalised by `qwen_train/text.py` (NFKC, digits spelled out in Urdu, whitespace/punctuation tidied); apply
the same function to text sent to the fine-tuned model at serving time.

## Layout of this folder

| path | what |
|---|---|
| `qwen_train/` | the package: derive, qc, prepare, layout, data, model_utils, train, check_alignment, synth_eval, score |
| `configs/` | training configs and the external evaluation references |
| `tests/` | layout and dataset tests (`pytest -q tests`) |
| `scripts/gpu_window.sh` | the validation run used on the production box (pauses the service, restarts it) |
| `docs/` | RESEARCH.md (findings, sources), EXPERIMENTS.md (validation numbers) |
| `data/`, `runs/` | derived datasets and training runs (gitignored) |
