# Build workflow reports (wf_d349d909-b7a, stopped 2026-09-24 at the user's request)

Final reports of the agents that finished. `build:vllm-omni-backend`, `review:engine-ops` and `review:bench` were
stopped mid-run: their partial edits are in the tree but unreviewed. `review:gateway` and `integrate:cpu-smoke` never ran.

## build:gateway-core

The gateway package and its tests are in place under `/home/vector/qwen3-tts-server/gateway`, and all 62 tests pass. The real server ran with the stub backend, served curl and bench_tts.py without errors, and I stopped it. Nothing touched the GPUs and nothing was downloaded. Everything below was run against the stub only: there is no engine yet.

**Files created** (the gateway directory did not exist before)
- `gateway/pyproject.toml`: dependencies and pytest settings.
- `gateway/tts_gateway/`: `__init__.py`, `config.py`, `logs.py`, `metrics.py`, `admission.py`, `textproc.py`, `audio.py`, `voices.py`, `quality.py`, `app.py`, `__main__.py`.
- `gateway/tts_gateway/backends/`: `__init__.py`, `base.py`, `stub.py`, `higgs_sglang.py`.
- `gateway/tests/`: `conftest.py`, `test_units.py`, `test_app.py`.

**Choices that go beyond DESIGN.md**
- **Unknown request fields get a 400.** The engine silently ignores them. `task_type` ("Base") and `stream_format` ("audio") are accepted so bench_tts.py and other vLLM-Omni clients still work. Fields sent as `null` count as absent.
- **Engine not up yet:** `/health` answers straight away. Startup keeps retrying (with a growing delay) until the engine is healthy, then registers every voice and warms each one up. Only then does `/ready` turn 200. `/ready` checks the engine's health on every call, so it goes back to 503 if the engine dies.
- **Queue waits and client disconnects:** while a request waits for a slot or runs on the engine, a client disconnect cancels the work and frees the slot within the same event-loop step. A stream holds its slot until it ends and closes the backend stream when the client leaves. An engine error after the first byte drops the connection, so the client never gets a short file that looks complete.
- **Sampling defaults:** the gateway passes `temperature=None` / `top_k=None` when the client didn't set them. The backend applies its own defaults, so a later Higgs backend can use 0.8.
- **Other behaviour:**
  - The gateway enforces `TTS_REQUEST_TIMEOUT_S` itself, as a backstop to the backend's own timeout.
  - A seeded request that is retried gets seed+1, otherwise it would repeat the same take.
  - Splitting text for a backend's per-call audio limit (`max_seconds_per_call`) is implemented for both normal and streaming requests.
  - Extra headers `X-TTS-Sample-Rate` and a `request_too_large` limit of 16 MB on the request body.
  - Prometheus `*_created` series are turned off.

**Notes for whoever writes `backends/vllm_omni.py`**
- The factory calls `VllmOmniBackend(settings, voices)`.
- `stream()` must be an async generator of PCM16 chunks, and closing it must cancel the engine call.
- `capabilities.sample_rate` is used for the streaming WAV header.
- The gateway always asks for `response_format="pcm"`.
- `register_voice` is only called when `TTS_VOICE_MODE=registered` and `capabilities.voice_registry` is true.
- Errors map as follows: an engine codec-limit error or 5xx becomes `EngineFailure(retryable=True)`, and a 4xx becomes `EngineBadRequest`.
- The gateway sends `max_new_tokens`, which switches off the engine's own retry, so the gateway does the retrying.

**How I tested**
- `cd /home/vector/qwen3-tts-server/gateway && /home/vector/qwen3-tts-server/venvs/gateway/bin/python -m pytest -q` gives **62 passed in about 6 s**. It is also clean under `-X dev -W default`, pyflakes and pycodestyle (line length 120; the linters were installed in the scratchpad, not the venv).
  - The tests cover every case in the task list.
  - They also cover validation errors, body and ref-audio size limits, the text-splitting path, the JSON log fields, the retry settings, and startup waiting for an unhealthy engine.
  - One test loads the real trump and shehbaz voices; both pass the sha256 check.
