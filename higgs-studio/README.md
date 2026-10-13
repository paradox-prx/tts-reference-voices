# Higgs Studio

Two internal web consoles on top of a Higgs TTS 3 engine (`bosonai/higgs-tts-3-4b` served by vLLM-Omni 0.28.0):

- **Studio** (`/studio`): one-at-a-time generation for customers. Preset voices or an uploaded reference,
  English / Urdu / Pashto / Punjabi (Shahmukhi) / Sindhi, control tags as chips, delivery controls, 1–3 takes
  side by side, streaming playback, and WAV/MP3 download.
- **Dataset** (`/dev`): mass dataset generation. Speaker references and rows in (CSV/JSON/JSONL), speaker
  distribution, sampling and seeds, tag modes, and QC with retries. Jobs run in a resumable background queue.
  Stratified samples can be reviewed and regenerated, and the result downloads as a streamed zip.

Both consoles are for the internal network or VPN only. **There is no login**, so do not expose the port to the
internet. All audio is AI-generated; label it as such wherever it is used.

```
higgs-studio/
  setup.sh  start.sh  stop.sh  install_units.sh   one-shot setup, background start/stop, systemd user units
  .env.example                                    every setting (copy to .env)
  engine/   run_engine.sh install_engine.sh download_models.sh apply_pr7065.sh
            deploy/higgs_3090_32.yaml (default) higgs_3090_16.yaml   patches/pr7065-package.diff
  app/      studio/ (FastAPI backend)  tests/  requirements.txt
  web/      React + Vite consoles (built into web/dist)
  voices/   preset voices, one folder each (see voices/README.md; the audio is not versioned)
  data/     jobs, uploads, takes, sqlite, logs (created at run time)
```

## Setup

You need:

- Linux with an NVIDIA GPU with 24 GB, driver ≥ 580 (CUDA 13); tested on one RTX 3090;
- `uv` (or Python 3.12), `ffmpeg`, `patch`, `curl`;
- node ≥ 18 to build the consoles;
- ~15 GB of disk for the engine venv, plus ~9.5 GB for the model.

```bash
cd higgs-studio
./setup.sh                      # creates .env, engine venv, model download, app venv, web build, unit tests
./start.sh                      # engine (waits until ready) + studio; logs in data/logs/
# or, to survive logouts and reboots:
./install_units.sh --now        # systemd --user units higgs-engine + higgs-studio + a health watchdog timer
sudo loginctl enable-linger $USER
```

Then open `http://<host>:8100/studio` and `http://<host>:8100/dev`.

**Reuse what is already on the box.** `setup.sh` skips every step that is already done:

- **Model and codec.** The Higgs checkpoint and the `k2-fsa/OmniVoice` audio codec are taken from the
  Hugging Face cache (`$HF_HOME/hub`) when they are there. Set `HF_HOME` to use another cache, or point
  `HIGGS_MODEL` at a local checkpoint directory.
- **Engine venv.** An existing vLLM 0.28.0 + vLLM-Omni 0.28.0 venv is reused when `HIGGS_ENGINE_VENV` in `.env`
  points to it. The PR #7065 patch is checked and applied if missing.

**One GPU, one engine.** The engine takes ~22 GB of a 24 GB card. Stop anything else on the GPU first. The
systemd unit declares `Conflicts=qwen3-tts-engine.service`.

Operations:

| | |
|---|---|
| `./start.sh [engine\|studio]` / `./stop.sh [engine\|studio]` | without systemd |
| `systemctl --user restart higgs-studio` | after a code or `.env` change (jobs resume) |
| `journalctl --user -u higgs-engine -f` / `data/logs/*.log` | logs |
| `curl localhost:8100/api/status` | engine health, queue |
| `cd web && npm run dev` | console development (proxies `/api` to :8100) |
| `cd app && ../.venv/bin/python -m pytest -q tests` | unit tests |

## Settings

All settings come from environment variables, usually through `.env`. Every one is listed in `.env.example`.
The prefixes:

- **`HIGGS_*`**: the engine. Venv, port, GPU, deploy YAML, model, codec path, and an optional API key.
- **`STUDIO_*`**: the app (`app/studio/settings.py`):
  - port, voices and data directories;
  - `STUDIO_MAX_INFLIGHT`: requests in flight at the engine. Keep it below the deploy's `max_num_seqs`.
  - `STUDIO_DEV_MAX_INFLIGHT`: the share that dev jobs may use. The rest is reserved for customers.
  - `STUDIO_CUSTOMER_QUEUE_MAX`: beyond this many waiting customer requests, the server answers "busy".
  - part length, join gap, and take retention.

No secrets are needed.

## How it works

- **One queue for both consoles** (`app/studio/scheduler.py`). Customer requests always go before waiting dev
  requests. Dev jobs never use the last `MAX_INFLIGHT - DEV_MAX_INFLIGHT` engine slots, so a customer request
  starts at once even during a large job.
- **Text pipeline** (`text.py`, `tags.py`, `audio.py`). This is shared by both consoles:
  1. Text is split into sentences: `. ! ?` for Latin script, `۔ ؟ !` for Urdu, and newlines.
  2. Tags are validated against the model's exact vocabulary.
  3. Text is packed into parts of at most ~25 s estimated speech. The estimate uses the voice's own pace,
     measured from its reference. The tags in force are restated at the start of each part.
  4. Each part's edges are trimmed of silence.
  5. Parts are joined with a 0.3 s gap and loudness-normalised (default −20 LUFS, −1 dBFS peak).
