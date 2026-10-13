# Research: omni-source

_vLLM-Omni Qwen3-TTS serving path read from source: vllm-omni 0.28.0 (stable) vs 0.30.0rc1. Wheels unpacked under research/omni-source/src28 and src30, GitHub tag trees under gh-v0.28.0 and gh-v0.30.0rc1, pip dry-run resolutions in report28.json and report30.json. Nothing was run on a GPU._

Produced 2026-09-24 by a research subagent (workflow wf_6c83c01a-7e3). Confidence: verified-source = read in the
package source; verified-doc = official docs/issue text; reported = third-party claim; unverified = not checked.
Scratch artifacts referenced below lived under /tmp/claude-1013/.../scratchpad/research/ (copied to docs/research/artifacts/ where small).

## Findings

### 1. Install: vllm-omni declares NO dependency on vllm. The version must match vLLM's major.minor: vllm 0.28.x with…

**Confidence:** verified-source

Install: vllm-omni declares NO dependency on vllm. The version must match vLLM's major.minor: vllm 0.28.x with vllm-omni 0.28.0, and vllm 0.30.x with vllm-omni 0.30.0rc1. A mismatch only produces a runtime warning. Python >=3.10,<3.14. vllm 0.28.0/0.30.0 pin torch==2.13.0 and torchaudio==2.11.0, and flashinfer-python 0.6.16.post3 (0.28) or 0.6.18.post1 (0.30). PyPI torch 2.13.0 is the CUDA 13.0 build (cuda-toolkit==13.0.3, nvidia-*-cu13). The box driver (580.82, CUDA 13.0) supports it, so plain pip works without uv or --torch-backend. `pip install --dry-run` resolves both pairs cleanly on Python 3.12. No flash-attn and no librosa are needed for Qwen3-TTS; soundfile and torchaudio are used. Suggested sequence: `python3.12 -m venv V; V/bin/pip install -U pip wheel; V/bin/pip install vllm==0.28.0; V/bin/pip install vllm-omni==0.28.0`, then `hf download Qwen/Qwen3-TTS-12Hz-1.7B-Base` (~4.5 GB).

**Evidence:** [28] vllm_omni-0.28.0.dist-info/METADATA Requires-Dist (no vllm entry); [28] vllm_omni/version.py:L26-58 warn_if_misaligned_vllm_version; gh-v0.28.0/docs/getting_started/installation/gpu/cuda.inc.md:L8,L23,L48,L73 ('ships CUDA 13.0-compatible binaries by default'); PyPI JSON for vllm/0.28.0, vllm/0.30.0, torch/2.13.0; report28.json/report30.json (torch 2.13.0, transformers 5.14.1, nvidia-cuda-runtime 13.0.96, nvidia-cuda-nvcc 13.4.92, no librosa); fa3/kernels are imported only under vllm_omni/diffusion (grep).

### 2. Pipeline: two stages. Stage 0 is the 'qwen3_tts' talker (LLM_AR). It samples codebook 0 with vLLM's sampler, s…

**Confidence:** verified-source

Pipeline: two stages. Stage 0 is the 'qwen3_tts' talker (LLM_AR). It samples codebook 0 with vLLM's sampler, stop token 2150. Inside the same stage, the code predictor (MTP/sub-talker, 5 layers) predicts residual codebooks 1-15 in 15 sequential sub-steps per frame, batched across the decode batch. The 2048-d x-vector speaker encoder and the 12 Hz speech-tokenizer encoder also live in stage 0, both hard-coded to bf16. Stage 1 'code2wav' (LLM_GENERATION) holds only the speech-tokenizer decoder, producing 24 kHz audio at 1920 samples per frame. Frames move to stage 1 over a SharedMemoryConnector. Code2Wav keeps a per-request stateful incremental decoder cache.

**Evidence:** [28] model_executor/models/qwen3_tts/pipeline.py:L16-58; qwen3_tts_talker.py:L388-412,L414-423,L468-485,L1244-1313; worker/gpu_model_runner.py:L1848-1975; qwen3_tts_code2wav.py:L96-111,L370-401

