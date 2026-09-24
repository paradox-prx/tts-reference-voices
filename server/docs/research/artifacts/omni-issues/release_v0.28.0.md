## Highlights

This release features 397 merged changes from 126 contributors, including 44 new contributors.

vLLM-Omni `v0.28.0` is led by three major advances: 1) Production level serving enhancement for Minimax-H3 on GPU and NPU, 2) **scheduler-managed paged KV cache for diffusion**,, and 3) a broader **full-duplex and realtime speech stack** spanning MiniCPM-o 4.5, PersonaPlex, and NVIDIA Nemotron VoiceChat. The release rebases onto vLLM 0.28, adds a wide range of speech, music, image, video, world-model, and VLA integrations.

### Key Improvements
* **Advanced MiniMax H3 from initial support to a much broader deployment stack**, adding modular pipelines, continuous batching, DLO on consumer GPUs, global FP8 and online INT8 paths, text-encoder disaggregation, TeaCache/Cache-DiT, Turbo and FlashGen LoRA variants, a fused four-step FastH3 adapter, and extensive GPU, NPU, ROCm, and MUSA optimizations. **(#5720, #5810, #5764, #5910, #6573, #5885, #5840, #6550, #6666, #6714)**
* **Added scheduler-managed paged KV cache for diffusion**, with native cache initialization, block allocation, worker RPC contracts, and a diffusion-native paged-KV backend. HunyuanImage3 DiT is the first complete model integration, supported on both GPU and NPU. **(#5541, #5550, #6094, #6102, #6563)**
* **Expanded full-duplex speech serving** with a native vLLM port of PersonaPlex, native full-duplex NVIDIA Nemotron VoiceChat serving, configurable concurrent MiniCPM-o sessions, and substantial improvements to barge-in, playback state, handoffs, cancellation, and bounded long-running context. **(#4771, #6089, #6021, #6170, #6529, #6626, #6772)**

### Core Architecture & Runtime

* Rebased the project onto **vLLM 0.28.0**, including corresponding NPU integration updates. **(#6606, #6674)**
* Added the **experimental** **Host Weight Runtime foundation** with exact artifact identity, atomic local publication, corruption detection, crash recovery, mmap leases, capacity policy, and explicit preferred/required resolution modes. Post-load publication can warm later startups without mutating the model serving the current startup. **(#6419, #6427)**
* Integrated final-layout HWR artifacts with **no-AllGather distributed layerwise offload**. Warm starts can skip ordinary DiT materialization, preserve a bounded two-slot staging path, or directly register mapped host-weight regions for asynchronous H2D transfer when supported. **(#6445, #6486, #6591)**
* Added an opt-in **event-driven orchestration loop** for autoregressive stages, replacing millisecond polling with awaitable stage readers and a blocking final-output drain while preserving the legacy loop as the default. **(#5221)**
* Added AR-stage **pause/resume and sleep/wake control** to `AsyncOmni`, including admission gating and acknowledged aborts for colocated serving, RLHF/weight-sync workflows, and idle memory reclamation. **(#6084)**
* Continued the scheduler cleanup with shared AR/generation lifecycle contracts, explicit stage transport capabilities, refined diffusion admission waiting, per-replica fault isolation, and pipeline validation for missing terminal output stages. **(#5461, #6149, #5843, #4583, #6291)**
* Consolidated configuration around `VllmOmniConfig` and reused native vLLM configuration objects, while removing the legacy stage-config loading path and its internal plumbing. **(#5678, #6050, #5647, #5741, #6200)**

### Model Support

* Added **PersonaPlex**, a Moshi-based full-duplex speech-to-speech model, with a native vLLM port and duplex serving. **(#4771)**
* Added **NVIDIA-NemotronLabs/VoiceChat-11B** for offline speech-to-speech inference and native full-duplex serving. **(#5842, #6089)**
* Added new TTS integrations for **IndexTTS 2.5**, **dots.tts** continuous-AR 48 kHz synthesis, and **Gepard 1.0** native-AR FSQ/NanoCodec offline inference. **(#5957, #4765, #5666)**
* Added **MiniMax Music 3** text-to-music generation. **(#6186)**
* Added **HiDream-O1-Image**, **SANA-Video 2B** T2V/I2V, and Stage-1 support for the **SANA world model**. **(#5194, #5508, #4061)**
* Added **LongCat-Video-Avatar-1.5** audio/image-to-video and audio/text-to-video support, and expanded LingBot Video with T2I and TI2V generation modes. **(#4099, #5311)**
* Added **LTX-2.5**, including its diffusion pipeline and VAE decoder, plus a standard two-stage LTX execution path. **(#6070, #6189, #5500)**
* Added the **pi0 vision-language-action model**, extending vLLM-Omni beyond media generation into VLA inference. **(#4222)**
* Added a Qwen3-Omni thinker-only pipeline for Instruct serving and a Ming Flash Omni TTS adapter. **(#6284, #5746)**

### Audio, Speech & Realtime Serving

* Matured the MiniCPM-o 4.5 duplex runtime with configurable concurrent sessions, native deploy configurations, resilient Stage-1 handoffs, barge-in isolation, playback checkpoints, camera/video unit binding, bounded auto-response, and sliding context recomputation. **(#6021, #6619, #6529, #6170, #6821, #6404, #6630, #6626)**
* Accelerated MiniCPM-o audio generation with TensorRT Code2Wav execution, CUDA Graphs for HiFT and CFM DiT, NPU Graph replay, batched codec sampling, and lower concurrent first-packet latency. **(#5638, #5869, #6082, #5604, #5792, #6767)**
* Improved TTS streaming through cached incremental Qwen3-TTS decoding, fused code-predictor projections, adaptive buffer-feedback chunk ramping, asynchronous MOSS-TTS scheduling, and hot-path optimizations for Voxtral TTS, Step-Audio2, GLM-TTS, and OmniVoice. **(#5202, #5791, #6001, #6241, #5175, #5067, #5068, #5174)**
* Added optional **TTS timestamps** through forced-aligner pooling and speech token-usage response headers. **(#4795, #4499)**
* Moved TTS detection, sampling overrides, and model capability metadata into adapters, reducing model-name special cases in shared serving code. **(#5682, #5272, #6138)**

### Diffusion, Image & Video Generation

* Added a complete **scheduler-managed paged-KV architecture for diffusion**, covering cache initialization, block allocation, worker contracts, RPC plumbing, and a native diffusion backend. **(#5541, #5550, #6094, #6102)**
* Enabled paged KV cache for **HunyuanImage3 DiT** on both GPU and NPU. **(#6563)**
* Added **UniProc diffusion execution** for single-GPU deployments and native SymmMem Fast Ulysses transport for distributed sequence parallelism. **(#6308, #6340)**
* Expanded MiniMax H3 execution with modular pipelines, scheduler-level continuous batching, packed and sparse attention paths, faster MP4/frame conversion, optimized output transfer, and dedicated VAE decoder operators. **(#5720, #5810, #5891, #6518, #6499, #6824, #6607)**
* Added request-level batching for Wan2.2, FastVideo VSA attention, distilled diffusion LoRA support, and FLUX.2-klein Host Weight Runtime contracts. **(#5676, #4820, #2783, #6651)**
* Improved distributed diffusion kernels with fused Q/K RMSNorm plus RoPE, a mask-free TensorRT-LLM packed-padding path, quantized FlashInfer attention for Blackwell, and a device-correct dedicated VAE communication group. **(#5990, #6542, #5344, #6401)**

### Quantization & Memory Efficiency

* Added **Qwen2.5-Omni thinker-only ModelOpt NVFP4 W4A4** checkpoint support and **AutoRound MXFP4** offline quantized-model support. **(#5073, #5544)**
* Added offline **SVDQuant W4A4** support for diffusion models. **(#6162)**
* Extended distributed layerwise offload with MiniMax H3 global FP8, generic online FP8 over DLO AllGather, and online INT8 over DLO AllGather. **(#5910, #6279, #6573)**
* Added MiniMax H3 online FP8, NPU RainFusion plus online INT8, and Qwen3-Omni ModelOpt FP8 inference on MUSA. **(#5737, #5706, #5671)**

### Serving, Frontend & API Behavior

* Added **batched Chat Completions** and speech token-usage headers. **(#5317, #4499)**
* Added **ComfyUI reference-to-video integration**, with MiniMax H3 as the initial example. **(#5756)**
* Added first-class diffusion metrics and returned them from image-edit serving as well as generation paths. **(#4755, #5999)**
* Improved model-tag synchronization, TTS validation for models without uploaded speakers, object-storage model resolution, media redirect policy, request overflow handling, and online profiler stage selection. **(#3805, #5878, #5036, #6122, #6598, #6609)**

### Platforms & Hardware Coverage

* Expanded **Ascend NPU** support for MiniMax H3 with RainFusion, online INT8, packed mask-free attention, distilled four-step schedules, sparse reference/target attention, fused encoder/DiT kernels, and paged KV cache for HunyuanImage3. **(#5706, #5891, #5991, #6518, #6040, #6410, #6563)**
* Completed the vLLM-Omni platform interfaces for **Moore Threads MUSA**, and expanded MiniMax H3 and Qwen-Image kernel compatibility alongside Qwen3-Omni ModelOpt FP8. **(#6058, #5881, #6110, #5671)**
* Added verified ROCm recipes for MiniMax H3 and Cosmos3 Nano, moved ROCm CI to MI300X, and refreshed AMD coverage for the v0.28 line. **(#5723, #5634, #6207, #5886, #6830)**
* Made autoregressive asynchronous output and image D2H synchronization more device-agnostic on **XPU**, and moved XPU CI onto the vLLM base image. **(#5569, #5571, #6727)**

### Breaking Changes

* **The legacy stage-configuration path has been removed.** `--stage-configs-path`, the internal `stage_configs_path` plumbing, and the legacy `stage_args` YAML loader are no longer supported. Deployments should use registered pipelines and deploy configurations through the unified `vllm serve --omni` flow. **(#5647, #5741, #6200, #6221)**
* **`OmniRequestOutput` now directly inherits vLLM `RequestOutput`.** Code using the removed nested `request_output` accessor must read the inherited fields directly. **(#5146, #6172)**
* Support was removed for **DreamID-Omni, MagiHuman, SoulX-Singer, and AudioX**. MammothModa2 was temporarily removed in the same cleanup series but restored before v0.28.0. **(#6357, #6362, #6353, #6694)**

### Note

* The event-driven orchestrator is **opt-in** through `VLLM_OMNI_EVENT_DRIVEN_ORCH=1`; the legacy polling loop remains the default in v0.28.0. **(#5221)**
* Host Weight Runtime is a general foundation, but the first concrete final-layout producer and DLO consumer in this release targets **MiniMax H3 BF16 no-AllGather deployments**. Registered mmap H2D is used only when supported and otherwise falls back to bounded pinned staging. **(#6445, #6486, #6591)**
* MiniMax H3 continuous batching provides scheduler-level control and request co-batching, but its dense DiT compute scales roughly with the number of packed requests; it should not be assumed to improve throughput for every workload. **(#5810)**
* Full-duplex serving continues to evolve. Users should validate session concurrency, barge-in policy, long-duration context behavior, and client/API compatibility for their target model and deployment. **(#4771, #6021, #6089)**

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
* [Bugfix][NPU] Eager-import mindiesd for every diffusion attention backend by @brandneway in https://github.com/vllm-project/vllm-omni/pull/6054
* [Model] Qwen3-Omni: register thinker-only pipeline for Instruct serve by @ZhengWG in https://github.com/vllm-project/vllm-omni/pull/6284
* [Benchmark][MiniCPM-o] Add Omni-DuplexEval support by @zyforsure in https://github.com/vllm-project/vllm-omni/pull/6634
* [Bugfix] Gate async-chunk segment resume by session mode by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/6680
* [CI/Build][MiniCPM-o] Derive duplex admission-probe limit from the deploy config by @dshah1333 in https://github.com/vllm-project/vllm-omni/pull/6678
* [Bugfix][MiniCPM-o] Bound native auto-response continuation by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/6630
* [Diffusion] Add LTX-2.5 Diffusion VAE decoder support by @mglyn in https://github.com/vllm-project/vllm-omni/pull/6189
* [Fix] Restore MammothModa2 support by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6694
* [Bugfix] Make HWR filesystem lifecycle transitions fail-closed by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6692
* [Bugfix] Honor stage selection in online profiler endpoints by @qujing226 in https://github.com/vllm-project/vllm-omni/pull/6609
* [Bugfix][MiniCPM-o] Retire CFM DiT CUDA graphs a generation at a time by @BruceLoveDecimal in https://github.com/vllm-project/vllm-omni/pull/6587
* [Test] Stabilize MiniMax-H3 reference accuracy compile by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/6688
* [Feature] Support text encoder Disaggregation for H3 by @gcanlin in https://github.com/vllm-project/vllm-omni/pull/5885
* Add HYvideo1.5 benchmark by @BLANKETusers in https://github.com/vllm-project/vllm-omni/pull/6349
* [AMD][CI] Fix AMD CI (Partial) by @tjtanaa in https://github.com/vllm-project/vllm-omni/pull/6704
* [Perf] MiniMax-H3 VAE Decoder Ops by @mglyn in https://github.com/vllm-project/vllm-omni/pull/6607
* [Bugfix][MiniCPM-o] Isolate duplex handoff failures and barge-in by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/6170
* [Core] Make diffusion worker titles topology-aware by @prettygirlisnotme in https://github.com/vllm-project/vllm-omni/pull/6307
* [Bugfix][MiniCPM-o] Bind omni-duplex video frames to the unit they close by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/6404
* [Feature][TTS] adaptive chunk ramp (Phase 2 buffer-feedback controller) by @Wallbreazzz in https://github.com/vllm-project/vllm-omni/pull/6001
* Revert "[Core] Make diffusion worker titles topology-aware" by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6717
* fix(npu): extend bf16 autocast to NPU in MossAudioTokenizer decode by @Wallbreazzz in https://github.com/vllm-project/vllm-omni/pull/6664
* [Diffusion] Make Flux2Pipeline text_encoder_out_layers configurable by @khairulkabir1661 in https://github.com/vllm-project/vllm-omni/pull/6390
* [bugfix][MiniCPM-o] Fix offline_inference/test_minicpmo_4_5.py and online_serving/ one by @ZacheryAU in https://github.com/vllm-project/vllm-omni/pull/5464
* Revert "[bugfix][MiniCPM-o] Fix offline_inference/test_minicpmo_4_5.py and online_serving/ one" by @Gaohan123 in https://github.com/vllm-project/vllm-omni/pull/6730
* [Core] Restore topology-aware diffusion worker titles by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6722
* [CI][XPU]switch to use vLLM base docker for XPU by @xuechendi in https://github.com/vllm-project/vllm-omni/pull/6727
* [BugFix] Fix local media access for diffusion speech by @AbelSara in https://github.com/vllm-project/vllm-omni/pull/6622
* [CI][Bugfix] Align the LTX-2 FP8 quality gate with the default recipe by @mglyn in https://github.com/vllm-project/vllm-omni/pull/5831
* [Bugfix] Scope MiniMax-H3 cuDNN SDPA state by @mglyn in https://github.com/vllm-project/vllm-omni/pull/6710
* [Bugfix][Engine] Make abort idempotent during shutdown by @EchoHayate in https://github.com/vllm-project/vllm-omni/pull/6327
* [Feat] Minimax H3 support ref and tgt video sparse attention on NPU by @fan2956 in https://github.com/vllm-project/vllm-omni/pull/6518
* [Model][Frontend] MiniMax-H3: Parallelize MP4 response frame conversion by @MosCloud in https://github.com/vllm-project/vllm-omni/pull/6499
* [CI] Gate qwen3-omni no-async-chunk perf on mean_audio_rtf by @IneshReddy249 in https://github.com/vllm-project/vllm-omni/pull/6743
* [Bugfix] Report engine-queued requests as waiting in vllm_omni:num_requests gauges by @zetxqx in https://github.com/vllm-project/vllm-omni/pull/6549
* [ci][bugfix] Fix MiniMax-H3 FP8 quality test OOM by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/6742
* [Bugfix][StepAudio2] Fix async-chunk metadata mismatch and boundary glitches by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/5917
* [bugfix][MiniCPM-o] Re-land empty full-payload and async_chunk=false processor tests by @ZacheryAU in https://github.com/vllm-project/vllm-omni/pull/6745
* [Bugfix] Honor request seed in MOSS-TTS adapters by @JiataiWang in https://github.com/vllm-project/vllm-omni/pull/6543
* [video][bugfix] Accept semantic video output in offline examples by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/6747
* Fix Qwen3-Omni audio encoder TP when heads are not divisible by TP size by @abrahamzewoudie in https://github.com/vllm-project/vllm-omni/pull/4322
* [Feature] Support MiniMax-H3 FlashGen native LoRA with the legacy manager by @Huangzjun in https://github.com/vllm-project/vllm-omni/pull/6666
* [Bugfix][Qwen3-Omni] Handle missing packed modules mapping by @psv666 in https://github.com/vllm-project/vllm-omni/pull/6748
* [Bugfix] Fix colocate-async sleep admission race and deliver AR abort tokens by @knlnguyen1802 in https://github.com/vllm-project/vllm-omni/pull/6367
* Perf/minimax h3 dit swiglu rope cache npu by @wjialish in https://github.com/vllm-project/vllm-omni/pull/6410
* [Feature][Diffusion] Allow online INT8 quantization with DLO AllGather by @brandneway in https://github.com/vllm-project/vllm-omni/pull/6573
* [Bugfix][MiniCPM-o] Fix duplex camera frame fixture by @psv666 in https://github.com/vllm-project/vllm-omni/pull/6757
* [NPU][Diffusion] MiniMax-H3 RainFusion end_step tail fallback by @HAAZZZEEEE in https://github.com/vllm-project/vllm-omni/pull/6037
* [CI]Split GPU jobs by cards_* and reject hand-written SKU marks by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/6650
* [Bugfix] Avoid invalid TPOT metrics by @AbelSara in https://github.com/vllm-project/vllm-omni/pull/6696
* Fix MiniCPM-o concurrent audio first-packet latency by @Gaohan123 in https://github.com/vllm-project/vllm-omni/pull/6767
* [Bugfix][Qwen3-TTS] Handle codec generations that exhaust their token budget by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/6728
* [Bugfix][MiniCPM-o] Bound full-duplex Talker context with sliding recompute by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/6626
* [Bugfix] Fix create_error_response import across vLLM versions by @Asthenia0412 in https://github.com/vllm-project/vllm-omni/pull/6773
* [diffusion][bugfix] Separate Diffusers hooks from model metadata by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/6749
* [Bugfix][MiniCPM-o] Stabilize native duplex streaming and Stage-1 handoffs by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/6529
* [Bugfix][MiniCPM-o] Anchor duplex soft-interrupt listen sandwich before commit by @y-null in https://github.com/vllm-project/vllm-omni/pull/6772
* [Diffusion] Add native SymmMem Fast Ulysses transport by @baonudesifeizhai in https://github.com/vllm-project/vllm-omni/pull/6340
* [Bugfix][MiniMax-Music3] Resolve stage subdirs against a real snapshot by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/6640
* [BugFix][Higgs-Audio-V3] Fix transcript and concurrent sampling tests by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/6422
* [CI/Build] Add dots.tts weekly e2e coverage by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/6174
* [NPU] upgrade to v0.28.0 by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/6674
* [Bugfix][Diffusion] Restore inline single-stage execution by @Gaohan123 in https://github.com/vllm-project/vllm-omni/pull/6813
* [Bugfix] Recover Omni benchmark TPOT from Stage 0 metrics by @Gaohan123 in https://github.com/vllm-project/vllm-omni/pull/6818
* [Core] Flag pipelines with no terminal output stage in PipelineConfig.validate() by @m0g3r in https://github.com/vllm-project/vllm-omni/pull/6291
* [Frontend] Encode interleaved video frames in parallel by @mo-ke-ke in https://github.com/vllm-project/vllm-omni/pull/6776
* [Diffusion][Performance] Optimize MiniMax-H3 video output transfer by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/6824
* [AMD] [CI] Fix tests for v0.28.0 by @tjtanaa in https://github.com/vllm-project/vllm-omni/pull/6830
* [Doc] Update vLLM-Omni WeChat QR code by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/6832
* [Bugfix] Use Seed-TTS reference audio with MiniCPM-o 4.5 by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/6628
* [CI/Build] Align duplex stage-input deadline with the e2e client timeout by @IneshReddy249 in https://github.com/vllm-project/vllm-omni/pull/6831
* [Feature][MiniMax-H3] Fuse the FastH3 four-step adapter at load time by @princepride in https://github.com/vllm-project/vllm-omni/pull/6714
* [Bugfix][Diffusion] Load plugins in spawned stage process by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/6750
* [Bugfix][MiMo-Audio] Restore make_empty_intermediate_tensors on the talker for vLLM 0.28 by @rk9595 in https://github.com/vllm-project/vllm-omni/pull/6803
* [CI] Fix Speech CI Validation Messages by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/6827
* [Bugfix][Kernel] Stage strided Ulysses QKV with copy engine by @bobboli in https://github.com/vllm-project/vllm-omni/pull/6814
* [Diffusion] Add paged KV cache support for HunyuanImage3 DiT on NPU and GPU by @Acerak01-fy in https://github.com/vllm-project/vllm-omni/pull/6563
* [CI][Bugfix]Drop dummy-weight Qwen3-TTS Base from Ready CI by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/6861
* [CI][MiniCPM-o] Make audio consistency checks deterministic by @Gaohan123 in https://github.com/vllm-project/vllm-omni/pull/6828
* [Bugfix][MiniCPM-o] Checkpoint playback before final input commit by @Gaohan123 in https://github.com/vllm-project/vllm-omni/pull/6821
* [Bugfix][Core] Do not advance the segment watermark past an unmaintained request counter by @IneshReddy249 in https://github.com/vllm-project/vllm-omni/pull/6834

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
* @zyforsure made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6634
* @dshah1333 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6678
* @qujing226 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6609
* @prettygirlisnotme made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6307
* @khairulkabir1661 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6390
* @zetxqx made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6549
* @JiataiWang made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6543
* @abrahamzewoudie made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4322
* @HAAZZZEEEE made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6037
* @Asthenia0412 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6773
* @rk9595 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6803

**Full Changelog**: https://github.com/vllm-project/vllm-omni/compare/v0.26.0...v0.28.0