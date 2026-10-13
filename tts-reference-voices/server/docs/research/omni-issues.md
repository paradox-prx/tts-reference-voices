# Research: omni-issues

_How vLLM-Omni handles Qwen3-TTS-12Hz-1.7B-Base voice cloning today, from GitHub issues and PRs, release notes 0.25 to 0.30.0rc1, the docs, recipes and the blog, and the 0.28.0 and 0.30.0rc1 source_

Produced 2026-09-24 by a research subagent (workflow wf_6c83c01a-7e3). Confidence: verified-source = read in the
package source; verified-doc = official docs/issue text; reported = third-party claim; unverified = not checked.
Scratch artifacts referenced below lived under /tmp/claude-1013/.../scratchpad/research/ (copied to docs/research/artifacts/ where small).

## Findings

### 1. Runaway generation (no end-of-speech token) is a property of the model, not of vLLM. Since 0.28.0 the server p…

**Confidence:** verified-source

Runaway generation (no end-of-speech token) is a property of the model, not of vLLM. Since 0.28.0 the server partly bounds it. A Base request that does not set max_new_tokens gets a cap of min(4096, max(192, 12 x text_tokens)) codec frames. If generation hits that cap (finish_reason 'length'), a non-streaming request is retried once with a fresh seed, but only when the caller sent neither seed nor max_new_tokens. Otherwise the client gets HTTP 500, SSE gets speech.audio.error with action 'discard', and a raw audio stream is cut off. The check does not catch skipped words, early truncation, or loops that do eventually stop. So the client-side duration band, ASR check and retry are still needed.

**Evidence:** PR #6728 https://github.com/vllm-project/vllm-omni/pull/6728 (merged 2026-08-29, in the 0.28.0 notes): the end-of-speech token was ranked 100-1400 (p about 1e-8) and was 'removed from the sampling set [top_k=50]'; the PR also says 'no evidence that disabling CUDA graphs is a root fix'. Source (0.30.0rc1 wheel): tts_adapters/qwen3_tts.py:33-34 (_MIN_CODEC_FRAMES=192, 12 frames per token), :513-594 apply_sampling_overrides, :596-626 validate_generation; serving_speech.py:2630-2655 retry-once logic, which logs 'failed generation validation; retrying once'. Upstream QwenLM/Qwen3-TTS#118 reports about 1 in 200 Base generations with no end token.

### 2. repetition_penalty cannot be set per request. The request schema has no sampling fields, and unknown top-level…

**Confidence:** verified-source

repetition_penalty cannot be set per request. The request schema has no sampling fields, and unknown top-level keys are silently dropped. extra_params maps only temperature, top_p and top_k onto the talker's sampling parameters. extra_params.repetition_penalty ends up in extra_args, which nothing in the Qwen3-TTS model code reads. So 'bench_tts.py --param repetition_penalty=1.15' does nothing, and so does a top-level temperature. To sweep repetition_penalty, restart the server with --stage-overrides or a copy of the deploy YAML (default 1.05).

**Evidence:** wheels/v030rc1/vllm_omni/entrypoints/openai/protocol/audio.py:58 (a plain pydantic BaseModel) and :280-290 (comment: 'silently dropped by pydantic when posted to /v1/audio/speech'); serving_speech.py:2011-2027 (for name in ('temperature','top_p','top_k'), then extra_args.update); grep finds no extra_args use in model_executor/models/qwen3_tts/; deploy/qwen3_tts.yaml:96 repetition_penalty: 1.05. 0.28.0 has the same code at serving_speech.py:3080-3094. bench/bench_tts.py:175 does p.update(args.params) at top level.

### 3. 0.30.0rc1 (2026-09-22) makes an experimental runner, Model Runner V2 (MRV2), the default for Qwen3-TTS on CUDA…

**Confidence:** verified-source