### 3. Default deploy/qwen3_tts.yaml puts BOTH stages on one GPU (devices '0'), with gpu_memory_utilization 0.3 each…

**Confidence:** verified-source

Default deploy/qwen3_tts.yaml puts BOTH stages on one GPU (devices '0'), with gpu_memory_utilization 0.3 each (~7.2 GiB per stage on a 24 GB 3090). Stage 0: max_num_seqs 64, enable_prefix_caching false, async_scheduling, max_num_batched_tokens 32768 in 0.28 (the comment wrongly says 512) and 512 in 0.30, max_model_len 4096, CUDA graphs (enforce_eager unset), sampling temperature 0.9 / top_k 50 / rep 1.05 / min_tokens 2 / max_tokens 4096, subtalker 0.9/50/1.0. Stage 1: max_num_seqs 64, enforce_eager false (inner CUDA graphs), max_num_batched_tokens and max_model_len 65536. Connector: async_chunk true, initial_codec_chunk_frames 1, codec_chunk_frames 25, codec_left_context_frames 72, decode_batch_max_size 4. Memory is budgeted per process: requested = total × utilization, capped to the free memory at startup (a warning, not an error), and KV = requested − that process's NVML usage. So co-locating with other tenants works if enough free VRAM exists. Talker KV is ≈112 KiB/token (28 layers × 8 KV heads × 128 × 2 × bf16), so 0.3 leaves only a few GiB of KV. Estimate: stage 0 needs ~0.45 for c=32-64.

**Evidence:** [28] deploy/qwen3_tts.yaml:L1-138; [30] deploy/qwen3_tts.yaml:L20,L69-125; [28] worker/memory_utils.py:L19-55; [28] worker/base.py:L92-170; HF config.json (hidden 2048, 28 layers, 8 KV heads, head_dim 128); recipe gh-v0.30.0rc1/recipes/Qwen/Qwen3-TTS.md (4090 at ~13.5 GiB idle with 0.3+0.3)

### 4. Precision: the talker runs bf16 on the RTX 3090. The config has torch_dtype null; vLLM 'auto' turns fp32 into…

**Confidence:** verified-source

Precision: the talker runs bf16 on the RTX 3090. The config has torch_dtype null; vLLM 'auto' turns fp32 into the platform's first supported dtype, which is bf16 on sm>=80. The speaker and codec encoders are always bf16. The Code2Wav decoder is FORCED to fp32 in 0.28 but follows the stage dtype, which the YAML sets to bf16, in 0.30. That precision change between versions may affect quality.

**Evidence:** vllm28/model.py:L2212-2234; vllm platforms/cuda.py supported_dtypes; [28] qwen3_tts_talker.py:L468,L478; [28] qwen3_tts_code2wav.py:L561 (dtype=torch.float32); [30] qwen3_tts_code2wav.py:L577; [30] deploy/qwen3_tts.yaml:L108-109

### 5. Request schema (OpenAICreateSpeechRequest, a plain pydantic BaseModel, so extra fields are SILENTLY IGNORED).…

**Confidence:** verified-source