- **References.** The engine accepts at most 30 s of reference audio. Voice folders are combined or cut to fit
  (see `voices/README.md`). Uploads longer than that are cut at a sentence pause.
- **Seeds.** Every take and row logs its seed. Higgs only reproduces a seed exactly when the request runs
  alone: batching with other requests changes the numerics. "Exact" in the Studio waits for an idle engine;
  dataset rows do not, so a regenerated row with the same seed sounds similar but is not bit-identical.
- **Streaming.** The Studio plays the first part live as PCM while it is generated. Later parts follow when
  they are ready. The downloadable WAV is the joined, normalised result.

### Dataset zip layout

```
wavs/<speaker>/<id>.wav
metadata.csv        audio_path,text,speaker,tags,seed,duration_s,sample_rate,qc_status,wer
metadata.jsonl      same fields, one object per line
rejected.csv        rows that errored or were flagged and excluded (reason, attempts)
speakers/<speaker>.wav + speakers.csv    the exact references used, with their transcripts
job_config.json     the full job config (importable in the Dataset console)
README.md           counts, per-speaker totals, settings
```

Flagged rows are left out by default (a toggle in the config and at download time). Other metadata formats
are small converters in `app/studio/export.py`, `CONVERTERS`. Currently there is `pipe_csv`
(`audio_file|text|speaker_name`, the qwen-train layout), added to the zip with `?extra_format=pipe_csv`.

QC checks:

- duration against the expected pace;
- long internal silences and near-silent takes;
- clipping.

A failing row is retried with new seeds, then flagged. **There is no ASR check:** no Whisper runs in this
deployment, so the `wer` column stays empty and uploaded references need a typed transcript.

## API

The consoles use the same JSON API, which can also be used directly. It has no authentication. The main
calls:

- `GET /api/voices`: preset voices.
- `POST /api/studio/generate` with `{text, voice: {preset} | {upload, start, end, transcript}, delivery, takes,
  seed, exact, stream}`. The response gives take ids. A take's progress comes from
  `/api/studio/takes/{id}/events` (SSE), and the audio from `.wav`, `.mp3` or `live.pcm`.
- `POST /api/dev/jobs` creates a dataset job. Rows and speaker uploads go first to `/api/dev/rows` and
  `/api/dev/speakers`.
- `GET /api/dev/jobs/{id}/download.zip` downloads the result.

The full list is in `app/studio/main.py`, and `/docs` while the server runs.

## Languages

The engine has no language parameter: Higgs reads the language from the text's script and words. Switching
language in the Studio changes the text direction, fonts, examples and suggested voices, nothing on the server.
Status as of 2026-10-07:

| Language | Boson model card | Checked here |
|---|---|---|
| English | WER/CER < 5 % tier | generates, QC pass |
| Urdu | WER/CER < 5 % tier | Urdu WER 1–6 % measured in our own benchmark (tts-reference-voices `higgs/REPORT.md`) |
| Pashto | 5–10 % tier ("usable, less polished") | generates with plausible length; intelligibility **not verified** |
| Sindhi | 5–10 % tier | generates with plausible length; intelligibility **not verified** |
| Punjabi (Shahmukhi) | "Eastern Punjabi" in the 5–10 % tier; the card names no script | generates with plausible length; **not verified** whether it is read as Punjabi or as Urdu |

"Not verified" means nobody has listened yet. There is no ASR in this deployment, and the samples from the
end-to-end check (`results/<date>_e2e/customer_{ps,pa,sd}.wav`) still need a native speaker to listen to them.
The only automatic signal is length: the duration came out within 0.9–1.15× the estimate, which rules out
silence, truncation and run-on babble, not mispronunciation. The Pashto voice's reference clips are Urdu
speech. The output follows the text's language, but expect an Urdu accent until there is a native Pashto
reference.

## Checking a deployment

`.venv/bin/python scripts/e2e_check.py` runs the whole flow through the API against the running server:

- a dev job with 3 speakers and 20 rows, with pinned rows, a tags column and a fixed seed. The script waits for
  the job, then checks samples, a row regeneration, and the zip: layout, metadata paths and counts against the
  distribution, WAV headers, and the pipe_csv extra;
- one Studio sample per language, plus one with tags, one with an uploaded reference, one streamed, and an MP3.

It writes `results/<date>_e2e/` (audio, the zip, `summary.json`) and exits 1 if any check fails.

## Known limits

- **Reproducibility.** Seeds are only bit-exact for requests that run alone (see above).
- **Pace.** Higgs copies the reference's pace and style more than the delivery controls. Speed and expressiveness
  tags nudge the output. Strong tag strength (a tag on every sentence) can make the voice drift from the
  reference.
- **Length.** The engine's ceiling is ~80 s of audio per request. Longer texts are always split.
- **Licence.** Higgs TTS 3 is under Boson's *Research and Non-Commercial License*. Commercial use (and serving
  customers is commercial use) needs a separate written licence from Boson (contact@boson.ai). The licence also
  forbids non-consensual voice cloning and impersonation, and requires disclosure of synthetic audio.
