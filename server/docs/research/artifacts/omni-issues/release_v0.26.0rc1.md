## Highlights

This release candidate features 145 merged pull requests from 71 contributors, including 21 new contributors.

vLLM-Omni `v0.26.0rc1` aligns the project with the vLLM 0.26 release line and delivers major improvements across streaming and realtime multimodal serving, diffusion and world-model execution, TTS performance, model coverage, quantization, hardware acceleration, runtime architecture, and CI infrastructure.

This release introduces a full-duplex realtime runtime with a MiniCPM-o 4.5 demo, midway prompt updates for streaming video generation, and session-state infrastructure for autoregressive diffusion world models. It expands model support with Cosmos3 Edge and Distilled checkpoints, LingBot Video, Boogu Image, MammothModa2-Dev, MOSS-TTS-Local v1.5, and broader MiniCPM-o 4.5 integration. It also adds new diffusion parallelism, offloading, attention, compilation, and caching capabilities while substantially improving Ming-TTS, Qwen3-TTS, MOSS-TTS, Qwen3-Omni, and MiniCPM-o performance and correctness.

### Key Improvements

* **Aligned with the vLLM 0.26 release line**, including the vLLM 0.26.0 rebase and compatibility updates across XPU, NPU, CUDA, ROCm, diffusion FusedMoE, deployment configuration, and CI images. **(#5443, #5066, #5115, #5167)**
* **Introduced full-duplex and interactive streaming capabilities**, adding a full-duplex realtime runtime, a MiniCPM-o 4.5 demo, midway prompt updates for streaming video generation, and improved realtime session lifecycle handling. **(#3907, #4652, #5383, #5388)**
* **Expanded diffusion and world-model support**, adding Cosmos3 Edge and Distilled checkpoints, LingBot Video dense and MoE variants, Boogu Image, MammothModa2-Dev, and session-state infrastructure for autoregressive diffusion world models. **(#5001, #5035, #4995, #5411, #4487)**
* **Improved diffusion performance and scalability**, adding CFG parallelism for FLUX Kontext, VAE patch parallelism and layerwise CPU offload for FLUX.2-dev, AllGather-KV sequence-parallel attention, TensorRT-LLM diffusion attention, configurable compile granularity, and Cache-DiT support. **(#2281, #5292, #5256, #4968, #5283, #4603, #4205)**
* **Accelerated TTS streaming and generation**, reducing Ming-TTS time to first packet, optimizing its Stage-0 flow head and speaker caching, improving Qwen3-TTS compilation and chunk scheduling, and enabling CUDA Graph execution for MOSS-TTS-Local v1.5. **(#5011, #4942, #5240, #5351, #5107, #5152, #5197)**
* **Strengthened multimodal and speech correctness**, fixing Qwen3-Omni speaker metadata and audio-video cache behavior, MiniCPM-o audio output and placeholder handling, realtime connector flushing, audio format propagation, and per-request speech-code routing. **(#5086, #5308, #5116, #5455, #5414, #4718, #5070)**
* **Expanded quantization capabilities**, adding BitsAndBytes W4 for diffusion transformers, Transformer Engine FP8 for FLUX.2-dev Mistral, Cosmos3 ModelOpt FP8 loading, NVFP4 scale remapping, and HSDP packed-parameter support. **(#5037, #5136, #5076, #5087, #5088)**
* **Modernized core runtime and pipeline architecture**, migrating legacy stage configurations to the pipeline registry, moving diffusion outputs to payload metadata, cleaning up diffusion executor, scheduler, worker, and model-runner interfaces, and consolidating connector and metrics infrastructure. **(#5031, #4922, #4980, #5215, #5216, #5217, #5218, #5096, #5168)**

### Core Architecture & Runtime

* Rebasing the project onto vLLM 0.26.0 aligned the runtime with the latest vLLM release line. **(#5443)**
* Added a session-state manager for autoregressive diffusion world models, establishing the first phase of persistent world-model sessions. **(#4487)**
* Generalized autoregressive diffusion KV-session capabilities and added support for prefetched KV jobs in the model runner. **(#5271, #4941)**
* Added the full-duplex realtime runtime and a MiniCPM-o 4.5 demonstration application. **(#3907)**
* Migrated legacy stage configurations to the pipeline registry and made stage metadata available through `VllmOmniConfig`. **(#5031, #5343)**
* Updated configuration construction to return `VllmOmniConfig` and fixed missing `sequence_parallel_size` values in generated deployment configurations. **(#4818, #5449)**
* Refactored diffusion outputs around payload metadata and moved multimodal payload accumulation into `MultimodalPayload`. **(#4922, #4980)**
* Refactored diffusion output streaming and cleaned up executor, scheduler, worker, and model-runner interfaces. **(#5166, #5215, #5216, #5217, #5218)**
* Cleaned up Omni connector runtime and transfer backends and fixed terminal async-chunk processor flushing. **(#5096, #5414)**
* Centralized metrics helpers and split the benchmark serving CLI into more focused modules. **(#5168, #5206)**
* Removed obsolete scheduler, diffusion-hook, model-loader, configuration, and example code. **(#5312, #5270, #5199, #5201, #5335)**

### Model Support

* Added support for **Cosmos3 Edge** and **Cosmos3 Distilled** checkpoints, together with an Edge deployment recipe and updated scheduler behavior. **(#5001, #5313, #5176)**
* Added dense and MoE support for **LingBot Video**. **(#5035)**
* Added support for **Boogu Image 0.1 Base** and **Boogu Image 0.1 Edit**. **(#4995)**
* Added support for **MammothModa2-Dev** and migrated its examples to the shared `x_to_text.py` interface. **(#5411, #5454)**
* Added support for the **MOSS-TTS-Local v1.5** vocoder graph. **(#4929)**
* Expanded **MiniCPM-o 4.5** support with offline and online examples, end-to-end tests, Ascend NPU talker and vocoder support, and multiple memory and performance optimizations. **(#5222, #5237, #5117, #5130, #5188, #5228, #5447)**
* Added **Fish Speech TTS** inference support on XPU. **(#4856)**
* Added a Cosmos3 Nano recipe for Ascend NPU hardware. **(#4978)**
* Fixed SoulX-Singer pipeline registration and several remote-code loading paths. **(#5210, #5006, #5213)**
* Fixed Ming processor registration with Transformers 5.x and newer. **(#5243)**

### Audio, Speech & TTS Serving

* Reduced Ming-TTS streaming time to first packet by emitting an initial latent chunk earlier. **(#5011)**
* Accelerated the Ming-TTS Stage-0 flow head with fused RoPE and QKV operations, optional `torch.compile`, and piecewise CUDA Graph execution. **(#4942)**
* Added speaker-embedding caching for uploaded Ming-TTS reference audio and moved speaker extraction and caching into Stage 0. **(#5240, #5351)**
* Improved Qwen3-TTS performance by caching decoder masks and compiling the pre-transformer path. **(#5107)**
* Added configurable Qwen3-TTS codec chunk ramp-up for smoother streaming startup. **(#5152)**
* Added mode-aware reference-audio artifact readiness for Qwen3-TTS. **(#5157)**
* Refactored MOSS-TTS-Local v1.5 talker execution for CUDA Graph compatibility and added a single-80GB deployment configuration. **(#5197, #4761)**
* Fixed Qwen3-Omni speaker metadata during non-async handoff and restored audio output for MiniCPM-o when async chunking is disabled. **(#5086, #5455)**
* Fixed MiniCPM-o 4.5 audio placeholder pooling, Hugging Face cache-path resolution, and single-GPU startup memory usage. **(#5116, #5301, #5447)**
* Fixed request-local speech-code routing for MiMo Audio under continuous batching. **(#5070)**
* Propagated Higgs Audio V3 sampling parameters to the sampler and adjusted an overly strict Higgs Audio V2 streaming quality threshold. **(#5406, #5232)**
* Kept the HiFT vocoder on Ascend NPU instead of unnecessarily transferring it to the CPU. **(#5242)**
* Fixed audio output format handling in chat completions. **(#4718)**

### Diffusion, Image & Video Generation

* Added CFG parallel execution for **FLUX.1-Kontext-dev**. **(#2281)**
* Added Cache-DiT support for FLUX.1-Kontext-dev and began reorganizing diffusion cache integrations. **(#4205, #5226)**
* Added FLUX.2-dev layerwise CPU offloading and VAE patch parallelism. **(#5256, #5292)**
* Added AllGather-KV sequence-parallel attention and a TensorRT-LLM diffusion attention backend with Skip-Softmax support. **(#4968, #5283)**
* Added configurable diffusion compilation granularity. **(#4603)**
* Extended Cosmos3 CPU offloading to component-level and layerwise execution paths. **(#4695)**
* Added Cosmos3 Edge and Distilled checkpoints and fixed configuration and scheduler compatibility for these models. **(#5001, #5239, #5176)**
* Added dense and MoE variants of LingBot Video and support for Boogu Image Base and Edit models. **(#5035, #4995)**
* Added midway prompt updates for streaming video generation. **(#4652)**
* Added per-video audio masks for Qwen Omni. **(#4656)**
* Fixed image CFG behavior in HunyuanImage and preserved image payloads when reasoning metadata is present. **(#4752, #5238)**
* Fixed Helios Cholesky failures caused by non-positive-definite matrices and unavailable CPU LAPACK paths. **(#4921)**
* Unified the LTX-2 and LTX-2.3 pipeline runtime. **(#5147)**
* Migrated the replica data-parallel Wan2.2 example to deployment configuration and added a replica-DP video DiT recipe and benchmark. **(#5267, #5052)**

### Quantization, Kernels & Performance

* Added BitsAndBytes W4 online quantization for diffusion transformers. **(#5037)**
* Added Transformer Engine online FP8 support for the FLUX.2-dev Mistral component. **(#5136)**
* Fixed loading of ModelOpt FP8 Cosmos3 checkpoints and remapped ModelOpt NVFP4 scale tensors. **(#5076, #5087)**
* Added support for packed quantized parameters with HSDP. **(#5088)**
* Initialized component-level quantization state consistently. **(#5103)**
* Fixed FP8 Quack GEMM execution under `inference_mode()` and `torch.compile()` and disabled it when required scale tensors are unavailable. **(#5153, #5262)**
* Added configurable diffusion compile granularity and expanded diffusion performance configurations. **(#4603, #5010)**
* Updated performance baselines using a seven-day average. **(#5231)**

### Serving, Frontend & API Behavior

* Added a full-duplex realtime serving runtime and removed the frontend restriction that prevented realtime use without async chunks. **(#3907, #5383)**
* Prevented disconnected realtime sessions from continuing to cycle through pipeline stages. **(#5388)**
* Added midway prompt updates for streaming video-generation requests. **(#4652)**
* Fixed async-streaming segment-stop accounting and ensured connector processors flush their final output on terminal sends. **(#5183, #5414)**
* Changed unsupported output modalities to return an explicit error instead of an empty choices array. **(#4720)**
* Fixed the `audio.format` parameter being silently ignored by chat completions. **(#4718)**
* Parsed `VLLM_USE_MODELSCOPE` through the standard vLLM environment configuration. **(#5428)**
* Cleaned up speech serving model validation by moving it into adapters. **(#4833)**
* Skipped non-positive scheduled token spans in Omni stage runners. **(#5269)**
* Coupled audio and video multimodal caches when `use_audio_in_video` is enabled. **(#5308)**

### Hardware Support

* Updated XPU support for the vLLM 0.25 compatibility line and fixed XPU memory-release and speculative-step failures. **(#5066, #5330)**
* Added Fish Speech TTS inference support on XPU and migrated the Voxtral TTS XPU configuration to deployment configuration. **(#4856, #5467)**
* Upgraded Ascend NPU CI images and added a Cosmos3 Nano recipe for A3 hardware. **(#5095, #4978)**
* Optimized Qwen3-TTS for Ascend 310P and kept the HiFT vocoder resident on the NPU. **(#4841, #5242)**
* Added Ascend NPU support for MiniCPM-o 4.5 talker and vocoder execution. **(#5117)**
* Ported the Omni connector model-runner mixin to NPU runners, fixing full-payload hangs when `async_chunk` is disabled. **(#5290)**
* Adapted HunyuanImage3 diffusion FusedMoE execution for newer vLLM versions. **(#5167)**
* Upgraded CUDA and ROCm Docker base images for the vLLM 0.25 compatibility line. **(#5115)**

### CI, Testing & Documentation

* Added local CI job-runner scripts for L2–L4 pytest execution. **(#4672)**
* Added JSON mark selection and paired parametrization for L4 performance tests, enabling more targeted NPU performance CI. **(#5084)**
* Added nightly Ascend NPU performance testing for Qwen3-TTS on A3 hardware. **(#5158)**
* Added pre-commit checks for missing pytest marks and improved local-model recognition in CI coverage checks. **(#4953, #5275)**
* Reorganized Buildkite configuration by hardware platform and unified CI-skip targeting and mirrored-hardware presets. **(#5119, #5254)**
* Optimized Docker caching and fixed editable-package discovery in containerized and Kubernetes CI environments. **(#5133, #5341, #5368)**
* Tiered diffusion-offloader tests to reduce merge-queue GPU pressure. **(#5185)**
* Added configuration-driven tiny-model builders and expanded MiniCPM-o 4.5 end-to-end testing. **(#5090, #5237)**
* Fixed or stabilized HunyuanImage, FrameSimilarityFilter, Qwen-Image, LTX FP8, FLUX Kontext, and audio-in-video test coverage. **(#5143, #4786, #5132, #5302, #5297, #5280)**
* Updated the README for v0.24.0, documented Cosmos3-Super AutoRound support, standardized serving names, and corrected Qwen3-Omni modality examples. **(#5060, #5062, #5081, #5173)**
* Removed stale BAGEL documentation and refreshed the WeChat community QR code. **(#5429, #5061, #5204, #5430)**

## What's Changed
* [Perf][Ming-TTS] Add initial latent chunk for lower streaming TTFP by @LHXuuu in https://github.com/vllm-project/vllm-omni/pull/5011
* docs: update README for v0.24.0 by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5060
* docs: document Cosmos3-Super AutoRound world-model support by @yiliu30 in https://github.com/vllm-project/vllm-omni/pull/5062
* docs: update WeChat QR code by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/5061
* [Perf] Ming-TTS Stage-0 flow-head speedup: RoPE/QKV fusion, opt-in torch.compile, PIECEWISE cudagraph by @ZhengWG in https://github.com/vllm-project/vllm-omni/pull/4942
* [XPU][CI] Fix xpu after rebasing for 0.25.0 by @xuechendi in https://github.com/vllm-project/vllm-omni/pull/5066
* [Bugfix] Pass --trust-remote-code via HunyuanImage3 DFX serve_args by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5006
* Extend Cosmos3 CPU offloading to component and layerwise paths by @rahul-steiger-nv in https://github.com/vllm-project/vllm-omni/pull/4695
* [Doc] Standardize serving names and identifiers by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5081
* [Bugfix] Restore Qwen3-Omni speaker metadata during non-async handoff  by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/5086
* [NPU] Upgrade CI IMAGE to v0.25.0 by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/5095
* [Quantization] Add BitsAndBytes W4 online quantization for diffusion transformer by @dpeng123 in https://github.com/vllm-project/vllm-omni/pull/5037
* [recipe] Add cosmos3-nano recipe for npu (1xA3) by @zhangj1an in https://github.com/vllm-project/vllm-omni/pull/4978
* [Bugfix] Accept kv_prefetch_jobs in ARDiffusionModelRunner.execute_model by @wjsuijlenh in https://github.com/vllm-project/vllm-omni/pull/4941
* [Bugfix][Quantization] Support packed parameters with HSDP by @pst2154 in https://github.com/vllm-project/vllm-omni/pull/5088
* [REFACT]Refactor diffusion outputs to payload metadata by @bjf-frz in https://github.com/vllm-project/vllm-omni/pull/4922
* [PERF][CI]Add Cosmos3 diffusion perf config by @bjf-frz in https://github.com/vllm-project/vllm-omni/pull/5010
* [Bugfix][Quantization] Initialize component quantization base state by @wuli666 in https://github.com/vllm-project/vllm-omni/pull/5103
* Fix loading of ModelOpt FP8 checkpoints for Cosmos3 by @wkutak in https://github.com/vllm-project/vllm-omni/pull/5076
* [Hardware][Ascend][Model] Optimize Qwen3-TTS on 310P by @zyz111222 in https://github.com/vllm-project/vllm-omni/pull/4841
* [Bug Fix] Hunyuan image cfg bugfix by @AbelSara in https://github.com/vllm-project/vllm-omni/pull/4752
* [CI] Add local job runner scripts for L2-L4 pytest execution by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/4672
* [Refactor][OutputProcessor 1/8]: clean up multimodal payload accumulation and move payload logic into MultimodalPayload & directory refactor by @bowieshi in https://github.com/vllm-project/vllm-omni/pull/4980
* [Bugfix] fix issue 5065 by @zhumingjue138 in https://github.com/vllm-project/vllm-omni/pull/5118
* [Bugfix] Fix audio.format parameter silently ignored in chat completions by @oglok in https://github.com/vllm-project/vllm-omni/pull/4718
* [Feature] Support MOSS-TTS-Local-v1.5 vocoder graph by @gcanlin in https://github.com/vllm-project/vllm-omni/pull/4929
* [CI][Perf] Add JSON mark support and paired parametrize for L4 perf, so as to further support performance‑case selection for NPU‑CI. by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5084
* Fix hunyuan ci by @BLANKETusers in https://github.com/vllm-project/vllm-omni/pull/5143
* Add Cosmos3 Edge and Distilled checkpoints support by @bastefaniak in https://github.com/vllm-project/vllm-omni/pull/5001
* [Bugfix][Quantization] Remap ModelOpt NVFP4 scale tensors by @pst2154 in https://github.com/vllm-project/vllm-omni/pull/5087
* Fix FP8 Quack GEMM call when inference_mode() and torch.compile() is used. by @bastefaniak in https://github.com/vllm-project/vllm-omni/pull/5153
* examples: replica data-parallel recipe + benchmark for video DiT (#4707) by @linzhenpl07 in https://github.com/vllm-project/vllm-omni/pull/5052
* [CI][NPU]:  Add nightly performance test for NPU - Qwen3-TTS on A3 by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/5158
* [bugfix] Use FlowMatchEulerDiscreteScheduler from diffusers 0.39.0 with correct RNG handling for upcoming Cosmos3 distilled models by @bastefaniak in https://github.com/vllm-project/vllm-omni/pull/5176
* [Bugfix] Add single-80GB deploy config for MOSS-TTS (resolves #4643 OOM) by @IneshReddy249 in https://github.com/vllm-project/vllm-omni/pull/4761
* [Bugfix] Fix broken FrameSimilarityFilter threshold test by @NickCao in https://github.com/vllm-project/vllm-omni/pull/4786
* [CI][Test] Tier diffusion offloader CI and reduce gpu_4_queue merge usage and fix #5182 by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5185
* [Config] Return VllmOmniConfig from create_from_model by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/4818
* [Refactor] Migrate Legacy Stage Configs to the Pipeline Registry by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/5031
* [Doc] Fix Qwen3-Omni modality documentation examples by @psv666 in https://github.com/vllm-project/vllm-omni/pull/5173
* Support Fish Speech TTS inference on XPU platform by @Liangyx2 in https://github.com/vllm-project/vllm-omni/pull/4856
* [Bugfix] Fix stale pipeline resolver test call by @Acerak01-fy in https://github.com/vllm-project/vllm-omni/pull/5193
* [CI/Build] Add Precommit Hooks for Catching Missing PytestMarks by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/4953
* [Refactor][CI] Reorganize .buildkite directory by platform by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5119
* [Feat] support CFG Parallel for FLUX kontext by @RuixiangMa in https://github.com/vllm-project/vllm-omni/pull/2281
* docs: update WeChat QR code by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/5204
* [Feature] Support per-video audio masks for Qwen Omni by @hbhflw2000 in https://github.com/vllm-project/vllm-omni/pull/4656
* [Cleanup]Migrate model validation to adapters and clean up serving_speech.py by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/4833
* [Bugfix][Qwen3-TTS] Mode-aware ref_audio artifact readiness (fixes #5049) by @ShengleiFu in https://github.com/vllm-project/vllm-omni/pull/5157
* [Quantization] Add FLUX.2-dev Mistral TE online FP8 support by @dpeng123 in https://github.com/vllm-project/vllm-omni/pull/5136
* [Refactor] Unify the LTX-2 and LTX-2.3 pipeline runtime by @mglyn in https://github.com/vllm-project/vllm-omni/pull/5147
* [Hardware][Ascend][Model] Add NPU support for MiniCPM-o 4.5 talker/vo… by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/5117
* [BugFix] Fix SoulX-Singer deploy pipeline registration by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/5210
* [Bugfix] Fix issue 5205, add trust-remote-code by @zhumingjue138 in https://github.com/vllm-project/vllm-omni/pull/5213
* Fix Qwen3-Omni thinker fused MoE LoRA by @napleon-liu in https://github.com/vllm-project/vllm-omni/pull/5191
* [Bugfix][Perf] mimo_audio: fix per-request speech-code routing under continuous batching by @JuanPZuluaga in https://github.com/vllm-project/vllm-omni/pull/5070
* [Example][MiniCPM-o] Add offline/online MiniCPM-o 4.5 examples by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/5222
* [Bug] Fix Ming feature extractor/processor registration crash under transformers >= 5.x by @mjZhaoElaine in https://github.com/vllm-project/vllm-omni/pull/5243
* [Hardware][Ascend] Keep HiFT vocoder on NPU by @00fish0 in https://github.com/vllm-project/vllm-omni/pull/5242
* [Bugfix] Fix MiniCPM-o 4.5 audio placeholder pool step by @frank-2077 in https://github.com/vllm-project/vllm-omni/pull/5116
* [bugfix] Cosmos3 edge fix config use_k_norm_und_for_gen name by @bastefaniak in https://github.com/vllm-project/vllm-omni/pull/5239
* [diffusion][model] Add LingBot Video dense and MoE support by @wtz2333 in https://github.com/vllm-project/vllm-omni/pull/5035
* [Bugfix][Quant] Skip quack FP8 GEMM when scales are unpopulated by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5262
* Update perf baseline base on 7/5-7/11 7 days avg. by @congw729 in https://github.com/vllm-project/vllm-omni/pull/5231
* [Refactor] Migrate replica-DP Wan2.2 example to --deploy-config by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5267
* [CI] skip test_audio_in_video_default_loader_sampling_regression (#5248) by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5280
* [Bugfix][CI] Recognize local_model in check-test-ci-coverage hook by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5275
* [BugFix][Diffusion] Preserve image payloads with reasoning metadata by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/5238
* [Model] Support Boogu/Boogu-Image-0.1-Base and Boogu/Boogu-Image-0.1-Edit by @zzehli in https://github.com/vllm-project/vllm-omni/pull/4995
* [Bugfix] MiniCPMo-4.5 bugfix by @R2-Y in https://github.com/vllm-project/vllm-omni/pull/5233
* [Refactor]: clean up diffusion executor lifecycle by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/5215
* [Core] Cleanup Omni connector runtime and transfer backends by @spencerr221 in https://github.com/vllm-project/vllm-omni/pull/5096
* [Refactor][Misc] Remove unused code in diffusion hooks/model_loader by @congw729 in https://github.com/vllm-project/vllm-omni/pull/5270
* [Bugfix][CI] Relax higgs_audio_v2 PCM streaming HNR threshold (fixes #5045) by @yuekaizhang in https://github.com/vllm-project/vllm-omni/pull/5232
* [Refactor]: clean up diffusion scheduler interfaces by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/5216
* [Model] Add Cache-DiT support for FLUX.1-Kontext-dev by @Sendoh-code in https://github.com/vllm-project/vllm-omni/pull/4205
* [Bug][CI] Pin the LTX FP8 quality gate to its established sigma schedule by @mglyn in https://github.com/vllm-project/vllm-omni/pull/5302
* [Refactor]: clean up diffusion worker interfaces by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/5217
* [Refactor]: clean up diffusion model runner surface by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/5218
* [CI][Bugfix] remove module-level skip_if_gated_repo_inaccessible in flux kontext e2e (#5250) by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5297
* [Refactor] Migrate Step-Audio2 online test to deploy config by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/5309
* [Refactor] [0/N] Scheduler clean dead code by @R2-Y in https://github.com/vllm-project/vllm-omni/pull/5312
* [Model] MiniCPM-o 4.5: optimize SigLIP position IDs by @Fyrgo8 in https://github.com/vllm-project/vllm-omni/pull/5130
* [Refactor]: Remove unnecessary config getattr by @princepride in https://github.com/vllm-project/vllm-omni/pull/5199
* [Bugfix] Return error for unsupported output modalities instead of empty choices by @oglok in https://github.com/vllm-project/vllm-omni/pull/4720
* [Bugfix][NPU] Port OmniConnectorModelRunnerMixin to NPU runners to fix async_chunk=false full-payload hang (#5234) by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/5290
* [Refactor]: Remove sensenova examples by @princepride in https://github.com/vllm-project/vllm-omni/pull/5201
* [Bugfix] Skip non-positive scheduled token spans in omni stage runners by @cr-gao in https://github.com/vllm-project/vllm-omni/pull/5269
* [Tests] Config driven tiny model builder by @NickCao in https://github.com/vllm-project/vllm-omni/pull/5090
* [CI/Perf] Optimize Docker Caching by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/5133
* [Refact] Refactor diffusion output streaming by @bjf-frz in https://github.com/vllm-project/vllm-omni/pull/5166
* [Perf][Ming-TTS] Cache speaker embeddings for uploaded reference audio by @LHXuuu in https://github.com/vllm-project/vllm-omni/pull/5240
* Generalize AR-Diffusion KV session capabilities by @Jack47 in https://github.com/vllm-project/vllm-omni/pull/5271
* [Diffusion] Add FLUX.2-dev CPU Offload (Layerwise) by @dpeng123 in https://github.com/vllm-project/vllm-omni/pull/5256
* [Model][MiniCPM-o 4.5] Resolve Hugging Face model ID to local cache path in TTS by @psv666 in https://github.com/vllm-project/vllm-omni/pull/5301
* [Full Duplex] Feat: Support Full-Duplex realtime runtime & add MiniCPM-o 4.5 demo by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/3907
* [CI] move Krea-2 expansion to slow and skip failing README snippets by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5347
* [CI/Bugfix] Fix empty vllm_omni stub breaking stage CLI imports after Docker cache (#5338) by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5341
* [Refactor] Centralize metrics related helpers to metrics/ by @ZacheryAU in https://github.com/vllm-project/vllm-omni/pull/5168
* [Refactor] Split vllm_omni/entrypoints/cli/benchmark/serve.py by @ZacheryAU in https://github.com/vllm-project/vllm-omni/pull/5206
* [Bugfix][XPU] Fix free-memory abort and num_speculative_steps crash on XPU by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/5330
* [Refector] Remove mammothmodal2-preview example by @princepride in https://github.com/vllm-project/vllm-omni/pull/5335
* [CI/Test] Skip realtime async_chunk WebSocket case blocked by #3907 (#5363) by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5367
* [Diffusion] Add VAE patch parallel support for FLUX.2-dev by @dpeng123 in https://github.com/vllm-project/vllm-omni/pull/5292
* [perf] Minicpm o4.5 optimization by @R2-Y in https://github.com/vllm-project/vllm-omni/pull/5228
* [Perf] Refactor MOSS-TTS-Local v1.5 talker and local structure for CUDA Graph by @gcanlin in https://github.com/vllm-project/vllm-omni/pull/5197
* [Bugfix][Core] Fix async streaming segment-stop accounting by @vklimkov-nvidia in https://github.com/vllm-project/vllm-omni/pull/5183
* [BugFix] Fix Helios Cholesky positive-definite crashes and CPU LAPACK… by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/4921
* [Refactor][CI] Unify skip-ci targeting and mirror_hardwares pipeline presets by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5254
* [Refactor][1/N]diffusion/cache: cache-dit by @yangjianjuan in https://github.com/vllm-project/vllm-omni/pull/5226
* [Feature] Add AllGather-KV sequence-parallel attention str… by @AbelSara in https://github.com/vllm-project/vllm-omni/pull/4968
* [perf] Add configurable diffusion compile granularity by @TaffyOfficial in https://github.com/vllm-project/vllm-omni/pull/4603
* [CI/Bugfix] Move CI editable APP_DIR to /opt/vllm-omni for k8s package discovery (#5364) by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5368
* [BugFix][CI] Upgrade ROCm and CUDA docker base images to v0.25.0 by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/5115
* [Bugfix][Frontend] Remove async-chunk guard from realtime API by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/5383
* [CI/Bugfix] Pin dev deps and downgrade mooncake for connector CI (#5389) by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5392
* perf(qwen3-tts): cache decoder masks and compile pre-transformer  by @Ma1oneZhang in https://github.com/vllm-project/vllm-omni/pull/5107
* [Bugfix][Higgs-Audio-V3] Propagate Sampling Parameters to Sampler by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/5406
* [BugFix]Add MiniCPM-o 4.5 end-to-end test suite (offline, online serving) by @y-null in https://github.com/vllm-project/vllm-omni/pull/5237
* [Refactor]: Intrduce x_to_text.py in examples by @princepride in https://github.com/vllm-project/vllm-omni/pull/5384
* [Recipe] Add Cosmos3-Edge by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5313
* [Refactor][Docs]: Remove stale BAGEL offline guide by @princepride in https://github.com/vllm-project/vllm-omni/pull/5429
* [Bugfix] skip test case for #5437 by @zhumingjue138 in https://github.com/vllm-project/vllm-omni/pull/5440
* feat(qwen3-tts): add codec_chunk_ramp for gradual chunk size warmup by @Wallbreazzz in https://github.com/vllm-project/vllm-omni/pull/5152
* [Bugfix][Frontend] Parse VLLM_USE_MODELSCOPE via vllm.envs by @yashkgp in https://github.com/vllm-project/vllm-omni/pull/5428
* [BugFix] Couple audio+video mm-cache for use_audio_in_video by @ZhengWG in https://github.com/vllm-project/vllm-omni/pull/5308
* test: make Qwen-Image diffusers-backend latency check fair and stable (#5108) by @IneshReddy249 in https://github.com/vllm-project/vllm-omni/pull/5132
* [Core] Session state manager for AR-diffusion world models (RFC #4480 Phase 0) by @wjsuijlenh in https://github.com/vllm-project/vllm-omni/pull/4487
* [Frontend] Add midway prompt update for streaming video generation by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/4652
* docs: update WeChat QR code by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/5430
* [Model] Optimize MiniCPM-o multimodal encoder memory by @xsmccc in https://github.com/vllm-project/vllm-omni/pull/5188
* [Refactor][WIP] Add missing test for modelrunner (G1/N) by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/5333
* [Deploy] Reduce MiniCPM-o single-GPU startup memory by @R2-Y in https://github.com/vllm-project/vllm-omni/pull/5447
* [Model] Support MammothModa2-Dev by @princepride in https://github.com/vllm-project/vllm-omni/pull/5411
* Fix missing sequence_parallel_size in deploy config output by @BLANKETusers in https://github.com/vllm-project/vllm-omni/pull/5449
* [Refactor]: Mammothmoda2-dev use x_to_text.py in examples by @princepride in https://github.com/vllm-project/vllm-omni/pull/5454
* [BugFix][MiniCPM-o] Restore audio output without async chunk by @R2-Y in https://github.com/vllm-project/vllm-omni/pull/5455
* [NPU][HunyuanImage3] Adapt diffusion FusedMoE for vLLM >= 0.24.0 by @jiangmengyu18 in https://github.com/vllm-project/vllm-omni/pull/5167
* [Config] Read stage metadata from VllmOmniConfig by @Acerak01-fy in https://github.com/vllm-project/vllm-omni/pull/5343
* [Attention] Add trtllm diffusion attention backend with Skip-Softmax by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5283
* [Refactor][Ming-TTS] Move speaker extraction and caching to Stage-0 by @LHXuuu in https://github.com/vllm-project/vllm-omni/pull/5351
* [Rebase] Rebase to vllm 0.26.0 by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/5443
* [Bugfix][Connectors] Flush processor tail on terminal async-chunk sends by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/5414
* [Bugfix][Realtime] Stop disconnected sessions from cycling through stages by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/5388
* [Refactor] Migrate Voxtral TTS XPU stage config to --deploy-config by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/5467

## New Contributors
* @dpeng123 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5037
* @wjsuijlenh made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4941
* @pst2154 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5088
* @wkutak made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5076
* @bowieshi made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4980
* @linzhenpl07 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5052
* @psv666 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5173
* @hbhflw2000 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4656
* @ShengleiFu made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5157
* @mjZhaoElaine made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5243
* @00fish0 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5242
* @frank-2077 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5116
* @wtz2333 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5035
* @Sendoh-code made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4205
* @Fyrgo8 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5130
* @cr-gao made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5269
* @Jack47 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5271
* @Ma1oneZhang made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5107
* @y-null made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5237
* @yashkgp made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5428
* @xsmccc made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5188

**Full Changelog**: https://github.com/vllm-project/vllm-omni/compare/v0.25.0rc1...v0.26.0rc1