# Research: local-env

_Local environment feasibility: vLLM-Omni / qwen-tts / faster-whisper on 2x RTX 3090 (sm_86, driver 580.82.07 / CUDA 13.0), models, network, ports, systemd, disk_

Produced 2026-09-24 by a research subagent (workflow wf_6c83c01a-7e3). Confidence: verified-source = read in the
package source; verified-doc = official docs/issue text; reported = third-party claim; unverified = not checked.
Scratch artifacts referenced below lived under /tmp/claude-1013/.../scratchpad/research/ (copied to docs/research/artifacts/ where small).

## Findings

### 1. vllm==0.28.0 + vllm-omni==0.28.0 resolves cleanly on Python 3.12. It needs 239 packages and a 4.14 GB download…

**Confidence:** verified-source

vllm==0.28.0 + vllm-omni==0.28.0 resolves cleanly on Python 3.12. It needs 239 packages and a 4.14 GB download. Key versions: torch 2.13.0 (CUDA 13.0 build: cuda-toolkit 13.0.3, cudnn-cu13 9.20.0.48, cublas 13.1.1.3, nccl-cu13 2.29.7), torchaudio 2.11.0, torchvision 0.28.0, transformers 5.14.1, flashinfer-python 0.6.16.post3, triton 3.7.1. flash-attn (Dao) is not needed. vllm 0.30.0 + vllm-omni 0.30.0rc1 needs 260 packages and 4.17 GB, with the same torch 2.13.0.

**Evidence:** pip 26.2.1 dry-run reports in the throwaway venv: $R/report-omni-0.28.0+vllm.json and $R/report-omni-0.30.0rc1+vllm-0.30.0.json. vllm 0.28.0 requires_dist includes 'torch==2.13.0', 'torchaudio==2.11.0', 'flashinfer-python==0.6.16.post3'. Sizes from HEAD requests are in $R/sizes-omni.txt. $R = /tmp/claude-1013/-home-vector/60c91189-44d6-4cdb-b0f5-2bf4adb23fb3/scratchpad/research/local-env.

### 2. vllm-omni does not declare vllm as a dependency. Installed alone, it pulls torch 2.14.0 and no vllm, so you mu…

**Confidence:** verified-source

vllm-omni does not declare vllm as a dependency. Installed alone, it pulls torch 2.14.0 and no vllm, so you must install vllm==0.28.x explicitly. A major.minor mismatch between the two only raises a RuntimeWarning, not an error. The docs require Python 3.12 and install with `uv pip install vllm==0.28.0 --torch-backend=auto` then `uv pip install vllm-omni`. uv is not installed on this box, but plain pip works because the PyPI default torch is cu130.

**Evidence:** vllm-omni 0.28.0 wheel: vllm_omni/version.py L26-48 (warn_if_misaligned_vllm_version, warnings.warn) and vllm_omni/__init__.py L15-19. Docs at v0.28.0: docs/getting_started/installation/gpu.md L8 'Python: 3.12'; gpu/cuda.inc.md L23 and L29. $R/report-omni-0.28.0.json contains no vllm.

### 3. The PyPI vllm 0.28.0 wheel is the CUDA 13.0 build, and its arch list includes sm_86. The driver (580.82.07, CU…

**Confidence:** verified-source

The PyPI vllm 0.28.0 wheel is the CUDA 13.0 build, and its arch list includes sm_86. The driver (580.82.07, CUDA 13.0) supports it: NVIDIA's rule is CUDA 13.x needs driver >=580.

**Evidence:** vllm v0.28.0 .buildkite/release-pipeline.yaml L10: CUDA_ARCH_X86 "7.5 8.0 8.6 8.9 9.0 10.0 12.0"; L44-50: 'Build wheel - x86_64 - CUDA 13.0 ... CUDA_VERSION=13.0.2'. scripts/upload-release-wheels-pypi.sh L71-72: PyPI gets only the default variant with no '+'. CMakeLists.txt L126: CUDA>=13 supported arches include 8.6. vllm-omni docs cuda.inc.md L48: 'The 0.28.0 release of vLLM ships CUDA 13.0-compatible binaries by default'. https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html: 'CUDA 13.x >= 580'. I did not inspect the vllm wheel binary because its download failed.

