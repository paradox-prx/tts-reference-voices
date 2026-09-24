# HANDOFF: Qwen3-TTS voice-clone server + benchmark

> ## Session 2 update (2026-09-25, machine `vector`): READ THIS FIRST
>
> The work moved from pb-ai-pc1 to a different machine. §0-§12 below describe session 1 on pb-ai-pc1 and stay as
> the research record; where they conflict with this box, this block wins.
>
> **Machine `vector`:** 1x RTX 3090 24 GB (GPU **0**, also drives the desktop: Xorg/GNOME/VS Code hold ~0.35 GB),
> driver 580.95.05 (CUDA 13.0), i9-14900K (32 threads; governor powersave, EPP balance_performance), 30 GB RAM,
> Ubuntu 25.04, Python 3.12 via pyenv (`/home/vector/.pyenv/versions/3.12.6/bin/python3.12`), uv 0.9.13. Internet is
> fast (~12 MB/s from HF), so everything was downloaded directly (no bundles). **Disk is tight (~17 GB free).** No
> translation-layer co-tenant, no Whisper servers here.
>
> **Layout:** the repo checkout `/home/vector/Documents/abdullah_workspace/qwen-server/tts-reference-voices` (branch
> `qwen3-omni-bench`) IS the working tree; `server/` is the project root (there is no separate
> `/home/vector/qwen3-tts-server` repo on this box; commits go straight to the branch). Gitignored assets under
> `server/`: `venvs/{engine,gateway,eval,qwentts,tools}`, `models/eval/` (4.8 GB, sha-verified), `results/`, `logs/`,
> `state/`. The Qwen weights are in `~/.cache/huggingface/hub` (snapshot fd4b2543…). Pushes use the `paradox-prx`
> GitHub account already signed in to `gh` on this box, without switching the active account:
> `TOKEN=$(gh auth token --user paradox-prx); git -c credential.helper= -c "credential.helper=!f() { echo
> username=x-access-token; echo password=$TOKEN; }; f" push origin qwen3-omni-bench`.
>
> **Engine:** `venvs/engine` = vllm 0.28.0 + vllm-omni 0.28.0 + torch 2.13.0 cu130 (flashinfer 0.6.16.post3,
> transformers 5.14.1), installed with `uv pip install -p venvs/engine/bin/python -c engine/constraints-omni28.txt
> vllm==0.28.0 vllm-omni==0.28.0`. **It must run with `VLLM_USE_FLASHINFER_SAMPLER=0`:** with FlashInfer's sampler,
> stage-0 init JIT-compiles it and fails (`CUDA compiler and CUDA toolkit headers are incompatible`: pip resolved
> nvcc 13.4.92 against 13.0 runtime headers; `logs/engine_smoke_default.log`). Start (GPU 0):
> `CUDA_VISIBLE_DEVICES=0 VLLM_USE_FLASHINFER_SAMPLER=0 bash engine/run_engine.sh engine/deploy/qwen3_tts_prod.yaml
> 8091 venvs/engine`. Measured with the prod YAML (0.45/0.18): stage 0 weights 4.15 GiB, activation peak 1.5 GiB, KV
> 6.2 GiB = **58,032 tokens** ("maximum concurrency for 4,096 tokens: 14.17x"); stage 1 ≈ 4.2 GiB; whole engine
> 15.2 GB on the card; stage-0 init 74 s (torch.compile 17 s).
>
> **First results (all saved with their numbers under `server/results/`):**
> - `00_first_engine_smoke/`: engine direct, c=1, both voices × inline/registered × stream/non-stream: RTF 0.19-0.21
>   (~5x realtime), streaming TTFA 110-117 ms; Whisper (CPU int8) transcribes English exactly and Urdu with minor
>   accent errors.
> - `00_first_gateway_smoke/`: through the gateway (registered voices, warmup 0.6-0.8 s): c=8 short texts 14.8x
>   realtime non-stream, 16.4x stream (TTFA ~0.63 s at c=8), 0 errors, 0 suspects.
>
> **Gateway changes (session 2):** voice-relative pace guardrail (s/letter vs `calibration/pace.json`, band
> 0.6-1.8x; the shehbaz reference clip is a slow address at 0.183 s/letter, so shehbaz uses a prior of 0.088 until
> recalibrated from real takes); QC sidecar client (`TTS_QC_URL`, retry reason `qc`, fail-open); local-time logs
> (Asia/Karachi); `GET /v1/voices`; `TTS_VOICE_MODE=precomputed` for engine custom voices (averaged embedding).
>
> **In progress:** engine-ops review + precomputed averaged-embedding voices (`engine/precompute_voices.py`); bench
> tooling + full plan (`bench/bench_tts.py`, `server/bench/`); eval stack + QC sidecar (`server/eval`, `server/qc`,
> `venvs/eval`); plain qwen-tts baseline (`server/baseline`, `venvs/qwentts`). Then: benchmark phases → quality eval →
> production units → README.md + REPORT.md. The user also asked that every run's audio and numbers be saved under a
> folder named for that experiment, with an index (`server/results/INDEX.md`).

# Session 1 record (pb-ai-pc1, state as of 2026-09-24 ~19:00 PKT)

**Where this lives:** on the box, `/home/vector/qwen3-tts-server` (its own git repo, branch `main`). On GitHub, the
same tree is the `server/` folder of branch **`qwen3-omni-bench`** of `paradox-prx/tts-reference-voices` (public;
the user chose this knowingly). That branch also carries the `bench_tts.py` changes. Sync the box repo into the branch
with `cd /home/vector/tts-reference-voices && git subtree pull --prefix=server /home/vector/qwen3-tts-server main`,
then push over SSH (deploy key `~/.ssh/tts_reference_voices_deploy`; see §11).

Written for the next Claude Code session (or engineer) picking this up cold. Read this file top to bottom, then
`docs/DESIGN.md`, then the research notes in `docs/research/`. Everything below was verified in this session unless
marked **UNVERIFIED**. Times are Asia/Karachi (UTC+5).

---

## 0. TL;DR

- **Goal:** production **Qwen/Qwen3-TTS-12Hz-1.7B-Base** voice-clone server on this box's GPU behind an
  OpenAI-compatible `POST /v1/audio/speech`, then a thorough benchmark (speed + quality), README, results and
  `REPORT.md` with a recommended production config.
