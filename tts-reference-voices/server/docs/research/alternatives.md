# Research: alternatives

_Alternatives to vLLM-Omni for serving Qwen3-TTS-12Hz-1.7B-Base (voice clone, ICL + x-vector) with high concurrency on RTX 3090 (sm_86), plus Higgs TTS 3 serving and gateway abstraction_

Produced 2026-09-24 by a research subagent (workflow wf_6c83c01a-7e3). Confidence: verified-source = read in the
package source; verified-doc = official docs/issue text; reported = third-party claim; unverified = not checked.
Scratch artifacts referenced below lived under /tmp/claude-1013/.../scratchpad/research/ (copied to docs/research/artifacts/ where small).

## Findings

### 1. Top 3 to benchmark against vLLM-Omni, in order: (1) SGLang-Omni 0.1.6. It has continuous batching, CUDA graphs…

**Confidence:** verified-source

Top 3 to benchmark against vLLM-Omni, in order: (1) SGLang-Omni 0.1.6. It has continuous batching, CUDA graphs, streaming, ICL and x-vector cloning, per-request repetition_penalty/seed/temperature/top_k/top_p, 503 admission control, an X-Finish-Reason header, a /v1/audio/voices API with the same shape as vLLM-Omni's, and it is Boson's named engine for Higgs TTS 3. (2) faster-qwen3-tts 0.4.0. It is the fastest single stream and supports precomputed prompts, which the averaged speaker embedding needs, but it runs batch 1, so concurrency needs replicas. (3) qwentts.cpp. It is a GGML C++ server with frame-boundary continuous batching, per-request repetition_penalty and seed, speaker-embedding upload, language=auto, and Q8_0/Q4_K_M precision. Runner-up: VoxServe. Control: official qwen-tts 0.1.1.

**Evidence:** This ranking is my synthesis of the findings below. SGLang-Omni: wheel sglang_omni-0.1.6 serve/protocol.py:325-372, serve/openai_api.py:328-349 and 1353. faster-qwen3-tts: README 237-246 and 491-556 (v0.4.0). qwentts.cpp: src/qwen.h:133-143, src/qwen.cpp:366-404, README 131-157 (HEAD 6a3e912, 2026-09-24).

### 2. vLLM-Omni 0.28.0 has no per-request repetition_penalty. The speech request model is a plain pydantic BaseModel…

**Confidence:** verified-source

vLLM-Omni 0.28.0 has no per-request repetition_penalty. The speech request model is a plain pydantic BaseModel, so a top-level repetition_penalty is silently dropped. extra_params only overrides temperature, top_p and top_k. The penalty is fixed at 1.05 in the deploy YAML. So 'bench_tts.py --param repetition_penalty=X' against vLLM-Omni has no effect and raises no error. Each penalty value needs its own deploy config and restart, and a retry policy can only change seed (and temperature, top_k, top_p).

**Evidence:** vllm_omni-0.28.0 wheel: entrypoints/openai/protocol/audio.py:57-191 (class OpenAICreateSpeechRequest(BaseModel), no ConfigDict, no repetition_penalty field). api_server.py:1334-1346 (create_speech(request: OpenAICreateSpeechRequest)). serving_speech.py:3089-3094 (loops only over 'temperature','top_p','top_k'). deploy/qwen3_tts.yaml:86 'repetition_penalty: 1.05'. tts_adapters/qwen3_tts.py:235-330 only changes max_tokens. I did not check whether vLLM core's sampler reads extra_args.

### 3. vLLM-Omni 0.28.0 accepts a request-level speaker_embedding, but it forces x_vector_only_mode=True. An averaged…

**Confidence:** verified-source

vLLM-Omni 0.28.0 accepts a request-level speaker_embedding, but it forces x_vector_only_mode=True. An averaged embedding therefore can't be combined with ICL there. faster-qwen3-tts, qwentts.cpp (spk_b64 upload) and official qwen-tts (VoiceClonePromptItem) can all combine an embedding with ICL codes.