- Real server: `TTS_BACKEND=stub TTS_API_KEY=smoke-key TTS_PORT=18437 TTS_ALLOW_INLINE_REF=1 python -m tts_gateway`.
  - curl checked the health, ready, models and voices routes, WAV and streaming output with the expected headers, the 404, an http `ref_audio` being rejected, and the JSON log lines.
  - Disconnecting at 0.5 s (normal and streaming) was logged as `cancelled`/499 at about 500 ms, and in-flight went back to 0.
  - After SIGTERM, a 2.8 s request that was already running finished with 200 before the shutdown event was logged.
- bench_tts.py with `-n 8 -c 4 --size short`, with nvidia-smi taken off PATH so the GPUs weren't queried:
  - Four runs: registered trump and shehbaz, inline for both voices, streaming trump, and a second server with `TTS_STUB_SUSPECT_TAKES=1`.
  - Every run was 8/8 OK with 0 suspect and 0 errors. The injected run showed `retries=1` on every request, and `tts_retries_total{reason="too_short"}` matched.
  - Results are in `/home/vector/qwen3-tts-server/results/_smoke_stub`; the audio is AI-labelled and must not be published.
- Both servers I started are stopped and port 18437 is free. I did not touch the listeners already on 18090 and 18091.

**Known gaps**
- Nothing has been run against real vLLM-Omni yet.
- bench_tts.py has no mode for a voice the server already knows: its `--voice-mode upload` calls POST `/v1/audio/voices`, which the gateway doesn't provide. The workaround is `--param voice=<id> --param ref_audio=null --param ref_text=null`. Its default inline mode needs `TTS_ALLOW_INLINE_REF=1`.
- The suspect check and the length cap only work for en and ur. For other scripts (e.g. Chinese) both are switched off, because splitting on spaces can't count words there.
- The engine's `X-VLLM-OMNI-*` token headers and `codec_frames` are not passed on to clients.
- When an engine error cuts a stream after the first byte, uvicorn adds one plain log line ("ASGI callable returned without completing response").
- `Retry-After` is only a rough estimate from recent request times, and there are no per-client rate limits.

## build:bench-orchestration

Both scripts and the plan are written, and the whole runner path works on CPU with the stub. The real engine path is untested because the engine venvs don't exist yet: it stops at the "missing venvs/engine/bin/vllm" check.

**Files** (all new, nothing outside `bench/` changed):
- `/home/vector/qwen3-tts-server/bench/run_plan.py`
  - **Engine start:** runs `bash engine/run_engine.sh <yaml> <port> venvs/<key>` in its own process group with `CUDA_VISIBLE_DEVICES=1`, logging to `logs/engine_<phase>.log`.
  - **Readiness:** polls `/health` and fails fast if the process dies, then runs `engine/wait_ready.py <url> --timeout <remaining budget>`.
  - **Gateway:** `python -m tts_gateway` bound to 127.0.0.1, waits for `/ready`, logs to `logs/gateway_<phase>.log`.
  - **Bench:** appends `--url --out results/<phase>/ --gpus 1 --tag <phase>[_suffix]`. Output goes to `bench_NN_<via>.log` and the console. nvidia-smi and engine/gateway `/metrics` are snapshotted before and after every command.
  - **phase.json:** versions (read from package metadata, no imports), the exact YAML (also copied to `deploy.yaml`), environment with secrets redacted, source hashes, host and CPU governor, commands, exit codes and GPU release status.
  - **Stop:** SIGINT, then SIGTERM, then SIGKILL to the process group, then any descendants that left it. GPU 1 must return within 256 MiB of its pre-engine level, or the run aborts.
  - **Flags:** `--only` (globs allowed), `--list`, `--dry-run`, `--force`, `--stop-on-error`, `--plan`, `--results`, `--logs`, `--engine-port`, `--gateway-port`, and the hidden `--stub` (engine kind `stub` also works in a plan).
  - **Resume:** a phase with `DONE` is skipped. An unfinished or forced phase directory is moved to `results/_attic/`, so runs never mix. A lock file stops two runners sharing one results directory.
  - **Plan checks:** it rejects top-level `temperature`/`top_k`/`top_p`/`repetition_penalty` on engine-direct commands and any runner-owned flags.
  - **Keys:** bench gets the key through its environment (`$TTS_API_KEY` for the gateway, a throwaway one if unset; `$TTS_ENGINE_API_KEY` for the engine), never on the command line or in logs.