- **Engine decision (from source-level research): vLLM-Omni 0.28.0 + vllm 0.28.0 (stable)** as primary.
  0.30.0rc1 is only an A/B candidate: its default runner (MRV2) is experimental, and the 0.30.0 release CI
  produced looping voice-clone audio (vllm-omni issue #8091). The official `qwen-tts` 0.1.1 is the control
  baseline. The alternatives (SGLang-Omni, faster-qwen3-tts, qwentts.cpp) were researched and ranked but not built;
  see §5.3.
- **Blocker: network.** The internet link is ~2.7-3 MB/s aggregate and throttles each TCP connection to ~20 KB/s.
  **No model weights and no vLLM/torch wheels are installed yet.** The user is fetching them on a faster machine
  (see §4). **Nothing has run on a GPU yet.**
- **Done:** GPUs freed (Whisper STT servers stopped at the user's request); research (5 of 6 topics complete, plus
  the source dive); `bench_tts.py` extended and tested against a stub; Auralis Urdu pools extracted; design doc;
  gateway venv; a second-bundle download script. A multi-agent **build workflow was running** when this was
  written (gateway, vLLM-Omni backend, engine ops, benchmark runner; see §7). Check what it left on disk.
- **Next:** receive the bundle(s) → install the engine venv → smoke test on GPU 1 → run the benchmark plan →
  quality eval → REPORT.md. The runbook is in §9.

---

## 1. The task (from the user, verbatim requirements condensed)

1. Clone https://github.com/paradox-prx/tts-reference-voices (done: `/home/vector/tts-reference-voices`). Read
   `NOTES.md` (Kaggle T4 learnings: model facts, settings, speed, Urdu failure modes, vLLM-Omni API) and
   `bench/README.md`. Treat them as starting points to verify on this hardware, not as settled.
2. **Serve** `Qwen/Qwen3-TTS-12Hz-1.7B-Base` (voice clone) behind an OpenAI-compatible `POST /v1/audio/speech`.
   vLLM-Omni is the first candidate: research its current state and pick the best option with evidence. Load the
   repo's voices (`trump` = English, `shehbaz` = Urdu, language "Auto") from `voices/<id>/references/`. Production
   basics: health endpoint, auth key via env, warmup, queueing and limits, structured logs, systemd or docker. Keep
   the model backend swappable (Higgs Audio v3 may be added later).
3. **Benchmark (the main goal).** Use and extend `bench/bench_tts.py`:
   - concurrency 1, 2, 4, 8, 16, 32 (higher if the GPU allows) × sizes short/medium/long/xlong × both voices;
   - streaming vs non-streaming (time to first audio vs total latency);
   - registered voice vs inline `ref_audio`; precision and batching options;
   - report latency p50/p90/p99, throughput (× realtime), req/s, GPU memory, errors, "suspect" (bad-length) takes;
   - quality on saved audio: **Whisper large-v3 WER** and **speaker similarity**; Urdu failure rate, and whether
     `repetition_penalty` 1.1-1.2 or a retry policy fixes it;
   - apples-to-apples with the team's XTTS/Auralis setup: run the Urdu SHORT, MEDIUM, LONG pools from
     `/home/serveradmin/services/xtts_optimized/auralis_new_architecture/benchmark_tts_urdu_new.py` via
     `bench_tts.py --pools`.
4. **Deliver:** the running service, a README, the benchmark results, and REPORT.md with tables and a recommended
   production config (engine, precision, max concurrency, batching, streaming, retry policy).
5. Don't publish generated audio, and label it as AI-generated.

### Instructions the user gave during the session (binding)

| when | instruction |
|---|---|
| 17:3x | "kill the whisper ones": stop the two Punjabi-STT Whisper vLLM servers. **Done** (§2.2). |
| 17:4x | **Do not test Auralis. Benchmark Qwen only.** Use Auralis only via its pools and the numbers the user pasted (§6). |
| 17:4x | **Save the outputs of all benchmarks, Urdu and English** (keep every WAV; `bench_tts.py` does by default). |
| 17:5x | Evals use **stock `openai/whisper-large-v3`**, NOT the Punjabi fine-tune (`punjabi-test-ckpt-meer`); the languages are Urdu and English. |
| 18:1x | Stop slow downloads; the user downloads big files on a faster machine and copies them here. They ran `get_models.py` (bundle 1, §4.1) **as-is and cannot re-run it with changes**, so plan around its defects. |
| 18:4x | If blocked by the internet, give the user a Python file to run on a fast machine (done: `ops/get_bundle2.py`, §4.2). |
| 18:5x | Write this handoff, and push all progress to GitHub so nothing is lost (§11). |

---

## 2. The machine (pb-ai-pc1)

### 2.1 Hardware and OS
- 2× **RTX 3090 24 GB** (Ampere, **sm_86**, bf16 supported, no FP8). Power limits: GPU0 370 W, GPU1 350 W (slightly
  different cards; benchmark on one GPU only). Driver **580.82.07** (CUDA 13.0 capable). PCIe link idles at gen1 x8
  (normal power saving; check under load).
- Intel Core Ultra 9 285K, 24 cores, 62 GB RAM. `intel_pstate` active, governor `powersave` **but EPP =
  `performance` and turbo on**, so the CPU is not pinned low. Changing it needs sudo; just record it in the report.
- Ubuntu 24.04, glibc 2.39, kernel 6.17. Python 3.10/3.11/**3.12** (system). No `uv`, no `gh`, **no docker access**
  (socket permission denied), no sudo (the user `vector` is in the sudo group, but it needs a password).
- CUDA toolkits: `/usr/local/cuda-12.8`, `/usr/local/cuda-12.9` (incomplete: no `bin/nvcc`), and `/usr/bin/nvcc` is
  **12.0**. Anything that derives nvcc from `CUDA_HOME=/usr/local/cuda` breaks. FlashInfer JIT must use the pip CUDA 13
  toolchain inside the venv (see `docs/research/local-env.md`).
- Disk: a single `/` filesystem, **~100 GB free (89% used), shared with production**. Budget ~40-45 GB for venvs,
  models and audio. Delete wheelhouses after install.
- `systemd --user` works (systemd 255, **Linger=yes**) with `export XDG_RUNTIME_DIR=/run/user/$(id -u)`
  (and optionally `DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus`). Without it you get
  "Failed to connect to bus: No medium found". The existing user units `tts-app.service` and
  `gradio-qa-app.service` belong to others: don't touch them or reuse their names.

### 2.2 GPU tenants (IMPORTANT, shared production box)
- `/home/vector/translation-layer` (NLLB FastAPI, **port 8016**, pid 1785705, the user's own service) holds
  **~4.4 GB on BOTH GPUs**. Leave it alone. So each GPU has **~19.6-20 GB free**.
- Two Punjabi-STT **Whisper vLLM servers were stopped at 17:5x at the user's request**: `:8000` on GPU0
  (upstream of the live whisper proxy on `:8003`) and `:8012` on GPU1. Each had held 18.5 GB
  (`--gpu-memory-utilization 0.75`) and served few requests (271 and 130 in 6 and 4 days). **Exact restart commands:
  `ops/STOPPED_WHISPER_SERVERS.md`.** If they come back at 0.75, vLLM-Omni cannot start: vLLM refuses to start a stage
  unless free memory ≥ total × gpu_memory_utilization. Any restart must pin a GPU and use a low utilization.
- Plan: **GPU 1 = TTS engine + load tests; GPU 0 = quality eval (Whisper large-v3, WavLM)**, so eval can run while
  benchmarks run. `bench_tts.py --gpus 1` samples only GPU 1. Its memory number still includes the translation-layer's
  4.4 GB on that GPU; subtract it or note it.
- Many other services run on this box under root (LLM proxies, qdrant, jazz-tts-demo, a live dubbing pipeline by
  user `wasifa`, and others). Never kill processes you didn't start.

### 2.3 Ports
Listening: 8000/8012 (stopped STT; they may return), 8003/8004 (live Whisper proxy/save), 8014, 8016
(translation-layer), 8020, 8500, 5008, 5009, 3001-3003, 6333/6334 (qdrant), 8002, 8009, 5000, 5001, 8100 (default of
a translation-layer denoise server). **Chosen: gateway `0.0.0.0:8090`, engine `127.0.0.1:8091`** (both verified
free). NOTE: `bench_tts.py` defaults to `--url http://127.0.0.1:8091` (the NOTES doc port), which here is the
**engine**, so pass `--url http://127.0.0.1:8090` to go through the gateway. Firewall rules can't be read without
root, so whether 8090 is reachable from the LAN is unknown.

### 2.4 Network (the blocker)
- Aggregate ~2.7-3 MB/s, flaky ("Connection reset by peer"). **Each TCP connection is throttled to ~15-25 KB/s from
  PyPI and ~80-110 KB/s from the HF CDN.** Speed grows with parallel connections.
- Tools that work: `docs/research/artifacts/local-env/fetch_wheels.py`, a stdlib parallel-range fetcher (24-32
  connections, 0.5-1.6 MB/s measured, sha256-verified, resumable, reads pip `--report` JSON or `hf:<repo>`).
  Plain `pip download`, `curl` and the HF xet downloader are 10-20× slower here.
- Unauthenticated GitHub API quota for this IP gets exhausted quickly (403). There are **no GitHub credentials on the
  box** (no gh, no SSH keys, no credential helper).

---

## 3. What exists on disk now

```
/home/vector/tts-reference-voices/            clone of the user's repo (public on GitHub)
  bench/bench_tts.py                          EXTENDED (uncommitted; original at qwen3-tts-server/ops/bench_tts.orig.py)
  bench/pools/auralis_ur.json                 NEW: Auralis Urdu pools, verbatim (short 151, medium 105, long 21)
/home/vector/qwen3-tts-server/                project root (not yet a git repo when this was written)
  HANDOFF.md                                  this file
  docs/DESIGN.md                              architecture, API, config vars, retry policy, backend interface
  docs/auralis_baseline.md                    the user's Auralis numbers + Auralis request settings
  docs/research/*.md                          research findings (see §5), one file per topic
  docs/research/artifacts/                    pip reports, fetch lists, fetch_wheels.py, release notes, paper text, etc.
  ops/STOPPED_WHISPER_SERVERS.md              how to restart the two STT servers
  ops/get_bundle2.py                          script for the user's fast machine (§4.2)
  ops/bench_tts.orig.py                       pristine upstream bench_tts.py
  ops/upstream/                               vllm-omni 0.28.0 + 0.30.0rc1 wheels AND unpacked sources, qwen3_tts examples
  venvs/tools/                                py3.12: huggingface_hub 2.0, httpx, numpy, soundfile, fastapi, uvicorn (downloads, stubs)
  venvs/gateway/                              py3.12: fastapi 0.141, uvicorn[standard], httpx, numpy, soundfile, pydantic 2,
                                              pydantic-settings, orjson, prometheus-client, python-multipart, pytest(-asyncio)
  wheels-extra/                               PARTIAL resumable download of wheels missing from bundle 1 (fetch28.txt, fetch30.txt;
                                              *.part files resume with curl -C -). ~54 of 158 wheels, ~100 MB as of 19:00.
  gateway/, engine/, deploy/, bench/          being written by the build workflow (§7); may be complete, partial or missing
  logs/                                       download logs
  models/eval/                                eval models (faster-whisper-large-v3, WavLM-large SV, wavlm-base-plus-sv, ECAPA); gitignored
  eval/lab/                                   eval scripts from the eval research agent (asr_eval, sim_eval, normalizers, checks, retry_sim)
  venvs/eval-asr, venvs/eval-sim              working eval venvs (faster-whisper; torch-cpu + transformers)
~/.cache/huggingface/hub/
  models--microsoft--wavlm-base-plus-sv       COMPLETE (sha256 verified); blob lives in hub/blobs/a4/... (xet layout, §4.1)
  models--Qwen--Qwen3-TTS-12Hz-1.7B-Base      config/tokenizer files only (weights NOT downloaded)
  models--openai--whisper-large-v3            json/txt only (weights NOT downloaded)
~/.claude/projects/-home-vector/memory/       two memory notes (box facts, project facts)
```

Temporary (will be lost when the session ends; the important parts were copied into `docs/research/`):
`/tmp/claude-1013/-home-vector/60c91189-44d6-4cdb-b0f5-2bf4adb23fb3/scratchpad/research/` (unpacked sources, cloned
alternative repos, venvs).

### 3.1 `bench_tts.py` changes (tested against a local stub server, all passing)
- `--gpus 1`: nvidia-smi sampling limited to the given GPU ids. The original summed memory over **all** GPUs, so the
  translation-layer's 4.4 GB on the other card inflated it.
- **TTFA fix:** a streamed WAV starts with a 44-byte header (vLLM-Omni sends it just before the first audio). The
  original measured TTFA at the first byte, i.e. the header. Now `ttfb` = first byte and `ttfa` = first byte **past
  the WAV header**.
- Saved audio is rewritten as a clean RIFF (streamed headers carry 0xFFFFFFFF sizes) with a **LIST/INFO ICMT
  "AI-generated … Do not publish."** chunk. `results/<ts>/AI_GENERATED_AUDIO.txt` is written too. `results/` is
  gitignored in that repo.
- `--takes K` (K independent takes per distinct text, for failure rates) and `--seed BASE` (per request
  `BASE + 100*text_index + take`). **Don't use `--seed` in throughput runs on vLLM-Omni 0.28** (§5.1).
- `--api-key` (default `$TTS_API_KEY`, sent as Bearer; also used for voice upload), `--tag` (run-name prefix),
  `--timeout` (default: per-size timeout × max(1, c/16)).
- Per-request rows add `lang, take, seed, ttfb, resp_headers (all x-* headers), params, file`. The summary adds
  `tag` and `retried` (count of `x-tts-retries` > 0). Reusing `--out` appends to the existing summary tables.
- Removed the now-unused `wav_seconds`/`audio_seconds`.
- **Caveat:** `--param k=v` sends TOP-LEVEL JSON fields. vLLM-Omni silently ignores top-level `temperature`,
  `top_k`, `top_p`, `repetition_penalty`. For engine-direct runs use
  `--param 'extra_params={"temperature":0.9,"top_k":50}'`. Through our gateway, top-level fields are accepted and
  mapped.

---

## 4. Model and wheel delivery (bundles)

### 4.1 Bundle 1: the user's `get_models.py` (already run on a fast machine, being copied here)
What it does: `snapshot_download` into `qwen_tts_bundle/hf_cache/` for `Qwen/Qwen3-TTS-12Hz-1.7B-Base` (all files),
`openai/whisper-large-v3` (ignoring `*.bin, *.msgpack, *.h5, *.onnx*, *.pt`), `microsoft/wavlm-base-plus-sv`, with
**`HF_XET_HIGH_PERFORMANCE=1`**. Then `pip download vllm-omni -d wheels --only-binary=:all: --platform
manylinux_2_28_x86_64 --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --python-version 3.12
--implementation cp`, and a README.txt.

**Defects to expect (verified by analysis, not by seeing the bundle):**
1. **The wheel step probably FAILED** (README.txt would say "INCOMPLETE"). vllm-omni requires
   `antlr4-python3-runtime==4.9.3` and `openai-whisper==20250625`, which are **sdist-only**, so `--only-binary=:all:`
   cannot resolve. Even if it succeeded:
2. It has **no `vllm` wheel**: vllm-omni does not declare vllm as a dependency (checked in the wheel METADATA).
3. It resolves **torch 2.14.0** (via torchsde/x-transformers), but **vllm 0.28.0/0.30.0 pin torch==2.13.0**,
   torchaudio==2.11.0, triton 3.7.1, cudnn-cu13 9.20.0.48 and nccl-cu13 2.29.7. vLLM's C extension is ABI-tied to
   torch, so torch 2.14 cannot be used for the engine. It is fine for the **eval** venv.
4. Some vLLM deps ship only `manylinux_2_31`/`2_34` wheels, which that platform list excludes.
5. **HF cache layout:** with `HF_XET_HIGH_PERFORMANCE=1`, large files are stored in a **top-level `hf_cache/blobs/<xx>/<sha>`**
   store, and `models--*/blobs/*` are symlinks into it (observed locally with WavLM). Its README says to copy only
   the `models--*` folders, which **would leave dangling symlinks**. Copy the whole `hf_cache` tree
   (`rsync -a qwen_tts_bundle/hf_cache/ ~/.cache/huggingface/hub/`) or set `HF_HUB_CACHE=<bundle>/hf_cache`, then check
   `find -L ~/.cache/huggingface/hub -type l` (it must print nothing).
6. Whisper: the ignore list does not exclude `model.fp32-0000{1,2}-of-00002.safetensors`, so the repo is ~9 GB
   instead of 3.1. That's harmless; transformers loads `model.safetensors` (fp16) by default.
7. `wavlm-base-plus-sv` has only `pytorch_model.bin`, which loads fine with torch ≥ 2.6 (weights_only).

Expected good parts: the three models. Verify sizes: Qwen `model.safetensors` 3,857,413,744 B (BF16, 1.929 B params)
+ `speech_tokenizer/model.safetensors` 682,293,092 B (F32); whisper `model.safetensors` ~3,087 MB; wavlm .bin
404,547,053 B (already complete locally). HF revision of the Qwen repo seen: `fd4b2543…`.

### 4.2 Bundle 2: `ops/get_bundle2.py` (given to the user to run on a fast machine)
It fetches, for Linux x86_64 / CPython 3.12 / glibc 2.39, into `qwen_tts_bundle2/` (no symlinks):
- sdists of `antlr4-python3-runtime==4.9.3`, `openai-whisper==20250625`, `sox==1.5.0`, plus pure-python wheels built
  from them, so `--only-binary` resolution works (`--find-links wheels`);
- pip/setuptools/wheel;
- sets: `omni28` = `vllm==0.28.0 vllm-omni==0.28.0` (required); `omni30` = `--pre vllm==0.30.0 vllm-omni==0.30.0rc1`;
  `qwentts` = `qwen-tts==0.1.1 torch==2.13.0 torchaudio==2.11.0`; `eval` = torch 2.13 + transformers 5.10-5.14 +
  jiwer, soundfile, librosa, scipy, matplotlib, speechbrain;
- each set is then **verified to install offline** (`pip install --dry-run --no-index --find-links wheels --target tmp
  --platform …`);
- models as plain folders: `speechbrain/spkrec-ecapa-voxceleb` (second speaker-similarity model); with `--all-models`
  also Qwen, Whisper, WavLM;
- `--have <bundle1>/wheels` drops identical files; writes `MANIFEST.txt` (sha256) and `README.txt`.

Status: **syntax-checked only**. A local test was aborted: my test set wrongly included openai-whisper, which pulls
torch over the slow link. The logic has not been end-to-end tested. If the user reports a failure, the likely
culprits are the platform tag list (35 `--platform` flags) or building the sdists (needs setuptools on the fast
machine).

### 4.3 Fallbacks if bundles are incomplete
- `wheels-extra/` holds the partial fetch of exactly the wheels bundle 1 lacks (`fetch28.txt`: 127 URLs, ~2.3 GB;
  `fetch30.txt`: 31 URLs, ~0.5 GB for the 0.30 pair). Resume with the same curl loop, or better, with
  `fetch_wheels.py` over `docs/research/artifacts/local-env/report-omni-0.28.0+vllm.json` (24 connections).
- **Reuse trick:** `/home/vector/translation-layer/.venv-translit` (Python 3.10) already has **torch 2.13.0+cu130**
  and exactly the NVIDIA libs vllm 0.28 needs (cublas 13.1.1.3, cudnn-cu13 9.20.0.48, nccl-cu13 2.29.7, cusparselt
  0.8.1; native sm_86 SASS verified with cuobjdump). The NVIDIA wheels are Python-agnostic, so copying them saves
  ~1.2 GB. A Python 3.10 engine venv (vllm is abi3, vllm-omni supports ≥3.10) could even reuse torch itself. This is
  non-standard, so prefer proper wheels. **Do not modify that venv** (it belongs to the translation-layer).
- The pip HTTP cache (`~/.cache/pip`, 3.1 GB) holds ~69 of the 239 engine wheels (0.86 GB), but not the heavy ones.

---

## 5. Research findings (details and citations in `docs/research/*.md`)

### 5.1 vLLM-Omni serving Qwen3-TTS (source-verified: `docs/research/omni-source.md`, `omni-issues.md`)
**Install:** `python3.12 -m venv V; V/bin/pip install vllm==0.28.0 vllm-omni==0.28.0` (239 packages, 4.14 GB; torch
2.13.0 cu130; flashinfer 0.6.16.post3; transformers 5.14.1; no flash-attn needed). The major.minor versions of vllm
and vllm-omni must match (a mismatch only warns). The PyPI vllm wheel is the CUDA 13.0 build with sm_86 in its arch
list, and driver 580 supports it.

**Pipeline (single GPU, `deploy/qwen3_tts.yaml`):**
- **Stage 0 `qwen3_tts` talker.** It samples codebook 0 with vLLM continuous batching (`max_num_seqs` 64), then
  runs the **code predictor (MTP, 5 layers) for codebooks 1-15 as 15 sequential sub-steps per frame**, batched
  across rows. It also contains the ECAPA speaker encoder and the 12 Hz tokenizer encoder (both bf16).
- **Stage 1 `code2wav`.** It holds the speech-tokenizer decoder (1920 samples per 80 ms frame at 24 kHz). It is
  **fp32 in 0.28** and bf16 in 0.30.
- Stages talk over a shared-memory connector.
- Defaults: `gpu_memory_utilization` 0.3 per stage, CUDA graphs on, `async_chunk: true`
  (`initial_codec_chunk_frames` 1, `codec_chunk_frames` 25, left context 72, `decode_batch_max_size` 4).
- Talker sampling defaults: temperature 0.9, top_k 50, **repetition_penalty 1.05**, `min_tokens` 2,
  `max_tokens` 4096. Sub-talker: 0.9 / 50 / 1.0.
- Talker KV is ≈112 KiB per token in bf16. At 0.3 the KV cache is small; ~0.45 is likely needed for c=32-64.
- **Memory rule:** requested = total × utilization, and **startup fails if free < requested** (vllm
  `v1/worker/utils.py` L444-464).
- Plan for GPU 1 (≈20 GB free): stage 0 ≈ 0.45 (10.8 GB) and stage 1 ≈ 0.18 (4.3 GB).

**Request schema** (`OpenAICreateSpeechRequest`, a plain pydantic model, so **unknown fields are silently
ignored**):
- Fields: `input, model, voice, task_type (Base), ref_audio (http/https/data:/file://), ref_text, language,
  response_format (wav/pcm/flac/mp3/opus), speed (0.25-4, post-hoc, not with streaming), stream, stream_format
  (sse/audio), x_vector_only_mode, speaker_embedding (2048 floats; forces x-vector-only), max_new_tokens (1..4096),
  seed, initial_codec_chunk_frames, non_streaming_mode, extra_params, word_timestamps`.
- `language` is validated: **"Urdu" → 400; use "Auto"**. For trump, try "English" as well as "Auto".
- `sample_rate` is not in 0.28 (it was added in 0.30).

**Sampling per request:**
- **Only `extra_params.{temperature, top_p, top_k}`** reach the talker, and only codebook 0.
- **`repetition_penalty` cannot be set per request**, neither top-level nor via extra_params (it lands in
  `extra_args`, which nothing reads). It is server-side only (YAML `default_sampling_params` or `--stage-overrides`).
  It acts **only on codebook 0 and is presence-based** (not count-based).
- ⇒ An rp sweep needs **one server config per value**, or the small patch the build workflow was asked to write
  (`engine/patches/`: add `repetition_penalty` to the extra_params loop at `serving_speech.py` ~L3079-3095 in 0.28,
  ~L2011-2042 in 0.30).
- Sub-talker sampling is server-side only.

**Seeds:**
- In 0.28, under the default full CUDA graphs, **a seeded row makes the MTP run row by row whenever batch > 1**
  (throughput collapse). Seeds are also not reproducible across batch compositions (#6361, #8009).
- ⇒ **Never send seeds on throughput runs.** A seed also disables the built-in retry.

**Built-in retry (PR #6728, in 0.28):**
- A Base request without `max_new_tokens` gets a cap of `min(4096, max(192, 12 × text_tokens))` codec frames.
- If the cap is hit (no EOS), a **non-streaming** request with neither seed nor max_new_tokens is retried once with a
  random seed. Otherwise it's an HTTP 500 (SSE: an error event; raw stream: cut off).
- It **does not catch skipped words, cut-short takes, or loops that eventually stop.** For Urdu, text is ~3.1-3.2
  Qwen tokens/word, so the cap is loose: 95-99 s loops fit under it.
- Sending `max_new_tokens` (the NOTES formula) disables that retry, so **the gateway must own retries.**

**Voices:**
- `POST /v1/audio/voices` is multipart: `audio_sample` (≤10 MB, 1-30 s) **or** `speaker_embedding`, plus `name`,
  `consent`, `ref_text` (enables ICL) and `speaker_description`. Also `GET /v1/audio/voices` and
  `DELETE /v1/audio/voices/{name}`.
- Voices persist as safetensors under `SPEAKER_SAMPLES_DIR` (default `~/.cache/vllm-omni/speakers`), capped at 1000.
- Features are cached in memory only: `ref_code` [T,16] and the x-vector (LRU 512 MiB). ICL prompt embeddings are
  rebuilt per request.
- Inline `ref_audio` and registered voices converge on the same caches. Inline costs a ~2-2.7 MB base64 body per
  request plus a SHA1 of it.
- A cold reference is encoded on the GPU inside the talker step, stalling the batch.
- **An averaged speaker embedding + ICL is only possible via `custom_voice_dir`**: precomputed safetensors with
  `speaker_embedding` + `ref_code` loaded at startup, generated with
  `ops/upstream/examples-qwen3_tts-0.28/precompute_custom_voice.py` (runs on CPU). The HTTP API alone cannot combine
  them.

**Streaming:**
- `stream=true` + `stream_format="audio"` with `response_format` pcm|wav. With wav, a 44-byte header (0xFFFFFFFF
  sizes) is sent right before the first PCM chunk.
- SSE: `speech.audio.delta` base64 events, then `speech.audio.done`.
- The first chunk comes after 1 codec frame, then every 25 frames (2 s).
- Published concern: streaming has audible gaps from c≥4 on a 3090 (#2562).

**Throughput knobs:**
- `async_chunk: true` (default) window-decodes even non-streaming requests. On a 4090 that cost ~15-40% throughput,
  +2-3.5 GB VRAM and a higher noise floor. `--no-async-chunk` exists in 0.28 (for batch work; "streaming" then
  arrives at the end).
- `--enforce-eager` (used in NOTES and in the docs' Base example) is global and **disables CUDA graphs on both
  stages** (~1.8× slower at c=1 on H200). Don't use it in production.
- Code2Wav batches at most 4 per group, effectively as batch-1 graph replays in 0.28.
- The talker is host-bound at high concurrency (#4855), so CPU speed matters.
- API-side CPU work runs on one event loop (single-thread tokenizer executor, synchronous WAV encode).

**Admission and health:**
- **No admission control or 429.** Excess requests queue in the scheduler without limit.
- `GET /health` returns 200, or 503 when a stage is dead (good for a watchdog). `/metrics` is Prometheus
  (`vllm_omni:*`, including `audio_ttfp_s`, `audio_rtf`, `request_queue_wait_s`).
- `--api-key` guards `/v1` only.
- Non-streaming responses carry `X-VLLM-OMNI-OUTPUT-TOKENS` (codec frames; ÷12.5 = seconds).
- The first start compiles FlashInfer JIT kernels (~158 s reported).
- `--api-server-count` is rejected under `--omni` in 0.28.

**Known crashes and bugs to design around:**
- **`voice` + inline `ref_audio` in the same request, with a label that changes, kills the talker** (#6970; the fix is
  only on main, after 0.30.0rc1). ⇒ The gateway must never send both.
- **Talker preemption under KV pressure can crash the engine or splice audio** (#4471 open, #6179/#6601). ⇒ Size the
  stage-0 KV cache so preemption never happens: set `max_num_seqs` from the concurrency the engine logs at startup,
  and cap concurrency in the gateway.
- A framework bug (#4355) can clone payloads across requests in a mixed batch. ⇒ Compare speaker similarity at 16
  mixed concurrent requests vs 1 request.
- Text with nothing speakable (e.g. `-------`) gave empty takes (fixed in 0.26).

**0.28 → 0.30.0rc1 differences:**
- MRV2 is the default runner (experimental; `model_runner: v1` opts out).
- Stage-0 `max_num_batched_tokens` drops from 32768 to 512.
- Code2Wav switches to bf16.
- Seeded batches stay batched.
- Bigger reference caches; `sample_rate` field; `--api-server-count` allowed (but it disables voice upload).
- Voice registration policy; stricter task/model validation.
- **Release CI for 0.30.0 produced looping garbage for voice-clone streaming (#8091, open).** ⇒ Pin 0.28.0; A/B 0.30
  only for evidence.

**Published RTX 3090 numbers (1.7B-Base voice clone, older vLLM-Omni 0.25/0.26):**
- PR #5202, streaming, per-request RTF (compute/audio) and TTFA: c1 0.222 / 143 ms; c4 0.308 / 203 ms;
  c8 0.431 / 364 ms; c16 0.718 / 837 ms.
- PR #5253, aggregate × realtime: 4.07 at c1, 9.57 at c4, 12.39 at c8, 14.10 at c16, 15.50 at c32, 17.39 at c64.
- Expect **~12-18× realtime aggregate and ~8-12 realtime streams per 3090**, roughly 10× faster per request than the
  Kaggle T4 fp32.
- Scale references: 2×H100 nightly 43× at c64; the vLLM blog (2×H20) 26-43× at c64 with TTFA 70 ms at c1 and
  1.13 s at c64.

### 5.2 The model and the official `qwen-tts` 0.1.1 (`docs/research/qwen-tts-internals.md`)

**Size and precision:**
- 1.929 B params in BF16: talker 1.409 B (28 layers, hidden 2048, 16 query / 8 KV heads × 128), text embedding
  311 M, code predictor 175 M, ECAPA ~12 M → 2048-d. Speech tokenizer 170.6 M (F32).
- Weights: bf16 4.20 GB total, fp32 8.40 GB.
- **Use bf16. fp16 overflows** (logits > 65504; NaN on Turing; #43, PR #355). fp32 gains nothing since the weights
  are bf16. Use **sdpa**, not FA2 (FA2 gave NaN logits in #333).

**How a frame is produced:** 1 talker forward (codebook 0; specials suppressed except EOS 2150) + **15 code-predictor
forwards**, plus HF generate overhead. Stock qwen-tts is CPU/dispatch-bound (4-16% GPU utilization, #89/#132).

**Repetition penalty:** it applies only to codebook 0, over the set of codebook-0 tokens generated so far
(presence-based, no window). The reference codes and the text are never penalised.

**Generation defaults:** talker temperature 0.9, top_k 50, top_p 1.0, rp 1.05, **`max_new_tokens` 8192
(~655 s!)**, `min_new_tokens` 2. Sub-talker: same sampling, exactly 15 tokens, no rp.

**Failure modes:**
- About **0.5% of Base generations miss EOS** (#118); a tight per-request cap is essential.
- Mixed or unsupported scripts hang (#318).
- **The output start can echo the tail of the reference** (#341). **The shehbaz reference ends with
  "السلام علیکم"**, so watch for a leading greeting.

**Text layout (non_streaming_mode):** the clone default `non_streaming_mode=False` sums reference and target text
over the reference frames. With 23-28 s references this is reported to cause **speaking-rate drift** (+16.7%), which
`True` removes (PR #362, #239). vLLM-Omni exposes `non_streaming_mode` as a request field. **Benchmark True vs False**
for the Urdu failures.

**Languages:** `auto` + zh/en/de/it/pt/es/ja/ko/fr/ru. Urdu → use Auto (no language tag).

**Tokenization:**
- Urdu is ~3.1-3.2 Qwen tokens/word, ~0.71 tokens/char (English 1.3 tokens/word).
- Pool means in text tokens (short/medium/long/xlong): Urdu 33/82/194/304, English 13/33/77/154.
- Tokenizer quirk (transformers 4.57.3, local-dir load): 4 of 576 Urdu texts tokenize differently. Minor; pin one
  loading path.
- Strip input text: a leading newline shifts the text slice.

**Speaker embedding:** `extract_speaker_embedding` needs 24 kHz audio, returns an **unnormalised** 2048-d vector and
is inserted raw, so its norm matters. The NOTES "mean over clips rescaled to typical norm" is doable by setting
`VoiceClonePromptItem.ref_spk_embedding`.

**qwen-tts as a backend:**
- No audio streaming.
- Static left-padded batching, with sampling and max_new_tokens shared per batch; latency = the longest (or runaway)
  row.
- **Not thread-safe** (rope_deltas is instance state), so it needs a single worker per instance.
- It re-decodes 23-28 s of reference audio and re-prefills the reference on every call.
- Forced `output_hidden_states` roughly doubles per-token memory.
- A reasonable **control baseline** only.

**Official numbers** (paper, Qwen's internal vLLM V0 engine, unnamed GPU): 1.7B first packet 101 ms, RTF 0.313 at
c1, 0.463 at c6. Quality for 1.7B-Base: Seed test-en WER 1.24, multilingual EN WER 0.934 / SIM 0.775. Community
numbers for qwen-tts: RTF ~1.47 on H100, ~0.97 on a 3090 (CustomVoice, batch 1).

### 5.3 Alternatives (`docs/research/alternatives.md`)
Ranked to benchmark against vLLM-Omni:
1. **SGLang-Omni 0.1.6.**
   - Pros: continuous batching, CUDA graphs, streaming, ICL and x-vector cloning, **per-request repetition_penalty
     and seed**, 503 admission control, the same `/v1/audio/voices` shape. It is Boson's engine for Higgs TTS 3.
   - Cons: **unvalidated on the 3090** (roadmap: 4090/5090 only); a heavy stack (torch 2.13, cu130 flashinfer,
     flash-attn-4, nixl, mooncake; Docker recommended); TTFP > 1 s from c≥24 for Base.
   - Defaults `mem_fraction_static` 0.85, which must be lowered here. Time-box it.
2. **faster-qwen3-tts 0.4.0** (MIT, CUDA graphs over a static KV).
   - Fastest single stream: 4090 4.22× realtime at 174 ms TTFA.
   - **Batch 1 only**, so concurrency needs replicas.
   - Supports precomputed prompts (averaged embedding + ICL).
3. **qwentts.cpp** (GGML C++): continuous batching at frame boundaries (`--max-batch`), per-request rp and seed,
   BF16/Q8_0/Q4_K_M, `language=auto`. No published GPU numbers, single maintainer; builds here (cmake 3.28, g++ 13,
   CUDA 12.8).

Other candidates:
- VoxServe: runner-up.
- Rejected: nari-qwen3-tts (H100/FP8 only), nano-qwen3tts-vllm (no license), qwen3-tts-fast-serve (hard-coded
  sampling), concurrent-faster-qwen3-server (no auto language), TensorRT-LLM (not planned), LMDeploy (no TTS).
- An independent H100 comparison (CustomVoice, streaming) ranked **vLLM-Omni strongest**: sustained 20 RPS vs 12 for
  SGLang-Omni and 8 for VoxServe.

**Higgs TTS 3** (`bosonai/higgs-tts-3-4b`) is also served by vLLM-Omni 0.28 (deploy profiles present) and by
SGLang-Omni. **The license is Research/Non-Commercial; production use needs a commercial license from Boson AI.**
It has a ~30 s generation ceiling, so the gateway must split sentences.

**Recommendation carried into DESIGN.md:** vLLM-Omni 0.28 primary, gateway with swappable backends, qwen-tts
control. Build SGLang-Omni/faster-qwen3-tts backends only if time allows after the main matrix.

### 5.4 Environment (`docs/research/local-env.md`)
Covered above (§2, §4). Extra points:
- qwen-tts cannot share a venv with vllm-omni (transformers 4.57.3 vs ≥5.10.1). Pinning torch 2.13 keeps its extra
  download at ~0.15 GB.
- faster-whisper 1.2.1 / ctranslate2 4.8.2 would use the system libcublas.so.12 (no cuDNN needed); runtime load
  UNVERIFIED.
- The resolved stack pulls CUDA **13.4** JIT tools (nvcc/nvvm/nvjitlink 13.4.92) while the driver is 13.0. Any PTX
  JIT path could fail (UNVERIFIED); SASS paths are fine.
- Process note from that agent: it ran `sudo -n true` once, which failed harmlessly.

### 5.5 Eval tooling (`docs/research/eval-tooling.md`, 31 findings, READ IT)
The eval research agent finished after the first push. It **built and calibrated a working eval stack on CPU**, now
copied out of the temporary scratchpad:
- `models/eval/` (gitignored, 4.6 GB, sha256-verified): `faster-whisper-large-v3` (stock Whisper large-v3 converted to
  CTranslate2, Systran rev edaa852e, model.bin sha 69f74147…), `wavlm-base-plus-sv`, `beatrice/` (the seed-tts-eval
  **WavLM-Large + ECAPA-TDNN** SV model, torch-native port), `sb_ecapa_embedding_model.ckpt` (SpeechBrain ECAPA).
  **So the Whisper in the user's bundle is not needed for eval.**
- `venvs/eval-asr` (faster-whisper 1.2.1, ctranslate2 4.8.2, jiwer) and `venvs/eval-sim` (torch 2.11 CPU,
  transformers 5.17, jiwer, soundfile). Both were copied from the scratchpad, so call them as `venvs/<v>/bin/python`.
  Their `bin/*` script shebangs point to the old paths.
- `eval/lab/`: `asr_eval.py` (WER/CER/CER-nospace, loop/skip checks, VAD audio checks, decode diagnostics; reads
  `results/<ts>/requests.jsonl`), `sim_eval.py` (SIM vs the prompt reference and vs a held-out-clip centroid;
  backends `base`/`large`; models via `eval/models` → `../models/eval`), `tts_textnorm.py` (Urdu + English
  normalizers), `tts_checks.py` (detectors), `retry_sim.py` (offline retry-policy simulation), calibration
  manifests/outputs (`asr_refs_int8*.jsonl`, `asr_synth.jsonl`), and `synth/` (synthetic loop/gap/truncation WAVs
  spliced from the reference clips; gitignored).
- ASR on GPU needs cuBLAS 12 on the loader path: `LD_LIBRARY_PATH=/usr/local/cuda-12.8/lib64` (or pip
  `nvidia-cublas-cu12`). Don't mix ctranslate2 into a torch-cu13 venv. Pass
  `--model /home/vector/qwen3-tts-server/models/eval/faster-whisper-large-v3`.

Key findings that change the plan:
- **ASR = faster-whisper large-v3** (fp16, beam 5, sequential long-form, **language forced** en/ur, `vad_filter=False`).
  Reject vLLM Whisper for scoring: it pre-splits audio > 30 s and can drop audio, hiding loops.
  `BatchedInferencePipeline` doesn't batch across files, so use several CT2 workers instead. Estimate ~4.5 GB per
  worker, **on GPU 0**.
- **Whisper's own Urdu error is ~18-26% WER on real speech**, so NOTES' "WER > 0.22 → re-roll" is unusable for Urdu.
  **Report WER, CER and CER-nospace, and gate Urdu on CER-nospace**: word segmentation varies (صورتحال vs صورت حال),
  and two spacing variants cost WER 0.105 but CER-nospace 0.
- **Whisper large-v3 swallows synthetic Urdu loops**: a syllable repeated 12× or a phrase 3× gave an unchanged
  transcript. So loops must be caught by audio and alignment checks (unaligned tail, char ratio, VAD gaps, repeated
  n-grams), not by WER alone. Compression ratio is computed on UTF-8 bytes, so the Urdu baseline runs higher
  (1.45-2.11) than English. Loops score 14-18.
- Text normalizers: English uses Whisper's `EnglishTextNormalizer` (vendored, no torch). For Urdu, **don't use
  BasicTextNormalizer**, which splits words on combining marks. Use `UrduNormalizer` (NFKC, hamza/yeh/kaf/heh
  folding, digit mapping, drop ZW*/bidi marks, strip diacritics and punctuation).