**Evidence:** vllm_omni-0.28.0 tts_adapters/qwen3_tts.py:90-98. faster-qwen3-tts README 491-556 and model.py:295-415. qwentts.cpp src/tts-server.h:460-486. qwen_tts 0.1.1 inference/qwen3_tts_model.py:40-51.

### 4. SGLang-Omni 0.1.6 honours per-request sampling for Qwen3-TTS: explicitly set fields are recorded and passed th…

**Confidence:** verified-source

SGLang-Omni 0.1.6 honours per-request sampling for Qwen3-TTS: explicitly set fields are recorded and passed through. Its payload fields (task_type, language, ref_audio as a data URL, ref_text, response_format, seed, x_vector_only_mode, max_new_tokens) match bench_tts.py, and unknown fields like stream_format are ignored. Streaming needs stream=true together with response_format=pcm. Uploaded references must be 1-30 s, so the 39.2 s shehbaz higgs-v3.wav can't be registered, while the 28.0 s and 23.2 s Qwen references fit. Defaults in 0.1.6 are max_running_requests 16, max_queued_requests 16 and mem_fraction_static 0.85; the last must be lowered on shared GPUs.

**Evidence:** sglang_omni-0.1.6: serve/speech_service.py:807-834, models/qwen3_tts/request_builders.py:622-652, serve/speech_voices.py:33-34 and 444-451, models/qwen3_tts/engine_builder.py:99-111, utils/audio.py:259. Cookbook docs/cookbook/qwen3_tts.md (main) lines 122-135 and 361-462. I measured the reference durations locally with the wave module.

### 5. Nobody has validated SGLang-Omni on an RTX 3090. The consumer-GPU roadmap targets the RTX 4090 and 5090 only.…

**Confidence:** verified-doc