- `/home/vector/qwen3-tts-server/bench/plan.py`: the phases P0 to P7 as specified. `CHOSEN`, `CHOSEN_VENV` and `CHOSEN_STREAM` sit at the top for after the screen. Engine-direct commands send sampling via `extra_params`, and there are no seeds anywhere. Variant names match `engine/make_variant.py` (`default`, `rp110` and so on).
- `/home/vector/qwen3-tts-server/bench/collect.py`: writes `results/ALL_summary.csv` with a phase column and prints one markdown table per phase with its status and error. It lists plan phases not yet run and skips `_`-prefixed directories.

**Testing** (runner under `venvs/gateway/bin/python`; test results and logs in the scratchpad, ports 18090/18091):
- **Dry run:** `--list` and `--dry-run` on the real plan printed every command. Plan checks correctly rejected ignored sampling fields, runner-owned flags, a bad venv, gateway-less gateway commands, duplicate names, unknown keys and unmatched `--only` patterns.
- **Self-test plan** (T0 stub engine + gateway, T1 reusing the engine, T2 bench crash):
  - T0 and T1 finished and T2 failed, exit 1. With stub suspect injection, retries=0 gave 4 suspect takes and retries=1 gave 0 suspect and 4 retried.
  - Rerunning skipped the DONE phases. `--force` moved the old directory to `_attic`, and a reuse phase with nothing running failed cleanly.
  - `--stop-on-error` stopped after the first failure, a second runner was refused by the lock, and an engine that dies at startup was caught.
  - SIGTERM to the runner and SIGINT to its process group (Ctrl-C) both gave exit 130, phase.json "interrupted", gateway and engine stopped, and no leftover processes or ports.
- **Real plan on the stub:** `--stub --only P0_smoke,P7_gateway` finished both phases. All gateway commands succeeded.
- **wait_ready.py** passed against a stub.
- **collect.py** ran on those results and on a missing directory.
- pyflakes (installed only in the scratchpad) is clean. All test results, logs and `__pycache__` are deleted, and my code never wrote under the project's `results/` or `logs/`.