- **Speaker similarity:** primary is **seed-tts-eval SIM (WavLM-Large + ECAPA)**. Calibration: same-speaker
  0.90-0.95, cross-speaker 0.11-0.18. Secondary is `wavlm-base-plus-sv` for continuity with NOTES ("0.974";
  same-speaker ≥0.975, cross-speaker 0.75-0.80, a compressed range). Compute SIM-prompt (vs
  `references/qwen3-tts.wav`) and SIM-heldout (vs the centroid of clips not in the prompt; shehbaz 02-06). SIM runs
  on **CPU** (WavLM-large at 15× realtime, ~26 min per 6.6 h of audio), so no GPU is needed.
- **The `bench_tts.py` "suspect" band misses all 4 known Kaggle Urdu failures** (their s/word 0.22, 0.25, 1.01 and
  1.01 all fall inside 0.18-1.1; good Qwen Urdu runs ~0.25-0.33 s/word). Replace it with a **voice-relative band**
  plus the detector suite: char_ratio outside 0.85-1.15, deletion run ≥4 (ur) / ≥3 (en), insertion run ≥4, n-gram
  repeat excess ≥4, unaligned tail, VAD gaps. **Also update the gateway's `quality.py` suspect logic
  accordingly.**
- **Retry evaluation:** generate **K=6 seeded takes per prompt per setting** (bench `--takes 6 --seed B`; seeds pair
  across rp settings). Label gate_pass online and "bad" offline, then simulate R retries empirically; **don't assume
  f^(R+1)**, since failures cluster on hard prompts. **Sample size:** the Kaggle 5/46 has a 95% CI of 4.7-23%.
  Detecting 11% → 4% needs ~221 takes per arm, so use ≥43 xlong prompts × K=6 per rp value. (Seeds are fine in
  these quality runs; just not in throughput runs.)
