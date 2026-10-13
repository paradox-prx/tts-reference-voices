# Research: qwen-tts-internals

_Qwen3-TTS-12Hz-1.7B-Base model and the official qwen-tts 0.1.1 package, read from source. Scratch root S=/tmp/claude-1013/-home-vector/60c91189-44d6-4cdb-b0f5-2bf4adb23fb3/scratchpad/research/qwen-tts-internals/. File keys: W=S/src/qwen_tts/inference/qwen3_tts_model.py, M=S/src/qwen_tts/core/models/modeling_qwen3_tts.py, T=S/src/qwen_tts/core/tokenizer_12hz/modeling_qwen3_tts_tokenizer_v2.py, C=S/hf/config.json, SC=S/hf/speech_tokenizer/config.json, tf/=transformers v4.57.3 sources. Source versions: wheel sha256 11a290d8… matches PyPI; the qwen_tts/ folder on GitHub main is byte-identical to the 0.1.1 wheel; HF repo revision fd4b2543. No GPU was used and no weights were downloaded (safetensors headers were fetched with HTTP range requests)._

Produced 2026-09-24 by a research subagent (workflow wf_6c83c01a-7e3). Confidence: verified-source = read in the
package source; verified-doc = official docs/issue text; reported = third-party claim; unverified = not checked.
Scratch artifacts referenced below lived under /tmp/claude-1013/.../scratchpad/research/ (copied to docs/research/artifacts/ where small).

## Findings

### 1. Size: 1,928,677,440 parameters, all stored in BF16. Breakdown: talker transformer 1.409B (28 layers, hidden 20…

**Confidence:** verified-source

Size: 1,928,677,440 parameters, all stored in BF16. Breakdown: talker transformer 1.409B (28 layers, hidden 2048, 16 query heads × head_dim 128, 8 KV heads, MLP 6144, M-RoPE [24,20,20], max_pos 32768); Qwen text-embedding table 311M (151,936 × 2048); code predictor 175M (5 layers, hidden 1024, 15 input embeddings + 15 LM heads); ECAPA-TDNN speaker encoder about 12M, with a 2048-d output. The speech tokenizer is a separate 170.6M-parameter F32 file.

