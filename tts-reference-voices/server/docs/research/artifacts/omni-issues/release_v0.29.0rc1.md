## Highlights

This release features 159 merged changes from 95 contributors, including 42 new contributors.

vLLM-Omni `v0.29.0rc1` focuses on three major advances: 1) **broader diffusion batching, parallelism, and memory control**, 2) **full-duplex runtime graduation and expanded realtime speech serving**, and 3) **new image, audiovisual, and speech model integrations**. The release rebases onto **vLLM 0.29.0**, improves multi-stage initialization and configuration resolution, and extends support for distilled generation models.

### Key Improvements

* **Expanded diffusion execution and deployment options**, adding BAGEL continuous batching, Boogu-Image request batching, SANA-Video tensor/sequence/CFG parallelism, and component-selective offload for DiT and text encoders. **(#6359, #6968, #5861, #5940, #5929)**
* **Graduated MiniCPM-o 4.5 and PersonaPlex full-duplex serving out of experimental**, added server-side VAD for turn-based omni models, and accelerated Nemotron VoiceChat across offline, streaming, and duplex deployment profiles. **(#6196, #6618, #6354)**
* **Broadened model coverage** with native MAGI-2 Preview audiovisual generation, Audio8 TTS Preview 0.6B, SenseNova-U1.5 distilled LoRA support, Boogu-Image Turbo, and HunyuanImage-3.0-Instruct-Distil. **(#5918, #6157, #6516, #6699, #4048)**

### Core Architecture & Runtime

* Rebased the project onto **vLLM 0.29.0**. **(#7230)**
* Centralized standard and headless startup through **one Omni configuration resolver**, sharing pipeline registration, deploy-config resolution, and override handling. Pipeline configurations now validate during construction. **(#5140, #6829)**
* Added **opt-in parallel initialization for colocated stages**, with memory admission checks and device phase locks. Improved initialization grouping for overlapping device layouts and enabled LLM replicas on separate GPUs to initialize concurrently. **(#5224, #7328, #7292)**
* Advanced **paged AR-to-DiT KV transfer** using vLLM’s native Mooncake connector, adding shared transfer identity, scheduler/worker metadata plumbing, and consumer-side load initiation. This is an incremental integration, with end-to-end completion handling still outside the PR’s scope. **(#6310)**
* Refactored diffusion prompt updates into a **pluggable interaction framework**, establishing modality handlers and chunk-boundary application while retaining prompt-only runtime behavior. **(#6294)**

### Model Support

* Added **MAGI-2 Preview** with native text/image-to-video-and-audio generation, synchronized stereo audio, distributed execution, Cache-DiT, and video API integration. **(#5918)**
* Added **Audio8 TTS Preview 0.6B**, a DualAR speech model with a 44.1 kHz codec, streaming synthesis, and zero-shot voice cloning. **(#6157)**
* Added support for **SenseNova-U1.5-8B-MoT and its distilled 8-step LoRA**, including correct adapter fusion and updated deployment recipes. **(#6516)**
* Added the **Boogu-Image Turbo native DMD execution path** and pipeline resolution, plus documented and tested **Boogu Edit-Turbo** serving. **(#6699, #6961, #6701)**
* Added **HunyuanImage-3.0-Instruct-Distil**, including CFG-distilled and MeanFlow execution support. **(#4048)**
* Added an **experimental JoyAI-VL-Interaction native multi-stage speech pipeline** through Qwen3-TTS, and an **experimental Mage-VL full-duplex adapter and offline integration** using its reference Transformers execution path. **(#5352, #6537)**

### Audio, Speech & Realtime Serving

* Moved the shared duplex engine, serving stack, and MiniCPM-o/PersonaPlex adapters into their core packages, and introduced a **Python `DuplexClient` API**. **(#6196)**
* Added **server-side VAD** to the Realtime WebSocket stack, with speech events, automatic audio commits, and turn-based response generation for models such as Qwen3-Omni. **(#6618)**
* Accelerated **Nemotron VoiceChat** with native vLLM talker execution, paged attention, CUDA Graphs, incremental codec decoding, and realtime startup warmup. The reported single-H100 offline fixture improved from 10.3 seconds to 3.7 seconds. **(#6354)**
* Added **dots.tts online serving** and **OmniVoice variable-length attention, request batching, and step execution**. Improved MOSS-TTS reference-audio preprocessing, batched execution, and streaming codec performance. **(#6235, #6408, #4982, #7202)**

### Diffusion, Image & Video Generation

* Added **BAGEL step execution and continuous batching**, **Boogu-Image T2I request batching and CFG parallelism**, and **LingBot World stepwise execution**. **(#6359, #6968, #6786, #6844)**
* Expanded **SANA-Video 2B** with tensor, sequence, and CFG parallelism, plus Cache-DiT and CPU offload. **(#5861, #5940, #5882)**
* Completed **MiniMax-H3 VSA and Ulysses support** and expanded compatibility across the full LightX2V Turbo LoRA matrix. **(#6909, #7062)**
* Optimized **LTX video output transport, Ulysses sequence parallelism, and LTX-2.5 DiffVAE operators**, including fused kernels on SM100 and SM103. **(#7000, #7079, #7308, #7350)**

### Quantization & Memory Efficiency

* Added **component-selective diffusion offload** for DiT and text encoders, supporting whole-module swapping or layer streaming with per-component weight-transfer policies. Unified offload topology resolution through a shared plan resolver. **(#5929, #7209)**
* Added **Boogu-Image FP8 support** and improved diffusion LoRA execution by retaining weights across activation cycles, optimizing accumulation, and fusing distilled adapters before HSDP sharding. **(#6925, #7195, #6268, #6948)**

### Serving, Frontend & API Behavior

* Added **configurable Speech API output sample rates**, plus opt-in WebSocket TTS split granularity and session seeds. **(#6553, #7046)**
* Added **Cosmos3 control uploads through the video API**. **(#7027)**
* Extended **Omni benchmarking to image and video endpoints** and exposed detailed diffusion pipeline timings. **(#4728, #6822)**

### Breaking Changes

* **`diffusion_batch_size` has been removed.** Use `max_num_seqs` as the single diffusion batching configuration. Existing Python callers and configuration plumbing using the removed argument must be updated. **(#6484)**

### Note

* Colocated parallel stage initialization remains **opt-in** through `parallel_stage_init`; it is disabled by default. **(#5224)**
* Turn-based server VAD requires **`interrupt_response=false`**; turn-based barge-in is not supported. **(#6618)**
* The experimental JoyAI native pipeline executes stages sequentially and does not support async-chunk streaming. Mage-VL integration does not yet provide native vLLM model execution. **(#5352, #6537)**

**Full Changelog**: https://github.com/vllm-project/vllm-omni/compare/v0.28.0...v0.29.0rc1

## What's Changed
* [Diffusion] Add Boogu Edit-Turbo support docs and tests by @xRay2016 in https://github.com/vllm-project/vllm-omni/pull/6701
* [Config] Remove diffusion_batch_size and use max_num_seqs instead. by @LyxWxj in https://github.com/vllm-project/vllm-omni/pull/6484
* [Core] Validate PipelineConfig in `__post_init__` by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/6829
* [Frontend] Add configurable output sample rate to Speech API by @AuFlow in https://github.com/vllm-project/vllm-omni/pull/6553
* [Test] Add MiniMax-H3 DLO DP2 variants and Turbo LoRA L3 test by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/6556
* [Doc] Update README and docs for v0.28.0 by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6858
* [Bugfix][Diffusion] Preserve stage attention backend by @AndyZhou952 in https://github.com/vllm-project/vllm-omni/pull/6645
* docs: add concise API server endpoint guide by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6114
* [Bugfix][Cosmos3] Avoid logging prompts at INFO level by @rahul-steiger-nv in https://github.com/vllm-project/vllm-omni/pull/6913
* [CI][ROCm] Fix deterministic AMD L3 blockers by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/6884
* [Model] Support SenseNova-U1.5-8B-MoT and its distilled 8-step LoRA by @MrlixiangWE in https://github.com/vllm-project/vllm-omni/pull/6516
* [Bugfix] Prevent build_engine_args_dict from mutating stage_config.engine_args by @Arifuzzamanjoy in https://github.com/vllm-project/vllm-omni/pull/6783
* [Bugfix][Ascend NPU][Boogu] Replace complex RoPE with real-valued operations by @JW-L-7 in https://github.com/vllm-project/vllm-omni/pull/6571
* [Bugfix][Diffusion] Keep the GQA ratio when padding Ulysses heads by @Xenoryn in https://github.com/vllm-project/vllm-omni/pull/5716
* [Hardware][Ascend] Use npu_rotary_mul fused kernel for MOSS-TTS codec RoPE by @jingchengtian in https://github.com/vllm-project/vllm-omni/pull/6908
* [CI] Migrate L4 jobs to l4-k8s and split by GPU count by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/6890
* [Model] Add TP and CFG parallelism to SANA-Video 2B by @cr-gao in https://github.com/vllm-project/vllm-omni/pull/5861
* [Feature][MiniMax-H3] Complete VSA and Ulysses support by @princepride in https://github.com/vllm-project/vllm-omni/pull/6909
* [Doc] Refine TRTLLM attention guidance by @bobboli in https://github.com/vllm-project/vllm-omni/pull/6724
* [Bugfix][Diffusion] Register Sana I2V pipeline as video output by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/6953
* [CI] Select mirror_hardwares presets via MIRROR_HW (H100/B200) by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/5543
* [Model] Add Cache-DiT and CPU offload support for SANA-Video 2B by @cr-gao in https://github.com/vllm-project/vllm-omni/pull/5882
* [Bugfix][Qwen3-TTS] Reject task mismatches before EngineCore dispatch by @gxxx-hum in https://github.com/vllm-project/vllm-omni/pull/6113
* [Bugfix][TTS] Isolate concurrent StepAudio2 TRT builds by @BANANASJIM in https://github.com/vllm-project/vllm-omni/pull/6957
* [Perf][Bugfix][OmniVoice] Restore float16 serving, and fuse the generator hot loop by @MrlixiangWE in https://github.com/vllm-project/vllm-omni/pull/6317
* [Bugfix] Fix vLLM serve error response imports by @maithilijoshi20 in https://github.com/vllm-project/vllm-omni/pull/6707
* [Bugfix][Cosmos3] Support multi-chunk transfer with distributed VAE by @rahul-steiger-nv in https://github.com/vllm-project/vllm-omni/pull/6920
* [Feature][Diffusion]: CFG parallelism support for Boogu-Image by @nagisa-kunhah in https://github.com/vllm-project/vllm-omni/pull/6786
* [Core] Optimize diffusion LoRA expand accumulation by @0z5a in https://github.com/vllm-project/vllm-omni/pull/6268
* [Feat] Add support and testcase for HunyuanImage-3.0-Instruct-Distil by @zengchuang-hw in https://github.com/vllm-project/vllm-omni/pull/4048
* [model]Add experimental Mage-VL full-duplex adapter and offline integration by @zyforsure in https://github.com/vllm-project/vllm-omni/pull/6537
* [Bugfix][XPU] Add MoTRMSNorm.forward_xpu delegating to forward_native by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/5568
* [Bugfix][Qwen2.5-Omni] Fix two stale call sites in the speech helpers by @Anai-Guo in https://github.com/vllm-project/vllm-omni/pull/6886
* [Bugfix] Validate --stage-overrides shape in parse_stage_overrides (drop field allowlist) by @MciG-ggg in https://github.com/vllm-project/vllm-omni/pull/6230
* [Bugfix][TTS] Make CosyVoice3 TRT plan publication concurrency-safe by @BANANASJIM in https://github.com/vllm-project/vllm-omni/pull/6955
* [Bugfix] Restore Omni health route ownership by @qujing226 in https://github.com/vllm-project/vllm-omni/pull/6723
* [Bugfix][LTX] Restore distilled two-stage video serving by @mglyn in https://github.com/vllm-project/vllm-omni/pull/6847
* [Doc] Add production diffusion model skill by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/6097
* [Bugfix] Preserve BF16 residual semantics in fused MiniMax-H3 modulation by @bobboli in https://github.com/vllm-project/vllm-omni/pull/6878
* [Model] Add BAGEL step execution and continuous batching by @Sky-Trigger in https://github.com/vllm-project/vllm-omni/pull/6359
* [Perf][NemotronVoiceChat] Fast defaults for all three deploy profiles: 2.8x offline, realtime full-duplex audio by @yuekaizhang in https://github.com/vllm-project/vllm-omni/pull/6354
* [Benchmark] Add local OmniInteract performance cases by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/6817
* [Perf][Model] Optimize LTX video output transport by @mglyn in https://github.com/vllm-project/vllm-omni/pull/7000
* [Diffusion] Enable request-level batching for Boogu-Image (T2I) by @ShengleiFu in https://github.com/vllm-project/vllm-omni/pull/6968
* [Bugfix] Release diffusion worker RPC results on ranks that do not reply by @heyuanliu-intel in https://github.com/vllm-project/vllm-omni/pull/6989
* [Perf][DreamZero] Remove redundant CUDA compile guard by @MikeyDong1 in https://github.com/vllm-project/vllm-omni/pull/6983
* [Bugfix] Fix Qwen3-Omni MoE backend selection by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/7019
* [Bugfix] Update Hub kernel dependency floor by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/7020
* [CI][Bugfix] Normalize spoken units in text comparison by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/6947
* [Bugfix][BAGEL] Restore original denoise step count by @Sky-Trigger in https://github.com/vllm-project/vllm-omni/pull/7049
* [Feat][dots.tts] Add Online Serving Support by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/6235
* [Bugfix] Give exact-shape codec models an unpadded input_ids view by @IneshReddy249 in https://github.com/vllm-project/vllm-omni/pull/6775
* [Bugfix] Fix Higgs Audio v3 voice-clone token validation by @LOGO127 in https://github.com/vllm-project/vllm-omni/pull/7065
* [Perf][CI] Use Whisper on GPU when memory permits by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/5675
* [Feature][Moss-TTS] Reference Audio Preprocessing by @BruceLoveDecimal in https://github.com/vllm-project/vllm-omni/pull/4982
* [Bugfix] Fix fallback loading for IndexTTS external models by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/6137
* [Model] Add sequence parallelism to SANA-Video 2B by @cr-gao in https://github.com/vllm-project/vllm-omni/pull/5940
* [Model] Add native MAGI-2 Preview diffusion support by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/5918
* [Core] Graduate MiniCPM-o 4.5 and PersonaPlex full-duplex serving out of experimental by @chickeyton in https://github.com/vllm-project/vllm-omni/pull/6196
* Parallel stage initialization (admission + SH/EX device locks) (Worker refactor 1/N) by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/5224
* [Bugfix] Drop the removed diffusion_batch_size kwarg from the stage-init test by @princepride in https://github.com/vllm-project/vllm-omni/pull/7101
* [Bugfix][Diffusion] Fuse distilled LoRA weights before HSDP sharding by @SamitHuang in https://github.com/vllm-project/vllm-omni/pull/6948
* [diffusion][feature] Add component-selective offload policies by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/5929
* [Diffusion] Implement paged AR↔DiT KV connector ("v1", reusing vllm's native mooncake) by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/6310
* [Doc] Fix markdownlint findings in the serving API reference by @MaxFreedomPollard in https://github.com/vllm-project/vllm-omni/pull/7111
* [Model] Add Boogu-Image Turbo native DMD path by @prettygirlisnotme in https://github.com/vllm-project/vllm-omni/pull/6699
* [CI][Bugfix] Use the matching checkpoint for Qwen3-TTS VoiceDesign tests by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/7054
* [Model] FP8 Support For Boogu-Image by @Dmaner in https://github.com/vllm-project/vllm-omni/pull/6925
* [CI/Build] Stabilize Qwen3-TTS speaker-embedding tests against miss-EOS flake by @mjZhaoElaine in https://github.com/vllm-project/vllm-omni/pull/6924
* [Perf][Diffusion] Skip the Ulysses length all-gather when shards are padded equal by @Xenoryn in https://github.com/vllm-project/vllm-omni/pull/5717
* [Feature][MiniMax-H3] Support the full LightX2V Turbo LoRA matrix by @princepride in https://github.com/vllm-project/vllm-omni/pull/7062
* [Bugfix] Fix Hunyuan Image-3 expert mapping contract by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/7021
* [Model] MiniMax-H3: validate versioned text-conditioning handoff by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6720
* [Model] Preserve MiniCPM-o Talker full attention until capacity by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/6799
* [Feature] Define the runner preprocess phase contract and regression coverage by @xiaobaixia222 in https://github.com/vllm-project/vllm-omni/pull/7136
* [Bugfix][Diffusion] Restore the TRTLLM attention default for the MiniMax-H3 modular alias by @princepride in https://github.com/vllm-project/vllm-omni/pull/7162
* [Core][Diffusion] Refactor prompt updates into a modality-ready interaction framework by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/6294
* [AR-Diffusion] Allocate K and V separately so the compiled path stops cloning the pool by @linzhenpl07 in https://github.com/vllm-project/vllm-omni/pull/6463
* [BugFix][Qwen-Image-Edit] restore txt_seq_lens RoPE width after #3588 regression by @NumberWan in https://github.com/vllm-project/vllm-omni/pull/5586
* [Feature][LingBot World]stepwise execution by @BruceLoveDecimal in https://github.com/vllm-project/vllm-omni/pull/6844
* [Doc] Add A100 recipe for Wan2.2-TI2V-5B by @lucasruan1618 in https://github.com/vllm-project/vllm-omni/pull/7189
* [Doc] Update vLLM-Omni WeChat QR code by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/7178
* [Bugfix][Diffusion] Canonicalize cache_backend=None to "none" by @zhang-keliang in https://github.com/vllm-project/vllm-omni/pull/7041
* [Bugfix][Diffusion] Include guidance_scale_2_provided in the request-batch key by @ShengleiFu in https://github.com/vllm-project/vllm-omni/pull/7078
* [Bugfix][Diffusion] Make Cosmos3 transfer image arrays writable by @rahul-steiger-nv in https://github.com/vllm-project/vllm-omni/pull/6915
* [Frontend][Model] Add Cosmos3 control uploads to video API by @FredHuangNV in https://github.com/vllm-project/vllm-omni/pull/7027
* [Bugfix][Cosmos3] Auto-pad non-divisible Ulysses GEN sequences by @rahul-steiger-nv in https://github.com/vllm-project/vllm-omni/pull/6918
* [Model][Perf] Optimize LTX Ulysses sequence parallelism by @mglyn in https://github.com/vllm-project/vllm-omni/pull/7079
* [skip ci][Doc] Module design doc for diffusion runtime by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/6440
* [Bugfix][MiniMax-H3] Stabilize keyframe VAE encoding by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/7191
* [Perf][Diffusion] Keep LoRA weights resident across activation cycles by @princepride in https://github.com/vllm-project/vllm-omni/pull/7195
* [Bugfix][NPU] Fix MiniMax-H3 INT8 quantization dispatch by @KrystalRay in https://github.com/vllm-project/vllm-omni/pull/6876
* [Bugfix][MiniCPM-o] Allow ragged audio_feature_lens across a batch by @pujitha24 in https://github.com/vllm-project/vllm-omni/pull/7071
* [Bugfix][Cosmos3] Fix distributed Transfer output envelope by @rahul-steiger-nv in https://github.com/vllm-project/vllm-omni/pull/7205
* [1/N] Stream Wan VAE chunks to the media consumer by @specture724 in https://github.com/vllm-project/vllm-omni/pull/7016
* [Model] Add Boogu-Image Turbo pipeline resolution by @Jerry2423 in https://github.com/vllm-project/vllm-omni/pull/6961
* [Migrate]Move model-specific helpers out of serving_speech by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/6697
* [Refactor] fish_speech: vendor DAC codec modules, drop external fish-speech dependency by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/4871
* [Frontend] Add omni benchmark support for image and video endpoints by @ZacheryAU in https://github.com/vllm-project/vllm-omni/pull/4728
* [Bugfix][Qwen3-Omni] Read code-predictor RoPE theta from rope_parameters by @dshah1333 in https://github.com/vllm-project/vllm-omni/pull/7228
* [Refactor 1/N] Centralize Omni config resolution by @fake0fan in https://github.com/vllm-project/vllm-omni/pull/5140
* [Bugfix] Fix Step-Audio2 L4 CI KV cache allocation by @wuli666 in https://github.com/vllm-project/vllm-omni/pull/6839
* [Perf]Boogu-Image Skip dense attention masks by @AbelSara in https://github.com/vllm-project/vllm-omni/pull/6871
* [Bugfix] Keep --disable-log-stats out of stage config resolution by @fake0fan in https://github.com/vllm-project/vllm-omni/pull/7237
* [Bugfix] Bound omni benchmark per-request timeout to 15 min by default by @tlysanhuo in https://github.com/vllm-project/vllm-omni/pull/7130
* [CI/Build] Wait for duplex reaper recovery in retry test by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/7225
* [Bugfix] Fix video benchmark timeout and failure accounting by @congw729 in https://github.com/vllm-project/vllm-omni/pull/7259
* [Frontend] Add server-side VAD for turn-based omni models by @LHXuuu in https://github.com/vllm-project/vllm-omni/pull/6618
* [Bugfix][Model] GR00T-N1.7: honor processor_config image pipeline (use_albumentations / crop_fraction / letter_box_transform) to match Isaac-GR00T by @liangmenghuang in https://github.com/vllm-project/vllm-omni/pull/7083
* [Model][JoyAI-VL-Interaction] Add native multi-stage pipeline by @ShuoleiWang in https://github.com/vllm-project/vllm-omni/pull/5352
* [Bugfix] Preserve additional_config for LLM stages by @AbelSara in https://github.com/vllm-project/vllm-omni/pull/7272
* [Bugfix][Examples] Use --profiler-config flag in offline TTS examples by @Asthenia0412 in https://github.com/vllm-project/vllm-omni/pull/6763
* [Bugfix] Skip HWR store-size scans when no limit is configured by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/7131
* [CI][ROCm] Route LTX2 Ulysses parity to two-GPU lane by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/7234
* [Bugfix][Model] GR00T-N1.7: honor the per-request seed for flow-matching noise by @liangmenghuang in https://github.com/vllm-project/vllm-omni/pull/7253
* Add vLLM-Omni library info to Hugging Face Hub requests by @hmellor in https://github.com/vllm-project/vllm-omni/pull/5381
* [Bugfix][NPU] Limit MiniMax H3 modulation grid size by @KrystalRay in https://github.com/vllm-project/vllm-omni/pull/6794
* [Bugfix] Build the forced-aligner prompt without a chat template (word timestamps one bin late) by @twu3202 in https://github.com/vllm-project/vllm-omni/pull/7240
* [Refactor][Diffusion] Resolve offload topology through one plan resolver by @specture724 in https://github.com/vllm-project/vllm-omni/pull/7209
* [Doc] Add AI usage policy for contributions by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/7305
* [Bugfix][MiMo-Audio] Align code2wav decode with tokenizer device by @smartDream-chao in https://github.com/vllm-project/vllm-omni/pull/6539
* [Bugfix][MiniCPM-o] Fix the audio_embeds input path by @eval-dev in https://github.com/vllm-project/vllm-omni/pull/5730
* [Feat][OmniVoice]Support Varlen Attn,  Request-Batch and Step-Execution by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/6408
* [Model] Add Audio8 TTS Preview 0.6B (DualAR, 44.1 kHz codec) by @NancyFyong in https://github.com/vllm-project/vllm-omni/pull/6157
* [Bugfix][Frontend] Accept the msgpack-numpy package's numpy markers on the OpenPI endpoint by @ZJLi2013 in https://github.com/vllm-project/vllm-omni/pull/6051
* [Frontend] Opt-in WebSocket TTS split_granularity and session seed by @rk9595 in https://github.com/vllm-project/vllm-omni/pull/7046
* [Bugfix][Frontend] Clear the P0 multimodal cache through the renderer by @ZenAlexa in https://github.com/vllm-project/vllm-omni/pull/7003
* [Bugfix][Frontend] Enforce image pixel limits for video input references by @BANANASJIM in https://github.com/vllm-project/vllm-omni/pull/6963
* [Bugfix][TTS] Isolate shared Higgs v3 reference encode from request cancellation by @EchoHayate in https://github.com/vllm-project/vllm-omni/pull/7076
* [Bugfix][CosyVoice3] Resolve hash snapshot pipeline by @XuTianle0101 in https://github.com/vllm-project/vllm-omni/pull/6896
* [CI] Skip Qwen3-Omni Server VAD multi-turn realtime test (#7279) by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/7314
* [Bugfix][Magi2] Allow import without an active Triton driver by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/7239
* [Core] Split Omni connector model runner mixin by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/6903
* [Bugfix] Make LTX vocoder decoding deterministic by @mglyn in https://github.com/vllm-project/vllm-omni/pull/7231
* [Doc] [Recipe] Add FLUX.1-schnell recipe for RTX 5090 32GB by @Sparks-M in https://github.com/vllm-project/vllm-omni/pull/7299
* [Doc] Qwen3-TTS: add 0.6B on 1x A100 40GB by @chi030303 in https://github.com/vllm-project/vllm-omni/pull/7289
* [Perf][Model] Add optimized LTX-2.5 DiffVAE operators by @mglyn in https://github.com/vllm-project/vllm-omni/pull/7308
* [2/N] Add a minimal temporal chunk callback for MiniMax-H3 by @specture724 in https://github.com/vllm-project/vllm-omni/pull/7017
* [Feature][Diffusion] Expose detailed pipeline timings by @bobboli in https://github.com/vllm-project/vllm-omni/pull/6822
* [Bugfix] Resolve #6931 hub FA3 on torch 2.13 via kernels 0.16.1 by @NumberWan in https://github.com/vllm-project/vllm-omni/pull/7185
* [Bugfix][Ascend] fix npu 310/a5 bugs by @zyz111222 in https://github.com/vllm-project/vllm-omni/pull/6685
* [Bugfix][Engine] Group overlapping device stages into one sequential init component by @ZhengWG in https://github.com/vllm-project/vllm-omni/pull/7328
* fix: reserve Qwen3-Omni NVFP4 backend fix by @kunkunblueberry in https://github.com/vllm-project/vllm-omni/pull/7200
* [BugFix] Add field validators for /v1/audio/generate request by @Shaun-Walsh in https://github.com/vllm-project/vllm-omni/pull/4741
* [CI][ROCm] Match CUDA/NPU L2/L3 label routing by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/6966
* [CI/Build] Avoid duplicate stage CLI deploy config by @CarrotSwordsman in https://github.com/vllm-project/vllm-omni/pull/7007
* [CI/Build][ROCm] Normalize SenseNova paged-decode hardware markers by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/6935
* [Model] Skip unused frame packing in Wan2.2 S2V by @yuweih205 in https://github.com/vllm-project/vllm-omni/pull/7155
* [Doc] Add dual DGX Spark MiniMax-H3 results by @bojiang-li in https://github.com/vllm-project/vllm-omni/pull/7343
* [Model] Optimize MOSS-TTS Local batched execution and streaming codec by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/7202
* [Bugfix][XPU] Restore N-D output shape for W8A16 FP8 linear by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/7301
* [Doc] Document num_outputs_per_prompt for /v1/videos by @Hiro208 in https://github.com/vllm-project/vllm-omni/pull/7341
* [Skills] Add perf-evidence isolation, stage-attribution, and realtime-contract requirements by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/6820
* [Bugfix] Allow LLM replicas on different GPUs to initialize concurrently by @Gaohan123 in https://github.com/vllm-project/vllm-omni/pull/7292
* [CI/Build] Stabilize LTX2 vocoder autocast test on ROCm by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/7336
* [NPU][CI] Add A5 and 310P CI support by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/6875
* [Kernel] Enable LTX DiffVAE fusions on SM100 and SM103 by @mglyn in https://github.com/vllm-project/vllm-omni/pull/7350
* [Bugfix][MiniCPM-o] Align structured chat content with native omni rendering by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/7344
* [Rebase] Rebase to vLLM 0.29.0 by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/7230

## New Contributors
* @xRay2016 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6701
* @LyxWxj made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6484
* @AuFlow made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6553
* @andyluo7 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6884
* @Arifuzzamanjoy made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6783
* @JW-L-7 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6571
* @Xenoryn made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5716
* @jingchengtian made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6908
* @BANANASJIM made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6957
* @0z5a made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6268
* @Anai-Guo made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6886
* @MciG-ggg made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6230
* @Sky-Trigger made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6359
* @heyuanliu-intel made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6989
* @MikeyDong1 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6983
* @LOGO127 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7065
* @MaxFreedomPollard made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7111
* @xiaobaixia222 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7136
* @lucasruan1618 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7189
* @zhang-keliang made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7041
* @FredHuangNV made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7027
* @KrystalRay made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6876
* @pujitha24 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7071
* @specture724 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7016
* @Jerry2423 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6961
* @tlysanhuo made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7130
* @liangmenghuang made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7083
* @ShuoleiWang made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5352
* @hmellor made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5381
* @twu3202 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7240
* @eval-dev made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5730
* @NancyFyong made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6157
* @ZenAlexa made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7003
* @XuTianle0101 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6896
* @Sparks-M made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7299
* @chi030303 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7289
* @kunkunblueberry made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7200
* @Shaun-Walsh made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4741
* @CarrotSwordsman made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7007
* @yuweih205 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7155
* @bojiang-li made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7343
* @Hiro208 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7341

**Full Changelog**: https://github.com/vllm-project/vllm-omni/compare/v0.28.0...v0.29.0rc1