- Run eval after the load tests, never alongside them, so it doesn't perturb them.

---

## 6. Auralis baseline (do NOT run Auralis)
The user pasted Auralis's README numbers. The same GPU model (RTX 3090 24 GB) was used, but with the **Pashto** model,
the full proxy stack, 20 concurrent, and `benchmark_tts.py` (not the Urdu pools):

| Metric | Before | After |
|---|---|---|
| Single request | 1.46 s | 0.32 s |
| 20 concurrent, ~3 s clips | – | p50 0.52 s |
| 20 concurrent, ~5 s clips (burst) | mean 2.46 s | mean 0.73 s, p99 0.90 s |
| 20 concurrent sustained (200 reqs) | mean ~3.2 s, p99 5.7 s | mean 0.86 s, p99 1.2 s |
| Aggregate throughput | ~28× realtime | ~110× realtime |
| GPU utilization under load | low (CPU-bound) | 67% avg / 96% peak |

Auralis Urdu request settings (from `benchmark_tts_urdu_new.py`): temperature 0.4, top_k 50, top_p 0.85,
repetition_penalty 2.0, length_penalty 1.0, enhance_speech, voice_key registry; defaults `-n 20 -c 20`. Its pools
are in `tts-reference-voices/bench/pools/auralis_ur.json`:

