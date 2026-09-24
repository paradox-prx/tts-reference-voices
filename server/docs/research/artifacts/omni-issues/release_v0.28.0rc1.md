## Highlights

This release candidate features 212 merged changes, including contributions from 22 new contributors.

vLLM-Omni `v0.28.0rc1` focuses on five major areas: 1) **expanding multimodal model coverage across speech, music, image, video, and robotics**, 2) advancing **diffusion scheduling, continuous batching, paged KV cache, and Host Weight Runtime–based distributed layerwise offload**, 3) delivering substantial **MiniMax H3, TTS, and MiniCPM-o performance improvements**, 4) strengthening **realtime and full-duplex speech serving**, and 5) improving **runtime reliability, observability, CI coverage, and hardware portability**. The release candidate also rebases the project onto vLLM 0.28.0 and removes additional legacy configuration paths.

### Key Improvements

* **Significantly expanded model coverage** with IndexTTS 2.5, dots.tts, Gepard-1.0, MiniMax Music 3, NVIDIA Nemotron VoiceChat, LTX-2.5, SANA-Video, SANA-WM, HiDream-O1-Image, and π0 VLA support. **(#5957, #4765, #5666, #6186, #5842, #6089, #6070, #5508, #4061, #5194, #4222)**
* **Advanced scalable diffusion execution** with native scheduler-managed paged KV cache, continuous batching for MiniMax H3, request-level batching for Wan2.2, realtime AR-diffusion tick sessions, and a single-GPU UniProc executor. **(#6094, #6102, #5810, #5676, #5491, #6308)**
* **Introduced the Host Weight Runtime foundation** and integrated it with DLO, including loader-owned host-weight plans, final-layout BF16 artifacts, mmap-backed direct H2D transfer, explicit post-load publication, online FP8 AllGather, and no-AllGather DLO execution. **(#6213, #6419, #6427, #6445, #6591, #6279, #6486, #6651)**
* **Improved speech and TTS serving** with forced-alignment timestamps, speech token-usage headers, native full-duplex Nemotron VoiceChat, concurrent MiniCPM-o duplex sessions, realtime audio fixes, and multiple hot-path optimizations. **(#4795, #4499, #6089, #6021, #6564, #5068, #5174, #5791)**
* **Further optimized MiniMax H3 across accelerators and execution modes**, adding global FP8 with DLO, Turbo LoRA, continuous batching, fused kernels, strict Ulysses boundary handling, reduced reference-video scanning, and new RTX PRO 5000 and NPU 950PR recipes. **(#5910, #6476, #6550, #5810, #5990, #6281, #6283, #6173, #6064, #5857, #6120)**

### Core Architecture & Runtime

* Rebased the project onto **vLLM 0.28.0**, updating engine, model-runner, scheduler, configuration, attention, and platform integrations for the vLLM 0.28 release line. **(#6606)**
* Added the **Host Weight Runtime**, providing a shared lifecycle for preparing, publishing, mapping, and transferring host-resident model weights. **(#6419, #6427)**
* Added loader-owned host-weight plans and final-layout BF16 artifacts for diffusion DLO deployments. **(#6213, #6445)**
* Integrated no-AllGather DLO with Host Weight Runtime and registered mmap-backed host weights for direct H2D transfer. **(#6486, #6591)**
* Added online FP8 support for DLO AllGather and established a FLUX.2-klein BF16 Host Weight Runtime contract. **(#6279, #6651)**
* Added native diffusion KV-cache initialization and scheduler-managed block allocation, together with a native paged-KV backend for diffusion workers. **(#6094, #6102)**
* Added realtime AR-diffusion tick sessions for LingBot World 2.0. **(#5491)**
* Added a **UniProc diffusion executor** for single-GPU deployments, avoiding unnecessary distributed-process overhead. **(#6308)**
* Added an opt-in event-driven engine orchestration loop. **(#5221)**
* Refactored diffusion parallel state and continued the worker/model-runner correctness cleanup. **(#5531, #5452)**
* Replaced hard-coded full-payload input-stage handling with resolved stage transport capabilities. **(#6149)**
* Added pause, resume, sleep, and wake support for autoregressive stages in `AsyncOmni`, including admission recovery after wake. **(#6084, #6581)**
* Fixed remote replica membership lifecycle races, replica device splitting when stages omit explicit devices, and per-stage runtime-environment restoration. **(#5277, #5445, #6214)**

### Model Support

* Added **IndexTTS 2.5** support. **(#5957)**
* Added **dots.tts**, a continuous-autoregressive 48 kHz TTS model from rednote-hilab. **(#4765)**
* Added **Gepard-1.0** native-autoregressive FSQ/NanoCodec TTS for offline inference. **(#5666)**
* Added **MiniMax Music 3** text-to-music generation. **(#6186)**
* Added NVIDIA NemotronLabs VoiceChat 11B offline speech-to-speech inference and native full-duplex serving. **(#5842, #6089)**
* Added **LTX-2.5** and the LTX standard two-stage pipeline, with improved audio parity and checkpoint-shard validation. **(#6070, #5500, #6342, #6234)**
* Added native **SANA-Video 2B** text-to-video and image-to-video generation. **(#5508)**
* Added stage-one **SANA-WM** support. **(#4061)**
* Added **HiDream-O1-Image** support. **(#5194)**
* Added **π0 VLA** model support for vision-language-action workloads. **(#4222)**
* Added offline SVDQuant W4A4 diffusion support and AutoRound MXFP4 quantized-model support. **(#6162, #5544)**
* Added a FastVideo VSA attention backend for Wan2.2. **(#4820)**
* Added native full-duplex and configurable concurrent-session support for MiniCPM-o. **(#6021, #6619)**

### MiniMax H3 Productionization

* Enabled **global FP8 with DLO** and added online-FP8 DLO AllGather support. **(#5910, #6279)**
* Added MiniMax H3 **diffusion continuous batching**. **(#5810)**
* Added Turbo LoRA support through both the legacy LoRA manager and DLO. **(#6476, #6550)**
* Optimized the DLO component lifecycle and integrated no-AllGather execution with Host Weight Runtime. **(#6526, #6486)**
* Added fused Q/K RMSNorm and RoPE, SwiGLU activation, and modulation with FP32 accumulation. **(#5990, #6283, #6281)**
* Added NPU-fused RMSNorm, RoPE, SwiGLU, native GQA, and fused AddNorm paths for the Qwen3-VL encoder. **(#5915, #6061, #6167, #6040)**
* Optimized strict Ulysses partition boundaries and avoided redundant reference-video scans. **(#6173, #6064)**
* Fixed model-level CPU-offload residency and a distributed VAE hang when decoder tiles are fewer than ranks. **(#6072, #6345)**
* Added optional planar video-response encoding. **(#6288)**
* Added deployment recipes for RTX PRO 5000 and Ascend NPU 950PR, plus DLO DP2 smoke coverage. **(#5857, #6120, #6555)**

### Audio, Speech & Omni Production Optimization

* Added TTS timestamps through a forced-aligner pooling model. **(#4795)**
* Added speech token-usage response headers and preserved detailed prompt-token accounting. **(#4499, #5181)**
* Optimized GLM-TTS by moving loop-invariant embeddings, RoPE, masks, and classifier-free-guidance batches outside the Euler loop. **(#5068)**
* Optimized the OmniVoice hot path with batched device-to-host transfers, mask caching, and cached text embeddings. **(#5174)**
* Fused QKV and `gate_up` projections in the Qwen3-TTS code predictor. **(#5791)**
* Enabled asynchronous scheduling for MOSS-TTS and aligned its default sample parameters with the official implementation. **(#6241, #6156)**
* Added CUDA Graph acceleration for the MiniCPM-o 4.5 CFM DiT estimator and NPU Graph replay for Code2Wav. **(#6082, #5604)**
* Restored MiniCPM-o streaming audio caching, fixed first-response stalls and mid-utterance truncation, and capped offline Talker generation to the remaining context window. **(#6274, #6346, #6458)**
* Improved native-duplex MiniCPM-o configuration, concurrent-session handling, hub-cache metadata loading, and async-chunk snapshot management. **(#6021, #6276, #6406, #6619)**
* Suppressed initial silence codec tokens for Qwen3-TTS. **(#5048)**
* Optimized the CosyVoice3 TensorRT stream handoff and fixed sampling, stage handoff, and STFT device mismatches. **(#5673, #6424, #6454)**
* Turned silent asynchronous TTS chunk failures into visible errors and reclaimed resumable requests after completion. **(#6033, #6360)**
* Reduced exposure of user-provided TTS and audio inputs by moving those log messages from INFO to DEBUG. **(#6329)**

### Diffusion, Image & Video Generation

* Added scheduler-managed native KV-cache initialization, block allocation, and a paged-KV worker backend. **(#6094, #6102)**
* Added request-level batching for Wan2.2 pipelines and continuous batching for MiniMax H3. **(#5676, #5810)**
* Added native SANA-Video 2B T2V/I2V, LTX-2.5, HiDream-O1-Image, and stage-one SANA-WM support. **(#5508, #6070, #5194, #4061)**
* Added offline SVDQuant W4A4 and online FP8 routing coverage for diffusion models. **(#6162, #3027)**
* Added diffusion request metrics and returned them from the image-edit endpoint. **(#4755, #5999)**
* Added text and image quality metrics. **(#6150)**
* Fixed lost asynchronous diffusion outputs in request-level batching and made the async-output wait timeout configurable. **(#6023, #6255)**
* Released GPU memory after diffusion execution failures and increased worker timeout tolerance for large broadcast payloads. **(#6385, #4845)**
* Fixed Wan spatial-reshard boundaries, HunyuanImage3 accuracy validation, and Hunyuan VAE/patch-embedding performance. **(#6062, #5981, #6306)**
* Fixed LongCat image-edit dimensions and TeaCache negative-branch CFG arguments. **(#6222, #6181)**
* Fixed FLASH_ATTN cross-attention key-padding unpadding. **(#5866)**
* Added a dedicated WORLD process group for distributed VAE communication. **(#6401)**
* Prevented LTX-2.5 from silently loading incomplete, unindexed Diffusers checkpoints. **(#6234)**

### Quantization, Attention & Memory Efficiency

* Added online FP8 execution with DLO AllGather and MiniMax H3 global FP8 support. **(#6279, #5910)**
* Added offline SVDQuant W4A4 support for diffusion pipelines. **(#6162)**
* Added offline AutoRound MXFP4 quantized-model support. **(#5544)**
* Fixed Qwen3-Omni AWQ quantization name mapping and stabilized compiled thinker MRoPE execution. **(#5687, #6449)**
* Scoped Bagel FP8 configuration to the diffusion stage. **(#6085)**
* Fixed compatibility between HSDP and the new online FP8 linear implementation. **(#5677)**
* Added fused Q/K RMSNorm and RoPE, fused SwiGLU, FP32-accumulation modulation, and a mask-free TensorRT-LLM packed-padding path. **(#5990, #6283, #6281, #6542)**
* Enabled fused SwiGLU on MUSA and avoided unsupported complex-RoPE alias guards. **(#6364, #6110)**
* Added native GQA and fused AddNorm for the MiniMax H3 encoder on NPU. **(#6040)**
* Upgraded Cache-DiT to 1.5.0 and Diffusers to 0.40.0. **(#6065, #6459)**

### Serving, Frontend & API Behavior

* Added native full-duplex serving for NVIDIA Nemotron VoiceChat. **(#6089)**
* Added configurable concurrent MiniCPM-o duplex sessions and strengthened native-duplex session lifecycle handling. **(#6021, #6318, #6619)**
* Added pause/resume and sleep/wake controls for autoregressive `AsyncOmni` stages. **(#6084)**
* Added forced-alignment TTS timestamps and speech token-usage response headers. **(#4795, #4499)**
* Added a local OmniInteract realtime benchmark. **(#6522)**
* Relaxed TTS request validation for models without uploaded speakers. **(#5878)**
* Fixed model-tag synchronization and command-line flag normalization in the API server. **(#3805)**
* Preserved object-storage URIs during model resolution and respected media redirect policies for image references. **(#5036, #6122)**
* Restored Hugging Face snapshot-path model detection, with the initial implementation subsequently reverted for further validation. **(#6624, #6642)**
* Improved SenseNova configuration and model detection. **(#5877)**
* Hardened request validation against denial-of-service overflow cases. **(#6598)**

### Output, Configuration & Compatibility

* Refactored `OmniRequestOutput` to inherit directly from vLLM `RequestOutput`, removing the nested request-output wrapper. **(#5146)**
* Updated downstream users after removal of the legacy `OmniRequestOutput.request_output` accessor. **(#6172)**
* Preserved `ec_transfer_params`, cache-creation-token counts, and prompt-token usage details on Omni outputs. **(#6152, #5181)**
* Reused upstream vLLM configuration objects in `VllmOmniConfig`. **(#6050)**
* Removed internal `stage_configs_path` plumbing and the legacy `stage_args` YAML loader. **(#5741, #6200)**
* Removed stale stage-configuration references from documentation and examples. **(#6270, #6347)**
* Moved sampling-parameter overrides and capability metadata from legacy dispatch logic into TTS adapters. **(#5272, #6138)**

### Platforms, Distributed Execution & Hardware Coverage

* Upgraded Ascend NPU support to **v0.27.0**. **(#6096)**
* Added MiniMax H3 recipes for RTX PRO 5000 and NPU 950PR. **(#5857, #6120)**
* Added NPU-native GQA, fused AddNorm, RoPE, SwiGLU, and RMSNorm optimizations for MiniMax H3. **(#6040, #6061, #6167, #5915)**
* Added MiniCPM-o Code2Wav NPU Graph replay and strengthened NPU CI coverage. **(#5604, #6275)**
* Added ROCm MI300X coverage for verified recipes and migrated the v0.27.x ROCm CI fleet to MI300X. **(#6207, #5886)**
* Fixed ROCm CPU-test and circular-import failures. **(#6267, #6287)**
* Fixed XPU CPU-offload device placement and made asynchronous AR and image-output paths device-agnostic. **(#6125, #5569, #5571)**
* Added a dedicated WORLD group for distributed VAE communication and fixed replica-layout validation. **(#6401, #5742)**
* Fixed Wan2.2-S2V complex indexing on NPU and NPU MoE registration. **(#6320, #6350)**

### CI, Benchmarks & Documentation

* Added per-model, per-entry-mode code-coverage collection and expanded dependency-based E2E test selection for shared model code. **(#5593, #5994)**
* Added MiniCPM-o 4.5 performance coverage to the ready gate and strengthened its NPU accuracy jobs. **(#6079, #6275)**
* Added tiny-model testing for Qwen-Image Edit and EditPlus and parallelized diffusion tiny-model tests. **(#5656, #6339)**
* Added API-server surface guardrails and re-enabled previously skipped E2E and example tests. **(#6202, #5641)**
* Added nightly Docker Hub publishing and cleanup to the release pipeline. **(#6048)**
* Strengthened pre-commit checks with Markdown linting, SPDX validation, and repository policy hooks. **(#6273)**
* Split scheduled L4/L5 pipelines, moved slower L1/E2E coverage to weekly runs, and demoted expensive nightly cases. **(#6311, #5944)**
* Improved performance-test stability by matching warmups to benchmark concurrency and reusing judge and server processes. **(#6356, #6208, #6613)**
* Added an environment-variable configuration reference and reconciled it with subsequent changes on the main branch. **(#6217, #6631)**
* Reorganized user-guide feature and quantization taxonomies, refreshed community documentation, and split diffusion attention and CPU-offload guides. **(#6045, #6074, #6141, #6075)**
* Unified recipe serving commands on `vllm serve --omni`. **(#6221)**
* Added a dedicated vLLM-Omni simplification-review skill. **(#6363)**

### Breaking Changes

* **The project now targets the vLLM 0.28 release line.** Out-of-tree integrations, platform plugins, attention backends, and code relying on internal vLLM APIs should be validated against vLLM 0.28 before upgrading. **(#6606)**
* **`OmniRequestOutput` now directly inherits from `RequestOutput`.** Code accessing the previous nested `request_output` property must migrate to the corresponding fields on `OmniRequestOutput`. **(#5146, #6172)**
* **The legacy `stage_args` YAML loader and remaining internal `stage_configs_path` plumbing have been removed.** Deployments and integrations must use registry-backed deployment configuration and the unified configuration model. **(#5741, #6200)**
* **Sampling overrides and TTS capability metadata now live in model adapters.** Out-of-tree TTS integrations relying on legacy dispatch tables may need to implement or update adapter metadata. **(#5272, #6138)**
* **Diffusers is now pinned to 0.40.0, Cache-DiT to 1.5.0, and the project is aligned with the updated NPU software stack.** Custom environments should review extension and dependency compatibility before upgrading. **(#6459, #6065, #6096)**

### Note

* This is a pre-release version. It is intended for evaluation and integration testing before the final release; production deployments should validate model quality, performance, and platform compatibility in their target environments.
* Host Weight Runtime, no-AllGather DLO, native diffusion paged KV cache, continuous batching, and the event-driven orchestration loop are newly introduced or rapidly evolving execution paths. Applications should validate memory residency, checkpoint compatibility, request cancellation, fault recovery, and long-running concurrency behavior before production adoption.
* Realtime and full-duplex serving behavior varies by model. Nemotron VoiceChat and MiniCPM-o users should validate session lifecycle, interruption handling, context limits, audio buffering, and concurrency requirements.
* Hardware capabilities remain backend-specific. Quantization formats, fused kernels, graph execution, attention implementations, CPU offload, and DLO configurations may require platform-specific dependencies and recipes.
* **#6557**, which changed Wan DMD pipeline-test alignment, was reverted in **#6574** and the revert was itself reverted in **#6578**. The final release state therefore retains the original **#6557** change.
* The Hugging Face snapshot-path model-detection change in **#6624** was reverted by **#6642** and is not included as an active behavior change in this release candidate.

## What's Changed
* [Docs] Add MiniMax-H3 recipe for RTX PRO 5000 by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5857
* docs: align User Guide feature taxonomy by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6045
* [New Model] Support IndexTTS 2.5 by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/5957
* [Misc] Build canonical image task prompts by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6049
* [Bugfix] Fix HunyuanImage3 accuracy test by @BLANKETusers in https://github.com/vllm-project/vllm-omni/pull/5981
* [CI][MiniCPM-o] Add MiniCPM-o 4.5 perf coverage to the ready gate by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/6079
* [Bugfix] Fix Wan spatial reshard boundary by @rahul-steiger-nv in https://github.com/vllm-project/vllm-omni/pull/6062
* docs: align quantization overview with navigation by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6074
* [CI/Build] Add examples policy to PR skills by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6046
* [Feature] timestamps for TTS via a forced-aligner pooling by @wjinxu in https://github.com/vllm-project/vllm-omni/pull/4795
* [Model] Support NVIDIA-NemotronLabs-VoiceChat-11B offline speech-to-speech by @yuekaizhang in https://github.com/vllm-project/vllm-omni/pull/5842
* [CI/Build] Add nightly DockerHub publish and cleanup to release pipeline by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/6048
* [Bugfix][MiniCPM-o] Align Daily-Omni offline loading and duplex soft-… by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/6095
* [Perf] MiniMax H3 Qwen3-VL support fused RMSNorm on NPU by @wjialish in https://github.com/vllm-project/vllm-omni/pull/5915
* [Refactor][OutputProcessor 2/3]: OmniRequestOutput should inherit RequestOutput and no nested wrap-up by @bowieshi in https://github.com/vllm-project/vllm-omni/pull/5146
* [Perf][TTS] glm_tts: hoist loop-invariant text embed, RoPE, mask and CFG batch out of Euler loop by @JuanPZuluaga in https://github.com/vllm-project/vllm-omni/pull/5068
* Add cosmos-guardrail dependency and update error message by @MaciejBalaNV in https://github.com/vllm-project/vllm-omni/pull/6107
* [Perf][TTS] omnivoice hot path: D2H batching, mask caching, cached text embeddings by @JuanPZuluaga in https://github.com/vllm-project/vllm-omni/pull/5174
* [Bugfix] Fix diffusion TTS adapter lookup in speech serving by @HaningZS in https://github.com/vllm-project/vllm-omni/pull/6121
* [Tests] Enable tiny model testing for Qwen-Image Edit and EditPlus by @NickCao in https://github.com/vllm-project/vllm-omni/pull/5656
* [CI/Build] Fix ReadTheDocs build under RTD's seeded pip 23.1 by @mjZhaoElaine in https://github.com/vllm-project/vllm-omni/pull/6129
* [Dependency] Upgrade Cache-DiT to 1.5.0 by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6065
* [Misc] Consolidate LingBot text-to-video runner by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6076
* [Perf][MiniCPM-O-4.5]Add CUDA Graph For CFM DiT estimator by @stringl1l1l1l in https://github.com/vllm-project/vllm-omni/pull/6082
* [Bugfix] Scope Bagel FP8 config to diffusion stage by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/6085
* [Metrics] Add Diffusion Metrics by @vraiti in https://github.com/vllm-project/vllm-omni/pull/4755
* [BugFix] Use MOSS-TTS-Local official sample params by @gcanlin in https://github.com/vllm-project/vllm-omni/pull/6156
* [Doc] Refresh community documentation by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6141
* [NPU] Upgrade to v0.27.0 by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/6096
* [Refactor] Remove internal stage_configs_path plumbing by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/5741
* [Feat] LTX Standard Two-Stage Pipeline by @mglyn in https://github.com/vllm-project/vllm-omni/pull/5500
* [Bugfix][Higgs-Audio-V3] Disable XQA decode by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/6068
* [Model][TTS] Add dots.tts (rednote-hilab): continuous-AR 48kHz TTS by @Moore-Z in https://github.com/vllm-project/vllm-omni/pull/4765
* [Kernel] Fuse Q/K RMSNorm and RoPE by @bobboli in https://github.com/vllm-project/vllm-omni/pull/5990
* [doc]: Update latest news section for verl-omni release by @SamitHuang in https://github.com/vllm-project/vllm-omni/pull/6187
* [Perf] Cap diffusion worker thread count before spawn by @ZJLi2013 in https://github.com/vllm-project/vllm-omni/pull/6165
* [CI] Per-model, per-entry-mode code coverage collection by @ShengleiFu in https://github.com/vllm-project/vllm-omni/pull/5593
* [ROCm] [CI] Migrate CI to mi300x for v0.27.x by @tjtanaa in https://github.com/vllm-project/vllm-omni/pull/5886
* [Bugfix] Fix HSDP compatibility with the new online FP8 linear method by @baonudesifeizhai in https://github.com/vllm-project/vllm-omni/pull/5677
* [Perf][Diffusion] Avoid redundant MiniMax-H3 reference video scans by @yeahdongcn in https://github.com/vllm-project/vllm-omni/pull/6064
* [Bugfix][MUSA][Qwen Image] Avoid complex RoPE alias guards by @yeahdongcn in https://github.com/vllm-project/vllm-omni/pull/6110
* [Perf][NPU] Fuse MiniMax H3 Qwen3-VL RoPE by @wjialish in https://github.com/vllm-project/vllm-omni/pull/6061
* [Perf][NPU] Fuse MiniMax H3 Qwen3-VL SwiGLU by @wjialish in https://github.com/vllm-project/vllm-omni/pull/6167
* [Feat/Bugfix] Fix API Server model tag <-> model sync & flag normalization by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/3805
* [Bugfix][XPU][Tests]Scope XPU pytest to explicit paths to fix collection crash by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/6175
* [Frontend] Loosen Validation for TTS Models with No Uploaded Speakers by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/5878
* [Bugfix] Stop reading the removed OmniRequestOutput.request_output accessor by @MrlixiangWE in https://github.com/vllm-project/vllm-omni/pull/6172
* [CI] Expand E2E source_file_dependencies for shared model code by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5994
* [Model] Add Gepard-1.0 native-AR FSQ/NanoCodec TTS (offline inference) by @mjZhaoElaine in https://github.com/vllm-project/vllm-omni/pull/5666
* [Bugfix] Preserve object storage URIs during model resolution by @Ma1oneZhang in https://github.com/vllm-project/vllm-omni/pull/5036
* [Docs] Split diffusion attention and CPU offload guides by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6075
* [codex] Fix diffusion worker timeout for large broadcast payloads by @hotTeaFun in https://github.com/vllm-project/vllm-omni/pull/4845
* [Model][Performance] Optimize MiniMax-H3 strict Ulysses boundaries by @mo-ke-ke in https://github.com/vllm-project/vllm-omni/pull/6173
* [Bugfix] Carry ec_transfer_params and num_cache_creation_tokens on OmniRequestOutput by @MrlixiangWE in https://github.com/vllm-project/vllm-omni/pull/6152
* [BugFix][Nightly CI] Adjust Qwen-Image accuracy thresholds for stable FA-deterministic mode by @NumberWan in https://github.com/vllm-project/vllm-omni/pull/5963
* [Model] Add LTX-2.5 support by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/6070
* [Bugfix] Fix lost async diffusion outputs in request-level batching by @SamitHuang in https://github.com/vllm-project/vllm-omni/pull/6023
* [CI] Refresh Voxtral-4B-TTS perf baselines from a clean window by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/6032
* [Bugfix] Restore per-stage runtime env during launch by @m0g3r in https://github.com/vllm-project/vllm-omni/pull/6214
* [Diffusion][Quantization] Enable MiniMax-H3 global FP8 with DLO by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5910
* [Perf] Support request-level batching for Wan2.2 pipelines by @nagisa-kunhah in https://github.com/vllm-project/vllm-omni/pull/5676
* Add MiniMax-H3 recipe for NPU 950PR by @yiminghub2024 in https://github.com/vllm-project/vllm-omni/pull/6120
* [Bugfix] Prevent DiffusionResultPump crash on cancelled futures (#5793) by @anurag12-webster in https://github.com/vllm-project/vllm-omni/pull/5983
* [Docs] Unify recipe serve commands on `vllm serve --omni` by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/6221
* [Core] Add realtime AR-Diffusion tick sessions for LingBot World 2.0 by @Jack47 in https://github.com/vllm-project/vllm-omni/pull/5491
* [Diffusion] Add loader-owned host-weight plans for DLO (TP=1) by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6213
* [Refactor] Remove legacy stage_args YAML loader by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/6200
* [BugFix][TTS] R1.1-R1.4: turn silent async-chunk failures into visible ones by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/6033
* [CI]demote slow nightly cases and trim Qwen-Image-Edit coverage by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5944
* [Migrate] Move sampling parameter overrides from legacy dispatches to TTS adapters by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/5272
* [Bugfix] Respect media redirect policy for image references by @HaningZS in https://github.com/vllm-project/vllm-omni/pull/6122
* [ROCm][Recipe]  Add MI300X coverage for verified recipes by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/6207
* [CI/Build] Gate one-word pronunciation on a success rate, not per request by @ShengleiFu in https://github.com/vllm-project/vllm-omni/pull/5681
* Add π0 VLA model support by @yicwang in https://github.com/vllm-project/vllm-omni/pull/4222
* [ROCm] [CI] Fix cpu test on rocm by @tjtanaa in https://github.com/vllm-project/vllm-omni/pull/6267
* [MiniCPM-o][NPU] Enable MiniCPM-o Code2Wav NPUGraph replay by @Zhou248 in https://github.com/vllm-project/vllm-omni/pull/5604
* [Docs] Classify PD disaggregation as an experimental feature by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6115
* [CI/Build][MiniCPM-o] Pin Seed-TTS scorer to npu:1 in the NPU accuracy job by @psv666 in https://github.com/vllm-project/vllm-omni/pull/6275
* Add speech token usage headers by @JLiu4Coding in https://github.com/vllm-project/vllm-omni/pull/4499
* [Bugfix][NPU] Break the pytest DiffusionOutput circular import by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/6293
* [Bugfix][MiniCPM-o] Load Daily-Omni QA metadata from the hub cache by @psv666 in https://github.com/vllm-project/vllm-omni/pull/6276
* [Model] Add MiniMax Music 3 text-to-music by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/6186
* [Diffusion] Add native KV cache initialization and Scheduler-managed block allocation by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/6094
* [Bugfix][Test] fix Qwen3-omni OOM reliability and drop voxcpm2 stability/reliability test cases by @zhumingjue138 in https://github.com/vllm-project/vllm-omni/pull/6299
* [ROCm] [CI] Fix circular import for rocm due to patch by @tjtanaa in https://github.com/vllm-project/vllm-omni/pull/6287
* [Config] Reuse vLLM configs in VllmOmniConfig by @Acerak01-fy in https://github.com/vllm-project/vllm-omni/pull/6050
* [XPU][SDXL] Fix text encoder input device under CPU offload by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/6125
* [Bugfix] Avoid eager pi0 runtime import in pipeline registry by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6322
* [Core] Support online FP8 with DLO AllGather by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6279
* [BugFix][NPU] Wan2.2-S2V RoPE: replace complex64 advanced indexing with index_select by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/6320
* [Bugfix | Model] Fix SenseNova & Use Well-defined Model Configs by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/5877
* [BugFix][TTS] Move user input from INFO to DEBUG in TTS/audio log lines by @dougbtv in https://github.com/vllm-project/vllm-omni/pull/6329
* [Perf] Fuse MiniMax H3 SwiGLU activation by @gcanlin in https://github.com/vllm-project/vllm-omni/pull/6283
* [Perf] Fuse MiniMax H3 modulation with FP32 accumulation by @gcanlin in https://github.com/vllm-project/vllm-omni/pull/6281
* [REFACT]Refactor diffusion parallel state by @bjf-frz in https://github.com/vllm-project/vllm-omni/pull/5531
* [Model] Add SANA-WM support(Stage-1 only) by @BruceLoveDecimal in https://github.com/vllm-project/vllm-omni/pull/4061
* [Ming] Cleanup Ming-family shared modules by @yuanheng-zhao in https://github.com/vllm-project/vllm-omni/pull/6119
* [Perf] Enable async schedule for MOSS-TTS by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/6241
* [Tests][Refactor] P0.1: Add API server surface guardrails by @herotai214 in https://github.com/vllm-project/vllm-omni/pull/6202
* [Bugfix][MiniCPM-o] Restore streaming audio cache and unstall the first duplex response by @BruceLoveDecimal in https://github.com/vllm-project/vllm-omni/pull/6274
* [skip ci][Doc] Remove obsolete DiffusionParallelConfig in many example scripts by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/6347
* [Doc] Update vLLM-Omni WeChat QR code by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/6369
* [Bugfix][FLUX.2-klein] Fix duplicated image position ids  by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/6130
* [Bugfix] Record device-agnostic torch.Event on XPU to fix async D2H image corruption [XPU] by @tthakkal in https://github.com/vllm-project/vllm-omni/pull/5571
* [Docs] Remove stale stage config references by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/6270
* [XPU][Bugfix] Make Omni AR async output path device-agnostic by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/5569
* [Perf][CI] Reuse the Whisper judge worker across a test module by @ShengleiFu in https://github.com/vllm-project/vllm-omni/pull/6208
* [Bugfix][MiniCPM-o] Stop Talker mid-utterance truncation and load cod… by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/6346
* [BugFix][Diffusion] Fix MiniMax-H3 VAE hang when decoder tiles are fewer than ranks by @linzhenpl07 in https://github.com/vllm-project/vllm-omni/pull/6345
* [MUSA] Fix SwiGLU to use fused op by @yeahdongcn in https://github.com/vllm-project/vllm-omni/pull/6364
* [CI/Build] Match perf warmups to benchmark concurrency by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/6356
* [Bugfix] Reclaim resumable async-chunk requests on finish by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/6360
* [Bugfix] Use dedicated WORLD group for distributed VAE communication by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/6401
* [Bugfix][MiniCPM-o][NPU] Skip Code2Wav dynamo unwrap when flow.encode… by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/6397
* [Refactor] Worker/ModelRunner runner correctness fixes (G2/N) by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/5452
* [CI/Build] Strengthen pre-commit with markdownlint, SPDX, and policy hooks by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/6273
* [Bugfix] Return diffusion metrics for image-edit endpoint by @kTorp in https://github.com/vllm-project/vllm-omni/pull/5999
* [Model] Suppress silence codec tokens for the first N Qwen3-TTS decod… by @IneshReddy249 in https://github.com/vllm-project/vllm-omni/pull/5048
* [Perf][Hunyuan] Optimize for vae and patch_embed by @Bounty-hunter in https://github.com/vllm-project/vllm-omni/pull/6306
* Fix npu moe registration by @BLANKETusers in https://github.com/vllm-project/vllm-omni/pull/6350
* [Bugfix][Core] Fix replica device split when a stage omits devices by @yashkgp in https://github.com/vllm-project/vllm-omni/pull/5445
* [Tests] Run diffusion tiny model tests in parallel by @NickCao in https://github.com/vllm-project/vllm-omni/pull/6339
* Cosmos3 transfer fix by @MaciejBalaNV in https://github.com/vllm-project/vllm-omni/pull/5614
* [CI/Build] Update perf baselines base on 8/1-8/7 7 days avg by @congw729 in https://github.com/vllm-project/vllm-omni/pull/6201
* Cosmos3 logging and prompt improvements by @MaciejBalaNV in https://github.com/vllm-project/vllm-omni/pull/6325
* [Perf][Qwen3-TTS] Fuse QKV and gate_up projections in code predictor by @l-wave in https://github.com/vllm-project/vllm-omni/pull/5791
* [Bugfix] Preserve prompt token usage details by @ieaves in https://github.com/vllm-project/vllm-omni/pull/5181
* [Core] Add Host Weight Runtime foundation by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6419
* [Model] Add HiDream-O1-Image support by @yixiaoer in https://github.com/vllm-project/vllm-omni/pull/5194
* [Core] Add explicit post-load Host Weight Runtime publication by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6427
* [Tests] Re-enable previously skipped e2e/example tests by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5641
* [Skills] Add vLLM-Omni simplification review skill by @princepride in https://github.com/vllm-project/vllm-omni/pull/6363
* [Docs] Restore the Star History chart by @congw729 in https://github.com/vllm-project/vllm-omni/pull/6446
* [Bugfix][MiniCPM-o] Fix async-chunk snapshot replacement and prompt cleanup by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/6406
* [Bugfix][Diffusion] Fix MiniMax-H3 model-level CPU offload residency by @yeahdongcn in https://github.com/vllm-project/vllm-omni/pull/6072
* [BugFix]: CosyVoice3 STFT window device mismatch by @princepride in https://github.com/vllm-project/vllm-omni/pull/6454
* [Bugfix] Drop librosa reintroduced by Step-Audio2 by @NickCao in https://github.com/vllm-project/vllm-omni/pull/6467
* [Bugfix] Fix LongCat TeaCache CFG negative-branch guidance kwargs by @yzong-rh in https://github.com/vllm-project/vllm-omni/pull/6181
* [Model][Frontend] MiniMax-H3: Add opt-in planar video response encoding by @MosCloud in https://github.com/vllm-project/vllm-omni/pull/6288
* [Misc] Bump diffusers pin to 0.40.0 by @NickCao in https://github.com/vllm-project/vllm-omni/pull/6459
* [Bugfix][MiniCPM-o] Cap offline Talker generation at remaining context by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/6458
* [Refactor] Move model-specific capability metadata into TTS adapters by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/6138
* [Diffusion] Add final-layout BF16 Host Weight Runtime artifacts by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6445
* fix: keep DLO hooks outside regional compilation by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6073
* [Diffusion] Add native paged KV backend for diffusion workers by @Acerak01-fy in https://github.com/vllm-project/vllm-omni/pull/6102
* [Core] Add UniProc diffusion executor for single-GPU by @rahul-steiger-nv in https://github.com/vllm-project/vllm-omni/pull/6308
* [Bugfix] Make the async-output wait bound configurable and default it higher by @ivanusto in https://github.com/vllm-project/vllm-omni/pull/6255
* [Bugfix] Preserve pipeline sampling constraints by @maithilijoshi20 in https://github.com/vllm-project/vllm-omni/pull/6182
* [Bugfix] Release GPU memory after diffusion execution failures by @nagisa-kunhah in https://github.com/vllm-project/vllm-omni/pull/6385
* [Bugfix][Qwen3-Omni] Stabilize thinker MRoPE compilation by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/6449
* [BugFix] Eliminate distributed test port race by switching to file:// rendezvous by @NickCao in https://github.com/vllm-project/vllm-omni/pull/6468
* [CI]Remove SoulX-Singer support by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/6362
* [CI/Build] Move L1/E2E coverage to weekly and split scheduled L4/L5 pipelines by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/6311
* [tts][bugfix] Fix CosyVoice3 sampling and stage handoff by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/6424
* [CI] Remove AudioX and MammothModa2 support by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/6353
* [diffusion][test] Cover FLUX.2-dev online FP8 routing by @Songrui625 in https://github.com/vllm-project/vllm-omni/pull/3027
* [Bugfix] Fix Qwen3-Omni AWQ quantization name mapping by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5687
* [Feature] Support MiniMax-H3 Turbo LoRA with the legacy manager by @mglyn in https://github.com/vllm-project/vllm-omni/pull/6476
* [FEAT]Add FastVideo VSA backend for Wan2.2 by @bjf-frz in https://github.com/vllm-project/vllm-omni/pull/4820
* [Feature]: Support pause / resume and sleep / wake for AR stages in AsyncOmni by @knlnguyen1802 in https://github.com/vllm-project/vllm-omni/pull/6084
* [Doc] Update vLLM-Omni WeChat QR code by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/6535
* [CI]Fix Wan DMD pipeline test alignment by @bjf-frz in https://github.com/vllm-project/vllm-omni/pull/6557
* [Bugfix] Prevent LTX-2.5 from silently loading unindexed Diffusers shards by @mglyn in https://github.com/vllm-project/vllm-omni/pull/6234
* [Feature][MiniMax-H3] Support diffusion continuous batching by @princepride in https://github.com/vllm-project/vllm-omni/pull/5810
* Revert "[CI]Fix Wan DMD pipeline test alignment" by @Gaohan123 in https://github.com/vllm-project/vllm-omni/pull/6574
* Revert "Revert "[CI]Fix Wan DMD pipeline test alignment"" by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6578
* [CI] Resume AR admission after sleep-mode wake by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6581
* [Diffusion] Integrate no-AllGather DLO with Host Weight Runtime by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6486
* [Test] Cleanup for helpers by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/6523
* [Model] Add native SANA-Video 2B T2V and I2V support by @liuyao0322 in https://github.com/vllm-project/vllm-omni/pull/5508
* [Bugfix] Invalidate stale ref_audio cache on local file modification (#4873) by @pranavthakur0-0 in https://github.com/vllm-project/vllm-omni/pull/5670
* [Bugfix] Honor height/width overrides in LongCatImageEditPipeline by @yzong-rh in https://github.com/vllm-project/vllm-omni/pull/6222
* [Feature][MiniCPM-o] Support configurable concurrent duplex sessions by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/6021
* [Bugfix] Fix remote replica membership lifecycle races by @hbhflw2000 in https://github.com/vllm-project/vllm-omni/pull/5277
* [minor, fix] Remove cuda sync on wake_up in AsyncOmni by @knlnguyen1802 in https://github.com/vllm-project/vllm-omni/pull/4092
* [Refactor][2/N Scheduler]Replace _FULL_PAYLOAD_INPUT_STAGES with a resolved stage transport capability. by @wy17003 in https://github.com/vllm-project/vllm-omni/pull/6149
* [perf] Add mask-free TRTLLM packed-padding path by @bobboli in https://github.com/vllm-project/vllm-omni/pull/6542
* [Test] add marker for stability and add Wan2.2 npu test case by @zhumingjue138 in https://github.com/vllm-project/vllm-omni/pull/6343
* [BugFix] Qwen-image performance regressed - Avoid mapping diffusion_batch_size onto scheduler max_num_seqs by @NumberWan in https://github.com/vllm-project/vllm-omni/pull/6525
* [CI] Fix response_format json_schema error expectation by @clumsylad21 in https://github.com/vllm-project/vllm-omni/pull/6290
* [Misc] move text-to-audio online examples to a unified folder by @zzehli in https://github.com/vllm-project/vllm-omni/pull/4807
* [CI/Build] Clean up Qwen3-Omni nightly tests by @psv666 in https://github.com/vllm-project/vllm-omni/pull/6570
* [AutoRound] Add offline quantized MXFP4 model support by @jl9876 in https://github.com/vllm-project/vllm-omni/pull/5544
* [CI] Reduce Qwen-Image Function and share step-execution perf server by @NumberWan in https://github.com/vllm-project/vllm-omni/pull/6613
* [Model] Optimize MiniMax-H3 DLO component lifecycle by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6526
* [Diffusion] Register HWR mmap for direct DLO H2D by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6591
* [Benchmark] Add local OmniInteract realtime benchmark by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/6522
* [Bugfix] Handle DoS Overflow Cases by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/6598
* [CI/Build] Pin GGUF plugin for diffusion nightly tests by @wxwxwwxxx in https://github.com/vllm-project/vllm-omni/pull/6303
* [Doc] Add environment variables configuration reference by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6217
* [Bugfix] Reconcile env-var inventory with post-#6217 main drift by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6631
* [Perf][NPU] Enable native GQA & fused AddNorm for MiniMax-H3 encoder by @MarkPoloChina in https://github.com/vllm-project/vllm-omni/pull/6040
* [CI]Remove DreamID-Omni and MagiHuman support by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/6357
* text and image metric  by @AbelSara in https://github.com/vllm-project/vllm-omni/pull/6150
* [Bugfix][MiniCPM-o] Serve native duplex from shipping YAMLs and fence… by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/6619
* [Model] Optimize CosyVoice3 TensorRT stream handoff by @EchoHayate in https://github.com/vllm-project/vllm-omni/pull/5673
* [Bugfix] Restore name-based model detection for HF cache snapshot paths by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/6624
* Revert "[Bugfix] Restore name-based model detection for HF cache snapshot paths" by @Gaohan123 in https://github.com/vllm-project/vllm-omni/pull/6642
* [Feature] Support MiniMax-H3 Turbo LoRA with DLO by @mglyn in https://github.com/vllm-project/vllm-omni/pull/6550
* [Doc] Add MiMo-Audio recipe for RTX 5090/5090D 32GB by @smartDream-chao in https://github.com/vllm-project/vllm-omni/pull/6559
* [Test] Add MiniMax-H3 DLO DP2 T2VA smoke by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/6555
* [Bugfix] Fix missing Realtime audio completion by @psv666 in https://github.com/vllm-project/vllm-omni/pull/6564
* [Model][Bugfix] Improve LTX audio parity and similarity guards by @mglyn in https://github.com/vllm-project/vllm-omni/pull/6342
* [Perf][Engine] Event-driven orchestration loop (opt-in) — S1 of #4855 by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/5221
* [Recipe] zai-org/GLM-TTS (2x non-standard RTX 4090 48GB) by @harley619 in https://github.com/vllm-project/vllm-omni/pull/5769
* [Bugfix] Reject instructions changes on locked native duplex sessions by @anurag12-webster in https://github.com/vllm-project/vllm-omni/pull/6318
* [Bugfix][Diffusion] Fix FLASH_ATTN cross-attention key-padding unpad by @cr-gao in https://github.com/vllm-project/vllm-omni/pull/5866
* [Bugfix] Validate per-stage device layout before spawning workers (#5003) by @ChoHee15 in https://github.com/vllm-project/vllm-omni/pull/5742
* [Model] Add native full-duplex Nemotron VoiceChat serving by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/6089
* [diffusion][feature] Add offline SVDQuant W4A4 support by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/6162
* [Diffusion] Add FLUX.2-klein BF16 HWR contract by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6651
* [Rebase] Rebase to vllm 0.28.0 by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/6606

## New Contributors
* @wjialish made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5915
* @HaningZS made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6121
* @stringl1l1l1l made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6082
* @Moore-Z made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4765
* @MrlixiangWE made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6172
* @hotTeaFun made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4845
* @mo-ke-ke made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6173
* @m0g3r made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6214
* @anurag12-webster made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5983
* @yicwang made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4222
* @yzong-rh made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6181
* @MosCloud made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6288
* @ivanusto made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6255
* @pranavthakur0-0 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5670
* @wy17003 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6149
* @clumsylad21 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6290
* @jl9876 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5544
* @wxwxwwxxx made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6303
* @MarkPoloChina made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6040
* @EchoHayate made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5673
* @smartDream-chao made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6559
* @harley619 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5769

**Full Changelog**: https://github.com/vllm-project/vllm-omni/compare/v0.27.0rc1...v0.28.0rc1