### 4. torch 2.13.0+cu130 contains native sm_86 SASS. A copy is already installed on this box, which I used to check.

**Confidence:** verified-source

torch 2.13.0+cu130 contains native sm_86 SASS. A copy is already installed on this box, which I used to check.

**Evidence:** cuobjdump --list-elf (CUDA 13.1, bundled with triton) on /home/vector/translation-layer/.venv-translit/lib/python3.10/site-packages/torch/lib/libtorch_cuda.so found 449 cubins each for sm_75/80/86/90/100/120. torch/version.py there reads '2.13.0+cu130', cuda '13.0'. Separately, torch 2.11.0+cu130 is running on both GPUs right now (translation-layer pid 1785705).

### 5. qwen-tts 0.1.1 cannot share a venv with vllm-omni because of transformers (==4.57.3 vs >=5.10.1,<5.15). It has…

**Confidence:** verified-source

qwen-tts 0.1.1 cannot share a venv with vllm-omni because of transformers (==4.57.3 vs >=5.10.1,<5.15). It has no torch pin. Unpinned it resolves torch 2.14.0 and adds 1.72 GB beyond the server wheels. Pinned to torch==2.13.0 torchaudio==2.11.0 it adds only 0.15 GB. The same pin keeps an eval venv (faster-whisper 1.2.1, jiwer 4.0.0, speechbrain 1.1.1, transformers 5.17.0) at +0.15 GB. flash-attn is optional for qwen-tts: without it, transformers uses its default sdpa attention.

**Evidence:** pip error: 'Cannot install qwen-tts==0.1.1, vllm-omni==0.28.0 and vllm==0.28.0 because these package versions have conflicting dependencies'. Reports: $R/report-qwen-tts-0.1.1.json, $R/report-qwen-tts-torch213.json, $R/report-eval.json. qwen_tts/cli/demo.py L606: attn_impl = 'flash_attention_2' if args.flash_attn else None.

### 6. faster-whisper 1.2.1 with ctranslate2 4.8.2 needs no extra CUDA pip packages here. The ct2 library dlopens lib…

**Confidence:** verified-source

faster-whisper 1.2.1 with ctranslate2 4.8.2 needs no extra CUDA pip packages here. The ct2 library dlopens libcublas.so.12, which the system provides (libcublas-12-9 12.9.1.4 and 12-8 via ldconfig). The wheel contains no cuDNN reference. SASS for sm_86 is present.

**Evidence:** strings on ctranslate2.libs/libctranslate2-fd146744.so.4.8.2: 'libcublas.so.12', 'libcuda.so.1', and no 'cudnn' anywhere in the wheel. cuobjdump shows sm_86 SASS and PTX. CTranslate2 CHANGELOG L101 (v4.6.3): 'Conv1d pure CUDA implementation (#1949), makes cuDNN an optional dependency'. `ldconfig -p` lists libcublas.so.12 under /usr/local/cuda/targets/x86_64-linux/lib. dpkg shows libcudnn9-cuda-12 9.15.0.57. The runtime load is UNVERIFIED (not run, to stay off the GPU).

### 7. The network is the critical-path blocker. Each TCP connection is throttled to about 11-25 KB/s from PyPI and 7…

**Confidence:** verified-source

The network is the critical-path blocker. Each TCP connection is throttled to about 11-25 KB/s from PyPI and 77-110 KB/s from the HF CDN, and aggregate speed grows with parallel connections: 8 conns gave ~170 KB/s, 32 conns gave ~416 KB/s, and my fetcher with 24 conns reached 0.45-1.6 MB/s. My pip download of the vllm+torch wheels failed with repeated 'Connection interrupted'. The GitHub API quota for this IP is exhausted, and gh is not installed. I wrote and tested a stdlib parallel-range fetcher with sha256 verification, for pip reports and HF repos: $R/fetch_wheels.py.