**Evidence:** C:15-18 and C:22-164; safetensors headers in S/hf/*.header.json (model.safetensors is 3,857,413,744 B; speech_tokenizer/model.safetensors is 682,293,092 B); the HF API reports {'BF16': 1928677440}.

### 2. How the 16 codebooks of each 80 ms frame are made. The talker input is the sum of the previous frame's 16 code…

**Confidence:** verified-source

How the 16 codebooks of each 80 ms frame are made. The talker input is the sum of the previous frame's 16 codebook embeddings plus the text-track embedding. codec_head predicts codebook 0 (the semantic codebook; the specials 2048-3071 are suppressed except EOS 2150). A separate HF generate() on the code predictor then makes codebooks 1-15: 15 new tokens, prefill [talker hidden, codebook-0 embedding], lm_head[k] at step k, and a fresh cache each frame. Cost per frame: 1 talker forward + 15 code-predictor forwards, with HF generate overhead on each. Stock qwen-tts is therefore CPU and dispatch bound: issues #89 and #132 report 4-16% GPU utilisation.

**Evidence:** M:1669-1692 (code_predictor.generate, then the sum of codebooks plus trailing text); M:1277-1281 and M:1299 (MTP steps); M:2059-2063 (suppress_tokens); M:2283-2289 (stop at EOS on codebook 0); paper.txt:145 (MTP description).

### 3. 12 Hz speech tokenizer. The encoder is a Mimi (MimiModel subclass) using 16 of its 32 quantizers. The decoder…

**Confidence:** verified-source

12 Hz speech tokenizer. The encoder is a Mimi (MimiModel subclass) using 16 of its 32 quantizers. The decoder takes 16 quantizers (1 semantic + 15 acoustic RVQ, codebook 2048), runs an 8-layer transformer with sliding window 72, then fully causal ConvNeXt and convolution upsampling (×2×2 then ×8×5×4×3), giving exactly 1920 samples per frame at 24 kHz. Output is clamped to [-1, 1]. Decoding uses chunked_decode with chunk=300 frames and left_context=25 frames.

**Evidence:** SC:6-43; T:159-208 (causal conv and transposed conv; the length arithmetic gives T×1920); T:824-896; T:899-909; T:983; T:1012-1015; paper.txt:137, 255.

### 4. Weight VRAM. bf16/fp16: main 3.86 GB + tokenizer 0.34 GB = 4.20 GB (3.91 GiB). fp32: 7.71 + 0.68 = 8.40 GB. Th…

**Confidence:** verified-source

Weight VRAM. bf16/fp16: main 3.86 GB + tokenizer 0.34 GB = 4.20 GB (3.91 GiB). fp32: 7.71 + 0.68 = 8.40 GB. The speech tokenizer is loaded in the same dtype and device as the main model, because dtype and device_map are forwarded to it. Talker KV cache is 112 KiB per token in bf16 (28 layers × 2 × 8 heads × 128 × 2 B). A hidden cost: generate() hard-codes output_hidden_states=True, because getattr() is called on a dict and always returns the default. HF then keeps all 29 layer hidden states for every step, about 116 KiB per token in bf16, until generation ends. Per-sequence memory is therefore about 2× the KV cache. Example: batch 32 × ~610 tokens ≈ 4.3 GiB.

**Evidence:** M:1915-1919 (kwargs forwarded to the tokenizer); M:2064 (getattr(kwargs, 'output_hidden_states', True)); tf/generation_utils.py:2818-2823 (hidden states accumulated per step); M:2280-2281 (only the last layer and the codec ids are used).

### 5. Precision. The checkpoint is stored in BF16, and the official evaluation and examples use dtype=torch.bfloat16…

**Confidence:** reported

Precision. The checkpoint is stored in BF16, and the official evaluation and examples use dtype=torch.bfloat16. fp16 is unsafe: #43 reports device-side asserts from inf/NaN probabilities on Turing and Maxwell GPUs, and open PR #355 says logits exceed the fp16 range (~65,504). The RTX 3090 supports bf16 natively, so use bf16. fp32 doubles memory and gains nothing, since the weights are already bf16.

**Evidence:** safetensors header dtype; README Evaluation ('dtype=torch.bfloat16… max_new_tokens=2048'); S/gh/issues/43.txt; S/gh/issues/355.txt.

### 6. Attention implementation. flash-attn 2 is optional: sdpa and eager are supported (plus flex for the talker), d…

**Confidence:** verified-source

Attention implementation. flash-attn 2 is optional: sdpa and eager are supported (plus flex for the talker), dispatched through ALL_ATTENTION_FUNCTIONS. The README recommends FA2 only to save memory. Issue #333 reports NaN logits with flash_attention_2 on the multilingual test set, while sdpa and eager worked. Recommendation: bf16 + sdpa. The 'flash-attn is not installed' warning comes only from the 25 Hz tokenizer and does not affect this 12 Hz model.

**Evidence:** M:467-477 and M:499-510 (support flags); M:787-789 (dispatch); core/tokenizer_25hz/vq/whisper_encoder.py:35 (warning source); S/gh/issues/333.txt; S/gh/issues/12.txt.

### 7. The two clone modes. ICL mode (the default) caches ref_code (T×16 from the 12 Hz encoder) and the speaker embe…

**Confidence:** verified-source

The two clone modes. ICL mode (the default) caches ref_code (T×16 from the 12 Hz encoder) and the speaker embedding, and uses both at generation time. x-vector-only mode uses only the embedding: its prompt is about 9 positions against about 300-360 for ICL, and the README warns of lower quality. create_voice_clone_prompt caches the tokenizer encode and the speaker-encoder pass. Not cached, and recomputed on every call: the reference-text tokenisation, the reference-code embeddings, the prefill over all reference positions (qwen-tts has no prefix cache), and decoding of the reference codes. The reference codes are prepended before speech_tokenizer.decode and cut off proportionally afterwards, so every request also decodes 23-28 s of reference audio.

**Evidence:** W:40-51, W:355-466, W:612-631; M:2102-2106, M:2188-2197; #341 confirms the proportional cut is exact.

### 8. Speaker embedding. extract_speaker_embedding(audio, sr) asserts sr == 24000. It computes a 128-bin mel on the…

**Confidence:** verified-source

Speaker embedding. extract_speaker_embedding(audio, sr) asserts sr == 24000. It computes a 128-bin mel on the CPU, runs the ECAPA-TDNN in the model dtype, and returns an unnormalised 2048-d vector. The vector is inserted directly, with no projection, as one position of the codec-embedding sequence: [think tags, spk, codec_pad, codec_bos]. That is why its norm matters. The NOTES.md 'mean over clips, rescaled to the typical norm' recipe needs no library change: set VoiceClonePromptItem.ref_spk_embedding (a mutable dataclass) to the mean of the per-clip embeddings (clips resampled to 24 kHz), rescaled to the mean per-clip norm. Pass a list of items; a plain dict breaks ICL mode.

**Evidence:** M:1940-1954; M:365-371 (unnormalised output layer); M:1956-1966 (only moved to device/dtype); M:2166-2172 (insertion point); W:584-586 together with M:2191 (dict path breaks ICL).

### 9. non_streaming_mode matters for quality. The clone default is non_streaming_mode=False, a simulated streaming-t…

**Confidence:** verified-source

non_streaming_mode matters for quality. The clone default is non_streaming_mode=False, a simulated streaming-text layout; CustomVoice and VoiceDesign were switched to True in commit 0c6a7cb. In ICL mode with False, the ref+target text is summed position-by-position over the reference's codec frames, and any overflow is fed one token per generated frame. With our references (shehbaz: 350 frames and 112 text tokens; trump: 290 frames and 67 text tokens), every short, medium and long target text sits entirely in the prefill. PR #362 and issue #239 report that this layout with long references causes speaking-rate drift (+16.7% with a 12.9 s reference) that non_streaming_mode=True removes (0.0%). Benchmark True against False, especially for the Urdu failure modes.

**Evidence:** W:478 and W:513-515; M:1968-2019 (layout); M:1689-1692 (trailing feed); S/gh/issues/362.txt and 239.txt (drift measurements); my token counts from S/tok_test.py.

### 10. Sampling defaults, from generation_config.json. Talker: do_sample, temperature 0.9, top_k 50, top_p 1.0, repet…

**Confidence:** verified-source

Sampling defaults, from generation_config.json. Talker: do_sample, temperature 0.9, top_k 50, top_p 1.0, repetition_penalty 1.05, max_new_tokens 8192 (about 655 s of audio; the wrapper's hard default of 2048 is not used), min_new_tokens 2, EOS 2150. Sub-talker: same temperature, top_k and top_p, no repetition penalty, no EOS, always exactly 15 tokens. The official evaluation used max_new_tokens=2048.

**Evidence:** S/hf/generation_config.json; W:319-351; M:2044-2066; M:1671-1680; C:87 (code predictor repetition_penalty 1.0); tf/generation_utils.py:1141-1142.

### 11. repetition_penalty acts only on codebook 0. It covers the set of codebook-0 tokens generated so far in the utt…

**Confidence:** verified-source

repetition_penalty acts only on codebook 0. It covers the set of codebook-0 tokens generated so far in the utterance: it is presence-based (not counts) and has no window. The talker runs from inputs_embeds only, so HF input_ids start empty; the reference codes, the text and the 15 acoustic codebooks are never penalised.

**Evidence:** tf/generation_utils.py:780-781 (input_ids initialised as (batch, 0)); tf/generation_logits_process.py:385-396 (scatter mask, divide/multiply).

### 12. Only whitelisted kwargs reach the model, although the docstring says any HF generate kwarg can be passed. Mode…

**Confidence:** verified-source

Only whitelisted kwargs reach the model, although the docstring says any HF generate kwarg can be passed. Model.generate swallows **kwargs and forwards only max_new_tokens, do_sample, top_k, top_p, temperature, repetition_penalty, eos_token_id and subtalker_*. no_repeat_ngram_size, min_new_tokens, logits processors, streamer and seed are silently ignored. Seed with torch.manual_seed before the call; the seed is shared across a batch.

**Evidence:** W:536-538 (docstring claim); M:2022-2066 and M:2272-2278 (what is actually forwarded).

### 13. Looping and length failures. EOS is missed about 0.5% of the time on the Base models (#118), and generation th…

**Confidence:** reported

Looping and length failures. EOS is missed about 0.5% of the time on the Base models (#118), and generation then runs to the 8192-frame default. The EOS-list 'fix' posted in #118 cannot work: token 2157 is suppressed and ids above 3071 are outside the 3072-entry codec vocab. Mixed or unsupported scripts hang (#318, Thai: 27 of 30). The start of the output can echo the tail of the reference (#341), and repetition_penalty 1.2-1.4 and greedy decoding did not help there. The shehbaz reference ends with 'السلام علیکم', so watch for a leading greeting. Mitigations: a tight per-request max_new_tokens plus the WER, similarity and duration re-roll guardrails.

**Evidence:** S/gh/issues/118.txt, 318.txt, 341.txt, 80.txt, 181.txt; M:2059-2063 (suppressed range).

### 14. Batching. Passing a list of texts works. A single prompt item is broadcast to all texts, and mixed voices in o…

**Confidence:** verified-source

Batching. Passing a list of texts works. A single prompt item is broadcast to all texts, and mixed voices in one batch are allowed. Prompts are left-padded with an attention mask (rope positions come from the mask), and trailing text is padded with tts_pad. A batch runs until every row hits EOS or max_new_tokens; finished rows are fed EOS and still cost compute. Latency is set by the longest or runaway row, and max_new_tokens and all sampling parameters are one value per batch. There is no continuous batching.

**Evidence:** W:556-586; M:2239-2269; M:1693-1711; tf/generation_utils.py:2832-2843; S/gh/main/repo/examples/test_model_12hz_base.py:91-188.

### 15. Thread safety: not safe. The talker stores rope_deltas as instance state, written on each prefill and read on…

**Confidence:** verified-source

Thread safety: not safe. The talker stores rope_deltas as instance state, written on each prefill and read on each decode step, so concurrent generate calls on one instance race. #350 reports multithreaded calls are slower than sequential and much slower than batching. A qwen-tts backend needs a single worker per model instance with a queue and batching.

**Evidence:** M:1584 and M:1699-1711; S/gh/issues/350.txt.

### 16. No streaming audio in qwen-tts 0.1.1. The only stream-related code is the non_streaming_mode text-layout flag.…

**Confidence:** verified-source

No streaming audio in qwen-tts 0.1.1. The only stream-related code is the non_streaming_mode text-layout flag. A Qwen collaborator said in #10 that the package targets demos and batch offline use, and that streaming belongs to vLLM-Omni. The architecture does support it: the decoder is fully causal and chunked_decode uses 25 frames of left context. The paper uses packets of 4 frames (320 ms).

**Evidence:** grep over the package source; S/gh/issues/10.txt; T:886-896; paper.txt:255.

### 17. Languages. Allowed values are 'auto' plus chinese, english, german, italian, portuguese, spanish, japanese, ko…

**Confidence:** verified-source

Languages. Allowed values are 'auto' plus chinese, english, german, italian, portuguese, spanish, japanese, korean, french and russian, case-insensitive; 'Urdu' raises ValueError. 'Auto' sets no language tag: the codec prefix is [nothink, think_bos, think_eos] instead of [think, think_bos, lang_id, think_eos]. The README advises setting the language explicitly when it is known, and the official evaluation mostly did, so try language='English' for trump.

**Evidence:** C:115-126; M:1831-1834, M:2110-2147; W:141-163, W:557.

### 18. Urdu tokenisation. The text tokenizer is Qwen2 byte-level BPE (151,643 merge-vocab entries), so Urdu never pro…

**Confidence:** verified-source

Urdu tokenisation. The text tokenizer is Qwen2 byte-level BPE (151,643 merge-vocab entries), so Urdu never produces <unk>, but it is nearly character-level: 0.71 tokens/char and 3.1-3.2 tokens/word, against 1.3 tokens/word for English. Pool means in text tokens: Urdu 33/82/194/304 and English 13/33/77/154 for short/medium/long/xlong. At 3-4 words/s, Urdu consumes 10-13 text tokens/s, close to the 12.5 frames/s text feed.

**Evidence:** My measurement with S/tok_test.py, using the repo's vocab.json and merges.txt and the Qwen2 PRETOKENIZE_REGEX (tf/qwen2_tok.py:39).

### 19. Tokenizer quirk. qwen-tts loads the processor with fix_mistral_regex=True. Under transformers 4.57.3, a model…

**Confidence:** verified-source

Tokenizer quirk. qwen-tts loads the processor with fix_mistral_regex=True. Under transformers 4.57.3, a model with config transformers_version 4.57.3 loaded from a local directory gets its pre-tokenizer regex replaced by the Mistral regex; loading by hub id keeps the Qwen regex. Upstream fixed this only in transformers PR #45444, on the v5 line. Impact on our data is tiny: 4 of 576 Urdu pool texts differ (tanween), 0 English texts differ, and the shehbaz reference text differs by 1 token. Pin one loading path.

**Evidence:** W:118; C:166; tf/tub.py:1957, 2461-2502; S/tok_regex_diff.py; https://github.com/huggingface/transformers/pull/45444 ('non-Mistral model type early exit was nested inside a version check').

### 20. Edge case: the target text is sliced input_id[:, 3:-5] after the '<|im_start|>assistant\n' wrapper. A text tha…

**Confidence:** verified-source

Edge case: the target text is sliced input_id[:, 3:-5] after the '<|im_start|>assistant\n' wrapper. A text that starts with a newline merges with the role's '\n' token and shifts the slice, so strip input text.

**Evidence:** M:2190; W:269-270; S/tok_test.py output ('assistant\n\nhello' → ['assistant','\n\n','hello']).

### 21. Official performance (paper Table 2). Measured on Qwen's internal vLLM V0 engine with torch.compile and CUDA g…

**Confidence:** verified-doc

Official performance (paper Table 2). Measured on Qwen's internal vLLM V0 engine with torch.compile and CUDA graphs on the tokenizer decode, on an unnamed 'single typical computational resource'. For 12Hz-1.7B: concurrency 1 gives first packet 101 ms (97 ms LM + 4 ms decode) and RTF 0.313; concurrency 3 gives 195 ms and RTF 0.363; concurrency 6 gives 333 ms and RTF 0.463. The 0.6B model reaches 97 ms. The README claims no RTF for the qwen-tts package; its quality numbers for 1.7B-Base are Seed test-en WER 1.24 and multilingual English WER 0.934 / SIM 0.775.

**Evidence:** paper.txt:125 and paper.txt:161-253; README evaluation tables (S/src_readme.md).

### 22. Community speed numbers for stock qwen-tts: RTF about 1.47 on H100 and about 3.31 on L4 (VoiceDesign 1.7B). Wi…

**Confidence:** reported

Community speed numbers for stock qwen-tts: RTF about 1.47 on H100 and about 3.31 on L4 (VoiceDesign 1.7B). With torch.compile and CUDA graphs: 0.40 and 0.74. Early vLLM-Omni was reported at RTF about 1.6 on a 4090 (January). torch.compile of the codec decoder gave 3-4× batch decode speedups (PR #191, not merged).

**Evidence:** S/gh/issues/89.txt lines ~474-485 and ~86; S/gh/issues/191.txt.

### 23. Package status. qwen-tts 0.1.1 (2026-02-06) is the latest release; GitHub main has no code changes since. Vers…

**Confidence:** verified-source

Package status. qwen-tts 0.1.1 (2026-02-06) is the latest release; GitHub main has no code changes since. Versions before 0.1.0 had decoder padding bugs: a transposed-conv trim fix in 0.1.0, and in 0.1.1 the batch-decode padding changed from 0 to -1 (before this, any frame whose first code was 0 shortened the audio). Any port such as vLLM-Omni should be checked for these fixes. The README's line that vLLM-Omni supports only offline inference is out of date.

**Evidence:** PyPI JSON (release dates); GitHub commits 5f8581d and 6cafe55 (diffs fetched); diff -r between the wheel and main is empty.

## Risks

- The default max_new_tokens of 8192 (about 655 s of audio), combined with about 0.5% EOS misses and hangs on unsupported or mixed scripts, can stall a worker and a whole batch. Every request needs a tight per-request cap.
- Thread safety: rope_deltas is instance state, so concurrent generate() calls on one qwen-tts instance are unsafe. Use a single worker per instance with batching.
- Batch latency is set by the longest or runaway row. Sampling parameters and max_new_tokens are shared per batch, and per-request seeds cannot be honoured inside a batch.
- Extra HF kwargs (no_repeat_ngram_size, seed, streamer, logits processors) are silently ignored. Benchmark code that relies on them would measure nothing.
- Memory: the forced output_hidden_states roughly doubles per-token memory; separately, #242 reports VRAM growth across generations. Run soak tests and watch memory.
- Quality: in the default streaming-text ICL layout, long references (ours are 23-28 s) are reported to cause speaking-rate drift. There is also a reported reference-tail echo; our shehbaz reference ends with a greeting. Both could inflate Urdu WER and failure rates if not controlled.
- fp16 is reported to overflow into NaN/inf, and FA2 produced NaN logits in #333. Stay with bf16 + sdpa.
- Tokenisation differs slightly between loading from a local directory and loading by hub id (the transformers 4.57.3 regex bug), and possibly between qwen-tts and vLLM-Omni. The effect is small (4 of 576 Urdu texts) but it affects reproducibility.
- Every request re-decodes 23-28 s of reference audio and re-runs the full reference prefill. At high concurrency this may cost a lot of throughput in a qwen-tts-based backend.
- The paper's 97/101 ms and RTF numbers come from an internal vLLM V0 engine on an unnamed GPU. They are not a target we can expect vLLM-Omni or qwen-tts to reach on a 3090.

## Open questions

- What are the actual RTF, latency and VRAM of stock qwen-tts on an RTX 3090 in bf16 vs fp32, at batch 1/4/8/16? This could not be measured under the GPU ban.
- Does vLLM-Omni's Qwen3-TTS port use the streaming-text ICL layout (non_streaming_mode=False) or the non-streaming one? Does it prepend the reference codes for decoding, include the 0.1.0/0.1.1 decoder padding fixes, and use the Qwen or the Mistral pre-tokenizer regex?
- Does fp16 work at all for this model on Ampere, or does it overflow as reported on Turing? Not needed if bf16 is used.
- What is the 'typical norm' of the 2048-d speaker embeddings for our clips (in bf16 vs fp32), and does a mean embedding help in ICL mode, where the reference codes also carry speaker identity?
- Does non_streaming_mode=True reduce the Urdu skip, cut-short and runaway failures and the English pace drift? How do repetition_penalty 1.1 and 1.2 (codebook 0 only) trade loop suppression against pace and quality?
- Does the shehbaz reference (ending in 'السلام علیکم') cause the reported reference-tail echo at the start of outputs?
- Is decoding only the last ~25 reference frames as left context audibly identical to decoding the full reference? This is the throughput optimisation for a qwen-tts backend.
- For trump, is language='English' better than 'Auto' on WER and pace?
- Is #223's claim of lost samples at chunk boundaries real in 0.1.1? My length arithmetic says the decoder output is exactly T×1920 samples, and #341 confirms exact lengths empirically.