0.30.0rc1 (2026-09-22) makes an experimental runner, Model Runner V2 (MRV2), the default for Qwen3-TTS on CUDA. It also shrinks the talker's per-step prefill budget from 32768 to 512 tokens. The release notes call MRV2 experimental. PR #7781 reports +73-76% single-GPU throughput at 64-128 concurrent requests on H200, but streaming underruns got 123-360% worse, and 'codec budget-exhaustion/repetitive-generation failures remain under investigation'. After the rc, the continuous-integration run for the 0.30.0 release produced looping garbage for a voice-clone streaming test (issue #8091, still open).

**Evidence:** PR #7930 https://github.com/vllm-project/vllm-omni/pull/7930 and PR #7781 https://github.com/vllm-project/vllm-omni/pull/7781; release_v0.30.0rc1.md ('Model Runner V2 remains experimental... Set model_runner: v1 to opt out'); diff of wheels v028 vs v030rc1 deploy/qwen3_tts.yaml. Issue #8091 https://github.com/vllm-project/vllm-omni/issues/8091: vLLM 0.30.0, commit 57d3e9fd (after the rc1 tag), transcript 'a roar, a roar, a roar...' on B200, A100 and L4 for test_voice_clone_streaming_001[no_async_chunk]. The rc1 tag is commit 59db6a42.

### 4. The default async_chunk: true decodes audio in small windows even for non-streaming requests. On an RTX 4090 t…

**Confidence:** verified-source