Request schema (OpenAICreateSpeechRequest, a plain pydantic BaseModel, so extra fields are SILENTLY IGNORED). Fields: input, model, voice (alias speaker), instructions, response_format (wav/pcm/flac/mp3/opus), speed (0.25-4; a post-hoc torchaudio phase vocoder, rejected when streaming), stream, stream_format (sse/audio), task_type (default CustomVoice, inferred Base when ref_audio/ref_text or a stored voice is given), language (validated against codec_language_id + Auto, so 'Urdu' returns 400 and 'Auto' is required), ref_audio (http/https/data:/file://; file:// needs --allowed-local-media-path; clip 1-30 s), ref_text, x_vector_only_mode, speaker_embedding (2048 floats for 1.7B; implies x-vector-only; excludes ref_audio), max_new_tokens (1..4096), seed, initial_codec_chunk_frames, non_streaming_mode (prompt mode, not HTTP), extra_params, word_timestamps. sample_rate is NOT in the 0.28 schema, so it is ignored there. 0.30 adds sample_rate, limited to 8000 or 24000 for Qwen3.

**Evidence:** [28] entrypoints/openai/protocol/audio.py:L57-342; [28] tts_adapters/qwen3_tts.py:L51-177,L212-227; [28] serving_speech.py:L106-107,L1332-1339,L3499-3503; tts_adapters/base.py:L168-172; [30] protocol/audio.py:L84-87; [30] tts_adapters/qwen3_tts.py:L51; [30] serving_speech.py:L1154-1168

### 6. Per-request sampling. Top-level temperature, top_k, top_p and repetition_penalty are silently dropped. extra_p…

**Confidence:** verified-source

Per-request sampling. Top-level temperature, top_k, top_p and repetition_penalty are silently dropped. extra_params.{temperature, top_p, top_k} ARE applied per request, by setattr on the stage-0 talker SamplingParams, so they affect codebook 0 only. repetition_penalty CANNOT be set per request: it is not in the schema and extra_params only copies the three names above. It is server-side only, through the stage-0 default_sampling_params in the YAML, and applies only to the talker (codebook 0). Sub-talker (code predictor) do_sample/temperature/top_k/top_p come ONLY from server subtalker_sampling_params, read at model init; there is no per-request path. seed works per request: stage-0 SamplingParams.seed plus a tts_local_seed torch.Generator for the MTP. Same in 0.30. Consequence: bench_tts.py --param repetition_penalty=X sends a top-level field that is ignored, so the Urdu rep-penalty sweep must use separate server configs (or a proxy), and temperature must go via extra_params.

**Evidence:** [28] serving_speech.py:L3079-3095 (for name in ('temperature','top_p','top_k'): setattr(sampling_params_list[0], ...)), L3102-3122; [30] serving_speech.py:L2011-2042; [28] qwen3_tts_talker.py:L488-491,L1277-1297; [28] gpu_model_runner.py:L1877-1880,L1938-1943; /home/vector/tts-reference-voices/bench/bench_tts.py:L166-178 (p.update(args.params) at top level)

### 7. Codec budget and built-in retry (already in 0.28, PR #6728 merged 2026-08-29). A Base request with no max_new_…

**Confidence:** verified-source

Codec budget and built-in retry (already in 0.28, PR #6728 merged 2026-08-29). A Base request with no max_new_tokens gets max_tokens = min(max(192, 12 × text_tokens), 4096). finish_reason=='length' raises Qwen3TTSCodecLimitError (retryable). NON-STREAMING requests are retried ONCE with a random seed, but only when the request had neither seed nor max_new_tokens. A second failure returns HTTP 500. SSE sends speech.audio.error {partial_audio:true, action:'discard'}; raw PCM streams just terminate. The retry is visible only in logs; no response header. It does NOT catch the Urdu skipped-word or cut-short failures, which end with a normal EOS. Sending max_new_tokens (the NOTES formula) disables the retry and turns a runaway into a 500. PR #6728 cites ~1 in 200 Base generations running away without EOS.

**Evidence:** [28] tts_adapters/qwen3_tts.py:L27-35,L235-333; [28] serving_speech.py:L3615-3639,L3692-3701,L2419-2433; [30] serving_speech.py:L2630-2655; https://github.com/vllm-project/vllm-omni/pull/6728

### 8. Voice registration.
- POST /v1/audio/voices is multipart: audio_sample (≤10 MB, 1-30 s) OR speaker_embedding (…

**Confidence:** verified-source

Voice registration.
- POST /v1/audio/voices is multipart: audio_sample (≤10 MB, 1-30 s) OR speaker_embedding (a JSON list), plus consent and name (required), ref_text (optional; enables ICL) and speaker_description.
- GET /v1/audio/voices returns voices and uploaded_voices. DELETE /v1/audio/voices/{name}.
- Storage: one safetensors file per voice (float32 audio plus header metadata) in SPEAKER_SAMPLES_DIR (default ~/.cache/vllm-omni/speakers), restored on restart; cap SPEAKER_MAX_UPLOADED=1000.
- Features are cached in memory only and recomputed after restart. The engine-side SpeakerEmbeddingCache (LRU 512 MiB, key = mode, voice, created_at) stores ref_code (the [T,16] reference codec codes), ref_spk_embedding (x-vector), icl_mode and ref_text. A waveform-SHA1-keyed ref-audio artifact cache stores ref_code and x-vector (256 entries in 0.28, 1024 in 0.30).
- The ICL prompt embeddings are NOT cached; they are rebuilt per request.
- After the first request per reference, an 'artifact-only' path stops shipping the waveform over IPC.
- Registered and inline ref_audio converge on the same engine caches. Inline still costs a ~2-2.7 MB base64 JSON body per request. Both hash a data-URL string with SHA1 per request.
- A cold reference is encoded on the GPU inside the talker step, stalling the batch.

**Evidence:** [28] api_server.py:L1468-1662; [28] serving_speech.py:L287-393,L894-917,L1027-1291,L1788-2033,L2972-2995; [28] utils/speaker_cache.py:L22,L228-330; [28] prompt_embeds_builder.py:L350,L598-639,L748-857,L1068-1262; gh-v0.28.0/docs/serving/speech_api.md:L462-525

### 9. Averaged or precomputed embeddings.
- Per-request speaker_embedding and embedding-only uploads work, but only…

**Confidence:** verified-source

Averaged or precomputed embeddings.
- Per-request speaker_embedding and embedding-only uploads work, but only in x-vector-only mode.
- ICL with a custom (e.g. averaged) embedding is possible ONLY via custom_voice_dir: a deploy YAML top-level key pointing to custom_voice_manifest.json plus a safetensors file per voice holding speaker_embedding, and ref_code for mode 'icl'. These are loaded into the engine speaker cache at startup, persist on disk, and have no cold start.
- The generator script examples/online_serving/text_to_speech/qwen3_tts/precompute_custom_voice.py can run on CPU. Its speaker_embedding can be replaced with our averaged, rescaled vector.
- x-vector-only mode is supported. silence_ban_frames is an optional fix for x-vector-only deploys.

**Evidence:** [28] config/stage_config.py:L725-740; engine/stage_init_utils.py:L1490-1492; qwen3_tts_talker.py:L517-558; utils/speaker_cache.py:L135-165; tts_adapters/capabilities.py:L72-104; serving_speech.py:L1175-1259,L2529-2567; gh-v0.28.0/examples/online_serving/text_to_speech/qwen3_tts/precompute_custom_voice.py:L1-243

### 10. Streaming.
- stream=true with no stream_format means SSE. stream_format='audio' alone triggers raw streaming.…

**Confidence:** verified-source

Streaming.
- stream=true with no stream_format means SSE. stream_format='audio' alone triggers raw streaming. Both need response_format pcm or wav.
- Raw WAV: a 44-byte header with 0xFFFFFFFF size placeholders is emitted just before the first audio chunk, followed by PCM16 LE chunks.
- SSE: speech.audio.delta events with base64 PCM (with wav, the first delta is the bare header), then speech.audio.done with usage, or speech.audio.error.
- Chunking: the first chunk comes after initial_codec_chunk_frames=1 codec frame (80 ms), decoded with up to 72 reference frames of context; then every 25 frames (2 s). Because a fixed IC is set in the YAML, the load-based dynamic IC is skipped, contrary to the field description.
- TTFA = API preprocessing (single-thread tokenizer executor; the tokenizer loads lazily on the first request) + stage-0 queue and prefill (ICL prompt ≈ ref frames + text; a cold reference adds encoder work) + first talker step with 15 MTP sub-steps + shared-memory transfer + Code2Wav decode of ~73 frames + orchestrator polling (open HOL issue #4561) + PCM encode on the API event loop.
- Blog reference on H20×2: c=1 TTFP 70.6 ms / E2E 564 ms; c=64 TTFP ≈1.13 s, 42.9 audio-s/s.

**Evidence:** [28] protocol/audio.py:L322-342; [28] serving_speech.py:L127-165,L2183-2433,L3565-3607; [28] stage_input_processors/qwen3_tts.py:L104-193,L300-343; chunk_size_utils.py:L11-39; https://vllm.ai/blog/2026-06-23-vllm-omni-tts; https://github.com/vllm-project/vllm-omni/issues/4561

### 11. The async_chunk trade-off. Non-streaming requests also use the windowed async-chunk Code2Wav path when async_c…

**Confidence:** reported

The async_chunk trade-off. Non-streaming requests also use the windowed async-chunk Code2Wav path when async_chunk is true. Issue #4371 measured --no-async-chunk at ~40-70% higher ×realtime on 2×3090 (vllm-omni 0.20, 1.7B CustomVoice, batch 16: ~13× vs 20-23×) and 19.5× vs 22.8× on a 4090 (1.7B Base, c=16). The quality complaint in that issue was retracted and traced to the cross-request reference leak fixed in #4370/#4373. PR #6898 (merged 2026-09-14) added full_utterance_decode, but the online /v1/audio/speech never sets it. For batch throughput, the lever is a server with async_chunk:false (--no-async-chunk exists in 0.28), where 'streaming' returns everything at the end.

**Evidence:** https://github.com/vllm-project/vllm-omni/issues/4371 (comments with the 3090 table); https://github.com/vllm-project/vllm-omni/pull/6898; [30] tts_adapters/qwen3_tts.py:L377 ('Online serving keeps the default windowed async-chunk path'); [28] entrypoints/cli/serve.py:L294-299; [28] serving_speech.py:L3009-3021

### 12. Batching and serialization.
- The talker gets vLLM continuous batching (max_num_seqs 64). Excess requests queu…

**Confidence:** verified-source

Batching and serialization.
- The talker gets vLLM continuous batching (max_num_seqs 64). Excess requests queue in the scheduler; there is NO HTTP admission limit or 429.
- The MTP is batched per step but runs 15 sequential sub-steps. Issue #4855 reports the talker is host-bound (~100 ms per step at c=64 vs ~10 ms of forward), so CPU speed matters.
- Code2Wav groups requests by decode phase, at most decode_batch_max_size (4) per group. With the default CUDA graph bucket [1], it runs effectively as sequential batch-1 graph replays per request per chunk; the 0.30 HC profiles add B2/B4/B8 buckets.
- API-side CPU work runs on the one event loop: a ThreadPoolExecutor(max_workers=1) for prompt-length tokenization, a synchronous token count for the codec cap, and synchronous soundfile encoding, speed phase vocoder and resampling.
- --api-server-count is REJECTED under --omni in 0.28. It is allowed in 0.30 but disables voice upload and delete.

**Evidence:** [28] serving_speech.py:L493-499,L3099-3100; audio_utils_mixin.py:L21-127; tokenizer_12hz/modeling_qwen3_tts_tokenizer_v2.py:L1211-1291; segmented_graph_wrapper.py:L53,L624-660; qwen3_tts_code2wav.py:L463-470,L685-688; [28] entrypoints/cli/serve.py:L148-168; gh-v0.30.0rc1/docs/cli/serve.md:L1-60; https://github.com/vllm-project/vllm-omni/issues/4855

### 13. In 0.28, SEEDED requests serialize the MTP. vLLM's default cudagraph_mode is FULL_AND_PIECEWISE, under which t…

**Confidence:** verified-source

In 0.28, SEEDED requests serialize the MTP. vLLM's default cudagraph_mode is FULL_AND_PIECEWISE, under which the Qwen3 talker sets talker_mtp_accepts_per_row_generators=False. Whenever the decode batch is >1 and any row has a seed, the runner then runs one scalar MTP forward per row. Seeds are also not reproducible under full graphs when batch>1. Triggers: an explicit seed, the built-in retry (which injects a random seed), or a YAML stage-0 seed. --enforce-eager avoids this but disables CUDA graphs for both stages. 0.30 always accepts per-row generators, and the MRV2 runner bypasses only the outer MTP graph for seeded rows. The 0.30 V1-runner behavior is unverified (open PR #8009). Implication: do not send seed in 0.28 throughput runs.

**Evidence:** [28] qwen3_tts_talker.py:L329-351; [28] worker/gpu_model_runner.py:L1911-1936; vllm28/vllm_cfg.py:L283,L1284-1290; [30] qwen3_tts_talker.py:L407-410; [30] worker_v2/model_states/omni_model_state.py:L1089-1096; https://github.com/vllm-project/vllm-omni/pull/8009; gh-v0.30.0rc1/benchmarks/tts/README.md ('production-performance runs should omit it')

### 14. Headers, metrics, health, auth.
- Non-streaming success responses carry X-VLLM-OMNI-INPUT-TOKENS, -OUTPUT-TOKE…

**Confidence:** verified-source

Headers, metrics, health, auth.
- Non-streaming success responses carry X-VLLM-OMNI-INPUT-TOKENS, -OUTPUT-TOKENS (codec frames, 12.5 per second of audio), -TOTAL-TOKENS, -INPUT-TEXT-TOKENS and -INPUT-AUDIO-TOKENS. Streaming responses have no headers; SSE carries usage in the done event.
- GET /health returns 200 {status: healthy} or 503 when the engine is dead.
- /metrics is Prometheus, with vllm_omni:num_requests_running/waiting, e2e_request_latency_s, requests_success/failed, request_queue_wait_s, audio_ttfp_s, audio_duration_s, audio_rtf, audio_underrun_s. These are on by default (log_stats = not --disable-log-stats).
- Auth via --api-key or VLLM_API_KEY guards /v1,/v2,/inference,/cohere; /health and /metrics stay open.
- The INFO log line '[SpeechE2E] ... total_ms first_chunk_ms' is plain text, not structured.

**Evidence:** [28] serving_speech.py:L83-87,L770-785,L2309-2323; [28] api_server.py:L732,L1777-1803; [28] metrics/definitions.py:L116-170,L133-137; metrics/modality.py:L38-61; vllm28/api_server.py:L284-288; vllm28/server_utils.py:L27-75; vllm28/instr_metrics.py:L57-82

### 15. Differences from 0.28.0 to 0.30.0rc1:
- qwen3_tts.yaml defaults to the EXPERIMENTAL MRV2 runner.
- Stage-0 max…

**Confidence:** verified-source

Differences from 0.28.0 to 0.30.0rc1:
- qwen3_tts.yaml defaults to the EXPERIMENTAL MRV2 runner.
- Stage-0 max_num_batched_tokens goes from 32768 to 512.
- Code2Wav goes from fp32 to bf16.
- sample_rate field added (8k/24k).
- Seeded batches stay batched.
- Bigger ref caches (1024).
- --api-server-count supported.
- Voice registration policy (immutable option) and names that shadow built-in voices rejected.
- task_type must match the checkpoint variant.
- base_config overlays deep-merge connectors (0.28 replaces the connectors block wholesale).
- WebSocket split_granularity and seed.
- New MRV2 profiles, including a single-GPU B8 profile.
Unchanged: extra_params handles only temperature/top_p/top_k, repetition_penalty is server-only, and the retry-once logic is the same.

**Evidence:** diff of src28 vs src30: deploy/qwen3_tts.yaml; protocol/audio.py; qwen3_tts_code2wav.py L561 vs L577; qwen3_tts_talker.py L329-351 vs L407-410; [28] config/stage_config.py:L689-700 vs [30] L753-779,L793; [30] serving_speech.py:L113-114,L249-252,L814-845; [30] tts_adapters/qwen3_tts.py:L80-143; gh-v0.30.0rc1/docs/serving/speech_api.md diff

## Risks

- Bench validity: top-level repetition_penalty and temperature in bench_tts.py (--param) are silently ignored by vLLM-Omni. The Urdu rep-penalty sweep would measure nothing unless it is run as separate server configs, one deploy YAML per value.
- Bench validity: sending per-request `seed` in 0.28 disables the built-in retry and runs the MTP row by row whenever the batch is >1 (under the default full CUDA graphs). That collapses throughput and seeds are still not reproducible. Use seeds only in dedicated determinism or quality runs.
- The NOTES.md serve command uses --enforce-eager. That disables talker CUDA graphs and Code2Wav inner graphs, since global CLI flags apply to every stage (config/stage_config.py:L47-89), which likely makes it much slower. Do not use it as the production setting.
- Passing max_new_tokens (the NOTES length-cap formula) turns an EOS runaway into HTTP 500 instead of the built-in retry. Our wrapper must then own the retry. The built-in retry never covers skipped-word or cut-short takes, nor streaming requests.
- Shared GPU: the default 0.3+0.3 reserves ~14.4 GiB. If other tenants leave less free memory, budgets are capped to free memory at startup and the talker's KV may be too small for c≥32, causing preemptions. Size per-stage gpu_memory_utilization, or kv_cache_memory_bytes, to the actual free VRAM.
- Default async_chunk=true costs a reported 40-70% of batch throughput on 3090s. Non-streaming and streaming servers may need different configs (async_chunk true for TTFA, false for throughput).
- 0.30.0rc1 defaults to the experimental MRV2 runner and a bf16 Code2Wav, and it is a pre-release paired with vllm 0.30.0. Quality and stability on Ampere are unverified.
- FlashInfer JIT on first start could pick up the system nvcc 12.0 on PATH or a stale CUDA_HOME instead of the CUDA 13 toolchain from pip (unverified). Start with a clean PATH and CUDA_HOME.
- 0.28's base_config overlay replaces the `connectors:` block wholesale, so a thin overlay that only changes a connector key drops the rest. Write a full YAML copy for 0.28.
- Open upstream issues: #4561 (head-of-line blocking inflates TTFP under queued concurrency) and #4855 (event loop can wedge on a full queue; no chunk-wait deadline on the async-chunk path; talker host-bound at high concurrency).
- No built-in admission control or 429. Requests beyond max_num_seqs queue without limit inside the engine, so the wrapper must enforce queue limits and timeouts.

## Open questions

- Does the API-side adapter actually see custom_voice_dir on engine_client.model_config.hf_config, so that precomputed voices appear in GET /v1/audio/voices and pass validation? Check at runtime.
- Do global CLI flags (e.g. --gpu-memory-utilization, --enforce-eager) override per-stage YAML values, or the reverse? Check the startup logs.
- Does stage 1 (Code2Wav, which has no vLLM attention KV) really consume its full gpu_memory_utilization reservation? Recipes suggest yes (the 0.6B on a 4090 idles at ~13.5 GiB with 0.3+0.3). Measure on the 3090.
- Actual RTX 3090 numbers for the 1.7B Base model: talker step time vs concurrency, TTFA, ×realtime with async_chunk true vs false, and fp32 vs bf16 Code2Wav quality (0.28 vs 0.30).
- Does the 0.30 V1 runner (model_runner: v1) with full CUDA graphs honor or drop per-row seeds? Open PR #8009 describes seeds being dropped.
- Does FlashInfer JIT or the FlashInfer sampler work on sm_86 with the pip CUDA 13 toolchain on this box, or does it need an env override?
- Does repetition_penalty 1.1-1.2 (codebook 0 only; it never reaches the sub-talker) reduce the Urdu loops? This needs separate server configs per value.
- The subagent could not write FINDINGS.md: the harness blocked subagent report-file writes. The full write-up is in this structured output, and the orchestrator should persist it if a file is needed.
