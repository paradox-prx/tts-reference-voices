## Highlights

This release candidate features 104 merged changes from 52 contributors, including 11 new contributors.

vLLM-Omni `v0.27.0rc1` focuses on four major areas: 1) **productionizing MiniMax H3 across serving modes, accelerators, quantization paths, and memory-constrained deployments**, 2) introducing **PersonaPlex full-duplex speech-to-speech serving**, 3) advancing **scheduler-managed diffusion execution and distributed layerwise offload**, and 4) delivering substantial **TTS and MiniCPM-o 4.5 performance improvements**. The release candidate also rebases the project onto vLLM 0.27.0, adds batched Chat Completions, expands diffusion and video-model coverage, and strengthens CI, documentation, and hardware portability.

### Key Improvements

* **Expanded MiniMax H3 into a broadly deployable video-and-audio generation stack**, with a modular pipeline, aligned official input modes, quality grading through dynamic Cache-DiT loading, TeaCache validation, FP8 and INT8 quantization, fused attention and normalization paths, and optimized distributed execution. **(#5720, #5752, #5853, #5840, #5737, #5706, #5801)**
* **Extended MiniMax H3 hardware coverage** across NVIDIA RTX 4090/5090, DGX Spark GB10, RTX PRO 6000, AMD MI350X, Ascend NPU, and Moore Threads MUSA, with platform-specific recipes and correctness fixes. **(#5764, #5946, #5863, #5723, #5896, #5837, #5881)**
* **Added PersonaPlex**, a native vLLM port of the Moshi-based full-duplex speech-to-speech model, including duplex serving support for realtime conversational workloads. **(#4771)**
* **Advanced scalable diffusion execution** with DLO data-parallel concurrency, scheduler-managed paged KV-cache worker contracts, modular MiniMax H3 support, distilled diffusion LoRA support, and scheduler admission-policy cleanup. **(#5864, #5550, #5720, #2783, #5843)**
* **Improved TTS and speech-generation performance** through cached incremental decoding for Qwen3-TTS, CUDA Graph acceleration and batched codec sampling for MiniCPM-o 4.5, TensorRT acceleration for its vocoder, and hot-path optimizations for Voxtral TTS and Step-Audio2. **(#5202, #5869, #5792, #5638, #5175, #5067)**

### Core Architecture & Runtime

* Rebased the project onto **vLLM 0.27.0**, aligning the engine, scheduler, model-runner, attention, deployment, and platform layers with the vLLM 0.27 release line. **(#5976)**
* Removed duplicated autoregressive and generation scheduler plumbing and established explicit shared scheduler lifecycle contracts. **(#5461)**
* Refactored diffusion request admission waiting to clarify scheduler behavior and improve concurrent request handling. **(#5843)**
* Added worker contracts and RPC plumbing for **scheduler-managed paged KV cache**, preparing diffusion pipelines such as HunyuanImage3 for scheduler-controlled KV allocation and reuse. **(#5550, #5541)**
* Added the first Cosmos3 session-memory port for UND text key/value state, continuing the stateful world-model execution work introduced in the previous release. **(#4657)**
* Read engine arguments directly from `VllmOmniConfig`, further consolidating pipeline, stage, and engine configuration behind the unified configuration model. **(#5678)**
* Improved per-replica fault isolation so a single stage failure does not automatically terminate the API server or unrelated replicas. **(#4583)**
* Removed the legacy `--stage-configs-path` serve option after completing the migration to registry-backed deployment configuration. **(#5647)**

### Model Support

* Expanded **MiniMax H3** support with a modular diffusion pipeline, the official input matrix, quality-grading requests, distilled four-step schedules on NPU, and stricter encoder checkpoint validation. **(#5720, #5752, #5853, #5991, #5824)**
* Added **PersonaPlex**, a Moshi-based full-duplex speech-to-speech model with native vLLM execution and duplex serving. **(#4771)**
* Added **LongCat-Video-Avatar-1.5** audio-image-to-video and audio-text-to-video generation. **(#4099)**
* Added **LingBot-Video** text-to-image and text-image-to-video generation modes. **(#5311)**
* Added distilled LoRA support for diffusion models. **(#2783)**
* Added a Ming Flash Omni TTS adapter and derived TTS model detection from adapter metadata rather than hard-coded model checks. **(#5746, #5682)**
* Added thinker-only ModelOpt NVFP4 W4A4 checkpoint support for Qwen2.5-Omni. **(#5073)**
* Improved MOSS-TTS codec v1/v2 detection and synchronized the vendored tokenizer behavior with upstream. **(#5635)**
* Added LoRA-request handling for non-diffusion models. **(#5374)**

### MiniMax H3 Productionization

* Added online **FP8 support** and Ascend **RainFusion attention with INT8 online quantization**. **(#5737, #5706)**
* Added fused RMSNorm and RoPE optimizations, refined TensorRT-LLM attention support, and restored dynamic RoPE fusion on MUSA. **(#5801, #5779, #5881)**
* Enabled DLO deployments on RTX 4090 and RTX 5090 and added multi-GPU performance coverage for 4xH100 configurations. **(#5764, #5836)**
* Added TeaCache support and Cache-DiT validation, including dynamic loading and unloading for quality-grading requests. **(#5840, #5853)**
* Added packed variable-length attention on NPU to avoid quadratic attention-mask materialization. **(#5891)**
* Added support for arbitrary video shapes in RainFusion attention. **(#6000)**
* Improved portability by making conditioned-VAE RNG handling device-aware on MUSA and NPU. **(#5703, #5837)**
* Added accuracy coverage for T2VA, I2VA, and Ref2VA, including FP8 validation and aligned official reference inputs. **(#5709, #5829, #5978)**
* Added deployment recipes for ROCm MI350X, DGX Spark GB10, RTX PRO 6000, and RTX 4090. **(#5723, #5946, #5863, #5850)**

### Audio, Speech & Omni Production Optimization

* Added **cached incremental decoding for Qwen3-TTS**, reducing repeated work during autoregressive generation. **(#5202)**
* Improved MiniCPM-o 4.5 by reusing FlashAttention unpadding metadata, optimizing Whisper chunk-attention mask construction, batching Talker codec sampling, and adding CUDA Graph support to HiFTGenerator. **(#5165, #5382, #5792, #5869)**
* Added TensorRT acceleration for the MiniCPM-o Code2Wav vocoder, covering both the DiT estimator and CampPlus components. **(#5638)**
* Optimized the Voxtral TTS hot path by removing unnecessary host synchronization, caching kernels, and selectively opting out of CUDA Graph execution where appropriate. **(#5175)**
* Kept Step-Audio2 streaming tokens on device and batched audio-feature length synchronization to reduce device-to-host overhead. **(#5067)**
* Fixed Qwen3-TTS short-sequence RoPE behavior on NPU by falling back to the supported BSND path. **(#5608)**
* Improved TTS CI stability by allowing expected branch-count decreases without incorrectly failing the ratchet. **(#6008)**

### Diffusion, Image & Video Generation

* Added MiniMax H3 modular-pipeline support and integrated it with Cache-DiT, TeaCache, DLO, quantization, and multiple attention backends. **(#5720, #5840, #5853)**
* Fixed DLO AllGather sizing for models with heterogeneous parameter layouts and corrected concurrent data-parallel request execution. **(#5802, #5864)**
* Documented and strengthened distributed layerwise-offload compatibility across supported execution modes. **(#5839)**
* Added scheduler-managed paged-KV-cache foundations for HunyuanImage3 through scheduler preparation, worker contracts, and RPC plumbing. **(#5541, #5550)**
* Added distilled diffusion LoRA support. **(#2783)**
* Added LongCat-Video-Avatar-1.5 AI2V/AT2V and LingBot-Video T2I/TI2V generation modes. **(#4099, #5311)**
* Avoided unnecessary attention masks for FLUX.2 and HunyuanVideo 1.5 when the non-varlen path is sufficient. **(#4645)**
* Fixed BAGEL multimodal RoPE position IDs, KV-only payload transfer behavior, and shared-memory connector coverage. **(#5775, #5744, #5898)**
* Restored packed-mask-free capability reporting for the TeaCache fake backend. **(#5997)**
* Normalized NumPy image outputs before saving and corrected image-count validation. **(#6031, #5838)**

### Quantization, Attention & Memory Efficiency

* Added MiniMax H3 online FP8 and NPU INT8 quantization paths. **(#5737, #5706)**
* Added Qwen2.5-Omni thinker-only ModelOpt NVFP4 W4A4 checkpoint support. **(#5073)**
* Enabled ModelOpt FP8 inference for Qwen3-Omni on MUSA. **(#5671)**
* Refreshed FlashInfer attention integration and added Blackwell quantized-attention support for QK16/V8 configurations. **(#5344)**
* Added GQA and MQA support to the ring-attention SDPA path. **(#5255)**
* Bounded memory usage during video-frame conversion instead of retaining all converted frames at once. **(#5732)**
* Added packed variable-length attention for MiniMax H3 on NPU, avoiding quadratic mask materialization for supported workloads. **(#5891)**

### Serving, Frontend & API Behavior

* Added **batched Chat Completions**, allowing multiple independent chat requests to be submitted through a single frontend request. **(#5317)**
* Added ComfyUI support for reference-to-video generation, with MiniMax H3 as the initial example. **(#5756)**
* Added native duplex serving for PersonaPlex. **(#4771)**
* Improved asynchronous Omni output documentation and clarified when output artifacts are materialized. **(#5610)**
* Switched reference-video decoding to the vLLM video loader for consistent input handling across serving paths. **(#5085)**
* Fixed image-count validation and normalized NumPy-backed image outputs before persistence. **(#5838, #6031)**

### Platforms, Distributed Execution & Hardware Coverage

* Expanded MiniMax H3 deployment support across **NVIDIA H100, RTX 4090/5090, RTX PRO 6000, DGX Spark GB10, AMD MI350X, Ascend NPU, and Moore Threads MUSA**. **(#5836, #5764, #5863, #5946, #5723, #5706, #5881)**
* Added RainFusion attention, INT8 online quantization, packed variable-length attention, and distilled four-step schedules for MiniMax H3 on Ascend NPU. **(#5706, #5891, #5991)**
* Completed additional vLLM-Omni platform interfaces for MUSA and enabled Qwen3-Omni ModelOpt FP8 inference. **(#6058, #5671)**
* Made MiniMax H3 VAE RNG handling portable across MUSA and NPU devices. **(#5703, #5837)**
* Added ROCm BF16 serving documentation for MiniMax H3 on gfx950 hardware. **(#5723)**
* Improved distributed diffusion through DLO concurrency fixes and scheduler-managed paged-KV-cache contracts. **(#5864, #5550)**

### CI, Benchmarks & Documentation

* Added MiniMax H3 accuracy coverage for T2VA, I2VA, Ref2VA, and FP8 configurations, plus a 4xH100 diffusion performance configuration. **(#5709, #5829, #5978, #5836)**
* Added MiniCPM-o 4.5 accuracy, performance, and online-serving coverage. **(#5524, #6056)**
* Added a tiny-model builder for `FluxKontextPipeline`. **(#5823)**
* Nested performance baselines by hardware label and fixed baseline resolution for concurrency sweeps. **(#5402, #5845)**
* Reduced sleep-mode entrypoint test time by sharing engines between compatible test cases. **(#5713)**
* Re-enabled BAGEL shared-memory connector testing and fixed Cache-DiT nested-module discovery. **(#5898, #5884)**
* Reorganized the architecture and module-design documentation, consolidated diffusion execution-mode guidance, and aligned CODEOWNERS with module ownership documentation. **(#5833, #5914, #5139, #5599, #5958)**
* Added and refreshed MiniMax H3 recipes for ROCm, DGX Spark, RTX PRO 6000, RTX 4090, and ComfyUI workflows. **(#5723, #5946, #5863, #5850, #5756)**
* Added repository guidance and a dedicated vLLM-Omni PR-review skill for agentic contributions. **(#6029, #5871)**

### Breaking Changes

* **The legacy `--stage-configs-path` serve option has been removed.** Deployments must use the pipeline registry and `--deploy-config`-based configuration instead. **(#5647)**
* **Engine arguments are now sourced through `VllmOmniConfig`.** Integrations that construct or mutate engine configuration through legacy stage-specific paths may need to migrate to the unified configuration model. **(#5678)**
* **The project now targets the vLLM 0.27 release line.** Out-of-tree integrations, custom attention backends, platform plugins, and code depending on internal vLLM APIs should be validated against vLLM 0.27 before upgrading. **(#5976)**

### Note

* This is a pre-release version. It is intended for evaluation and integration testing before the final release; production deployments should validate model quality, performance, and platform compatibility in their target environments.
* PersonaPlex duplex serving is a newly introduced runtime path. Applications should validate session lifecycle, latency, interruption behavior, and long-running concurrency requirements before production adoption. **(#4771)**
* MiniMax H3 capabilities vary by hardware backend. Quantization formats, attention implementations, cache accelerators, distilled schedules, and supported generation modes may require backend-specific recipes and dependencies.
* The Qwen3-TTS fused QKV and `gate_up` projection optimization from **#4958** was reverted in **#5777** after CI failures and is therefore not included as an active performance improvement in this release candidate.
* Scheduler-managed paged KV cache remains an incremental architecture effort. This release adds preparation, worker contracts, and RPC plumbing, but should not be interpreted as complete support across every diffusion pipeline. **(#5541, #5550)**

## What's Changed
* Update WeChat community QR code by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/5701
* [Refactor] Remove legacy --stage-configs-path from the serve CLI by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/5647
* [Model] Add MiniMax H3 T2VA accuracy test by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/5709
* [Bugfix] Fix MiniMax H3 reference video URL by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/5740
* [Doc] Update README and installation docs for v0.26.0 by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5715
* [Doc] Document async Omni output materialization by @fake0fan in https://github.com/vllm-project/vllm-omni/pull/5610
* [Refactor][1/N Scheduler]Remove duplicated AR/generation scheduler plumbing and establish explicit shared lifecycle contracts. by @R2-Y in https://github.com/vllm-project/vllm-omni/pull/5461
* [Model][Feat] MiniMax H3 online FP8 support by @mglyn in https://github.com/vllm-project/vllm-omni/pull/5737
* [Frontend] Add ComfyUI support for r2v (MiniMax H3 as example) by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/5756
* [Perf][Qwen3-TTS] Fuse QKV and gate_up projections in code predictor by @l-wave in https://github.com/vllm-project/vllm-omni/pull/4958
* [Bugfix][Hunyuan/Bagel]Avoid payload connector for KV-only senders by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/5744
* [CI failed] Revert "[Perf][Qwen3-TTS] Fuse QKV and gate_up projections in code predictor" by @Gaohan123 in https://github.com/vllm-project/vllm-omni/pull/5777
* [Refactor] Use vLLM video loader for video reference decoding by @NickCao in https://github.com/vllm-project/vllm-omni/pull/5085
* fix(bagel): correct CFG position ID concatenation for multimodal RoPE by @atharv0o in https://github.com/vllm-project/vllm-omni/pull/5775
* [Bugfix][XPU][Tests] Add tests/e2e/accuracy/__init__.py to fix pytest… by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/5780
* [Test] Prefix-cache passthrough test coverage prerequisite for W2 (#4855) by @ShengleiFu in https://github.com/vllm-project/vllm-omni/pull/5310
* [Feature] PersonaPlex (Moshi-based full-duplex S2S): native vLLM port + duplex serving by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/4771
* [CI/Build] Speed up omni sleep-mode entrypoint tests with shared engines by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5713
* [Perf][MiniCPM-o] TensorRT acceleration for the Code2Wav vocoder (DiT estimator + campplus) by @yuekaizhang in https://github.com/vllm-project/vllm-omni/pull/5638
* [Bugfix][NPU] Fallback to BSND RoPE when Qwen3-TTS short-seq BNSD li… by @gxxx-hum in https://github.com/vllm-project/vllm-omni/pull/5608
* [Feature] Align MiniMax H3 official input matrix by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/5752
* [BugFix] Fix MOSS-TTS codec v1/v2 detection and align vendored tokenizer with upstream by @Wallbreazzz in https://github.com/vllm-project/vllm-omni/pull/5635
* [Bugfix][Diffusion] Fix DLO AllGather size mismatch for models with h… by @brandneway in https://github.com/vllm-project/vllm-omni/pull/5802
* [CI]For NPU CI, Nest perf baselines by hardware label (H100/A3) by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5402
* [Hardware][MUSA] Make MiniMax H3 conditioned VAE RNG device-aware by @yeahdongcn in https://github.com/vllm-project/vllm-omni/pull/5703
* [Doc] add comfyui hint for Minimal-H3 by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/5785
* Add @NickCao to CODEOWNERS by @NickCao in https://github.com/vllm-project/vllm-omni/pull/5807
* [docs] consolidate diffusion execution modes by @bjf-frz in https://github.com/vllm-project/vllm-omni/pull/5599
* [Doc] Add Cosmos3-Nano ROCm recipe (1x MI350X) by @ZJLi2013 in https://github.com/vllm-project/vllm-omni/pull/5634
* feat(minimax-h3): enable RTX 4090/5090 support with DLO by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5764
* Optimize MiniCPM-o 4.5 Whisper chunk-attention mask construction by @frank-2077 in https://github.com/vllm-project/vllm-omni/pull/5382
* [CI][Bugfix] Fix Minimax-H3 FP8 Accuracy Test by @mglyn in https://github.com/vllm-project/vllm-omni/pull/5829
* [Perf] Minimax-H3 support fused RMSNorm and RoPE opt by @fan2956 in https://github.com/vllm-project/vllm-omni/pull/5801
* fix(minimax-h3): pass device_type to fork_rng so VAE condition encode works on NPU devices by @brandneway in https://github.com/vllm-project/vllm-omni/pull/5837
* docs: reorganize vLLM-Omni design navigation by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5833
* [NPU][Quantization] Add RainFusion attention and INT8 online quantization for MiniMax H3 by @Huangzjun in https://github.com/vllm-project/vllm-omni/pull/5706
* [Perf] Bound memory during video frame conversion by @Xunzhuo in https://github.com/vllm-project/vllm-omni/pull/5732
* [Attention] Refine TRTLLM attention support for MiniMax H3 by @bobboli in https://github.com/vllm-project/vllm-omni/pull/5779
* [Diffusion] Add Minimax-H3 modular pipeline support by @Isotr0py in https://github.com/vllm-project/vllm-omni/pull/5720
* [CI/Build] Resolve hardware-nested perf baselines per concurrency sweep by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5845
* docs: document distributed layerwise offload compatibility by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5839
* [Perf][CI] Add MiniMax-H3 4xH100 diffusion perf config by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/5836
* [Model] MiniCPM-o 4.5: reuse FlashAttention unpadding metadata by @Fyrgo8 in https://github.com/vllm-project/vllm-omni/pull/5165
* [Config] Read engine args from VllmOmniConfig by @Acerak01-fy in https://github.com/vllm-project/vllm-omni/pull/5678
* [Bugfix] Support GQA/MQA in the ring attention SDPA path by @linzhenpl07 in https://github.com/vllm-project/vllm-omni/pull/5255
* [Kernel] Refresh FlashInfer attention; Add quantized attention support (Blackwell QK16/V8) by @xrq-phys in https://github.com/vllm-project/vllm-omni/pull/5344
* [Bugfix] Fix image num check error by @Bounty-hunter in https://github.com/vllm-project/vllm-omni/pull/5838
* [bugfix][CI] Fix Cache-DiT nested module discovery [issue 5879] by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/5884
* [Model][Feat] Support Minimax-H3 quality grading requests through dynamic loading/unloading with Cache-DiT by @mglyn in https://github.com/vllm-project/vllm-omni/pull/5853
* [BugFix][Nightly CI] Opt in FA deterministic for Qwen-Image accuracy by @NumberWan in https://github.com/vllm-project/vllm-omni/pull/5887
* [BugFix][CI] Project fa_deterministic into OmniDiffusionConfig fields by @NumberWan in https://github.com/vllm-project/vllm-omni/pull/5897
* [Frontend] Implement Batched Chat Completions by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/5317
* [Diffusion] Fix DLO DP concurrent request execution by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5864
* [Docs] [templates] Reorganize module design documentation  by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5139
* [Model] Fail MiniMax H3 encoder load when a weight or fused shard is missing by @ShengleiFu in https://github.com/vllm-project/vllm-omni/pull/5824
* [Misc] Add vLLM-Omni PR review skill by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5871
* [Quantization][Qwen2.5-Omni] Support thinker-only ModelOpt NVFP4 W4A4 checkpoints by @Caspian443 in https://github.com/vllm-project/vllm-omni/pull/5073
* docs: update vLLM-Omni architecture overview by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5914
* [Feat] Cosmos3 session-memory port for UND text K/V (RFC #4480 Phase 0) by @linzhenpl07 in https://github.com/vllm-project/vllm-omni/pull/4657
* [Refactor][TTS] Derive TTS model detection from adapter metadata by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/5682
* [BugFix][NPU] MiniMax-H3 RoPE crash: add the missing batch dim before the mindiesd kernel by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/5896
* [Recipe] Document MiniMax H3 ROCm (gfx950) BF16 serving by @amd-xiaoyu12 in https://github.com/vllm-project/vllm-omni/pull/5723
* [Perf][MiniCPM-O-4.5]Add CUDA Graph For HiFTGenerator by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/5869
* [MiniMax-H3] TeaCache support and Cache-DiT validation by @dpeng123 in https://github.com/vllm-project/vllm-omni/pull/5840
* Add MiniMax-H3 recipe for DGX Spark (GB10) by @yiminghub2024 in https://github.com/vllm-project/vllm-omni/pull/5946
* [doc]Add recipe for MiniMax-H3 on RTX PRO 6000 by @yiminghub2024 in https://github.com/vllm-project/vllm-omni/pull/5863
* [Diffusion] Prepare HunyuanImage3 for Scheduler-managed paged KV cache by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/5541
* [Refactor] Add Ming Flash Omni TTS adapter by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/5746
* [diffusion][feature] Add LingBot-Video T2I and TI2V generation modes by @wtz2333 in https://github.com/vllm-project/vllm-omni/pull/5311
* docs: update vLLM-Omni WeChat QR code by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/5959
* [CI] Re-enable bagel shared-memory connector test (#5475) by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5898
* [bugfix] Support lora request for non diffusion model by @knlnguyen1802 in https://github.com/vllm-project/vllm-omni/pull/5374
* [Core][Refactor][Diffusion] refactor request scheduler's admission wait policy by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/5843
* Update Wan2.2 I2V performance baselines by @bjf-frz in https://github.com/vllm-project/vllm-omni/pull/5977
* [Docs] Preserve generated quantization URLs and link recipes in supported models by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5969
* Add Ref2VA measurements to the MiniMax-H3 DGX Spark (GB10) recipe by @yiminghub2024 in https://github.com/vllm-project/vllm-omni/pull/5972
* [Perf][MUSA] Restore MiniMax-H3 dynamic RoPE fusion by @yeahdongcn in https://github.com/vllm-project/vllm-omni/pull/5881
* docs: keep shared task examples in navigation by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5987
* [Misc] Align CODEOWNERS with module/feature design docs by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5958
* [Perf][Diffusion] MiniMax-H3: opt into packed varlen attention on NPU to eliminate quadratic mask materialization by @brandneway in https://github.com/vllm-project/vllm-omni/pull/5891
* [Docs] Fix broken attention backend link by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5998
* [Bugfix][Diffusion] Restore supports_packed_mask_free on teacache FakeBackend by @brandneway in https://github.com/vllm-project/vllm-omni/pull/5997
* [BugFix] Don't fail the TTS ratchet when the branch count goes down by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/6008
* [Bugfix] rainfusion support all shape video by @fan2956 in https://github.com/vllm-project/vllm-omni/pull/6000
* [Bugfix] Per-replica fault isolation: keep API server alive on single-stage death (#4285) by @ShengleiFu in https://github.com/vllm-project/vllm-omni/pull/4583
* [Perf][TTS] voxtral_tts hot path: cudagraph opt-out, host-sync removal, kernel caches by @JuanPZuluaga in https://github.com/vllm-project/vllm-omni/pull/5175
* [Perf][TTS] step_audio2: keep streaming tokens on-device and batch audio-feature length syncs by @JuanPZuluaga in https://github.com/vllm-project/vllm-omni/pull/5067
* [Perf][Qwen3-TTS]Cached Incremental Decode by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/5202
* [CI] Align MiniMax H3 Ref2VA inputs and add I2VA/Ref2VA accuracy coverage by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/5978
* [NPU][Model] Add distilled 4-step sigma schedule support for MiniMax H3 t2va by @Huangzjun in https://github.com/vllm-project/vllm-omni/pull/5991
* [Bugfix] Normalize NumPy image outputs before saving by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6031
* [Model] Batch MiniCPM-o Talker codec sampling by @Zhou248 in https://github.com/vllm-project/vllm-omni/pull/5792
* Add MiniMax-H3 recipe for RTX 4090 setup by @yiminghub2024 in https://github.com/vllm-project/vllm-omni/pull/5850
* [Doc] Explain repository skills for agentic contributions by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6029
* [CI][MiniCPM-o] Add MiniCPM-o 4.5 accuracy and performance coverage by @R2-Y in https://github.com/vllm-project/vllm-omni/pull/5524
* [Diffusion] Add Worker contracts and RPC plumbing for Scheduler-managed paged KV cache by @Acerak01-fy in https://github.com/vllm-project/vllm-omni/pull/5550
* [Model] Add LongCat-Video-Avatar-1.5 ai2v,  at2v support by @weiyanlin117 in https://github.com/vllm-project/vllm-omni/pull/4099
* [Perf][Flux2][HunyuanVideo1.5] Skip attention-mask to avoid varlen path by @kTorp in https://github.com/vllm-project/vllm-omni/pull/4645
* [Hardware][MUSA] Enable Qwen3-Omni ModelOpt FP8 inference by @yeahdongcn in https://github.com/vllm-project/vllm-omni/pull/5671
* [Hardware][MUSA] Complete Omni platform interfaces by @yeahdongcn in https://github.com/vllm-project/vllm-omni/pull/6058
* [CI][MiniCPM-o] Align MiniCPM-o 4.5 online serving tests with minicpm… by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/6056
* [Feature]: Adds distilled LoRA support for diffusion models by @Songrui625 in https://github.com/vllm-project/vllm-omni/pull/2783
* [Test] Add tiny model builder for FluxKontextPipeline by @NickCao in https://github.com/vllm-project/vllm-omni/pull/5823
* [Rebase] Rebase to vllm 0.27.0 by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/5976

## New Contributors
* @atharv0o made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5775
* @ZJLi2013 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5634
* @Huangzjun made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5706
* @Xunzhuo made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5732
* @bobboli made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5779
* @xrq-phys made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5344
* @Caspian443 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5073
* @amd-xiaoyu12 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5723
* @yiminghub2024 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5946
* @Zhou248 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5792
* @weiyanlin117 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4099

**Full Changelog**: https://github.com/vllm-project/vllm-omni/compare/v0.26.0...v0.27.0rc1