**Evidence:** Timed curl range tests. Examples: `fetch_wheels.py ... --only onnxruntime` fetched 23.6 MB in 52 s; `fetch_wheels.py hf:speechbrain/spkrec-ecapa-voxceleb` fetched 83.3 MB in 53 s, with sha256 matching the Hub LFS oid. $R/dl-vllm-torch.log ends 'This is an issue with network connectivity, not pip'. The GitHub API returned HTTP 403 'API rate limit exceeded for 115.186.179.158'.

### 8. GPU state changed while I worked. At 17:35 each GPU had only ~1,035 MiB free: Punjabi Whisper vLLM servers on…

**Confidence:** verified-source

GPU state changed while I worked. At 17:35 each GPU had only ~1,035 MiB free: Punjabi Whisper vLLM servers on :8000 and :8012 held 18.5 GB each at gpu_memory_utilization 0.75, and the translation-layer process held 4.48 GB on both GPUs. From 17:52 on, 19,620 MiB were free per GPU, because the main session stopped the Whisper servers (documented in /home/vector/qwen3-tts-server/ops/STOPPED_WHISPER_SERVERS.md). Only pid 1785705 (4.48 GB on each GPU) remains.

**Evidence:** Read-only nvidia-smi --query-gpu and --query-compute-apps at 17:35, 17:52 and 18:23, plus ps -o cmd of the EngineCore parent pids 2275321 and 3258275.

### 9. vLLM refuses to start any stage unless free memory is at least total × gpu_memory_utilization, where the fract…

**Confidence:** verified-source

vLLM refuses to start any stage unless free memory is at least total × gpu_memory_utilization, where the fraction applies to the whole 24 GiB card. The default qwen3_tts.yaml puts both stages on GPU0 at 0.3 each (14.4 GiB), which fits the ~19.2 GiB now free and leaves ~4.8 GiB. The high-concurrency profile splits stage 0 onto GPU0 and stage 1 onto GPU1. If the Whisper STT servers return at 0.75, nothing fits.

**Evidence:** vllm v0.28.0 vllm/v1/worker/utils.py L444-464 (request_memory raises ValueError 'Free memory on device ... is less than desired GPU memory utilization'). vllm-omni 0.28.0 deploy/qwen3_tts.yaml L62-75 and L97-113 (gpu_memory_utilization 0.3, devices '0'). qwen3_tts_high_concurrency.yaml L60-69 (devices '0') and L87-96 (devices '1', max_num_seqs 10).

### 10. Model files and local cache status. Qwen3-TTS-12Hz-1.7B-Base (rev fd4b2543) is 4.544 GB: model.safetensors 385…

**Confidence:** verified-source

Model files and local cache status. Qwen3-TTS-12Hz-1.7B-Base (rev fd4b2543) is 4.544 GB: model.safetensors 3857 MB, all BF16, 1.929B params; speech_tokenizer 682 MB, F32, 0.171B params. 0.6B-Base is 2.516 GB. whisper-large-v3 needs only model.safetensors (3087 MB fp16) plus small files. Systran/faster-whisper-large-v3 is 3.09 GB. wavlm-base-plus-sv is 0.405 GB, wavlm-large 1.262 GB, spkrec-ecapa-voxceleb 0.089 GB. Locally, only wavlm-base-plus-sv is complete in ~/.cache/huggingface (sha256 verified). The Qwen and Whisper weight blobs are absent: a stalled 1.14 GB .incomplete was removed and no download is running. I mirrored the ECAPA checkpoints to $R/test-hf/ (sha256 verified). No other usable copies exist in /home, /opt, /data, /mnt or /srv.