| pool | texts | words (min / mean / max) |
|---|---|---|
| short | 151 | 6 / 8.9 / 12 |
| medium | 105 | 10 / 17.3 / 21 |
| long | 21 | 38 / 42.4 / 49 |

Run: `bench_tts.py --voice shehbaz --pools bench/pools/auralis_ur.json --size short medium long -n 20 -c 20` plus a
sweep. Expect Qwen3-TTS 1.7B to be several times slower than Auralis/XTTS on this GPU (~12-18× vs ~110× realtime),
and say so plainly in the report together with the quality comparison. Auralis's optimization lessons (CUDA graphs,
multi-step scheduling, GPU repetition penalty, voice-key registry, micro-batched vocoder, no per-request
`empty_cache`, uvloop) are summarized in `docs/auralis_baseline.md`.

---

## 7. Build workflow (STOPPED at the user's request, ~19:40)
**Final status:** `build:gateway-core` DONE, `build:engine-ops` DONE, `build:bench-orchestration` DONE (their reports
are in `docs/build-reports.md`). **`build:vllm-omni-backend` was stopped mid-run.** `backends/vllm_omni.py`,
`tests/fake_vllm_omni.py` and `tests/test_vllm_omni_backend.py` exist but may be incomplete: run the tests and finish
them. **`review:engine-ops` and `review:bench` were stopped mid-run** (their partial fixes are unreviewed).
`review:gateway` and `integrate:cpu-smoke` never ran, so do those checks yourself (the prompts in §7 below list what
they cover).

