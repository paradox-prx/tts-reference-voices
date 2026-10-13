## Highlights

This release features 252 merged changes from 96 contributors, including 35 new contributors.

vLLM-Omni `v0.26.0` is led by three major additions: 1) **MiniMax H3 joint video/audio generation**, 2) an **experimental full-duplex realtime runtime for MiniCPM-o 4.5**, and 3) **distributed layerwise diffusion offload with DP multi-concurrency and mmap-backed weight loading**. The release also aligns with vLLM 0.26, broadens model and hardware coverage, and advances interactive streaming, diffusion parallelism, TTS performance, quantization, and runtime architecture.

### Key Improvements

* **Added MiniMax H3 joint video/audio generation**, supporting T2VA, first-frame-to-video+audio (FL2VA), and image/audio or multi-video reference-to-video+audio (Ref2VA) through OpenAI-compatible `/v1/videos` serving. **(#5691)** NPU and ROCm are also supported in Day-0.
* **Introduced an experimental full-duplex realtime runtime for MiniCPM-o 4.5**, with native and Realtime-compatible WebSocket paths, streaming audio input/output, cancel and barge-in handling, overlap policy, and playback-aware session state. **(#3907)**
* **Added distributed layerwise offload for multi-device diffusion deployments**, combining sharded mmap-backed weight loading, AllGather reconstruction, double-buffered prefetch, and DP multi-concurrency. On the PR's Ascend 910B3 Cosmos3-Nano DP4 workload, cgroup peak memory fell from 178 GB to 47 GB while four requests ran concurrently. **(#5397)**
* **Scalable diffusion serving and performance improvement**, with midway prompt updates, asynchronous image outputs, OmniGen2 sequence parallelism, FLUX CFG/VAE parallelism, AllGather-KV attention, TensorRT-LLM diffusion attention, and official LTX multimodal guidance. **(#4652, #4981, #3206, #2281, #5292, #4968, #5283, #5148)**

### Core Architecture & Runtime

* Rebased the project onto **vLLM 0.26.0**, aligning engine, scheduler, model-runner, deployment, and platform integration with the vLLM 0.26 release line. **(#5443)**
* Added Phase 1 of **composable parallel strategy overlays**. An opt-in `strategy.yaml` can describe TP, DP, PP, EP, and stage-replica degrees while preserving existing deploy configurations and CLI precedence; TP and stage replicas received live end-to-end validation in this phase. **(#4281)**
* Added the experimental full-duplex runtime and extended it to three-stage MiniCPM-o serving, with session-scoped state and data-plane support for streaming, cancellation, barge-in, overlap handling, and playback acknowledgement. **(#3907, #5380, #5613)**
* Added the first session-state foundation for autoregressive diffusion world models, then generalized KV-session and prefetch-job capabilities for stateful world-model execution. **(#4487, #5271, #4941)**
* Migrated legacy stage configurations to the pipeline registry, surfaced stage metadata through `VllmOmniConfig`, and improved generated deployment configuration. **(#5031, #4818, #5343, #5449)**
* Modernized multimodal output and diffusion runtime boundaries through payload metadata, `MultimodalPayload`, output-streaming cleanup, and narrower executor, scheduler, worker, model-runner, connector, and metrics interfaces. **(#4922, #4980, #5166, #5215, #5216, #5217, #5218, #5096, #5168)**

### Model Support

* Added **MiniMaxAI/MiniMax-H3** support for joint video and synchronized audio generation. The new pipeline covers T2VA, FL2VA, and Ref2VA workloads and supports synchronous or asynchronous OpenAI-compatible video serving. **(#5691)**
* Added **Krea 2** text-to-image support and **OmniGen2** sequence parallelism. **(#4730, #3206)**
* Expanded world-model and video coverage with **Cosmos3 Edge and Distilled**, **LingBot Video dense and MoE**, and **MammothModa2-Dev**. **(#5001, #5035, #5411)**
* Added **Boogu Image 0.1 Base and Edit** and **Nemotron Audex** support. **(#4995, #4976)**
* Expanded **MiniCPM-o 4.5** with offline and online examples, full-duplex serving, end-to-end coverage, multimodal encoder and startup-memory optimizations, and Ascend NPU talker/vocoder support. **(#5222, #3907, #5237, #5188, #5447, #5117)**
* Added the **MOSS-TTS-Local v1.5** vocoder graph and **Fish Speech TTS** inference on XPU. **(#4929, #4856)**
* Fixed model integration and loading across Qwen3-Omni, Ming, SoulX-Singer, HunyuanImage3, and remote-code model paths. **(#5086, #5191, #5243, #5210, #5006, #5213)**

### Audio, Speech & Omni Production Optimization

* Reduced **Ming-TTS** streaming time to first packet with an initial latent chunk, accelerated its Stage-0 flow head with fused RoPE/QKV plus optional `torch.compile` and piecewise CUDA Graphs, and cached uploaded speaker embeddings in Stage 0. **(#5011, #4942, #5240, #5351)**
* Improved **Qwen3-TTS** throughput and streaming by avoiding per-step hidden-state device-to-host transfers, restoring batched MTP sampling, aligning CUDA Graph capture with async output, caching decoder masks, compiling the pre-transformer, and adding codec chunk ramp-up. **(#4879, #4970, #4923, #5107, #5152)**
* Improved **MOSS-TTS-Local v1.5** with a vocoder graph, dynamic-batch streaming sessions, CUDA Graph-compatible talker execution, and compile support for the talker and codec. **(#4929, #5235, #5197, #5530)**
* Strengthened MiniCPM-o speech correctness and memory behavior across audio placeholder handling, non-async output, three-stage full-duplex serving, vocoder headroom, implicit connector resolution, and single-GPU generation. **(#5116, #5455, #5380, #5621, #5533, #5637)**
* Fixed request-local MiMo Audio speech-code routing, VoxCPM2 chunked-prefill length handling, Qwen3-Omni speaker metadata, and chat-completion audio format propagation. **(#5070, #5416, #5086, #4718)**
* Optimized Qwen3-TTS for Ascend 310P and kept the HiFT vocoder resident on NPU. **(#4841, #5242)**

### Diffusion, Image & Video Generation

* Added **distributed layerwise offload** for multi-NPU diffusion deployments. Parameter sharding, mmap-backed loading, AllGather reconstruction, two-slot prefetch, and DP multi-concurrency reduce host-memory replication and enable large Cosmos3 workloads that do not fit as fully resident per-rank models. **(#5397)**
* Expanded distributed diffusion execution with CFG parallelism for FLUX.1-Kontext-dev, VAE patch parallelism for FLUX.2-dev, AllGather-KV sequence-parallel attention, and a TensorRT-LLM diffusion attention backend with Skip-Softmax. **(#2281, #5292, #4968, #5283)**
* Added layerwise CPU offload for FLUX.2-dev, component/layerwise CPU offload for Cosmos3, configurable diffusion compile granularity, and Cache-DiT support for FLUX.1-Kontext-dev. **(#5256, #4695, #4603, #4205)**
* Added **midway prompt updates** for chunked streaming video generation and asynchronous artifact output for diffusion image models. **(#4652, #4981)**
* Unified the LTX-2 and LTX-2.3 runtime, aligned one-stage multimodal guidance and numerical behavior with the official Lightricks implementation, and generalized CFG parallelism across the guidance plan. **(#5147, #5148, #5547)**
* Expanded Cosmos3 with Edge/Distilled checkpoints and presets, CPU-offload paths, NPU recipes, ModelOpt FP8 loading, and scheduler/configuration fixes. **(#5001, #5313, #5596, #4695, #4978, #5097, #5076, #5176)**
* Improved diffusion serving correctness around CFG companion dispatch, explicit `guidance_scale=0`, MagCache residual application, BAGEL CFG KV transfer, Wan2.2 guidance resolution, video tensor layout, offline Hub behavior, and image output metadata. **(#5482, #4999, #5561, #5620, #5615, #5418, #5403, #5619)**

### Quantization & Memory Efficiency

* Added **BitsAndBytes W4 online quantization** for diffusion transformers and **Transformer Engine online FP8** for the FLUX.2-dev Mistral text-encoder component. **(#5037, #5136)**
* Improved ModelOpt checkpoint compatibility with Cosmos3 FP8 loading and NVFP4 scale-tensor remapping. **(#5076, #5087)**
* Added packed-parameter support with HSDP and fixed component quantization initialization. **(#5088, #5103)**
* Fixed Quack FP8 GEMM behavior under `inference_mode()` plus `torch.compile()` and skipped the path when scale tensors are not populated. **(#5153, #5262)**
* Moved GGUF diffusion-model support from vLLM-Omni core to the out-of-tree `vllm-project/vllm-gguf-plugin`. **(#4769)**

### Serving, Frontend & API Behavior

* Added native `/v1/duplex` and Realtime-compatible `/v1/realtime?duplex=1` WebSocket entrypoints for the experimental MiniCPM-o 4.5 full-duplex runtime. **(#3907)**
* Added `session.prompt_update` steering for streaming video generation and asynchronous output for diffusion image generation. **(#4652, #4981)**
* Improved realtime lifecycle handling by allowing input commit without closing the speech WebSocket, stopping disconnected sessions, flushing connector tails, and making runtime-control payloads serializable. **(#5517, #5388, #5414, #5613)**
* Returned diffusion metrics from `/v1/images/generations`, corrected per-stage timing/token statistics, and normalized diffusion request extras in chat serving. **(#5278, #4974, #5171)**
* Improved API validation by rejecting unsupported output modalities, preserving caller sampling parameters, honoring explicit `guidance_scale=0`, and rejecting incompatible completions requests for thinker+talker models when remote code is unavailable. **(#4720, #4115, #4999, #5525)**

### Platforms, Distributed Execution & Hardware Coverage

* Added the distributed layerwise offload path validated on **Ascend 910B3**, and aligned Ascend NPU integration and CI with vLLM 0.26. **(#5397, #5490)**
* Expanded Ascend model coverage and recipes for MiniCPM-o 4.5, Qwen3-TTS, Cosmos3 Nano/Super, Qwen3-Omni, Wan2.2, Qwen-Image-Edit, and HunyuanImage3. **(#5117, #4841, #4978, #5097, #5339, #5167, #5436)**
* Added **CosyVoice3 support on Moore Threads MUSA**. **(#5164)**
* Added Fish Speech TTS on XPU and delivered vLLM 0.26 XPU compatibility fixes. **(#4856, #5476)**
* Updated CUDA and ROCm base images for the vLLM 0.25 line, then restored ROCm CI for v0.26.0. **(#5115, #5528)**
* Improved pure-TP KV receive behavior and added typed SAGE support for `TRTLLM_ATTN`. **(#5636, #5509)**

### CI, Benchmarks & Documentation

* Added local L2-L4 CI job runners, JSON mark selection and paired performance parametrization, and missing-pytest-mark pre-commit checks. **(#4672, #5084, #4953)**
* Expanded nightly performance and compatibility coverage across NPU models, Qwen3-TTS, MiniCPM-o 4.5, distributed diffusion, and hardware-specific GPU pools. **(#5158, #5339, #5237, #5353, #5695)**
* Reorganized Buildkite and the test tree, unified mirrored-hardware/skip-CI presets, optimized Docker caching, and fixed release-line pipeline upload and package-discovery issues. **(#5119, #4951, #5254, #5133, #5572, #5368)**
* Added and refined recipes for MiniMax H3, Cosmos3 Edge/Super/Nano, MiniCPM-o 4.5, distributed offload, and standardized model-serving names and examples. **(#5691, #5313, #5097, #4978, #5222, #5081)**

### Breaking Changes

* **LTX pipeline registry names changed.** `LTX2Pipeline` is now the unified one-stage entry for LTX-2/LTX-2.3 T2V and I2V. The former `LTX2ImageToVideoPipeline`, `LTX23Pipeline`, and `LTX23ImageToVideoPipeline` names were removed, and the distilled two-stage path is now `LTX2DistilledPipeline`. The official full-guidance path can perform up to four Transformer passes per denoise step, so users may see higher compute cost in exchange for reference-aligned guidance behavior. **(#5148)**
* **GGUF diffusion support moved out of tree.** Deployments using GGUF diffusion models should install and configure `vllm-project/vllm-gguf-plugin`; the implementation is no longer maintained in vLLM-Omni core. **(#4769)**

### Note

* The full-duplex implementation is an **experimental preview**. It validates the MiniCPM-o 4.5 realtime demo path, but does not yet claim production-complete persistent KV leases, multi-session/multi-replica admission and recovery, long-duration conversation tuning, or full byte-for-byte OpenAI Realtime API compatibility. **(#3907)**
* The distributed layerwise offload performance and memory figures above were measured on Ascend 910B3 with Cosmos3 Nano/Super. Treat them as validated reference results for that environment, not universal guarantees across models or hardware backends. **(#5397)**
* MiniMax H3 requires approved checkpoint access, separate FL2VA/Ref2VA checkpoint partitions, and `ffmpeg`/`ffprobe` for reference preparation and MP4 output. FlashAttention 4 is an optional Blackwell-specific dependency. See the MiniMax H3 recipe for supported serving configurations. **(#5691)**


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
* Fix Voxtral TTS feedback and short ASR checks by @liuyao0322 in https://github.com/vllm-project/vllm-omni/pull/4954
* [Bugfix] Drop out-of-vocabulary stop ids from min-tokens masking (qwen3-tts min_tokens engine crash) by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/4971
* [Perf][Qwen3-TTS] Skip per-step hidden-state D2H via hidden pooler payload opt-out by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/4879
* [Perf][Qwen3-TTS] Drop default seed from qwen3_tts.yaml to restore batched MTP sampling by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/4970
* [Diffusion] Improve HuggingFace hub kernel loading in flash_attn_hub by @SamitHuang in https://github.com/vllm-project/vllm-omni/pull/4977
* [Tests] Tiny Diffusion Model Pattern by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/4524
* Bump safetensors to the 0.8.0 release by @oglok in https://github.com/vllm-project/vllm-omni/pull/4713
* [Perf][Qwen3-TTS] Align talker MTP CUDA graph capture with Qwen3-Omni & Adapt to async output by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/4923
* Fix VoxCPM2 perf server trust remote code by @liuyao0322 in https://github.com/vllm-project/vllm-omni/pull/4984
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
* Fix Qwen3-Omni thinker fused MoE LoRA by @liuyao0322 in https://github.com/vllm-project/vllm-omni/pull/5191
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
* [bugfix] validate AR sampled-token logprob alignment by @hbhflw2000 in https://github.com/vllm-project/vllm-omni/pull/5273
* [CI][NPU]: Add nightly performance test for NPU - qwen3-omni/wan2.2/qwen-image-edit-2511 by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/5339
* [New Model] support nemotron Audex by @yuekaizhang in https://github.com/vllm-project/vllm-omni/pull/4976
* [CI] Skip known-failing tests and filter NPU ready TTS by npu mark by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5489
* [Bugfix] Select the AR-Diffusion engine in the DreamZero CFG-parallel deploy config by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/5439
* [Feature] Add official LTX multimodal guidance and precision guard by @mglyn in https://github.com/vllm-project/vllm-omni/pull/5148
* [BugFix] Fix 'GPUARWorker' attribute error by @Semmer2 in https://github.com/vllm-project/vllm-omni/pull/5478
* [Perf][GLM-Image] Skip redundant hidden state D2H by @herotai214 in https://github.com/vllm-project/vllm-omni/pull/5346
* Revert "[BugFix] Fix 'GPUARWorker' attribute error" by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5507
* [Refactor] Make MOSS-TTS-Local stream session dynamic batch by @gcanlin in https://github.com/vllm-project/vllm-omni/pull/5235
* [Test] Give the logprobs scheduler doubles the vLLM 0.26 contracts by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/5483
* [Test] Add regression test for MiniCPM-o 4.5 audio-stream output kinds by @IneshReddy249 in https://github.com/vllm-project/vllm-omni/pull/5356
* [Bugfix] Return diffusion metrics from /v1/images/generations by @Zhiyu0603 in https://github.com/vllm-project/vllm-omni/pull/5278
* [Bugfix][Minicpm] Support full-duplex three-stage serving by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/5380
* [Feature] Flush the speech WebSocket on input.done without closing it by @iancarrasco-b10 in https://github.com/vllm-project/vllm-omni/pull/5517
* Xpu/vllm 0.26 fixes by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/5476
* [recipe][NPU] add cosmos3-super recipe on 8xA3 by @zhangj1an in https://github.com/vllm-project/vllm-omni/pull/5097
* [Hardware] Enable CosyVoice3 on Moore Threads MUSA by @yeahdongcn in https://github.com/vllm-project/vllm-omni/pull/5164
* [NPU] upgrade to v0.26.0 by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/5490
* [skip ci][Misc] remove stray md introduced in #4652 by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/5473
* fix(diffusion): convert caller sampling params instead of discarding … by @BruceLoveDecimal in https://github.com/vllm-project/vllm-omni/pull/4115
* [Perf] Enable compile for MOSS-TTS-Local v1.5 talker and codec by @gcanlin in https://github.com/vllm-project/vllm-omni/pull/5530
* Support Python 3.10 runtime compatibility by @yeahdongcn in https://github.com/vllm-project/vllm-omni/pull/5366
* Add vae-patch-parallel-size and vae-use-tiling for HunyuanImage Benchmark by @BLANKETusers in https://github.com/vllm-project/vllm-omni/pull/5502
* [Refactor][CI] Reorganize test tree, and move slow e2e to weekly by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/4951
* [Doc][NPU] Fix a missed version reference: 0.25.0 → v0.26.0 by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/5538
* [Bugfix][CI/Build] Avoid refetching HunyuanVideo I2V input during sim… by @whisper-la in https://github.com/vllm-project/vllm-omni/pull/5552
* Enable Diffusion Image models asynchronous output  by @BLANKETusers in https://github.com/vllm-project/vllm-omni/pull/4981
* [Feat] [CI] [bugfix] Generalize LTX CFG parallelism to the complete guidance plan by @mglyn in https://github.com/vllm-project/vllm-omni/pull/5547
* [refactor][MiniCPM-o] Consolidate MiniCPM-o 4.5 2-GPU deploy configs and E2E tests by @y-null in https://github.com/vllm-project/vllm-omni/pull/5458
* [bugfix][MiniCPM-o]delete duplicate files by @R2-Y in https://github.com/vllm-project/vllm-omni/pull/5535
* [Bugfix] Trim AR sampled logprob rows with new_token_ids on mid-step stop by @yashkgp in https://github.com/vllm-project/vllm-omni/pull/5564
* [ROCm] [CI] Fix ROCm CI for v0.26.0 by @tjtanaa in https://github.com/vllm-project/vllm-omni/pull/5528
* [CI/Build] Fix nested group breaking nightly pipeline upload by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5572
* [Refactor] Normalize diffusion request extra arguments in Chat serving by @TaffyOfficial in https://github.com/vllm-project/vllm-omni/pull/5171
* [Bugfix] Add Cosmos3-Edge preset (fix wrong Nano/Super defaults in T2V/I2V examples) by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5596
* [Model] Remove Text Encoder Output Layer Hardcoding in Flux2 by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/5589
* [Refactor] Migrate Qwen3 Omni thinker-only deploy config by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/5285
* [Refactor] Migrate Step-Audio2 offline test to deploy config by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/5319
* [Feature] Distributed layerwise offload with DP multi-concurrency + mmap weight… by @evanchueng in https://github.com/vllm-project/vllm-omni/pull/5397
* [Bugfix][Diffusion] Apply MagCache residual once per skipped step by @yashkgp in https://github.com/vllm-project/vllm-omni/pull/5561
* [CI/Build][MiniCPM-o] Allow auto-response before input commit by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/5567
* [Bugfix] Qwen3-TTS full-payload: emit one placeholder frame on a degenerate take instead of an empty payload by @henryj in https://github.com/vllm-project/vllm-omni/pull/5472
* [Bufix] Ming-omni-tts-16.8B Skip rejected and unused weights loading by @yuanheng-zhao in https://github.com/vllm-project/vllm-omni/pull/5607
* [Bugfix] Fix active_stream_window silently stalling audio generation (#5349) by @ShengleiFu in https://github.com/vllm-project/vllm-omni/pull/5373
* [Bugfix][Diffusion] Honor HF_HUB_OFFLINE in OmniDiffusionConfig (align with AR stage) by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/5403
* [BugFix][Diffusion] Add CPU LAPACK fallback for FlowUniPC by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/5329
* [BugFix] Never dispatch diffusion with an incomplete CFG companion bundle by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/5482
* [Tests] Further extend the tiny model testing framework and enable multiple models by @NickCao in https://github.com/vllm-project/vllm-omni/pull/5353
* [Bugfix] Use MiniCPM-o speech template in long audio test by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5623
* [Bugfix] Leave MiniCPM-o vocoder memory headroom by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5621
* [Bugfix][VoxCPM2] Fix Chunked Prefill Length Mismatch by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/5416
* [Bugfix][CI] Reuse servers across paired perf cases by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5624
* [Bugfix] Restore Gradio demo dependency by @maithilijoshi20 in https://github.com/vllm-project/vllm-omni/pull/5632
* [Bugfix][MiniCPM-o]Fix implicit deploy connector resolution for registered pipelines by @R2-Y in https://github.com/vllm-project/vllm-omni/pull/5533
* [Bugfix] Default missing legacy stage input sources by @wuli666 in https://github.com/vllm-project/vllm-omni/pull/5498
* [Bugfix][Full Duplex] Make runtime_control payloads JSON serializable by @TheCodeWrangler in https://github.com/vllm-project/vllm-omni/pull/5613
* [Perf] Cache RoPE cos/sin tables in code predictor by @l-wave in https://github.com/vllm-project/vllm-omni/pull/5503
* [Kernel] Add typed SAGE for TRTLLM_ATTN by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5509
* [CI][NPU] Add MiniCPM-o 4.5 dependencies by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/5660
* [Bugfix][MiniCPM-o] Stabilize single-GPU audio generation by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/5637
* diffusion: Fix silent override of explicit `guidance_scale=0` by @harenome in https://github.com/vllm-project/vllm-omni/pull/4999
* [BugFix][Metrics] Fix per-stage time and token stats in metrics API by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/4974
* [CI/Build] Let audio assertions pin the transcript language by @ShengleiFu in https://github.com/vllm-project/vllm-omni/pull/5646
* [Bugfix][MiniCPM-o] Align Daily-Omni bench with MiniCPM interleaved A… by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/5625
* [Bugfix] Preserve channel-last video tensor layout by @pxljs in https://github.com/vllm-project/vllm-omni/pull/5418
* [Bugfix] Restore BAGEL CFG KV transfers by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5620
* [Bugfix] Match image file metadata to output format by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5619
* [Bugfix] Fix Wan2.2 omitted guidance scale resolution by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5615
* [BugFix] Make pure-TP KV receive fallback all-or-nothing across ranks by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/5636
* [Bugfix] Reject /v1/completions for thinker+talker models when --trust-remote-code is unset by @ChoHee15 in https://github.com/vllm-project/vllm-omni/pull/5525
* [CI/Build] Split diffusion distributed nightly tests by L4 and H100 by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5695
* [Model] Add MiniMax H3 diffusion support by @Isotr0py in https://github.com/vllm-project/vllm-omni/pull/5691
* Adapt HunyuanImage3.0 test for npu by @BLANKETusers in https://github.com/vllm-project/vllm-omni/pull/5436
* [Model] Add soundfile fallback for MiniMax H3 audio loading by @brandneway in https://github.com/vllm-project/vllm-omni/pull/5699

## New Contributors
* @zwhzzz0821 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4647
* @IneshReddy249 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4760
* @liuyao0322 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4954
* @l-wave made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4261
* @Abhinay1997 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4730
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
* @Zhiyu0603 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5278
* @whisper-la made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5552
* @evanchueng made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5397
* @maithilijoshi20 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5632
* @TheCodeWrangler made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5613
* @harenome made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4999
* @pxljs made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5418
* @ChoHee15 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5525
* @brandneway made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5699

**Full Changelog**: https://github.com/vllm-project/vllm-omni/compare/v0.24.0...v0.26.0