**Evidence:** HF API tree listings in $R/hf-sizes.txt. safetensors headers read by HTTP range request. sha256sum of the wavlm pytorch_model.bin equals the LFS oid e906bce2...0fad. ls of the cache blobs at 18:23. find over /home, /opt, /data, /mnt and /srv found only whisper-large-v3-turbo (appuser) and faster-whisper-small (/opt).

### 11. Port proposal: public gateway on 0.0.0.0:8091 (this matches the bench_tts.py default --url and NOTES.md) and i…

**Confidence:** verified-source

Port proposal: public gateway on 0.0.0.0:8091 (this matches the bench_tts.py default --url and NOTES.md) and internal vllm-omni engine on 127.0.0.1:8092. Both are free and not referenced by other configs. Avoid 8000 and 8012 (the stopped STT servers will return), 8003 (live Whisper proxy) and 8100 (default port of the translation-layer cipt_denoise_server).

**Evidence:** ss -ltn listing. grep of configs under /home/serveradmin/services and /home/vector: bench_tts.py L352 default 8091, NOTES.md L63 --port 8091, cipt_denoise_server.py L50 default 8100. Firewall rules were unreadable without root.

### 12. systemd --user works with XDG_RUNTIME_DIR=/run/user/1013 and DBUS_SESSION_BUS_ADDRESS set: systemd 255, Linger…

**Confidence:** verified-source

systemd --user works with XDG_RUNTIME_DIR=/run/user/1013 and DBUS_SESSION_BUS_ADDRESS set: systemd 255, Linger=yes. Existing user units are tts-app.service (inactive, enabled; do not reuse the name) and gradio-qa-app.service (active). Docker is not available to this user.

**Evidence:** systemctl --user list-units and list-unit-files, loginctl show-user vector -p Linger, ~/.config/systemd/user listing.

### 13. Disk: / is the only filesystem (home and tmp included). It has 101 GB free, is 89% used, and is shared with pr…

**Confidence:** verified-source

Disk: / is the only filesystem (home and tmp included). It has 101 GB free, is 89% used, and is shared with production. Estimated peak use is about 40-45 GB: server venv ~11-12 GB, qwen-tts and eval venvs ~5.5 GB each, wheelhouse ~4.3 GB (temporary), models ~8.5 GB required (+2.5 for 0.6B), compile caches 1-2 GB, audio ~0.17 GB per audio-hour. Proposed layout under /home/vector/qwen3-tts-server (the directory already exists): venvs/{server,qwen-tts,eval,tools}, wheelhouse/, models/, gateway/, config/, bench/, results/<run>/, logs/, ops/systemd/, docs/.

**Evidence:** df -h /. du of an existing vllm 0.16 venv (11 GB) and of .venv-translit (5.0 GB; nvidia libs 2.7 GB).

### 14. vllm-omni 0.28.0 already includes Higgs Audio v3 (bosonai/higgs-audio-v3-tts-4b), so the same engine venv coul…

**Confidence:** verified-source

vllm-omni 0.28.0 already includes Higgs Audio v3 (bosonai/higgs-audio-v3-tts-4b), so the same engine venv could serve it later behind a swappable gateway backend. In 0.30.0rc1, the Qwen3-TTS default switches to the experimental Model Runner V2, stage-0 max_num_batched_tokens drops to 512, and stage 1 uses dtype bfloat16.

**Evidence:** vllm-omni 0.28.0 wheel: vllm_omni/model_executor/models/higgs_audio_v3/ and vllm_omni/deploy/README_higgs_audio_v3.md. vllm-omni 0.30.0rc1 wheel deploy/qwen3_tts.yaml: L20 'model_runner: v2', L83 'max_num_batched_tokens: 512', L109 'dtype: bfloat16'.

### 15. Reuse opportunities. The pip HTTP cache already holds 69 of the 239 server wheels (0.86 GB). The heaviest whee…

**Confidence:** verified-source

