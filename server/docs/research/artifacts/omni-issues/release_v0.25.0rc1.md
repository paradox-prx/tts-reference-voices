## Highlights

This release candidate features 32 merged pull requests from 22 contributors, including 5 new contributors.

vLLM-Omni `v0.25.0rc1` aligns the project with the vLLM 0.25 release line and delivers improvements across composable parallel execution, diffusion and image generation, TTS performance and correctness, model integration, quantization extensibility, endpoint behavior, testing, and documentation.

This release adds Krea 2 text-to-image support, sequence parallelism for OmniGen2, and the first phase of composable parallel strategy overlays. It also improves Qwen3-TTS performance and batching, strengthens Ming-TTS, MOSS-TTS, Voxtral, and VoxCPM2 serving, migrates additional models and examples to standardized registries and `model_extras`, and moves GGUF diffusion quantization support into an out-of-tree plugin.

### Key Improvements

* **Aligned with the vLLM 0.25 release line**, including the vLLM v0.25.0 rebase and compatibility fixes for custom IR operations, RMSNorm, stage payloads, deployment configuration, and model test levels. **(#5042, #5009, #5015, #5008)**
* **Introduced composable parallel strategy overlays**, providing the first phase of unified TP, DP, and stage-replica configuration for distributed Omni workloads. **(#4281)**
* **Expanded diffusion and image-generation support**, adding Krea 2, sequence parallelism for OmniGen2, Hugging Face kernel-package integration, improved hub-kernel loading, and standardized Ming-flash-omni-2.0 examples. **(#4730, #3206, #4926, #4977, #4835)**
* **Improved Qwen3-TTS performance and batching**, eliminating unnecessary per-step device-to-host transfers, restoring batched MTP sampling, aligning CUDA Graph capture with async output, and adding Gumbel-max code-predictor sampling. **(#4879, #4970, #4923, #4261)**
* **Strengthened TTS and speech correctness**, fixing out-of-vocabulary stop-token masking, direct speaker-embedding handling, MOSS-TTS codec resolution, Voxtral feedback and short-ASR checks, and VoxCPM2 remote-code loading. **(#4971, #5005, #4760, #4954, #4984)**
* **Improved model and pipeline integration**, migrating MammothModa2 and OmniVoice to the pipeline registry and fixing Qwen3-Omni video metadata handling when audio from video is enabled. **(#4647, #4959)**
* **Expanded quantization extensibility**, migrating GGUF diffusion-model support to an out-of-tree plugin. **(#4769)**
* **Improved serving resilience and validation**, adding endpoint rejection support, fixing LoRA argument forwarding, correcting RoPE shape handling, and expanding compact diffusion and image-to-video test coverage. **(#4762, #4936, #4655, #4524, #3573)**

### Core Architecture & Runtime

* Added the first phase of composable parallel strategy overlays, enabling TP, DP, and stage-replica settings to be composed through a unified execution strategy. **(#4281)**
* Added a mechanism for endpoints to reject unsupported requests before execution, improving routing behavior and frontend error handling. **(#4762)**
* Migrated MammothModa2 and OmniVoice to the pipeline registry, consolidating model discovery and pipeline configuration. **(#4647)**
* Removed redundant functions and logging as part of the first phase of runtime cleanup. **(#4986)**
* Fixed stale CI expectations following recent stage-payload and deployment-configuration changes. **(#5015)**
* Restored `vllm_c` IR operation priority and `torch.nn.RMSNorm` behavior required by Qwen-Image after upstream compatibility changes. **(#5009)**

### Model Support

* Added support for the **Krea 2** text-to-image diffusion model. **(#4730)**
* Added sequence parallelism support for **OmniGen2**, improving distributed diffusion execution. **(#3206)**
* Migrated **MammothModa2** and **OmniVoice** to the pipeline registry. **(#4647)**
* Migrated Ming-flash-omni-2.0 image-generation examples to the standard `model_extras` configuration style. **(#4835)**
* Fixed Qwen3-Omni video metadata handling when `use_audio_in_video` is enabled. **(#4959)**
* Fixed RoPE handling for inputs that could otherwise produce shape mismatches. **(#4655)**

### Audio, Speech & TTS Serving

* Improved Qwen3-TTS performance by allowing hidden-pooler payloads to opt out of per-step hidden-state device-to-host transfers. **(#4879)**
* Removed the default Qwen3-TTS seed configuration that prevented batched MTP sampling. **(#4970)**
* Aligned Qwen3-TTS talker MTP CUDA Graph capture with Qwen3-Omni behavior and added async-output compatibility. **(#4923)**
* Added Gumbel-max sampling for Qwen3-TTS code-predictor outputs. **(#4261)**
* Fixed Qwen3-TTS engine crashes by dropping out-of-vocabulary stop IDs from minimum-token masking. **(#4971)**
* Fixed Ming-TTS voice handling so uploaded direct speaker embeddings are used correctly. **(#5005)**
* Improved MOSS-TTS codec compatibility by resolving the decode method across remote-code and vendored tokenizer implementations. **(#4760)**
* Fixed Voxtral TTS feedback handling and short-ASR validation. **(#4954)**
* Fixed VoxCPM2 performance-server loading when models require `trust_remote_code`. **(#4984)**

### Diffusion & Image Generation

* Added Krea 2 text-to-image model support. **(#4730)**
* Added sequence parallelism for OmniGen2 diffusion inference. **(#3206)**
* Added support for the Hugging Face kernels package in native diffusion attention backends. **(#4926)**
* Improved Hugging Face Hub kernel discovery and loading in `flash_attn_hub`. **(#4977)**
* Migrated GGUF diffusion quantization support to an out-of-tree plugin. **(#4769)**
* Fixed LoRA argument forwarding in the offline text-to-image example. **(#4936)**
* Added a reusable tiny-diffusion-model testing pattern for lightweight and deterministic diffusion tests. **(#4524)**
* Restored operation priority and RMSNorm compatibility required by Qwen-Image. **(#5009)**

### Quantization, Kernels & Dependencies

* Migrated GGUF diffusion-model support into an out-of-tree quantization plugin, reducing core coupling and improving extensibility. **(#4769)**
* Added Hugging Face kernel-package support for native diffusion attention backends. **(#4926)**
* Improved remote kernel loading behavior in `flash_attn_hub`. **(#4977)**
* Updated `safetensors` to the 0.8.0 release. **(#4713)**

### Serving, Frontend & API Behavior

* Added endpoint rejection support so incompatible or unsupported requests can be rejected through a standardized mechanism. **(#4762)**
* Fixed LoRA argument propagation in offline text-to-image serving examples. **(#4936)**
* Fixed Qwen3-Omni video metadata propagation for requests using audio embedded in video. **(#4959)**
* Fixed direct speaker-embedding handling for Ming-TTS voice requests. **(#5005)**
* Corrected the MiniCPM-o 4.5 curl-based TTS example and clarified `chat_template_kwargs` usage. **(#4950)**

### CI, Testing & Documentation

* Added image-to-video offline example documentation and test coverage. **(#3573)**
* Added a tiny diffusion model pattern for faster and more focused diffusion testing. **(#4524)**
* Fixed core-model CI level selection for non-diffusion models. **(#5008)**
* Updated invalid-layer DFX tests to use the supported 2–10 range. **(#5047)**
* Fixed CI failures caused by stale expectations after stage-payload and deployment-configuration changes. **(#5015)**
* Updated the WeChat community group QR code. **(#4939)**

## What's Changed
* [Refactor] Migrate Ming-flash-omni-2.0 Image-gen examples with model_extras by @yuanheng-zhao in https://github.com/vllm-project/vllm-omni/pull/4835
* [Bugfix] Fix LoRA arguments passing in offline text-to-image script by @SamitHuang in https://github.com/vllm-project/vllm-omni/pull/4936
* [BugFix] fix possible shape mismatch when using ROPE by @Semmer2 in https://github.com/vllm-project/vllm-omni/pull/4655
* Update WeChat group QR code by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/4939
* [Refactor] Migrate MammothModa2 and OmniVoice to pipeline registry by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/4647
* [Diffusion][Feature] Add SP for Omnigen2 by @zhangj1an in https://github.com/vllm-project/vllm-omni/pull/3206
* [Test] Add image-to-video offline example docs and tests by @loveysuby in https://github.com/vllm-project/vllm-omni/pull/3573
* [Bugfix] MOSS-TTS codec: resolve decode method across remote-code and vendored tokenizers by @IneshReddy249 in https://github.com/vllm-project/vllm-omni/pull/4760
* Support HuggingFace kernels package for native diffusion attention backends by @SamitHuang in https://github.com/vllm-project/vllm-omni/pull/4926
* docs(recipe): fix MiniCPM-o 4.5 curl TTS example and clarify chat_template_kwargs usage by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/4950
* [Core / Bugfix] Add Mechanism for Endpoint Rejection by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/4762
* Fix Voxtral TTS feedback and short ASR checks by @napleon-liu in https://github.com/vllm-project/vllm-omni/pull/4954
* [Bugfix] Drop out-of-vocabulary stop ids from min-tokens masking (qwen3-tts min_tokens engine crash) by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/4971
* [Perf][Qwen3-TTS] Skip per-step hidden-state D2H via hidden pooler payload opt-out by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/4879
* [Perf][Qwen3-TTS] Drop default seed from qwen3_tts.yaml to restore batched MTP sampling by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/4970
* [Diffusion] Improve HuggingFace hub kernel loading in flash_attn_hub by @SamitHuang in https://github.com/vllm-project/vllm-omni/pull/4977
* [Tests] Tiny Diffusion Model Pattern by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/4524
* Bump safetensors to the 0.8.0 release by @oglok in https://github.com/vllm-project/vllm-omni/pull/4713
* [Perf][Qwen3-TTS] Align talker MTP CUDA graph capture with Qwen3-Omni & Adapt to async output by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/4923
* Fix VoxCPM2 perf server trust remote code by @napleon-liu in https://github.com/vllm-project/vllm-omni/pull/4984
* [Perf][Qwen3-TTS] Sample code predictor outputs via Gumbel-max by @l-wave in https://github.com/vllm-project/vllm-omni/pull/4261
* [Bugfix][Model] Fix Qwen3-Omni video metadata handling for use_audio_in_video by @ZhengWG in https://github.com/vllm-project/vllm-omni/pull/4959
* [BugFix][Ming-TTS] Use uploaded direct speaker embeddings by voice by @LHXuuu in https://github.com/vllm-project/vllm-omni/pull/5005
* [Refactor][Phase 1]Remove redundant functions and logs by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/4986
* [BugFix] Fix CI failures caused by stale test expectations after recent stage-payload / deploy-config changes. by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/5015
* [BugFix] Restore vllm_c IR op priority and torch.nn.RMSNorm for Qwen-Image (#4964) by @NumberWan in https://github.com/vllm-project/vllm-omni/pull/5009
* [Core] Composable parallel: Phase 1 strategy overlay (TP/DP/stage-replica) (RFC #4084) by @kushanam in https://github.com/vllm-project/vllm-omni/pull/4281
* [Quantization] Migrate GGUF diffusion model support to OOT plugin by @Isotr0py in https://github.com/vllm-project/vllm-omni/pull/4769
* [Model] Add Krea 2 text-to-image diffusion model by @Abhinay1997 in https://github.com/vllm-project/vllm-omni/pull/4730
* [CI] Fix core_model Level for non-Diffusion Models by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/5008
* [BugFix] Align invalid layers DFX tests with 2-10 range (#5044) by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5047
* [Rebase] Rebase to vllm v0.25.0 by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/5042

## New Contributors
* @zwhzzz0821 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4647
* @IneshReddy249 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4760
* @napleon-liu made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4954
* @l-wave made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4261
* @Abhinay1997 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4730

**Full Changelog**: https://github.com/vllm-project/vllm-omni/compare/v0.24.0...v0.25.0rc1