The default async_chunk: true decodes audio in small windows even for non-streaming requests. On an RTX 4090 this gave a higher noise floor, about 17% less throughput at 16 concurrent requests, and 2-3.5 GB more VRAM. The fix in 0.30.0rc1 (#6898) only applies to offline callers that set full_utterance_decode. Its title says it gates on non_streaming_mode, but the shipped code does not. Online serving still uses windowed decode, and there is no per-request switch. So use the --no-async-chunk server flag for batch and non-streaming work.

**Evidence:** Issue #4371 https://github.com/vllm-project/vllm-omni/issues/4371 (RTX 4090, 0.22.0, 1.7B-Base; x-realtime at 16 concurrent: 19.47 at 18.5 GB vs 22.76 at 16.1 GB; 'with --no-async-chunk the output matches the official package by ear'). PR #6898. Source: tts_adapters/qwen3_tts.py:377-381 ('Online serving keeps the default windowed async-chunk path'); stage_input_processors/qwen3_tts.py:222-228; cli/serve.py:411-416 defines --async-chunk/--no-async-chunk. Issue #3809: an L4 ran out of memory only with async_chunk.

### 5. The docs' Base example and our NOTES.md both use --enforce-eager. Global CLI flags override the deploy YAML fo…

**Confidence:** verified-doc

The docs' Base example and our NOTES.md both use --enforce-eager. Global CLI flags override the deploy YAML for every stage, so this turns off CUDA graphs on the talker too. On H200 at 1 concurrent request those graphs gave about 1.8x end-to-end speed. Leave the flag off, or set eager per stage with --stage-overrides.

**Evidence:** stage_configs_030rc1.md:196-202 (precedence: per-stage overrides > global CLI flags > platform > YAML); speech_api_030rc1.md:460-470 (Base example has --enforce-eager); repo/docs/design/qwen3_omni_tts_performance_optimization.md:200-215 (H200: end-to-end 1339 to 733 ms at 1 concurrent; throughput 33.5 to 47.2 audio-s/s at 10 concurrent). Issue #4815's 'enforce_eager fixes runaway' claim was retracted as not reproducible.

### 6. Published RTX 3090 numbers exist for exactly our model and task (1.7B-Base voice clone, SeedTTS English, one 3…

**Confidence:** reported

Published RTX 3090 numbers exist for exactly our model and task (1.7B-Base voice clone, SeedTTS English, one 3090, default YAML, streaming). PR #5202 (vLLM 0.26.0) reports: 1 request RTF 0.222, first audio 143 ms; 4 requests RTF 0.308, 203 ms; 8 requests RTF 0.431, 364 ms; 16 requests RTF 0.718, 837 ms. Here RTF is compute time divided by audio length, so lower is faster. PR #5253 (vLLM 0.25.0) reports aggregate throughput in seconds of audio per wall-clock second: 4.07 at 1 request, 9.57 at 4, 12.39 at 8, 14.10 at 16, 15.50 at 32, 17.39 at 64, with per-request RTF above 1 from 16 requests. Expect roughly 8-12 real-time streams per 3090 and a ceiling of about 12-18x real time. That is about 10x faster per request than the Kaggle T4 fp32 RTF of 2.2-2.5.

**Evidence:** PR #5202 https://github.com/vllm-project/vllm-omni/pull/5202 ('Benchmarked on single 3090-24GB', commit b8edbc8d, word error rate 0.0089 on 32 requests; 'batch size 4 or larger [graph buckets] improved performance at concurrency 16 and above'). PR #5253 https://github.com/vllm-project/vllm-omni/pull/5253 ('Test and Benchmarked on RTX3090+CUDA13.0', commit 9dd1474b, 128 prompts). The RTF definition is in repo/vllm_omni/metrics/definitions.py:386-395.

### 7. Other published numbers, for scale. Nightly baseline on 2x H100 (talker on one GPU, audio decoder on the other…

**Confidence:** verified-doc

Other published numbers, for scale. Nightly baseline on 2x H100 (talker on one GPU, audio decoder on the other), 1.7B-Base voice clone: 1 request first audio 141 ms, RTF 0.159; 8 requests 227 ms, 24.2x real time; 16 requests 647 ms, 40.4x; 64 requests 4777 ms, 43.3x. H20-3e: RTF 0.15 at 1 request up to 0.77 at 32, with first audio jumping 4-6x between 4 and 8 requests. The blog (2x H20, voice clone, streaming, 64 concurrent) reports 26.55 to 42.88x real time, and first audio of 70.6 ms at 1 request up to 1128 ms at 64. MRV2 on 1x H200 at 64 requests: 55.4 to 97.3x real time. On an RTX 4090, 1.7B-Base ran 5.25-5.43x real time at 1 request and 19.5-22.8x at 16.

**Evidence:** repo/tests/dfx/perf/tests/test_tts.json (test_qwen3_tts_base baseline for H100); repo/benchmarks/tts/README.md:270-285; https://vllm.ai/blog/2026-06-23-vllm-omni-tts (fetched); PR #7781; issue #4371. Issue #3163: 'RTX 4090 ≈ 2.7× slower than H200'.

### 8. Some single requests can still kill the whole server. Inline ref_audio plus a voice label that changes between…

**Confidence:** verified-source

Some single requests can still kill the whole server. Inline ref_audio plus a voice label that changes between requests kills the talker process, and /health then returns 503. The fix (#6974) was merged after 0.30.0rc1 and is in no release, so never send 'voice' together with ref_audio. bench_tts.py's inline mode is safe because it sends only ref_audio and ref_text. Text with no speakable content, such as '-------', produces an empty take; this was reproduced on RTX 3090s and fixed in 0.26.0 (#5269/#5472). An x-vector request followed by an ICL request with the same ref_audio was fixed in 0.26.0 (#5157).

**Evidence:** Issue #6970 https://github.com/vllm-project/vllm-omni/issues/6970 and PR #6974 (merged 2026-09-22T23:19Z; rc1 was published 16:33Z; commit d2aa0715 is after the v0.30.0rc1 tag in the repo log). Issues #5196 and #5471 ('Single RTX 3090 (also reproduced on multiple different 3090 hosts)'; 'punctuation-only strings such as "-------"'). Issue #5049. Source: api_server.py:1917-1940 (/health returns 503 on EngineDeadError).

### 9. Preemption of the talker under memory pressure is still unsafe. Issue #4471 remains open: an RTX 4090 at 16 co…

**Confidence:** reported

Preemption of the talker under memory pressure is still unsafe. Issue #4471 remains open: an RTX 4090 at 16 concurrent requests crashes the talker process when a preempted request resumes. PR #4559 (0.24.0) fixed only the first cause; a gather assertion 'remains', and maintainers say to size the talker's KV cache so preemption never happens. Recompute preemption can also splice two unrelated halves of audio together (#6179 and PR #6601, both open). The default max_num_seqs of 64 with gpu_memory_utilization of 0.3 on a 24 GB card oversubscribes that cache. Set max_num_seqs from the concurrency figure the engine logs at startup, and limit concurrency in the gateway.

**Evidence:** Issue #4471 https://github.com/vllm-project/vllm-omni/issues/4471 (still open); PR #4559 (merged 2026-07-02; 'stable deployments should size Stage-0 KV cache to prevent preemption'); issue #6179 ('Raise the stage's gpu_memory_utilization or lower max_num_seqs'); PR #6601 (open); deploy/qwen3_tts.yaml:70-71; PR #7488 (a 0.6B model's KV cache holds '4.59x maximum concurrency at 4,096 tokens').

### 10. Seeds are not reproducible across batches. Fixed-seed output differs between sequential and co-batched request…

**Confidence:** reported

Seeds are not reproducible across batches. Fixed-seed output differs between sequential and co-batched requests (issue #6361), because the talker's numerics depend on the batch and the audio decoder's convolutions are not covered by batch invariance. Under CUDA-graph replay, per-row seed generators for the extra codebooks are silently dropped (PR #8009, open). Setting VLLM_BATCH_INVARIANT=1 crashes the speaker encoder. A seed also disables the server's retry, and the default YAML seed was removed because it forced serial sampling (#4970). Benchmark without seeds, and do not pair takes by seed across concurrency levels.

**Evidence:** Issue #6361 https://github.com/vllm-project/vllm-omni/issues/6361 (comments: 'RuntimeError: Input type (float) and bias type (c10::BFloat16)' with VLLM_BATCH_INVARIANT=1; 'VLLM_BATCH_INVARIANT=1 does not currently cover conv1d'); PR #8009 https://github.com/vllm-project/vllm-omni/pull/8009; PR #5253; 0.25.0rc1 notes for #4970; serving_speech.py:2636.

### 11. The HTTP API cannot combine an averaged speaker embedding with in-context (ICL) cloning. A request's speaker_e…

**Confidence:** verified-source

The HTTP API cannot combine an averaged speaker embedding with in-context (ICL) cloning. A request's speaker_embedding turns on x-vector-only mode and cannot be sent with ref_audio. Voice upload takes audio_sample or speaker_embedding, never both. It can be done offline. Precomputed voices (custom_voice_dir, since 0.22.0) are safetensors files holding speaker_embedding plus ref_code, so a custom precompute step can store the mean embedding next to the ICL ref_code.

**Evidence:** protocol/audio.py:147-153 ('Implies x_vector_only_mode=True. Mutually exclusive with ref_audio'); api_server.py:1548-1598 ('audio_sample' and 'speaker_embedding' are mutually exclusive); repo/examples/online_serving/text_to_speech/qwen3_tts/precompute_custom_voice.py:185-196 (tensors speaker_embedding + ref_code in icl mode); custom_voice_dir appears in wheels/v028 and v030rc1 (speaker_cache.py, qwen3_tts_talker.py); added in #3492 (tag v0.22.0).

### 12. Streaming has audible gaps under load on consumer GPUs: from 4 concurrent requests on a 3090 or A100, and from…

**Confidence:** verified-source

Streaming has audible gaps under load on consumer GPUs: from 4 concurrent requests on a 3090 or A100, and from 6 on a 4090. Voice clone is limited by the talker stage, whose chunk interval is 11x slower than CustomVoice's. The fixed-size and adaptive chunk ramps (#5152 in 0.26, #6001 in 0.28) are opt-in YAML settings that may reduce the gaps. Event-driven orchestration (#7088) is the default for Qwen3-TTS in 0.30.0rc1. Deadline-aware scheduling (#6600) is not merged.

**Evidence:** Issue #2562 https://github.com/vllm-project/vllm-omni/issues/2562 ('concurrency 4 or more on 3090/A100/H100(mig20) and 6 or more on 4090'); issue #3535 ('voice_clone 263 ms, CV 23 ms' chunk-emit interval; underrun p99 16-19 s at 64+ requests on H20); issue #4913 (open); deploy/qwen3_tts.yaml:36-53 (codec_chunk_ramp and codec_chunk_adaptive commented out); speech_api_030rc1.md:971-1017 (VLLM_OMNI_EVENT_DRIVEN_ORCH).

### 13. TTS changes by release. 0.25.0rc1: removed the default seed so sampling batches again, aligned the MTP CUDA gr…

**Confidence:** verified-doc

TTS changes by release. 0.25.0rc1: removed the default seed so sampling batches again, aligned the MTP CUDA graph, added Gumbel-max sampling. 0.26.0: chunk ramp, fixes for the ref_audio cache and for empty takes, decoder mask cache. 0.27.0rc1: cached incremental audio decode (+10-40% throughput on a 3090). 0.28.0 (latest stable): the codec-budget cap and retry (#6728), silence_ban_frames, adaptive ramp, token-usage response headers, sampling overrides moved into adapters. 0.29.0rc1: 8 kHz output, rejects task/model mismatches before they reach the engine. 0.30.0rc1: MRV2 on by default (experimental), event-driven orchestration, audio decoder uses bf16, streaming metrics, a voice registration policy. Separately, 0.24.0 had a 28-34% throughput regression (warning 'Error concatenating tensor for key sr').

**Evidence:** release_v0.25.0rc1.md through release_v0.30.0rc1.md (GitHub releases API, saved in the research folder); issue #7347 https://github.com/vllm-project/vllm-omni/issues/7347 (audio-s/s at 25 concurrent: 0.22 35.8, 0.24 25.6, 0.26 54.1).

### 14. Defaults in the 0.30.0rc1 deploy YAML. Talker: max_num_seqs 64, gpu_memory_utilization 0.3, max_num_batched_to…

**Confidence:** verified-source

Defaults in the 0.30.0rc1 deploy YAML. Talker: max_num_seqs 64, gpu_memory_utilization 0.3, max_num_batched_tokens 512, max_model_len 4096, CUDA graphs on, prefix caching off, sampling temperature 0.9, top_k 50, repetition_penalty 1.05, min_tokens 2, max_tokens 4096; the code predictor also samples at temperature 0.9, top_k 50. Audio decoder: bf16, max_num_seqs 64, 0.3, graphs on, decode_batch_max_size 4. Chunking: codec_chunk_frames 25, left context 72, first chunk 1 frame. Note that the docs list the max_new_tokens default as 2048 while the YAML sets max_tokens to 4096. The high-concurrency profile splits the talker onto GPU 0 and the audio decoder onto GPU 1.

**Evidence:** wheels/v030rc1/vllm_omni/deploy/qwen3_tts.yaml:20-133; deploy/qwen3_tts_high_concurrency.yaml:1-115; speech_api_030rc1.md:138-150 (max_new_tokens default 2048).

### 15. Useful production hooks. GET /health returns 503 once any stage process is dead, which suits a systemd watchdo…

**Confidence:** verified-source

Useful production hooks. GET /health returns 503 once any stage process is dead, which suits a systemd watchdog. Every non-streaming response carries x-vllm-omni-output-tokens, the number of codec frames; divided by 12.5 it gives audio seconds, a cheap runaway check. Uploaded voices persist as .safetensors under SPEAKER_SAMPLES_DIR. VLLM_OMNI_SPEAKER_REGISTRATION_POLICY=immutable blocks overwrites, but there is no per-user ownership. First start compiles FlashInfer kernels, which took about 158 s in #7488.

**Evidence:** api_server.py:1917-1940; speech_api_030rc1.md:162-178 (headers) and :229-310 (voices); PR #6848; PR #7488 ('Startup ~158 s on the first run including a one-time FlashInfer JIT compile').

### 16. Nothing specific to the 3090's architecture (Ampere, sm_86) is broken. Several bugs only hit fp16-only GPUs su…

**Confidence:** reported

Nothing specific to the 3090's architecture (Ampere, sm_86) is broken. Several bugs only hit fp16-only GPUs such as the T4 (#6545 open, #3253, #2385), and Ampere has bf16, so they do not apply. They also explain why vLLM-Omni was not an option on Kaggle T4s. No Urdu- or 'Auto'-specific issue exists in vllm-omni. Mixed-script input is reported upstream to make missing end tokens much easier to trigger.

**Evidence:** Searches for 3090 / Ampere / sm_86 / A10 in about 760 cached issue and PR bodies (db.json). PR #6545 https://github.com/vllm-project/vllm-omni/pull/6545 ('crashing every request on fp16-only GPUs (T4/sm75)'). PR #6728 cites QwenLM/Qwen3-TTS#318 ('mixed Thai/Chinese/English input made the failure substantially easier to reproduce').

## Risks

- 0.30.0rc1 makes the experimental runner (MRV2) the default, and issue #8091 is open: the 0.30.0 release test produced looping garbage for Base voice-clone streaming. Pin 0.28.0, or set model_runner: v1 on 0.30.x, until MRV2 wins a quality and underrun A/B on our hardware.
- The GPUs are shared. Memory pressure has crashed the orchestrator with no recovery (#2316), and talker preemption can crash the engine (#4471, still open) or splice audio together (#6179). max_num_seqs must be sized to the KV cache the engine actually gets, concurrency capped in the gateway, and systemd set to restart the service on a /health 503.
- Inline ref_audio plus a voice field crashes the talker on every released version up to 0.30.0rc1 (#6970; the fix is only on main). An OpenAI SDK or gateway that always fills in 'voice' would take the server down.
- The benchmark sweep of repetition_penalty (and temperature) through bench_tts.py --param is silently ignored. Unless the server is restarted per value, the Urdu results would show no effect even if there is one.
- The server's automatic cap (12 frames per text token) is loose. Our 95-99 s Urdu loops probably stay under it, and skipped words or early truncation are never flagged. The client-side duration, word error rate and speaker-similarity checks are still needed.
- The default async_chunk mode lowers audio quality for non-streaming requests and uses more memory (#4371, #3809). Comparing streaming and non-streaming results from one server profile would mix a quality variable in with the latency comparison.
- Seed-based comparisons across concurrency levels are unreliable (#6361, #8009), and seeding turns off the server retry.
- An open framework bug (#4355) can silently clone audio payloads across requests in a mixed batch. It needs a guard: compare speaker similarity at 16 mixed concurrent requests against 1 request.
- The published 3090 numbers come from vLLM 0.25/0.26-era commits. Today's 0.28/0.30 code paths may differ (MRV2, prefill budget of 512, event-driven orchestration).

## Open questions

- Does vLLM's repetition_penalty actually act on the talker's codebook-0 tokens? The prompt positions are embeddings with placeholder IDs. Only a restart-per-value sweep will show whether 1.1-1.2 reduces the Urdu loops.
- How many Qwen text tokens does Urdu text use? That decides whether the automatic cap ever catches Urdu runaways.
- Does MRV2 work, and help, on sm_86? All published MRV2 validation is on H200 and H100.
- Does part 2 of #4471 (a gather assertion on resume) still happen on 0.28/0.30, and with MRV2?
- What causes #8091 (looping in the 0.30 release test), and does it also hit the V1 runner?
- Does vLLM 0.28-0.30 refuse to start a stage when free memory is below total x gpu_memory_utilization on a shared card? #5362 has no maintainer answer.
- Do the 16-bit-only reference-audio problems (#7899, Gradio demos) also affect the /v1/audio/voices and ref_audio API paths? Safest is to always send 16-bit PCM.
- Which vLLM wheel does vllm-omni 0.28.0 need for CUDA 12.x drivers? The A100 recipe needed the cu129 wheel on driver 570. Our driver is 580 (CUDA 13.0), so the default cu130 wheels should load. Left for the local-env topic.
- GitHub API quota ran out: search pages 7-10 of 1,089 results and most issue comments were not fetched. Some issues listed here may have later resolutions not captured.