**Wheels:** the background fetch **completed: all 158 wheels (2.8 GB) in `wheels-extra/`**, i.e. everything bundle 1
lacks for vllm 0.28.0 + vllm-omni 0.28.0 and for vllm 0.30.0 + vllm-omni 0.30.0rc1 (per `fetch28.txt`/`fetch30.txt`).
Together with bundle 1's wheels that should be a complete offline set; verify with
`pip install --dry-run --no-index --find-links <bundle1>/wheels --find-links wheels-extra vllm==0.28.0 vllm-omni==0.28.0`.
Bundle 2 (`ops/get_bundle2.py`) is then only needed if that dry-run fails.

### Original plan of the workflow
Workflow run `wf_d349d909-b7a` ("qwen3-tts-build"). Its journal (one line per agent result):
`/home/vector/.claude/projects/-home-vector/60c91189-44d6-4cdb-b0f5-2bf4adb23fb3/subagents/workflows/wf_d349d909-b7a/journal.jsonl`.
Branches:
1. **gateway-core** → `gateway/tts_gateway/` (config, voices, textproc, audio labelling, admission 429/503, quality
   and retry, JSON logs, Prometheus metrics, backends/{base,stub,higgs_sglang}, app, `__main__`) + pytest suite; then
   **vllm-omni-backend** → `backends/vllm_omni.py`
   - content-addressed voice registration: `<id>-<sha256[:10]>`;
   - `extra_params` mapping; rp gated by `TTS_ENGINE_PER_REQUEST_RP`;
   - never sends `voice` together with `ref_audio`;
   - PCM streaming; error mapping;
   - `tests/fake_vllm_omni.py`, a fake engine for CPU tests;
   - then an adversarial review and fixes.