Nobody has validated SGLang-Omni on an RTX 3090. The consumer-GPU roadmap targets the RTX 4090 and 5090 only. The merged 4090 profile (PR #1156, 0.6B Base, max_running 8, mem 0.75, peak about 20 GiB) is called 'an experimental Functional profile'. The stack is heavy: torch 2.13, cu130 flashinfer, flash-attn-4, nixl-cu13, mooncake-cuda13; Docker is recommended and UCX 1.20 is listed for manual installs. The Base path is known to be slow at high concurrency: RFC #2146 says 'Mean TTFP exceeds one second starting at concurrency 24', and 0.6B Base at c16 on an H200 had a per-request RTF of 1.51.

**Evidence:** https://github.com/sgl-project/sglang-omni/issues/1120, https://github.com/sgl-project/sglang-omni/pull/1156, https://github.com/sgl-project/sglang-omni/issues/2146. sglang_omni-0.1.6 dist-info METADATA Requires-Dist. docs/get_started/installation.md:17-54 and 125-142. docs/cookbook/qwen3_tts.md:251-279 and 538-558.

### 6. faster-qwen3-tts 0.4.0 (MIT, CUDA graphs over a static KV cache) runs one request at a time. Its static buffer…

**Confidence:** verified-source

faster-qwen3-tts 0.4.0 (MIT, CUDA graphs over a static KV cache) runs one request at a time. Its static buffers have shape (1,1,hidden), generate_voice_clone takes a single string, and the example OpenAI server serialises requests behind a global threading.Lock. Published speeds for 1.7B with streaming chunk 8: RTX 4090 4.22x realtime at 174 ms TTFA, H100 3.30x at 241 ms, T4 0.925x at 1096 ms. It takes per-call temperature, top_k, top_p and repetition_penalty. Issue #80 about batch generation is still open.

**Evidence:** repos/andimarafioti_faster-qwen3-tts at v0.4.0: faster_qwen3_tts/talker_graph.py:26-52, model.py:808-830, examples/openai_server.py:71 and 181, README 237-246 (its 'RTF' is audio/compute). https://github.com/andimarafioti/faster-qwen3-tts/issues?q=batch

### 7. qwentts.cpp batches continuously: a worker admits queued jobs into free slots at frame boundaries, up to --max…

**Confidence:** verified-source

qwentts.cpp batches continuously: a worker admits queued jobs into free slots at frame boundaries, up to --max-batch (default 1). Its OpenAI server takes per-request seed, max_new_tokens, temperature, top_k, top_p and repetition_penalty, streams s16le when response_format=pcm, and registers voices from wav_b64 or a precomputed spk_b64/rvq_b64 plus ref_text. It has no inline ref_audio per request. language 'auto' sends no language id, which is the Urdu path. It offers BF16, Q8_0 and Q4_K_M. It publishes no GPU throughput numbers. It should build here: cmake 3.28.3, g++ 13.3 and CUDA 12.8 are installed.

**Evidence:** repos/ServeurpersoCom_qwentts.cpp: src/qwen.h:133-143, src/qwen.cpp:366-372 and 396-404, tools/tts-server.cpp:53 and 98-119, src/tts-server.h:182-237 and 460-486, src/prompt-builder.h:415-424, README 24-25, 59 and 131-157. I checked the toolchain with 'which cmake g++ ninja' and 'ls /usr/local'.

### 8. In an independent H100 comparison (Qwen3-TTS 1.7B CustomVoice, not Base; streaming; open-loop Poisson; all eng…

**Confidence:** reported

In an independent H100 comparison (Qwen3-TTS 1.7B CustomVoice, not Base; streaming; open-loop Poisson; all engines tuned or patched), vLLM-Omni was the strongest public engine. p95 TTFA was 56.8 ms at 1 RPS and 93.5 ms at 6 RPS, and it sustained 20 RPS (396.9 ms). M* sustained 12 RPS, SGLang-Omni 12 RPS (120.9 ms at 1 RPS, 273.7 ms at 6, 2381.7 ms at 12), and VoxServe 8 RPS (49.3 ms at 1, 363.2 ms at 6, 3205.9 ms at 8). It is unknown whether the ranking holds for Base ICL on sm_86.

**Evidence:** repos/nari-labs_benchmarks/reports/Qwen3-TTS-1.7B-CustomVoice/{vLLM-Omni,SGLang-Omni,VoxServe,MStar}/README.md (2026-08-20). https://narilabs.com/blog/qwen3-tts-speed-cost-frontier/

### 9. VoxServe (runner-up) supports Base ICL only through multipart /generate. Its /v1/audio/speech forwards voice,…

**Confidence:** verified-source

VoxServe (runner-up) supports Base ICL only through multipart /generate. Its /v1/audio/speech forwards voice, language and cfg_alpha, with no reference audio. Sampling, including repetition_penalty, is a server-wide CLI flag. The reference is written to disk and re-processed on every request. It has been stale since 2026-06-20.

**Evidence:** repos/vox-serve_vox-serve at ce212de: vox_serve/launch.py:43-107, 252-257, 801-860 and 914-972; vox_serve/model/qwen3_tts.py:1178-1186.

### 10. Official qwen-tts 0.1.1 has no audio streaming ('non_streaming_mode … only simulates streaming text input'). I…

**Confidence:** verified-source

Official qwen-tts 0.1.1 has no audio streaming ('non_streaming_mode … only simulates streaming text input'). It batches statically (left-padded HF generate), and sampling is shared by the whole call. On an RTX 3090, 1.7B CustomVoice at batch 1 measured compute/audio RTF 0.97, or 0.87 with FlashAttention-2. A vLLM-Omni build from Jan 2026 measured 0.83 on the same card; those vLLM-Omni numbers are stale.

**Evidence:** repos/QwenLM_Qwen3-TTS: qwen_tts/inference/qwen3_tts_model.py:287-354 and 513-515; core/models/modeling_qwen3_tts.py:2241-2254. The PyPI 0.1.1 wrapper is identical to GitHub main (diffed). groxaxo/Qwen3-TTS-Openai-Fastapi BENCHMARK_RESULTS.md, read via git show HEAD (Jan 25, 2026).

### 11. Rejected, with the reason for each. nari-qwen3-tts refuses to start without an H100, uses FP8 DeepGEMM, and se…

**Confidence:** verified-source

Rejected, with the reason for each. nari-qwen3-tts refuses to start without an H100, uses FP8 DeepGEMM, and serves CustomVoice only. nano-qwen3tts-vllm has no LICENSE file and no repetition penalty, and its author moved the work to vLLM-Omni. qwen3-tts-fast-serve hard-codes temperature 0.8 and repetition_penalty 1.05 and post-processes audio, though it gives an RTX 3090 data point: 0.6B Base at batch 40 reaches about 12x realtime in aggregate. concurrent-faster-qwen3-server has no 'auto' language (so no Urdu) and forces an ICL repetition penalty of at least 1.3. X-Square Qwen3TTS-Streaming needs Docker and marks ICL experimental. TensorRT-LLM support was closed as not planned. TensorRT Edge-LLM is batch 1 and CLI only. LMDeploy lists no TTS models. M* has no Qwen3-TTS in its README, so Base support is unverified.

**Evidence:** nari src: serve.py:151, model/checkpoint.py:321-322, config.py:9. nano: sampling_params.py (no penalty field), no LICENSE file. fast-serve: qwen3_tts_engine/interface.py:778-964 and README 35-81. alfonsodg: server/src/main.rs:153-163, vendor/qwen3-tts-rs/src/lib.rs:975-978 and 2297. X-Square README 25-27 and 205-216. https://github.com/NVIDIA/TensorRT-LLM/issues/11118. https://nvidia.github.io/TensorRT-Edge-LLM/latest/user_guide/examples/tts.html. https://lmdeploy.readthedocs.io/en/latest/supported_models/supported_models.html

### 12. Both engines can serve Higgs TTS 3. SGLang-Omni is the stack named first on the model card, and vLLM-Omni 0.28…

**Confidence:** verified-source

Both engines can serve Higgs TTS 3. SGLang-Omni is the stack named first on the model card, and vLLM-Omni 0.28.0 ships Higgs v3 deploy profiles and a TTS adapter whose only per-request override is max_new_tokens. The model id is bosonai/higgs-tts-3-4b; the old id higgs-audio-v3-tts-4b redirects with HTTP 307. The license is Research and Non-Commercial: 'Production, hosted APIs, embedding in a product/service … requires a separate commercial license.' I found no server-side sentence splitting in the SGLang-Omni 0.1.6 Higgs code, so the gateway must split text for the roughly 30 s ceiling. The two SGLang-Omni docs disagree on the Higgs streaming format (raw PCM vs SSE with base64 WAV). The SGLang Higgs default temperature is 1.0, while NOTES used 0.8.

**Evidence:** HF API: models/bosonai/higgs-tts-3-4b (license:other, lastModified 2026-09-04); huggingface.co/bosonai/higgs-tts-3-4b/raw/main/README.md lines 2-4, 124, 357-383, 416-437, 516-535 and 570-576. vllm_omni-0.28.0: deploy/README_higgs_audio_v3.md, deploy/higgs_multimodal_qwen3*.yaml, tts_adapters/higgs_audio_v3.py:18-47. sglang-omni docs/cookbook/higgs_tts.md:8, 165-207, 257-292, 557-596. sglang_omni-0.1.6 models/higgs_tts/* (searched for split, sentence and turn).

### 13. An engine-swappable gateway needs a capability record for each engine and model covering: request mapping (ref…

**Confidence:** verified-source

An engine-swappable gateway needs a capability record for each engine and model covering: request mapping (ref_audio/ref_text vs references[]; sampling at top level, in extra_params, or in the deploy config); voice-store rules (inline allowed or not, 30 s upload limit, whether an embedding can be supplied, reference file per model); one normalised streaming format with a single TTFA definition; handling of inline tags (Higgs uses them, Qwen Base reads them aloud); language mapping (Auto for Urdu on Qwen, native on Higgs); sentence segmentation with crossfade and per-segment retry for Higgs; a length cap per codec frame rate (12.5 Hz vs 25 fps); finish-reason and retry signals (seed, plus repetition_penalty only where it works per request); explicit sampling defaults for each model; health, admission and memory-fraction knobs for shared GPUs; license and consent gating. Two existing projects show usable backend interfaces: groxaxo's api/backends/base.py and fr820's src/tts_server/backends/base.py.

**Evidence:** This is my synthesis of the evidence above. repos/groxaxo_Qwen3-TTS-Openai-Fastapi api/backends/base.py (read via git show HEAD). repos/fr820_tts-server src/tts_server/backends/base.py:21-68.

## Risks

- The GPUs are occupied by other people's production services. SGLang-Omni (mem_fraction_static defaults to 0.85 in 0.1.6) and vLLM-Omni both reserve a fraction of total VRAM at startup, so they need explicit low fractions and enough free memory, or they fail to start or OOM other tenants. Adding faster-qwen3-tts replicas also adds about 4-6 GB each (an UNVERIFIED estimate).
- SGLang-Omni on sm_86 is unvalidated. The consumer-GPU roadmap covers only the 4090 and 5090. The cu130/torch-2.13/flash-attn-4/nixl/mooncake stack is heavy, Docker (recommended) isn't available here, and UCX may be needed. My pip dry-run failed twice on flaky downloads, so whether it resolves is unknown. The install could eat the time budget: time-box it and fall back to VoxServe.
- Benchmark validity: bench_tts.py '--param repetition_penalty=...' is silently ignored by vLLM-Omni 0.28.0. The Urdu repetition-penalty sweep on vLLM-Omni needs a separate deploy YAML and restart per value, or the results will be mislabelled.
- Streaming TTFA isn't comparable across engines unless it is measured the same way. SGLang-Omni needs response_format=pcm to stream. vLLM-Omni uses stream_format audio or sse. The Higgs docs disagree between raw PCM and SSE. Some engines trim leading silence and others don't (nari measured 'audible' TTFA).
- The Higgs TTS 3 license is non-commercial. Putting it behind a production or hosted API needs a separate commercial license from Boson AI.
- faster-qwen3-tts appends 0.5 s of silence to references by default. It also computes over a static cache, which is not bit-identical to upstream. Quality comparisons should either set append_silence=False or record the setting.
- qwentts.cpp is maintained by one person, publishes no GPU batch numbers, and its GGML CUDA kernels may lag cuBLAS bf16 at high batch. Its quantised variants need their own WER and similarity checks, especially for Urdu.
- The H100 CustomVoice results from nari may not carry over to Base ICL on an RTX 3090. Base adds reference prefill and encode cost, which is where SGLang-Omni reports TTFP above 1 s at c≥24.
- The full findings could not be saved as FINDINGS.md: the harness blocks subagents from writing report files. The material is in this structured output only.

## Open questions

- Does SGLang-Omni 0.1.6 install and run on an RTX 3090 (sm_86) with the cu130 wheels, without Docker or a system UCX? Which attention backend does it pick automatically on sm_86?
- Can SGLang-Omni accept a precomputed or averaged speaker embedding over HTTP? SpeechReference has vq_codes but no embedding field.
- What throughput, latency and quality does qwentts.cpp reach at --max-batch 8, 16 and 32 on sm_86 in BF16, Q8_0 and Q4_K_M? Does it match upstream WER and speaker similarity on Urdu?
- How much VRAM does one faster-qwen3-tts 1.7B replica use, what is its single-stream xRT and TTFA on a 3090 (vs 4.22x and 174 ms on a 4090), and how many replicas fit next to the other tenants?
- Does M* support Qwen3-TTS Base voice cloning? GitHub API rate limiting blocked the tree listing.
- Could vLLM core's sampler ever honour repetition_penalty passed through extra_params/extra_args for vLLM-Omni Qwen3-TTS? I only searched vllm_omni.
- What streaming format does SGLang-Omni actually use for Higgs: raw PCM (cookbook) or SSE with base64 WAV (model card)? Does SGLang-Omni or vLLM-Omni split long text server-side for Higgs to get around the roughly 30 s ceiling?
- Does SGLang-Omni's Qwen3 prompt builder treat 'Auto' and 'auto' the same? It passes the language string through normalize_language unchanged.
