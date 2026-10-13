## Highlights

This release features 262 merged changes from 126 contributors, including 45 new contributors.

vLLM-Omni `v0.30.0rc1` focuses on three major advances: 1) **a unified full-duplex framework and scalable serving**, 2) **interactive video generation and improved cross-stage data transfer**, and 3) **expanded speech, image, and vision-language-action model support**. The release rebases onto **vLLM 0.30.0**, advances streaming execution, and improves quantization and memory efficiency across multimodal pipelines.

### Key Improvements

* **Unified full-duplex execution around engine-owned sessions**, introducing dedicated duplex orchestration, an in-process client, and AURA integration through the shared Realtime API. **(#7413, #7633)**
* **Advanced interactive and streaming video generation**, adding live camera control for LingBot World, worker-side MP4 encoding, asynchronous chunk transfers, and MiniMax-H3 latent editing and long-video continuation. **(#7198, #7048, #7406, #7465, #7838)**
* **Broadened model coverage** with Tencent AuK/AuK-Flash, Breeze-TTS-2, Anima, and π0.5, alongside Gepard-1.0 online speech serving and direct FastH3 8-Step V2 checkpoint loading. **(#7385, #7084, #4083, #6950, #7499, #7610)**

### Core Architecture & Runtime

* Rebased the project onto **vLLM 0.30.0**. **(#7820)**
* Introduced **`DuplexOmni`, `DuplexOmniEngine`, and `DuplexOrchestrator`**, moving session ownership and execution into the engine layer. Added `InlineDuplexClient` for in-process use and a shared model plugin interface. **(#7413)**
* Added an optional **NIXL connector** for cross-stage tensor and structured-payload transport, plus **native Mooncake AR-to-DiT KV transfer** with scheduler-owned GPU pages and opt-in HunyuanImage3 prefetch. **(#6093, #7166, #7637)**
* Preserved **structured configurations through runtime startup** and refactored Omni prefix caching into separate manager and controller components. **(#6849, #6654)**
* Added the initial **world-model rollout serving API**, with session creation, stepping, reset, closure, and committed-step tracking. This establishes a serving interface for external RL integrations. **(#4770)**

### Model Support

* Added **Tencent AuK and AuK-Flash** through a two-stage encoder–diffusion pipeline for instruction-driven speech generation and audio editing, including the distilled four-step Flash checkpoint. **(#7385)**
* Added **Breeze-TTS-2**, with a two-stage autoregressive talker and codec pipeline, incremental 24 kHz audio, voice design, reference-based cloning, and voice direction. **(#7084)**
* Added **Anima native text-to-image generation**, including local single-file safetensors checkpoint loading. **(#4083)**
* Added **π0.5 (Pi0.5)** vision-language-action inference through the OpenPI realtime robot API, generating action chunks from camera images, language instructions, and robot state. **(#6950)**
* Extended **Gepard-1.0** to `/v1/audio/speech` with streaming and concurrent-request isolation, and added **direct FastH3 8-Step V2 checkpoint loading**. **(#7499, #7610)**

### Audio, Speech & Realtime Serving

* Integrated **AURA’s ASR → Thinker → Talker → Code2Wav pipeline** into the unified full-duplex runtime, supporting video-only inputs and shared session, interruption, and resume controls. **(#7633)**
* Enabled **Qwen3-TTS Model Runner V2** and made it the experimental default in the bundled CUDA profile. Enabled event-driven orchestration by default for Qwen3-TTS. **(#7781, #7930, #7088)**
* Improved **CosyVoice3 flow batching and incremental vocoder streaming**, and accelerated MOSS-TTS on Ascend with incremental depth-transformer KV caching, NPUGraph codec decoding, and disaggregated deployment profiles. **(#4876, #7521, #6967, #7280, #7052)**

### Diffusion, Image & Video Generation

* Added **mid-stream camera interaction for LingBot World 2**, plus Ulysses sequence parallelism and streaming VAE decoding distributed across Ulysses ranks. **(#7198, #6841, #7651)**
* Advanced the **streaming video output pipeline** with session-owned VAE decoding, bounded worker-side encoding, and asynchronous device-to-host chunk transfers through reusable pinned buffers. **(#6533, #7018, #7048, #7406)**
* Expanded **MiniMax-H3** with latent-mask editing, long-video latent continuation with driving audio, and VAE encoders in disaggregated deployments. **(#7465, #7838, #6939)**
* Migrated **MammothModa2’s DiT stage to the shared diffusion runtime** and enabled Cache-DiT acceleration. Added SeaCache support for Cosmos3. **(#7134, #7291, #6922)**

### Quantization & Memory Efficiency

* Added **Cosmos3 mixed W8A8/W8A16 and W4A4/W4A16 denoising**, online FP8 support for the Boogu-Image MLLM and LingBot World, and FP8 KV caching for MammothModa2’s AR stage. **(#6560, #7342, #7549, #7436)**
* Improved **HSDP startup with rank-0 shared weight loading**, accelerated LoRA delta computation, and reduced MiniMax-H3 video VAE memory peaks. **(#7005, #7590, #7241)**
* Expanded **Wan2.2 quantized execution on Ascend** with MXFP4 options, W4A8 fallback, and MindIE dense and sparse quantized attention. **(#7210, #7561)**

### Serving, Frontend & API Behavior

* Added opt-in **multi-process API serving** through `--api-server-count`, allowing supported local EngineCore pipelines to share GPU stage engines across frontend workers. **(#6923)**
* Expanded **ComfyUI workflows** for MiniMax-H3 reference-based generation, upscaling, and latent editing, and added a music-generation node with MiniMax Music 3 support. **(#7483, #7472, #7898, #7516)**
* Added **Speech API streaming metrics**, duplex performance metrics, and a LingBot World realtime streaming benchmark. **(#6853, #7714, #7645)**

### Breaking Changes

* **Removed first-party Dynin-Omni and dots.tts support**, including their model registrations, deployment configurations, and examples. **(#7655)**
* **Updated the duplex session protocol.** `/v1/duplex` is now an alias for `/v1/realtime?duplex=1`; `native_duplex` and client-selected IDs for new sessions have been removed. New session IDs are server-assigned. **(#7413, #7647)**
* **Unknown diffusion configuration fields now raise errors** instead of being silently discarded. Supported legacy aliases emit deprecation warnings, and conflicting alias/canonical values are rejected. **(#5172)**

### Note

* Qwen3-TTS **Model Runner V2 remains experimental**. The bundled CUDA profile defaults to V2; other supported backends retain V1. Set `model_runner: v1` to opt out. **(#7930)**
* **AuK support is offline and non-streaming** in this release; an OpenAI Speech API adapter is not included. Breeze-TTS-2 currently supports `cfg_scale=1.0` only. **(#7385, #7084)**
* Multi-process API serving remains **opt-in** and excludes diffusion and remote/headless stages. Native Mooncake KV prefetch is also **opt-in**, with initial support scoped to HunyuanImage3 on CUDA using Mooncake TCP. **(#6923, #7637)**

## What's Changed
* [Refactor] P0.2: Migrate API server helpers out of api_server by @herotai214 in https://github.com/vllm-project/vllm-omni/pull/5453
* [CI] Stabilize Qwen3-Omni Server VAD E2E by @LHXuuu in https://github.com/vllm-project/vllm-omni/pull/7356
* [CI/Build] Diff-aware source_file_dependencies for CUDA/NPU pipelines by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/6597
* [Core][Diffusion] Add a typed pre-D2H video media contract by @NancyFyong in https://github.com/vllm-project/vllm-omni/pull/6615
* [Bugfix] Bound HWR domain initialization lock waits by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/7128
* [Bugfix] Escalate diffusion worker shutdown and retain survivors by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/7126
* [Misc] Add standalone safetensors retention diagnostic by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/7145
* [CI] Isolate layerwise offload memory measurements by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/6938
* [Model] Add Cosmos3 mixed W8A8/W8A16 and W4A4/W4A16 denoising by @wkutak in https://github.com/vllm-project/vllm-omni/pull/6560
* [Test] Use public render_jinja_template in MiniCPM-o native template test by @tlysanhuo in https://github.com/vllm-project/vllm-omni/pull/7362
* [Bugfix] Fix video prewarm cache retention and cancel-restart delay by @psv666 in https://github.com/vllm-project/vllm-omni/pull/7363
* Cosmos3 action policy improvements by @MaciejBalaNV in https://github.com/vllm-project/vllm-omni/pull/6460
* [BugFix][CI] Restore diff-aware source filtering for post-merge L3 by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/7371
* [Bugfix] Fail when a diffusion LoRA adapter binds no layer by @Hiro208 in https://github.com/vllm-project/vllm-omni/pull/7349
* [Bugfix] Fix host-memory leak on aborted /v1/images/generations (#6462) by @zhang-keliang in https://github.com/vllm-project/vllm-omni/pull/6561
* [Refactor] Declare model-local KV held outside the paged manager by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/6171
* [Realtime] Emit current (non-beta) OpenAI audio/transcript event names by @NickCao in https://github.com/vllm-project/vllm-omni/pull/7339
* [Bugfix][Core] Clean up failed HWR atomic metadata writes by @BANANASJIM in https://github.com/vllm-project/vllm-omni/pull/6956
* [Bugfix] Keep MiniMax-H3 reference audio budgets separate by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/7281
* [Bugfix] Fix Helios USP: per-component split for correct sequence parallelism by @yancaocn in https://github.com/vllm-project/vllm-omni/pull/6930
* [Perf][Diffusion] Optimize HSDP startup via Rank-0 shared weight loading and accelerated LoRA delta computation by @SamitHuang in https://github.com/vllm-project/vllm-omni/pull/7005
* [Example] Migrate HunyuanImage-3.0 to model_extras + shared task examples by @suyanli220 in https://github.com/vllm-project/vllm-omni/pull/5559
* [Model] Avoid scalar synchronizations in GLM-Image preparation by @yuweih205 in https://github.com/vllm-project/vllm-omni/pull/7172
* [Model][ERNIE-Image] Delay AdaLN modulation broadcast by @yuweih205 in https://github.com/vllm-project/vllm-omni/pull/7171
* [Kernel][MiniMax-H3] Run Q/K RMSNorm-RoPE in one launch by @yuweih205 in https://github.com/vllm-project/vllm-omni/pull/7167
* [CI][ROCm] Align AMD image with vLLM 0.29 by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/7395
* [Bugfix] Add embed_multimodal to MiniCPM-o 4.5 omni LLM class by @Hiro208 in https://github.com/vllm-project/vllm-omni/pull/7384
* [Model] Add LingBot World Ulysses sequence parallelism by @wtz2333 in https://github.com/vllm-project/vllm-omni/pull/6841
* [Feature][TTS] Add Speech API streaming metrics by @gxxx-hum in https://github.com/vllm-project/vllm-omni/pull/6853
* [Bugfix][Model] Fix FLUX.2 Klein multi-image edit metadata by @kuafou in https://github.com/vllm-project/vllm-omni/pull/7430
* [BugFix] Fix leftovers of the legacy OpenAI realtime API event names by @NickCao in https://github.com/vllm-project/vllm-omni/pull/7426
* [Model] Add Tencent AuK speech generation and editing (encoder + diffusion pipeline) by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/7385
* [XPU][Docker] Align XPU image and CI with vLLM v0.29.0 by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/7441
* [Bugfix] Add explicit error when using CFGP with distilled Cosmos3 models by @MaciejBalaNV in https://github.com/vllm-project/vllm-omni/pull/7427
* [Perf][Diffusion] Run MammothModa2 DiT attention through the shared attention layer by @MrlixiangWE in https://github.com/vllm-project/vllm-omni/pull/7094
* [Bugfix] Give model CLI flags typed owners in the Omni config by @Hiro208 in https://github.com/vllm-project/vllm-omni/pull/7390
* [Bugfix] Require a model for `vllm serve --omni` (fixes #4158) by @abinggo in https://github.com/vllm-project/vllm-omni/pull/4167
* [Bugfix] Send a downstream terminal chunk when a parked stage ends by @psv666 in https://github.com/vllm-project/vllm-omni/pull/6889
* [NPU] upgrade to v0.29.0 by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/7433
* [Bugfix][Model][Lance] Support decoded video frames in video editing by @junpengw67-max in https://github.com/vllm-project/vllm-omni/pull/5128
* [Refactor][Diffusion] Remove model-specific names from LoRA and ModelOpt loader defaults by @congw729 in https://github.com/vllm-project/vllm-omni/pull/5907
* Optimize CosyVoice3 Stage1 flow batching by @gerayking in https://github.com/vllm-project/vllm-omni/pull/4876
* [3/N] Encode streamed video on the worker with bounded batching by @specture724 in https://github.com/vllm-project/vllm-omni/pull/7018
* [Kernel][Boogu-Image] Fuse Q/K RMSNorm + interleaved RoPE via fused_qk_norm_rope by @Holworth in https://github.com/vllm-project/vllm-omni/pull/6982
* [Bugfix][Frontend] Honor output_compression on the image generations route by @hsliuustc0106 in https://github.com/vllm-project/vllm-omni/pull/7447
* [Core] Add NIXL omni connector by @yuanwu2017 in https://github.com/vllm-project/vllm-omni/pull/6093
* [AR-Diffusion] Add session-owned streaming VAE decode by @linzhenpl07 in https://github.com/vllm-project/vllm-omni/pull/6533
* [Perf][Frontend] Chunk in-memory image file responses by @kuafou in https://github.com/vllm-project/vllm-omni/pull/7459
* [Doc][NPU] Keep AllGather for MiniMax-H3 INT8 DLO by @KrystalRay in https://github.com/vllm-project/vllm-omni/pull/7444
* [P0][RFC #3747] RL rollout serving: session management + world_model_env by @Srinivasoo7 in https://github.com/vllm-project/vllm-omni/pull/4770
* [Bugfix][NPU] Materialize causal mask in FlashAttention dense path by @Oliver7th in https://github.com/vllm-project/vllm-omni/pull/7324
* [CI/Build] Align CUDA release image with vLLM 0.29 by @LiquidGunay in https://github.com/vllm-project/vllm-omni/pull/7445
* [Doc] Update vLLM-Omni WeChat QR code by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/7490
* [Frontend] Add ComfyUI FastH3 node, fix t2va aspect ratio and dropped audio by @princepride in https://github.com/vllm-project/vllm-omni/pull/7456
* [CI/Build] Add experimental AMD MI300 nightly lane by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/6978
* [CI/Build] Share nightly CUDA YAML between H100/L4 and B200 by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/7028
* [Performance][MammothModa2] Enable and validate FP8 KV cache for AR stage by @JiahengX in https://github.com/vllm-project/vllm-omni/pull/7436
* [Bugfix] Forward Qwen3-Omni streaming video sampling parameters by @psv666 in https://github.com/vllm-project/vllm-omni/pull/7325
* [Bugfix][MiniCPMO45] Return bare tensor in Thinker forward to fix repetition loop (#7497) by @BeatSeat in https://github.com/vllm-project/vllm-omni/pull/7517
* fix(qwen-image): drop the shadowed dead _get_qwen_prompt_embeds duplicate by @Anai-Guo in https://github.com/vllm-project/vllm-omni/pull/7461
* [Bugfix][Frontend] Preserve duplex chat audio format and duration by @NolenLiang in https://github.com/vllm-project/vllm-omni/pull/7316
* [Model] Add Breeze-TTS-2 two-stage AR TTS support (talker + codec, streaming) by @lzwnoname in https://github.com/vllm-project/vllm-omni/pull/7084
* [Qwen2.5-Omni] Avoid redundant embedding computation by @nodeeeeee in https://github.com/vllm-project/vllm-omni/pull/7477
* [Bugfix][Qwen3-Omni] Fix synchronous Thinker pipeline parallelism by @dshah1333 in https://github.com/vllm-project/vllm-omni/pull/7345
* [Model][MiniMax-H3] Multi-GPU serving fixes and layer-wise offload component selection by @heyuanliu-intel in https://github.com/vllm-project/vllm-omni/pull/7047
* [Bugfix] Allow Fish Speech phoneme-control tokens through normalize_fish_speech_text by @pujitha24 in https://github.com/vllm-project/vllm-omni/pull/7043
* [Bugfix][Hardware][Ascend] Fix Qwen3-TTS code predictor dtype and nested graph replay by @yadongtan in https://github.com/vllm-project/vllm-omni/pull/6639
* [BugFix] Fix importing renamed module vllm.entrypoints.openai.engine.… by @NickCao in https://github.com/vllm-project/vllm-omni/pull/7531
* [Tests] Skip global GPU cleanup for parallel online diffusion tests by @NickCao in https://github.com/vllm-project/vllm-omni/pull/7534
* [Misc][HiggsAudioV3] Diagnose skipped reference audio substitution by @LOGO127 in https://github.com/vllm-project/vllm-omni/pull/7098
* [Model] Stop MiniCPM-o Thinker at TTS boundaries by @vuuihc in https://github.com/vllm-project/vllm-omni/pull/7463
* [Performance] Optimize MammothModa2 AR → DiT hidden-state transfer by @kunkunblueberry in https://github.com/vllm-project/vllm-omni/pull/7102
* [Hardware][Ascend][Model] Support MOSS-TTS-Nano on Ascend A2 by @Big2Wheel in https://github.com/vllm-project/vllm-omni/pull/7192
* [Kernel] Fuse Ming streaming ISTFT overlap-add and normalization by @yashkgp in https://github.com/vllm-project/vllm-omni/pull/7338
* [Bugfix][MiniCPM-o] Attach a unit's whole frame group and size the vision slot budget like Stage0 by @twu3202 in https://github.com/vllm-project/vllm-omni/pull/7271
* [Model] Add VoxCPM2 startup LoRA adapter support by @Bezdarnost in https://github.com/vllm-project/vllm-omni/pull/7108
* [Bugfix][Qwen3-TTS] Gate async-chunk Code2Wav on non_streaming_mode (#4371) by @smartDream-chao in https://github.com/vllm-project/vllm-omni/pull/6898
* [Frontend][Benchmark] Add duplex performance metrics for OmniInteract and Omni-DuplexEval benchmark by @ZacheryAU in https://github.com/vllm-project/vllm-omni/pull/7242
* [Bugfix] Don't shutdown Engine on py_generator=True by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/6334
* [Bugfix] Use current OpenAI audio event names in duplex client metrics by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/7541
* [Refactor][Diffusion] Complete generic backend plan consumption by @specture724 in https://github.com/vllm-project/vllm-omni/pull/7313
* [Bugfix] Restore the async PP sampled-token broadcast in the AR runner by @dshah1333 in https://github.com/vllm-project/vllm-omni/pull/7393
* [CI][ROCm] Add non-blocking engine and model executor GPU coverage by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/7397
* [Frontend] Add MiniMax H3 video upscale workflow (WF-07) by @xuexueligao in https://github.com/vllm-project/vllm-omni/pull/7472
* [Lingbot World] Bound image condition storage and extend temporal RoPE by @wtz2333 in https://github.com/vllm-project/vllm-omni/pull/6838
* [Diffusion][Perf] Add Qwen-Image QK RoPE Triton path by @dongbo910220 in https://github.com/vllm-project/vllm-omni/pull/5931
* [Tests] Test image edit input limits in tiny model framework by @NickCao in https://github.com/vllm-project/vllm-omni/pull/7434
* [Model] Add Gepard-1.0 OpenAI /v1/audio/speech serving by @mjZhaoElaine in https://github.com/vllm-project/vllm-omni/pull/7499
* [Perf][Cosmos3] Add SeaCache support for Cosmos3 by @yzhautouskay in https://github.com/vllm-project/vllm-omni/pull/6922
* [CI][ROCm] Add non-blocking entrypoint GPU coverage by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/7398
* [Bugfix][Core] Keep sample-rate snapshots bounded in delta output by @LOGO127 in https://github.com/vllm-project/vllm-omni/pull/7448
* [NPU][CosyVoice3] Add CPU STFT fallback by @peterDengcx in https://github.com/vllm-project/vllm-omni/pull/7520
* [CI][Bugfix] Update Qwen3-TTS CI Validation Message by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/7276
* [Bugfix] Route Music3 float32 attention to SDPA by @liuyao0322 in https://github.com/vllm-project/vllm-omni/pull/7354
* [Voxtral] Raise BadRequest for ref_audio by @clodaghwalsh17 in https://github.com/vllm-project/vllm-omni/pull/7012
* [Bugfix] Fix Qwen3-Omni streaming crops in mixed-length batches by @dshah1333 in https://github.com/vllm-project/vllm-omni/pull/7340
* [Bugfix] Tolerate a bounded TTS tail in the audio-text similarity gate by @tlysanhuo in https://github.com/vllm-project/vllm-omni/pull/7358
* [Bugfix][Wan2.2] Apply UniPC flow shift once by @HAAZZZEEEE in https://github.com/vllm-project/vllm-omni/pull/7576
* [CI/Build][Hardware][Ascend] Add torchmetrics to the NPU CI image by @GodHu777777 in https://github.com/vllm-project/vllm-omni/pull/7570
* [Bugfix] Align video frame consumption reporting with prompt sampling by @psv666 in https://github.com/vllm-project/vllm-omni/pull/7329
* [Bugfix] Per-key accumulation strategy for Qwen3-TTS codec frame outputs by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/7608
* [Bugfix] Keep async video jobs queued until inference and abort on delete by @ZhengWG in https://github.com/vllm-project/vllm-omni/pull/6759
* [Feature][Qwen3-TTS] Make Code2Wav honor the stage dtype by @gxxx-hum in https://github.com/vllm-project/vllm-omni/pull/6059
* [Diffusion] MAGI-2: regional compile coverage by @cr-gao in https://github.com/vllm-project/vllm-omni/pull/7174
* [Bugfix] Skip generic text-only warmup for DreamZero by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/7548
* [LingBot World] Reuse the text encode for a prompt already encoded by @linzhenpl07 in https://github.com/vllm-project/vllm-omni/pull/6845
* [Core][Frontend] Unified Full-duplex Framework by @chickeyton in https://github.com/vllm-project/vllm-omni/pull/7413
* [Attention] [P1] Keep H3 VSA policy in the model and share sparse primitives by @lishunyang12 in https://github.com/vllm-project/vllm-omni/pull/7535
* [Bugfix][MiniCPM-o] Stabilize code2wav CFM CUDA graph caching with reference audio normalization and mel-frame bucketing by @y-null in https://github.com/vllm-project/vllm-omni/pull/7416
* [Frontend] Add MiniMax-H3 references and Ref2VA workflow by @LinzeShi in https://github.com/vllm-project/vllm-omni/pull/7483
* [feat] Extend disaggregated MiniMax-H3 stage with VAE encoders by @asukaqaq-s in https://github.com/vllm-project/vllm-omni/pull/6939
* [Frontend] Add MiniMax H3 ComfyUI text-to-video workflow (WF-01) by @zhuhu00 in https://github.com/vllm-project/vllm-omni/pull/7423
* [Boogu-Image] Fuse QKV/FFN projections + switch to diffusion RMSNorm by @Bounty-hunter in https://github.com/vllm-project/vllm-omni/pull/6649
* [Diffusion] Fuse Qwen-Image-Edit select01 modulation for CUDA by @dongbo910220 in https://github.com/vllm-project/vllm-omni/pull/5921
* [Bugfix][Omni-DuplexEval] Load local Hugging Face dataset layouts in duplex eval loader by @RyanYun09 in https://github.com/vllm-project/vllm-omni/pull/7331
* [Bugfix] Fail a duplex session that outgrows max_model_len instead of killing the EngineCore by @twu3202 in https://github.com/vllm-project/vllm-omni/pull/7277
* [Perf][CosyVoice3] Bounded-window incremental HiFT vocoder streaming by @timzsu in https://github.com/vllm-project/vllm-omni/pull/7521
* [Bugfix] Preserve benchmark metric sample counts in results by @psv666 in https://github.com/vllm-project/vllm-omni/pull/7624
* [Bugfix][Qwen-Image] Restore RotaryEmbedding CUDA RoPE for Diffusers e2e by @NumberWan in https://github.com/vllm-project/vllm-omni/pull/7513
* [CI][MiniCPM-o] Lower the Daily-Omni accuracy gate to 0.77 by @y-null in https://github.com/vllm-project/vllm-omni/pull/7657
* [Bugfix] Reject failed diffusion benchmark warmups by @yuweih205 in https://github.com/vllm-project/vllm-omni/pull/7092
* [Misc] Remove dead deploy keys from personaplex.yaml by @THUqliu in https://github.com/vllm-project/vllm-omni/pull/7454
* [Bugfix][Qwen3-Omni] Include deferred residual in captured Thinker states by @dshah1333 in https://github.com/vllm-project/vllm-omni/pull/7304
* [BugFix][NPU] Fix Fish Speech S2 Pro NPU support by @KrystalRay in https://github.com/vllm-project/vllm-omni/pull/7546
* [Bugfix][Frontend] Route synthetic aborts through final stage by @CarrotSwordsman in https://github.com/vllm-project/vllm-omni/pull/7006
* Preserve audio boundary embeddings in Qwen2.5-Omni interleaved input by @nodeeeeee in https://github.com/vllm-project/vllm-omni/pull/7510
* [BugFix][TTS] Fix MOSS Realtime serving and generation by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/5661
* [Bugfix] Fix Breeze-TTS-2 repeated silence and audio EOS handling by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/7667
* [Frontend] Add ComfyUI Generate Music node with initial MiniMax Music 3 support by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/7516
* [Bugfix] Fix Qwen3-TTS word timestamps with async chunking by @Bezdarnost in https://github.com/vllm-project/vllm-omni/pull/7544
* [Frontend] Allow explicit turn-based serving by @LinzeShi in https://github.com/vllm-project/vllm-omni/pull/7675
* [Doc] Scope Spark FP8 guidance to the validated revision by @bojiang-li in https://github.com/vllm-project/vllm-omni/pull/7536
* [CI][bugfix] Fix MiniMax H3 FP8 quality test remote-code loading by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/7617
* [Bugfix] Update ComfyUI serving-mode mock after helper rename by @LinzeShi in https://github.com/vllm-project/vllm-omni/pull/7694
* [Hardware][Ascend] Add Wan2.2 MXFP4 UOS, Smooth and W4A8 fallback by @HAAZZZEEEE in https://github.com/vllm-project/vllm-omni/pull/7210
* [Core] Retain structured configs through runtime startup by @maithilijoshi20 in https://github.com/vllm-project/vllm-omni/pull/6849
* [Bugfix][NPU] Fix talker_mtp ACL graph capture missing force_uniform_decode by @Wallbreazzz in https://github.com/vllm-project/vllm-omni/pull/7008
* [Frontend] Scale Omni serving across API processes by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/6923
* [Model][PersonaPlex] Add paced multi-session validation by @LOGO127 in https://github.com/vllm-project/vllm-omni/pull/7428
* [CI] Fix Structured Diffusion Config Wan Test by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/7707
* [Diffusion][Model] Add direct FastH3 8-Step V2 checkpoint loading by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/7610
* [Model][PersonaPlex] add per-row RingKV offsets and active rows by @MrDongsls in https://github.com/vllm-project/vllm-omni/pull/7670
* [Core] Give the OpenAI Realtime wire codec a reusable home (RFC #6592 P0a) by @psv666 in https://github.com/vllm-project/vllm-omni/pull/7640
* [Bugfix][MiniCPM-o] Size the duplex HD slice reservation from the frame by @twu3202 in https://github.com/vllm-project/vllm-omni/pull/7654
* [Voxtral] Follow up to raise BadRequest for ref_audio by @clodaghwalsh17 in https://github.com/vllm-project/vllm-omni/pull/7649
* [Doc][NPU] Refresh MiniMax-H3 Ascend recipes for 0.28-era configurations by @brandneway in https://github.com/vllm-project/vllm-omni/pull/7720
* [Model] Add π0.5 (Pi0.5) VLA model support by @chenchaoxu7575 in https://github.com/vllm-project/vllm-omni/pull/6950
* fix(minicpmo45): deadline-align native duplex silence continuation by @Tiagosf00 in https://github.com/vllm-project/vllm-omni/pull/7059
* [Qwen3-Omni] Remove redundant text embedding in DeepStack path by @howard-shan in https://github.com/vllm-project/vllm-omni/pull/7573
* [Feature][TTS] MOSS-TTS: place the reference-audio encoder on the code2wav stage's GPU by @gcanlin in https://github.com/vllm-project/vllm-omni/pull/7724
* [Frontend] Add a shared realtime web UI for MiniCPM-o and Qwen3-Omni (#7222) by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/7585
* [4/N] Unify worker-side MP4 encoding and wire Wan into it by @specture724 in https://github.com/vllm-project/vllm-omni/pull/7048
* [Kernel] Fuse LongCat paired Q/K RoPE by @dongbo910220 in https://github.com/vllm-project/vllm-omni/pull/7500
* [Bugfix][MAGI-2] Fix layerwise offload OOM by pointing offload block attrs to 'block' (#7523) by @BeatSeat in https://github.com/vllm-project/vllm-omni/pull/7540
* [Diffusion] Fuse ERNIE-Image Q/K RoPE for eager execution by @dongbo910220 in https://github.com/vllm-project/vllm-omni/pull/7502
* [Misc] treewide: remove shm_threshold_bytes from deploy config by @NickCao in https://github.com/vllm-project/vllm-omni/pull/7522
* [XPU][HunyuanImage3] Fix HunyuanImage-3.0 text-to-image on XPU by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/7674
* [Bugfix] Fix Parallel State Initialization For MoE + Diffusion by @alex-jw-brooks in https://github.com/vllm-project/vllm-omni/pull/7676
* [5/N] Schedule chunk transfers as their own stage by @specture724 in https://github.com/vllm-project/vllm-omni/pull/7406
* [Hardware][Ascend] Integrate MindIE dense and sparse quantized attention for Wan2.2 T2V by @De-cs in https://github.com/vllm-project/vllm-omni/pull/7561
* [CI/Build][ROCm] Stabilize shared AMD test lanes by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/7706
* [AR-Diffusion] Bound KV metadata for long rollouts by @wtz2333 in https://github.com/vllm-project/vllm-omni/pull/7498
* [Bugfix][MiniMax-H3] Use Hopper-safe modulation precision by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/7693
* [Bugfix][Ascend NPU][Diffusion] Load over-wide unquantized fallback weights straight into host memory under DLOFix/mxfp online offload after quant by @brandneway in https://github.com/vllm-project/vllm-omni/pull/7009
* [Test][Ascend] Share HunyuanVideo-1.5 E2E across GPU and NPU by @zengchuang-hw in https://github.com/vllm-project/vllm-omni/pull/7547
* [Perf][Diffusion] Activate NPU/GPU matmul for LoRA delta computation when weights are on CPU by @holykie in https://github.com/vllm-project/vllm-omni/pull/7590
* [CI/Build][MiniCPM-o] Fix the Nightly tests by @chickeyton in https://github.com/vllm-project/vllm-omni/pull/7758
* [BugFix][TTS] Restore MOSS v1 codec streaming by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/6420
* [Bugfix][Core] Fix CLI parallel flags losing to nested deploy parallel_config by @zwhzzz0821 in https://github.com/vllm-project/vllm-omni/pull/7786
* [CI/Build] Retarget skipped HiDream and MammothModa2 E2E tests to current issues by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/7755
* [CI][Qwen3-Omni] Compare structured-config sampling defaults against vLLM normalization by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/7742
* [CI][Qwen3-Omni] Keep the deploy-YAML literal in the structured-config sampling check by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/7803
* [Bugfix][Core] Apply Realtime item truncation once per command by @NolenLiang in https://github.com/vllm-project/vllm-omni/pull/7800
* [XPU][Bugfix] Make AR-Diffusion KV preallocation device-agnostic by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/7777
* [Model] Migrate MammothModa2 DiT to the shared diffusion runtime by @Levius-Fubuki in https://github.com/vllm-project/vllm-omni/pull/7134
* [XPU][CI] Drop the USTC PyPI mirror from the XPU image build by @Joshna-Medisetty in https://github.com/vllm-project/vllm-omni/pull/7808
* [CI/Build] Restrict ERNIE fused RoPE tests to NVIDIA CUDA by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/7771
* [Refactor][Diffusion] Resolve distributed layerwise topology in the plan by @specture724 in https://github.com/vllm-project/vllm-omni/pull/7326
* [Core] Refactor omni prefix cache into Manager/Controller by @ZhengWG in https://github.com/vllm-project/vllm-omni/pull/6654
* [Bugfix] Use monotonic clocks for test server startup timeouts by @psv666 in https://github.com/vllm-project/vllm-omni/pull/7628
* [Refactor] Reject unknown diffusion config fields by @TaffyOfficial in https://github.com/vllm-project/vllm-omni/pull/5172
* [Model] Add circlestone-labs/Anima by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/4083
* [Bugfix]Include Reference Audio Cache Salt for HiggsAudio v2 by @sphinxkkkbc in https://github.com/vllm-project/vllm-omni/pull/7826
* [Bugfix][Qwen-Image] Keep AutoRound W4A16 on CPU when offloading; Fixes #7555 by @NumberWan in https://github.com/vllm-project/vllm-omni/pull/7579
* [Bugfix][Test] Assert stable-audio CPU offload savings on max_memory_allocated by @IneshReddy249 in https://github.com/vllm-project/vllm-omni/pull/6826
* [Bugfix] Register statistics for dynamically added replicas by @leegangtoe in https://github.com/vllm-project/vllm-omni/pull/7298
* fix(e2e): re-point HunyuanImage3 offline test to text_to_image.py by @chethanuk in https://github.com/vllm-project/vllm-omni/pull/7525
* [CI/Build][ROCm] Cache AMD test images in registry by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/7712
* [Bugfix][RAINFUSION_ATTN] Fix padding-mask rejection on packed [real, pad] layouts and reuse query tail as output padding by @brandneway in https://github.com/vllm-project/vllm-omni/pull/7235
* [Perf][MiniMax-H3] Cut video VAE encode/decode memory peaks for low-memory serving by @brandneway in https://github.com/vllm-project/vllm-omni/pull/7241
* [Hardware][Ascend] Enable VoxCPM2 eager optimizations by @Big2Wheel in https://github.com/vllm-project/vllm-omni/pull/7207
* [Bugfix] Avoid multimodal cache collisions in multistage image editing by @princepride in https://github.com/vllm-project/vllm-omni/pull/7817
* [Model][Frontend] MiniMax-H3: Add latent-mask editing by @xiaoyu-xyz in https://github.com/vllm-project/vllm-omni/pull/7465
* [Bugfix] Stabilize NIXL ownership test claim queries by @zengchuang-hw in https://github.com/vllm-project/vllm-omni/pull/7870
* [Misc] Remove Dynin-Omni and dots.tts support by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/7655
* [Bugfix] Honor request-level seed in VoxCPM2 CFM noise by @tlysanhuo in https://github.com/vllm-project/vllm-omni/pull/7866
* [Benchmark][MiniCPM-o] Port Video-MME dataset support to Omni bench s… by @amy-why-3459 in https://github.com/vllm-project/vllm-omni/pull/6987
* [Refactor][Diffusion] Move single-model layers into their model directories by @congw729 in https://github.com/vllm-project/vllm-omni/pull/5908
* [Hardware][Ascend] Use incremental KV-cache decode for MOSS-TTS depth transformer by @jingchengtian in https://github.com/vllm-project/vllm-omni/pull/6967
* [Bugfix] Avoid waveform-list GC scans and release completed MOSS batches by @gcanlin in https://github.com/vllm-project/vllm-omni/pull/7885
* [Bugfix] Replace ffmpeg subprocess with PyAV to avoid HEVC decoder hang (#7364) by @RyanYun09 in https://github.com/vllm-project/vllm-omni/pull/7504
* [Bugfix] Fix Qwen3-Omni realtime playback interruption and conversation history by @psv666 in https://github.com/vllm-project/vllm-omni/pull/7791
* [Feat] Add native Mooncake KV transfer from AR to DiT by @asukaqaq-s in https://github.com/vllm-project/vllm-omni/pull/7166
* [Bugfix] Route text-only chat as per-request comprehension in HunyuanImage3 AR sampler by @MrlixiangWE in https://github.com/vllm-project/vllm-omni/pull/6111
* [Model] Add MiniMax-H3 long-video latent continuation with driving audio by @princepride in https://github.com/vllm-project/vllm-omni/pull/7838
* [Core][Diffusion] Camera interaction for diffusion streaming generation (LingBot World 2 as example) by @fhfuih in https://github.com/vllm-project/vllm-omni/pull/7198
* [Performance] Capture MOSS-TTS codec streaming decode with NPUGraph by @Wallbreazzz in https://github.com/vllm-project/vllm-omni/pull/7280
* feat(comfyui): add MiniMax H3 first and last frame inputs by @avraichur96 in https://github.com/vllm-project/vllm-omni/pull/7449
* [Model] Add online FP8 support for Boogu-Image MLLM by @Dmaner in https://github.com/vllm-project/vllm-omni/pull/7342
* [Core][Model] Enable Qwen3-TTS MRV2 and optimize the TTS pipeline by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/7781
* [LingBot World] Eleven bit-identical removals of repeated work in the realtime path by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/7648
* [Bugfix] Honor the requested output canvas in BAGEL img2img by @nussejzz in https://github.com/vllm-project/vllm-omni/pull/7287
* [Bugfix][MiniMax-H3] Fix Hopper keyframe and modulation precision by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/7913
* [Bugfix][Engine] Preserve text_encoder_tp_size in OmniEngineArgs by @CarrotSwordsman in https://github.com/vllm-project/vllm-omni/pull/7652
* [Feature] Add experimental LingBot World last-step KV reuse by @wtz2333 in https://github.com/vllm-project/vllm-omni/pull/7816
* [LingBot World] Shard the streaming VAE decode across the Ulysses ranks by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/7651
* [Test] add stability test case for High-priority model by @zhumingjue138 in https://github.com/vllm-project/vllm-omni/pull/7571
* [Model] Enable online FP8 linears for LingBot World by @tsinghua-code in https://github.com/vllm-project/vllm-omni/pull/7549
* [Frontend] Add MiniMax-H3 latent editing workflows (WF-05) by @FayeSpica in https://github.com/vllm-project/vllm-omni/pull/7898
* [Benchmark] Add LingBot-World realtime streaming benchmark by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/7645
* [Doc] Update vLLM-Omni WeChat QR code by @david6666666 in https://github.com/vllm-project/vllm-omni/pull/7911
* [CI/Build] Promote LingBot-Video dense smoke to ready/merge and wire L4 expansion by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/7892
* [BugFix] Fix diffusion TTS voice error responses by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/7798
* [Bugfix] Preserve NextStep rectangular latent dimensions by @0z5a in https://github.com/vllm-project/vllm-omni/pull/7853
* [Bugfix] Isolate weekly CPU tests from inherited attention env and hf_api mocks by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/7565
* [Bugfix] Refresh duplex client defaults after session updates by @wuli666 in https://github.com/vllm-project/vllm-omni/pull/7784
* [Model] Integrate AURA into Full-Duplex Runtime by @NumberWan in https://github.com/vllm-project/vllm-omni/pull/7633
* [Core][Diffusion] Add pause_generation(mode="keep") for diffusion stages by @cr-gao in https://github.com/vllm-project/vllm-omni/pull/7685
* [Model] Default Qwen3-TTS to experimental Model Runner V2 by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/7930
* [Perf][Qwen3-TTS] Enable event-driven orchestration by default by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/7088
* [Bugfix] Keep --no-guardrails out of diffusion stage config by @Levius-Fubuki in https://github.com/vllm-project/vllm-omni/pull/7917
* [tts][feature][NPU] Add 2-NPU and 3-NPU disaggregated deploy profiles for MOSS-TTS-Local by @jingchengtian in https://github.com/vllm-project/vllm-omni/pull/7052
* [Model] MammothModa2: enable Cache-DiT acceleration for the DiT stage by @shihongzhi in https://github.com/vllm-project/vllm-omni/pull/7291
* [Bugfix] Add opt-in MiniCPM-o 4.5 Stage-0 sliding window by @0z5a in https://github.com/vllm-project/vllm-omni/pull/7631
* [Misc] Deprecate VLLM_OMNI_VOXCPM_CODE_PATH by @armaanamatya in https://github.com/vllm-project/vllm-omni/pull/7779
* [CI][ROCm] Shorten the blocking CosyVoice test path by @andyluo7 in https://github.com/vllm-project/vllm-omni/pull/7748
* [Misc] Refactor static stage metadata lookups by @NickCao in https://github.com/vllm-project/vllm-omni/pull/7602
* [Bugfix] Catch asyncio.TimeoutError so duplex serving starts on Python 3.10 by @twu3202 in https://github.com/vllm-project/vllm-omni/pull/7412
* [Frontend] Reject built-in name collisions in voice upload and add VLLM_OMNI_SPEAKER_REGISTRATION_POLICY by @hoseung2 in https://github.com/vllm-project/vllm-omni/pull/6848
* [Frontend] Remove obsolete experimental duplex client parameters by @natureofnature in https://github.com/vllm-project/vllm-omni/pull/7647
* [Bugfix] Reject stray <|AUDIO|> placeholder with use_audio_in_video in Qwen2.5-Omni by @LiRunGuo in https://github.com/vllm-project/vllm-omni/pull/7959
* [Bugfix][Model] Fix CoVo-Audio prompt processing and dummy loading by @jeffaa729 in https://github.com/vllm-project/vllm-omni/pull/7909
* [Bugfix][TTS] Fix Audio8 voice clone reference resolution by @liuyihua95 in https://github.com/vllm-project/vllm-omni/pull/7815
* [Core] Optimize Qwen2.5-Omni Token2Wav buffer loading by @akshatvishu in https://github.com/vllm-project/vllm-omni/pull/7061
* [Bugfix] Fix GLM-TTS DiT float32 crash with flash-attn backends by @Sworol in https://github.com/vllm-project/vllm-omni/pull/7756
* [CI][Perf] migrate diffusion DFX benches to vllm bench serve --omni by @yenuo26 in https://github.com/vllm-project/vllm-omni/pull/7737
* [Doc][skip ci] Add design doc for scheduler-managed diffusion paged KV cache by @Acerak01-fy in https://github.com/vllm-project/vllm-omni/pull/6891
* [Misc] Add portable MiniMax H3 skills by @princepride in https://github.com/vllm-project/vllm-omni/pull/7923
* [Model] Reduce MOSS TTS reference audio preparation overhead by @Sy0307 in https://github.com/vllm-project/vllm-omni/pull/7725
* [CI] Count VLLM_OMNI_SPEAKER_REGISTRATION_POLICY in the inventory snapshot by @armaanamatya in https://github.com/vllm-project/vllm-omni/pull/7977
* [Bugfix] Keep resumable duplex prompts out of async-chunk prewarm by @twu3202 in https://github.com/vllm-project/vllm-omni/pull/7992
* [CI/Build] Give diffusion CPU tests more timeout headroom by @cr-gao in https://github.com/vllm-project/vllm-omni/pull/7983
* [Bugfix] Stabilize NIXL manager receiver tests by @cr-gao in https://github.com/vllm-project/vllm-omni/pull/7984
* [Feat] Add prefetch for Mooncake cross-stage paged KV transfer in HunyuanImage3 by @Acerak01-fy in https://github.com/vllm-project/vllm-omni/pull/7637
* [Frontend][Benchmark] Add duplex performance metrics to refactored full-duplex framework by @ZacheryAU in https://github.com/vllm-project/vllm-omni/pull/7714
* [CI] Bump the public env var snapshot count after #6848 landed by @linyueqian in https://github.com/vllm-project/vllm-omni/pull/7964
* [CI][Voxtral] Resolve failing test_prepare_speech_generation_awaits_voxtral_async  by @clodaghwalsh17 in https://github.com/vllm-project/vllm-omni/pull/7601
* [Bugfix] Mark Omni chat benchmark streams with error events as failed by @Levius-Fubuki in https://github.com/vllm-project/vllm-omni/pull/8000
* [Bugfix] Restore GLM-Image unshifted timesteps after set_timesteps by @cs-fisha in https://github.com/vllm-project/vllm-omni/pull/7953
* [Bugfix] Mark image edit benchmark stream errors as failed by @Levius-Fubuki in https://github.com/vllm-project/vllm-omni/pull/8015
* [Doc] Correct the SessionClosed admission-slot guarantee (#7636 Issue 22) by @yanbao1217 in https://github.com/vllm-project/vllm-omni/pull/7869
* [Rebase] Rebase to vLLM 0.30.0 by @tzhouam in https://github.com/vllm-project/vllm-omni/pull/7820

## New Contributors
* @yancaocn made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6930
* @kuafou made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7430
* @junpengw67-max made their first contribution in https://github.com/vllm-project/vllm-omni/pull/5128
* @gerayking made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4876
* @Holworth made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6982
* @yuanwu2017 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6093
* @Srinivasoo7 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/4770
* @Oliver7th made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7324
* @LiquidGunay made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7445
* @JiahengX made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7436
* @NolenLiang made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7316
* @lzwnoname made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7084
* @nodeeeeee made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7477
* @yadongtan made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6639
* @vuuihc made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7463
* @Big2Wheel made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7192
* @Bezdarnost made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7108
* @xuexueligao made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7472
* @yzhautouskay made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6922
* @peterDengcx made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7520
* @GodHu777777 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7570
* @LinzeShi made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7483
* @zhuhu00 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7423
* @RyanYun09 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7331
* @THUqliu made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7454
* @chenchaoxu7575 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6950
* @Tiagosf00 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7059
* @howard-shan made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7573
* @De-cs made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7561
* @holykie made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7590
* @Levius-Fubuki made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7134
* @leegangtoe made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7298
* @chethanuk made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7525
* @xiaoyu-xyz made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7465
* @avraichur96 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7449
* @tsinghua-code made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7549
* @shihongzhi made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7291
* @armaanamatya made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7779
* @hoseung2 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/6848
* @LiRunGuo made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7959
* @jeffaa729 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7909
* @liuyihua95 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7815
* @Sworol made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7756
* @cs-fisha made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7953
* @yanbao1217 made their first contribution in https://github.com/vllm-project/vllm-omni/pull/7869

**Full Changelog**: https://github.com/vllm-project/vllm-omni/compare/v0.29.0rc1...v0.30.0rc1