**Known gaps:**
- **Engine-direct commands fail on the stub:** the gateway rejects the unknown field `extra_params`, so they get HTTP 400 there. They are counted as errors and the runner path is still exercised. The stub would be a faithful engine stand-in if the gateway accepted `extra_params` the way it accepts `task_type`.
- **Gateway commands use a workaround, one command per voice:** bench has no way to send only a voice id, and the gateway has no voice upload route. So each command sends `--param voice=<id> --param ref_audio=null --param ref_text=null`.
- **The n=max(16,2c) rule needs two commands per screen:** c=1,8 share n=16 and c=32 uses n=64. The second command starts the text pool over and repeats bench's 2 warm-up requests. Prefix caching is off in the variant YAMLs, so this doesn't cause cache hits.
- **Things I added beyond the spec:**
  - An extra `P1_screen_mrv2_engine30` (0.30's own defaults), next to our default settings on 0.30.
  - A gateway n=20 c=20 run in P6, because Auralis was measured through its full proxy stack.
- **Warm-up and other side effects:**
  - `wait_ready.py` makes one short synthesis before bench, which also warms the engine.
  - bench overwrites `config.json` on every command; phase.json keeps all the commands.
- **GPU check depends on the other process on GPU 1:** its baseline includes a process I did not start (pid 1785705, about 4.5 GB). If that process's usage changes between phases, the check can be wrong either way.
- **Leftover directory:** `results/_smoke_stub` is from another agent's bench run, not mine. I left it alone, and collect.py ignores it.

## build:engine-ops

All six deliverables are written and tested on CPU; the engine and gateway units are installed but not enabled or started. I couldn't run a real engine: there is no engine venv yet and the Qwen weights (`model.safetensors`) are not in the HF cache. So memory use, CUDA graphs, the FlashInfer compiler setup and the fp16/fp32 talker variants are untested on the GPU.

**Files created** (under `/home/vector/qwen3-tts-server/`)
- `engine/install_engine.sh`: builds the venv, installs vllm and vllm-omni together offline (`--no-index`; several wheel dirs can be joined with `:`, `-` means PyPI), applies the patch, and checks the pip CUDA 13 `nvcc`. It then imports torch, vllm and vllm_omni with the GPUs hidden and fails if CUDA was initialised or the versions don't match.
- `engine/deploy/qwen3_tts_prod.yaml`: full copy of the 0.28 upstream file. Stage 0 is 0.45 and stage 1 is 0.18 of the card, both on device "0", `max_num_seqs` 64, CUDA graphs on, sampling 0.9 / 50 / 1.05. The memory arithmetic is in the header: about 15.4 GiB for the engine plus 4.4 GiB for the other tenant, leaving roughly 4 GiB free.
- `engine/make_variant.py`: all the requested flags plus `--decode-graph-batch-sizes`, `--code2wav-max-num-seqs` and `--model-runner`. `--help` says `--code2wav-dtype` only works on 0.30 (0.28 forces the decoder to fp32) and that 0.28 ignores `model_runner`. Every file is checked against the loader's schema, which catches typos the loader would silently drop. `--check VENV` also loads the files with the real loader inside an engine venv, without CUDA.
- `engine/deploy/variants/*.yaml`: the 11 requested variants plus `mrv2`, which reproduces the 0.30 upstream defaults.
- `engine/patches/apply_patches.py`: adds per-request `extra_params.repetition_penalty`. It locates the package with `find_spec` (so the package is never imported) and needs the exact upstream snippet, which is identical in 0.28 and 0.30. It writes atomically, adds a marker comment, is idempotent, and refuses (exit 2) if the snippet has changed. Bad values (≤0, NaN, inf, strings, booleans) return HTTP 400.
- `engine/run_engine.sh`, `engine/wait_ready.py`: engine launcher and readiness check (details below).
- `deploy/systemd/qwen3-tts-engine.service`, `deploy/systemd/qwen3-tts-gateway.service`, `deploy/env.example`, `deploy/install_units.sh`.
- `engine/tests/test_engine_tools.py`: 6 tests covering the patch and the variants.

**run_engine.sh details**
- **CUDA toolchain:** `CUDA_HOME` and `FLASHINFER_NVCC` point to `site-packages/nvidia/cu13` in the venv, and `PATH` / `LD_LIBRARY_PATH` are reset, so the system `/usr/bin/nvcc` 12.0 and the incomplete `/usr/local/cuda` are never used. `FLASHINFER_CUDA_ARCH_LIST=8.6` builds for the 3090 directly, because the 580 driver cannot compile PTX from nvcc 13.4.
- **libcudart link:** FlashInfer links its compiled kernels with `-lcudart`, which would otherwise pick up the system's CUDA 12.0 `libcudart.so`. The install script adds a `libcudart.so` link to the venv's `.so.13` and `run_engine.sh` points FlashInfer at it.
- **Flags:** `--omni`, `--deploy-config`, `--async-chunk/--no-async-chunk`, `--trust-remote-code`, `--allowed-local-media-path`, `--served-model-name`, `--stage-init-timeout` and `--init-timeout` exist in both versions. `--stage-configs-path` was removed in 0.28 and now raises an error. `vllm serve … --omni` hands over to vllm-omni.
- **API key:** passed as `VLLM_API_KEY`, which vLLM reads when `--api-key` is not given, so the key never appears in `ps`.
- **Model:** with `HF_HUB_OFFLINE=1` the repo id is resolved to its HF cache snapshot and the repo id is kept as the served name. The script refuses to start if the snapshot is incomplete.
- **wait_ready.py:** polls `/health`, then runs one Base synthesis, using a registered voice if the engine lists it, otherwise the trump reference sent inline (sha256-checked). It checks the WAV but never saves it. Exit 0 = ready, 1 = timed out, 2 = error that waiting won't fix.

**Where async_chunk lives:** only the top-level `async_chunk:` key. The loader copies it into every stage, and the CLI `--async-chunk/--no-async-chunk` overrides it (`config_factory.py` L456-458). 0.30 also accepts a per-stage opt-out.

**Repetition penalty evidence:**
- Stage-0 defaults are built as `SamplingParams(**default_sp)` (`stage_init_utils.py` L619, L636 in 0.30), so `repetition_penalty` exists on them.
- The patch writes to the per-request deep copy made just before the loop. The adapter's `copy.copy` (`qwen3_tts.py` L257) and the built-in retry (`request.model_copy`, L3624) both keep it.
- vLLM reads it when a request joins the batch (`gpu_input_batch.py` L424-428 in 0.28; `PenaltiesState.add_request` in 0.30) and applies it every step (`Sampler.apply_penalties`, `sampler.py` L405/L422). The omni runner only clamps prompt padding (`gpu_ar_model_runner.py` L2032-2037).
- Nothing overwrites it per step: the talker's `compute_logits` only masks, and generation_config only updates EOS.
- **Caveats:**
  - It affects codebook 0 only; the sub-talker has no penalty.
  - It counts every earlier codebook-0 token in the request, not a recent window.
  - The talker prompt is `[1] * N` placeholder ids (L2992; 0.30 `qwen3_tts.py` L458), so codec id 1 is always treated as already seen.

**Tests run:**
- `bash -n` and `shellcheck` 0.11 (installed in a throwaway venv) are clean on all 3 scripts. `systemd-analyze --user verify` is clean on both units.
- `make_variant.py --standard`: all files pass the schema check.
- Real loader: I ran the actual upstream loader (heavy imports stubbed, omegaconf in a throwaway venv, on copies of the upstream trees). The prod file and all 12 variants loaded under both 0.28 and 0.30, with the resolved stage settings matching the files. A negative test caught a deliberately mismatched value.
- `apply_patches.py` on copies of both versions:
  - `--check` returns 1 before patching and 0 after.
  - Applying twice leaves the file byte-identical.
  - Running the patched code with fake requests gives the expected results.
  - Refusal (exit 2) works for a changed snippet, missing `import math`, and a directory that isn't a package.
  - `--venv` discovery works. `ops/upstream` hashes are unchanged.
- `install_engine.sh` ran end to end on stand-in wheels (two wheel dirs, patch, link, import check); a second run was a no-op.
- `run_engine.sh` was run against a fake `vllm` binary that prints its arguments and environment, both with explicit arguments and with the installed env file. It refuses the real HF cache because the weights are missing.
- `wait_ready.py` against a fake engine on port 18731, 9 cases: inline, registered, Urdu voice, streaming header, silent audio, 400, 401, never healthy, nothing listening. Those servers are stopped.
- `install_units.sh` was run once for real without `--enable` (only exercised `--enable` against a fake `systemctl`). Both units are installed, disabled and inactive; `~/.config/qwen3-tts/env` was created with random keys, mode 600. The gateway's `Settings` loads that file correctly.
- pytest: 6 passed.

**Known gaps and decisions:**
- The units start the gateway only after the engine's `ExecStartPost` `wait_ready.py` has produced audio (`TimeoutStartSec=1800`).
- `run_engine.sh` falls back to `TTS_ENGINE_DEPLOY` / `TTS_ENGINE_PORT` / `TTS_ENGINE_VENV` when positional arguments are missing, so the unit can call it with no arguments.
- `fp32_talker` also uses stage-0 memory 0.55 and `max_num_batched_tokens` 8192. At 0.45 there would be almost no KV cache left, but the comparison is no longer a single-variable change.
- `seqs128` keeps the production memory budget, so the KV cache (about 45k tokens) is the real limit at c=128.
- Upstream never tested fp16/fp32 talker; the talker builds its prompt embeddings in bf16.
- Running `default` on `engine30` means the V1 runner and a bf16 Code2Wav; `mrv2` is the upstream 0.30 setup.
- Stage 1's real memory use is unmeasured.
- If FlashInfer's compiled sampler fails on this box, set `VLLM_USE_FLASHINFER_SAMPLER=0`.
- With the patch, the bench's repetition-penalty phase could send `extra_params.repetition_penalty` per request instead of restarting the engine for each rp variant.
- `env.example` sets `TTS_ENGINE_PER_REQUEST_RP=1`, because every venv built by `install_engine.sh` carries the patch.