2. **engine-ops**, then an adversarial review:
   - `engine/install_engine.sh` (offline install from wheels + patches);
   - `engine/deploy/qwen3_tts_prod.yaml`, a full copy tuned for one 3090 with the 4.4 GB co-tenant;
   - `engine/make_variant.py` and `engine/deploy/variants/*.yaml`: default, no_async_chunk, eager, fp16_talker,
     fp32_talker, seqs32, seqs128, rp110, rp115, rp120, decode8;
   - `engine/patches/apply_patches.py` (per-request rp via extra_params, 0.28 and 0.30);
   - `engine/run_engine.sh` (CUDA_VISIBLE_DEVICES=1, HF offline, clean CUDA env, `vllm serve … --omni
     --deploy-config`);
   - `engine/wait_ready.py`;
   - `deploy/systemd/*.service`, `deploy/env.example`, `deploy/install_units.sh` (not enabled).
3. **bench-orchestration**, then an adversarial review:
   - `bench/run_plan.py`: resumable phases; starts/stops the engine and gateway; snapshots; DONE markers;
     `--dry-run/--list/--only`;
   - the plan (phases P0-P7 below);
   - `bench/collect.py`.
4. **integrate:cpu-smoke**: gateway + fake engine + bench_tts.py end to end; checklist.

**On pickup:** check the journal for results. For each of `gateway/`, `engine/`, `deploy/`, `bench/`, run the tests
(`cd gateway && ../venvs/gateway/bin/python -m pytest -q`), `bash -n` the scripts, and `run_plan.py --dry-run --list`.
If the workflow died midway, resume it with
`Workflow({scriptPath: "<the script path printed in the session>", resumeFromRunId: "wf_d349d909-b7a"})` in the same
session, or re-implement the missing pieces from DESIGN.md. None of it has touched a GPU. The **engine flags,
YAML keys and patch targets must be re-verified against the installed 0.28 package at runtime.**

---

## 8. Benchmark plan (P0-P7) and measurement rules

| phase | what | notes |
|---|---|---|
| P0_smoke | 1 short request per voice, non-stream + stream, engine direct + via gateway | confirm WAV, headers, label |
| P1_screen_* | variants default, no_async_chunk, eager, fp16_talker, fp32_talker, seqs32, seqs128, decode8, 0.30rc1 default; both voices, medium, c=1,8,32, n=max(16,2c); stream for default + no_async_chunk | pick the production config |
| P2_matrix | chosen config; both voices × short/medium/long/xlong × c=1,2,4,8,16,32,48,64; non-stream | main table |
| P3_stream | same with `--stream` (TTFA p50/p90/p99) | on an async_chunk config |
| P4_voice_mode | registered (`--voice-mode upload`) vs inline, c=1,8,32, medium, both voices, engine direct | |
| P5_urdu_rp_* | rp 1.05/1.10/1.15/1.20 (variants or patched per-request rp); shehbaz long + xlong `--takes 3`, c=16; trump xlong `--takes 2` control | failure rate + WER/SIM cost |
| P6_auralis | shehbaz `--pools auralis_ur.json` short/medium/long: `-n 20 -c 20` and sweep 1,4,8,16,32,64 | apples-to-apples |
| P7_gateway | gateway (retries 0 vs 1) vs engine direct at c=1,16 medium/xlong | overhead + live retry behaviour |

