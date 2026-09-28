# Higgs TTS 3 on this box: what was checked before the first run (2026-09-28)

Sources: the model card and files of `bosonai/higgs-tts-3-4b` (HF, revision 239f63fb, last modified 2026-09-04;
README.md, PROMPTING.md, AGENTS.md, LICENSE, config.json), the vLLM-Omni 0.28.0 package installed in
`server/venvs/engine` (read at the paths below), the vLLM-Omni recipe
(github.com/vllm-project/vllm-omni/blob/main/recipes/BosonAI/Higgs-Audio-V3-TTS.md), the SGLang-Omni cookbook
(sgl-project.github.io/sglang-omni/cookbook/higgs_tts.html), the LMSYS launch post
(lmsys.org/blog/2026-06-04-higgs-audio-v3-tts) and an optimisation write-up (popsoda2002.github.io/higgs_tts_v3.html).
"Verified" below means read in the installed source or the model files; "reported" means a third-party claim.

## The model (verified from the model card / config)

- `bosonai/higgs-tts-3-4b` is the only Higgs TTS 3 checkpoint Boson publishes (the older names
  `higgs-audio-v3-tts-4b` in the vLLM-Omni docs point at the same repo; `bosonai/higgs-tts-2-3b-base` is the previous
  generation). One `model.safetensors` of 9.31 GB (bf16), `model_type: higgs_multimodal_qwen3`, backbone Qwen3-4B
  (hidden 2560, 32 query / 8 KV heads), 8 codebooks at 25 fps (2048-frame default cap = 82 s), 24 kHz output.
- Zero-shot voice cloning from a reference clip; the transcript "materially improves cloning fidelity". 43 inline
  control tags `<|category:tag|>` (21 emotions, 10 prosody, 3 styles, 9 sound effects; PROMPTING.md). Unknown tags are
  read out loud.
- 100+ languages. **Urdu is in the model card's "WER/CER under 5, polished, production-quality" list** (85 languages),
  unlike Qwen3-TTS, which has no Urdu language id at all.
- Boson's recommended sampling for voice cloning: `temperature 0.8, top_k 50, max_new_tokens 1024`
  (README "Voice cloning"); SGLang-Omni's own defaults are temperature 1.0, top_p / top_k unset, 2048 tokens.
- Boson's hardware note (AGENTS.md): benchmarked on 1x H100 80 GB, "confirmed on 1x A100 40 GB"; **24 GB cards are
  "reported to work, not officially verified"**, with the advice to lower concurrency / max_new_tokens.
- Published speed (SGLang-Omni, 1x H100, bf16, CUDA graphs, Seed-TTS EN): c=1 617 ms mean latency, RTF 0.147,
  6.9 audio s/s; c=8 898 ms, RTF 0.217, 37.4 audio s/s; c=16 1079 ms, RTF 0.262, 61.8 audio s/s; streaming TTFB
  ~350 ms. vLLM-Omni's recipe: ~35 audio s/s on an H20 at c=16. There are no published RTX 3090 numbers.
- Published quality (macro WER/CER): Seed-TTS 1.11 %, CommonVoice-3 (9 langs) 4.41 %, MiniMax-Multilingual (23)
  2.74 %, Higgs-Multilingual (111) 3.61 %.

## The licence (verified: LICENSE, "Last Updated: July 8, 2026")

Research and non-commercial only. Explicitly allowed for a for-profit entity: "limited internal evaluation,
benchmarking, security testing" that is not deployed in production, not made available to end users, not used to
generate revenue. **Hosting it behind an API, embedding it in a product, or any production use needs a separate
commercial licence from Boson** (contact@boson.ai). Also prohibited: cloning a voice without consent, impersonation.
So this folder is a benchmark, not a deployment: the Qwen3-TTS service stays the production candidate unless the
team licenses Higgs.

## Serving it here (verified in `server/venvs/engine`, vllm-omni 0.28.0)

- The installed vLLM-Omni already serves Higgs TTS 3: `vllm_omni/model_executor/models/higgs_audio_v3/`
  (talker + code2wav + tokenizer adapter), registry `config/pipeline_registry.py:185`
  (`higgs_multimodal_qwen3` -> HIGGS_AUDIO_V3_PIPELINE), deploy profiles `vllm_omni/deploy/higgs_multimodal_qwen3*.yaml`
  with `README_higgs_audio_v3.md`. Same two-stage layout as Qwen3-TTS: stage 0 = the 4B talker (LLM_AR), stage 1 =
  code2wav (the codec decoder, bundled in the checkpoint), shared-memory connector, `async_chunk: true`, first chunk
  after 1 frame then 25 frames (1 s) with 25 frames of left context and 4 of right hold-back
  (`stage_input_processors/higgs_audio_v3.py`). Stop tokens 151643 / 151671.