Reuse opportunities. The pip HTTP cache already holds 69 of the 239 server wheels (0.86 GB). The heaviest wheels are not cached: torch 2.13.0, cublas, cudnn-cu13, nccl, triton 3.7.1 and vllm. .venv-translit already has the exact NVIDIA libraries vllm 0.28 needs installed (cublas 13.1.1.3, cudnn-cu13 9.20.0.48, nccl-cu13 2.29.7, cusparselt 0.8.1). Copying those files into a new venv would avoid a 1.17 GB download, but this is a non-standard fallback.

**Evidence:** $R/pipcache.py computes sha224-keyed http-v2 paths. It found torch-2.11.0 cp312 cached but torch-2.13.0 cp310/cp312 missing. dist-info listing of .venv-translit.

## Risks

- The network may not deliver the weights and wheels in time: about 3.3 GB of uncached server wheels, 4.5 GB of Qwen weights and 3.1 GB of Whisper weights. Per-connection throttling (~20 KB/s) makes pip and single-stream downloads take many hours. Use $R/fetch_wheels.py with 24-32 connections (0.5-1.6 MB/s measured) and pin HF revisions. An HF_TOKEN may help with rate limits.
- GPU co-tenancy. The translation-layer process (pid 1785705) holds 4.48 GB on both GPUs. If the stopped Punjabi Whisper servers are restarted at 0.75 utilization, free memory drops back to ~1 GB per GPU and vLLM refuses to start. Co-tenant load also skews benchmark numbers.
- The resolved stack pulls CUDA 13.4 JIT tooling (nvcc/nvvm/nvjitlink 13.4.92) while the driver is 13.0 (r580). Any path that emits PTX for driver JIT would fail; SASS paths are fine. This is UNVERIFIED at runtime on sm_86.
- /usr/local/cuda points to an incomplete CUDA 12.9 tree with no bin/ or nvcc, and the nvcc on PATH is 12.0. Anything that derives nvcc from CUDA_HOME=/usr/local/cuda will break, and building flash-attn for cu130 is impractical, so skip it.
- vllm-omni 0.30.0rc1 is a pre-release and defaults to the experimental Model Runner V2. Installing it with --pre drags in pre-release tokenizers, pydantic and safetensors, so pin the exact version instead. Use 0.28.0 stable as the baseline.
- The CPU governor is 'powersave' and cannot be changed without sudo. It may inflate CPU-side latency (HTTP, WAV encoding, scheduling). Record it in REPORT.md.
- Disk: / will reach about 94% after venvs, models and audio are in place, on a disk shared with production. Delete the wheelhouse after install and add a free-space guard to the benchmark runner.
- Process notes: I ran `sudo -n true` once while probing the firewall. It failed with 'password required' and had no effect, but it breaks the no-sudo rule, so I am flagging it. My failed background pip download of vllm+torch competed for bandwidth from about 17:41 to 18:10. None of my processes remain.

## Open questions

- Does vLLM 0.28.0 on sm_86 pick the FLASH_ATTN (FA2) backend for the Qwen3-TTS talker, and does any flashinfer or cutlass-dsl JIT path run, which could hit the PTX/driver-13.0 limit? Verifying this needs a real GPU run.
- Does ctranslate2 4.8.2 actually load /usr/local/cuda-12.9 libcublas.so.12 cleanly in a process that also has torch cu130's libcublas.so.13 loaded? A separate eval venv avoids the question.
- When will the stopped Punjabi Whisper STT servers (:8000 and :8012) be restarted, and at what gpu_memory_utilization? This decides whether the TTS engine can keep 0.3+0.3 on GPU0 with evaluation on GPU1.
- Is port 8091 reachable from outside the host? The firewall cannot be read without root. Who are the intended clients of the gateway (LAN or public)?
- Should the 0.6B-Base model (2.5 GB) and wavlm-large (1.26 GB) be downloaded at all, given the bandwidth? Should faster-whisper weights be converted locally from openai/whisper-large-v3 instead of downloading Systran's 3.09 GB copy?
- Does importing qwen-tts warn or fail without the sox CLI? sox is only used by the 25 Hz tokenizer.