Extra experiments worth adding if time allows:
- `non_streaming_mode` true vs false (Urdu pace drift / skips);
- `language` English vs Auto for trump;
- averaged speaker embedding via `custom_voice_dir`;
- the length-cap formula on vs off;
- the mixed-batch payload-leak guard (#4355): SIM at c=16 mixed voices vs c=1.

**Rules:**
- **No `--seed` in throughput phases.**
- The rp sweep must change the server config (or use the patched per-request rp). Top-level `--param
  repetition_penalty` against the engine does nothing.
- Sampling on engine-direct runs goes via `--param 'extra_params={...}'`.
- Always `--gpus 1`. Nothing else runs on GPU 1 during benchmarks. Eval runs on GPU 0.
- Record engine YAML, versions, `nvidia-smi` and CPU governor per phase.
- Disable gateway retries in the performance matrix so retries don't hide failures, and measure retries separately
  (P5/P7).
- Watch the engine log for the KV "maximum concurrency" line and for preemption warnings. Preemption means reducing
  `max_num_seqs` or raising stage-0 memory.
- Keep all audio (`results/`, gitignored). Never publish it.

---

## 9. Runbook for the next session

1. **Read** this file, `docs/DESIGN.md` and `docs/research/*.md`. Check the GPU tenants:
   `nvidia-smi --query-compute-apps=pid,used_memory --format=csv`. Expect only the translation-layer (4.4 GB per GPU).
2. **Receive the bundles** (the user copies them into this box, probably under `/home/vector/`):
   - bundle 1: `rsync -a qwen_tts_bundle/hf_cache/ ~/.cache/huggingface/hub/`, then
     `find -L ~/.cache/huggingface/hub -type l` (it must print nothing). Also check `wheels/README.txt` for
     "INCOMPLETE".
   - bundle 2: check `README.txt` (every set OK) and `MANIFEST.txt` (`sha256sum -c`).
   - Verify the model files load offline: `HF_HUB_OFFLINE=1`.
3. **Engine venv (0.28):**
   `python3.12 -m venv venvs/engine && venvs/engine/bin/pip install --no-index --find-links <bundle2>/wheels
   --find-links <bundle1>/wheels --find-links wheels-extra vllm==0.28.0 vllm-omni==0.28.0`
   (or `engine/install_engine.sh`). Then run `engine/patches/apply_patches.py` for per-request rp. Optionally repeat
   as `venvs/engine30` for 0.30.0rc1 (with `model_runner: v1` as well as default MRV2).
4. **Eval:** already set up (§5.5): `venvs/eval-asr` + `venvs/eval-sim` + `models/eval/` + `eval/lab/*.py`.
   Smoke them on the reference clips first (`sim_eval.py --calibrate`).
5. **First GPU start** on GPU 1: `engine/run_engine.sh engine/deploy/qwen3_tts_prod.yaml 8091`.
   - Expect a FlashInfer JIT compile (minutes). If JIT fails, it is likely the nvcc/CUDA_HOME issue (§2.1) or
     CUDA 13.4 PTX vs driver 13.0.
   - Watch memory against the ~20 GB free, and the KV max-concurrency log line.
   - Then `engine/wait_ready.py`.
6. **Smoke**, engine direct:
   `curl -s localhost:8091/v1/audio/speech -H 'Content-Type: application/json' -d
   '{"input":"Hello there.","task_type":"Base","language":"English","ref_audio":"data:audio/wav;base64,…","ref_text":"…","response_format":"wav"}' -o /tmp/x.wav`.
   Then register the voices and repeat with `voice`.
7. **Gateway:** `cd gateway && TTS_API_KEY=… TTS_BACKEND=vllm_omni TTS_ENGINE_URL=http://127.0.0.1:8091
   ../venvs/gateway/bin/python -m tts_gateway` (port 8090); check `/ready`, then run `bench_tts.py --url
   http://127.0.0.1:8090 --api-key … --gpus 1`.
8. **Run the plan:** `venvs/gateway/bin/python bench/run_plan.py --list`, then phase by phase (P0 → P1). Choose the
   config, set it in the plan, then run P2-P7.
9. **Quality eval** on GPU 0 over every `results/*/requests.jsonl` + audio: WER/CER, SIM, loop/skip detectors, Urdu
   failure rate per rp, retry simulation from `--takes`.
10. **Production:** `deploy/install_units.sh` (creates `~/.config/qwen3-tts/env` with a random key, mode 600), then
    enable and start the units with `XDG_RUNTIME_DIR` set. Put the chosen config in the prod YAML.
11. **Write** README.md (how to run and operate), REPORT.md (tables: latency percentiles, TTFA, × realtime, req/s,
    GPU memory, errors, suspects, WER/CER, SIM, Urdu failure rates vs rp/retry, the Auralis comparison; the
    recommended config: engine, precision, max concurrency, batching, streaming, retry policy), and `bench/collect.py`
    output. State caveats honestly (Pashto vs Urdu Auralis numbers, shared GPU, CPU governor, vLLM-Omni version).

---

## 10. Open questions / decisions pending
- Engine config choice depends on P1:
  - `async_chunk` on (streaming TTFA) vs off (throughput/quality). Possibly two engine profiles, or one decision per
    deployment.
  - `max_num_seqs` and the stage-0 memory split, given the ~20 GB free.
- Whether per-request rp (the patch) is worth carrying in production, vs one server-wide rp. English and Urdu may want
  different values.
- The retry policy defaults (`TTS_RETRY_MAX`, thresholds) are provisional until the P5/P7 + eval data.
- Whether the gateway should split long texts at sentence boundaries even for Qwen (loop risk grows with length;
  parallel chunk generation could cut long-text latency). Untested idea.
- Whether the stopped Whisper STT servers must come back, and on which GPU/utilization (ask the user before they
  do; they would compete with the TTS engine).
- Whether the gateway must be reachable from the LAN (firewall unknown), and who the clients are.

## 11. GitHub
- The box had **no GitHub credentials**. At the user's choice, pushes use an **SSH deploy key** generated on the box:
  `~/.ssh/tts_reference_voices_deploy` (ed25519; the public key must be added under the repo's Settings → Deploy keys
  with write access). `/home/vector/tts-reference-voices` has `core.sshCommand` set to use it, and a pushurl of
  `git@github.com:paradox-prx/tts-reference-voices.git`. GitHub's host key was checked against GitHub's published
  ed25519 fingerprint before being added to `~/.ssh/known_hosts`.
- **Everything goes to branch `qwen3-omni-bench`** of the **public** repo `paradox-prx/tts-reference-voices`: the
  bench changes + `bench/pools/auralis_ur.json` + this project under `server/` (via `git subtree`). The user accepted
  that the internal paths, ports and service names in these docs become public.
- Never commit `venvs/`, `wheels-extra/`, `results/` (AI-generated audio), `logs/`, `state/`, `ops/upstream/`
  (third-party sources; re-downloadable) or any key/env file (see `.gitignore`). Before each push, scan staged files
  for secrets. The pip reports in `docs/research/artifacts/` were slimmed to drop upstream READMEs, which contained
  public badge tokens that would trip secret scanners.

## 12. Session log (for context)
- 17:31: box inspected; the GPUs were full (2 Whisper vLLM servers at 75% + the translation-layer).
- 17:32: research workflow `wf_6c83c01a-7e3` launched (6 topics + verify + decision memo; the verify and decision
  steps had not run when this was written).
- 17:35: the user said to stop the Whisper servers; stopped them with SIGTERM (clean exit, GPU memory released).
- 17:38-18:15: model downloads crawled at 0.3-3 MB/s. On the user's instruction, stopped and removed the partials
  (WavLM completed).
- 17:40-17:50: bench_tts.py extended and stub-tested. Auralis pools extracted. The user said don't test Auralis, keep
  all outputs, and use stock Whisper.
- 18:17: DESIGN.md written; the build workflow `wf_d349d909-b7a` launched.
- 18:20: the user's bundle-1 script reviewed; its defects identified (§4.1); started a resumable fetch of the missing
  wheels into `wheels-extra/`.
- 18:45: `ops/get_bundle2.py` written for the fast machine.
- 18:50: the user asked for this handoff + GitHub push.