- Requests go through the same `POST /v1/audio/speech` (`serving_speech.py:1628 _build_higgs_audio_v3_params`):
  plain TTS = `input` only; voice clone = `ref_audio` (data: URL / http / file) + optional `ref_text`; the prompt is
  `<|tts|> <|ref_text|> {ref text} <|ref_audio|> [-100 x N] <|text|> {text} <|audio|>`. `task_type` and `language`
  are Qwen fields; Higgs takes neither (the bench sends `--task-type none --language none`).
- **Reference clips must be 1-30 s** (`serving_speech.py:106-107`, enforced at `:1115-1123` for every model), so the
  39 s `voices/shehbaz/references/higgs-v3.wav` the Kaggle Higgs runs used is rejected; the benchmark uses
  `references/qwen3-tts.wav` (28.0 s shehbaz, 23.2 s trump), the same clip as the Qwen benchmark, which also makes the
  comparison reference-for-reference (the model card's own methodology: "every model shares the same reference audio
  per prompt").
- Reference encoding uses the Higgs v2 codec from `k2-fsa/OmniVoice` `audio_tokenizer/` (806 MB;
  `higgs_audio_v2_tokenizer.py:166-262`: Boson's own `higgs-audio-v2-tokenizer` repo ships the wrong weights). Found
  through `HIGGS_AUDIO_TOKENIZER_PATH`, else `snapshot_download` at the first clone request, which cannot happen with
  the engine's `HF_HUB_OFFLINE=1`: `higgs/engine/run_higgs.sh` pre-resolves the cached snapshot. Encoded reference
  codes are cached per clip (LRU 256 entries / 64 MiB, `serving_speech.py:112-113`), so a registered or repeated clip
  costs the encoder once.
- Per-request `extra_params.{temperature, top_p, top_k}` and `seed` apply to every model (`serving_speech.py:3080-3115`,
  not Qwen-only), and `extra_params.repetition_penalty` through the engine patch already applied to this venv.
  `max_new_tokens` maps to the talker's `max_new_tokens` (frames at 25 fps). Uploaded voices (`POST /v1/audio/voices`)
  work for Higgs (`serving_speech.py:959-1001`), without speaker embeddings.
- Upstream deploy profiles pin **`seed: 42`** in the stage-0 sampling defaults, i.e. every take of a prompt would be
  identical: `higgs/engine/deploy/*.yaml` drop the seed and use Boson's cloning sampling (0.8 / 50 / top_p 1.0). The
  high-throughput profile keeps stage 0 `enforce_eager: true` (Higgs' own local MLP CUDA graph); the low-latency profile
  captures vLLM `FULL_DECODE_ONLY` graphs for batch 1-16 (the two graph paths are mutually exclusive). Stage 0 pins
  `attention_backend: FLASHINFER` with the TRT-LLM XQA path off (README_higgs_audio_v3.md: XQA was 5 % slower on H800);
  `flash_attn.yaml` is the fallback if FlashInfer needs a JIT kernel this venv cannot build (the sampler story in
  `server/engine/run_engine.sh`).
- Memory: upstream 0.60 (stage 0) + 0.25 (stage 1) of the card = 20.9 GB of 24 GB; with the desktop's 0.35 GB that is
  the whole 3090, so the Qwen3-TTS units (21 GB) must be stopped while Higgs runs. Talker KV per token: 36 layers x 8 KV
  heads x 128 x 2 x 2 B = 144 KiB (Qwen3-TTS: 112 KiB); a 30 s reference is 750 prompt rows + its transcript, a 30 s
  take 750 more, so ~1,600 tokens per xlong request.

## Alternatives not built

- **SGLang-Omni** is Boson's reference stack (Docker image, `sgl-omni serve`), with radix caching of references and
  batched vocoder decode; its cookbook benchmarks only H100 and its Ampere support is unstated (the Qwen research,
  `server/docs/research/alternatives.md`, found its 3090 status "unvalidated: roadmap 4090/5090"). Not installed:
  ~30 GB free disk would be needed for a second CUDA stack, and the vLLM-Omni path already exists here.
- The Boson hosted API and MLX-Audio (Mac) are not applicable.
