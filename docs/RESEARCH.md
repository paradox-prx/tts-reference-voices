# Research notes: fine-tuning Qwen3-TTS for Urdu (2026-09-29)

## 1. What the model is and how it conditions on language and voice

Qwen3-TTS-12Hz-1.7B-Base = a 28-layer Qwen3 "talker" (2048 hidden) that predicts codebook 0 of a 16-codebook,
12.5 Hz speech codec, a 5-layer code predictor (MTP) that fills codebooks 1-15 of each frame from the talker's hidden
state, an ECAPA speaker encoder (frozen, 2048-d x-vector from a 24 kHz mel) and the Code2Wav decoder. It was
pre-trained on 5M+ hours in 10 languages (zh, en, de, it, pt, es, ja, ko, fr, ru) and post-trained with DPO / GSPO
(technical report, arXiv 2601.15621). Urdu is not among the ten: the model reads it through the "Auto" language
path with a foreign accent (our benchmark: WER 0.34, CER-nospace 0.14 on Whisper large-v3, severe failures 3-8%).

Language is an explicit codec-channel token: the prefix is `[think, think_bos, LANG, think_eos]` when a language is
given and `[nothink, think_bos, think_eos]` for Auto. The ids live in `talker_config.codec_language_id` (2050-2074);
row 2080 of the codec embedding is untrained in the Base checkpoint (norm 0.03 vs 1.1-1.3 for trained rows), so an
Urdu tag can be added there and initialised from the mean of the ten language rows. vLLM-Omni reads the map from
config.json, so a checkpoint with `"urdu": 2080` serves `language: Urdu` without code changes.

Voice cloning has two prompt forms, both used by the production gateway: x-vector only (the speaker embedding in the
prefix) and in-context (ICL: the reference clip's text and codes precede the target text, plus the x-vector). The
training format must contain both, or the fine-tuned model drifts away from what the server sends.

## 2. The official fine-tuning code and its bugs

`QwenLM/Qwen3-TTS/finetuning` (commit 022e286, March 2026): `prepare_data.py` extracts codes, `dataset.py` lays out
`{audio, text, ref_audio}` rows in the x-vector-only, non-streaming form, `sft_12hz.py` trains every parameter of
the model except the speaker encoder with AdamW (bf16) and saves a CustomVoice-type checkpoint with one registered
speaker (row 3000). It is single-speaker by construction and has three defects that we verified in the source:

1. **Talker labels shifted twice.** The script passes `inputs[:, :-1]` and `labels[:, 1:]`, and `talker.forward`
   then applies transformers' `ForCausalLMLoss`, which shifts again. Position t is trained to predict frame t+2.
   Symptom reported as "speech gets faster every epoch" (issue #179, PR #178 discussion). The instavar LoRA repo
   fixed it with a manual cross-entropy.
2. **Code-predictor labels off by one frame and one codebook.** `hidden_states[codec_mask[:, :-1]]` pairs the hidden
   state at frame j with frame j's codes, while at inference the code predictor consumes the hidden state that
   produced frame j (the previous position); `forward_finetune` then applies the shifted loss again.
3. **Text embeddings without `text_projection`.** The script uses `talker.model.text_embedding(ids)` directly; every
   inference path uses `talker.text_projection(text_embedding(ids))`. The shapes agree (both 2048) so nothing
   errors, but training and inference see different text vectors.

Our trainer keeps the model package untouched (`qwen-tts 0.1.1`) and replaces only the layout and the loss
(`qwen_train/layout.py`, `model_utils.py`), mirroring `generate()` and `generate_icl_prompt()` position by position.
`check_alignment.py` confirms it with the pretrained model: teacher-forced next-frame accuracy under our layout versus
the official shifts (see docs/EXPERIMENTS.md for the numbers).

## 3. What others got on new languages

| who | language | data | method | result |
|---|---|---|---|---|
| vadimbelsky/qwen3-TTS-KSA (HF) | Saudi Arabic | ~13k utterances, 1 speaker | official script, full FT, lr 2e-6, 5 epochs, accum 4 (~32/step), Arabic tag initialised from the mean of language rows | published weights, no metrics, custom-voice speaker only |
| issue #323 | Bengali | 7 h, 1 speaker | official script, lr 2e-6, 10 epochs, 3090 | "Bengali with a Hindi/foreign accent", loss plateaus after 2-3 epochs; closed unanswered |
| issue #27 | Turkish | 15 h, 1 speaker | official script | unintelligible noise |
| discussion #208 | Arabic | 103 h, 33k clips | official script, lr 2e-6, 5 epochs | no answer |
| discussion #189 | Persian | "rich" single speaker | grapheme first, then a language tag in the prompt; phonemes helped homographs | reported success on the 0.6B model |
| aguken-ai Indic LoRA (HF) | 15 Indic languages | 500 utterances per language/gender | LoRA r16 on 0.6B, lr 2e-6, 5 epochs | weights only |
| arXiv 2604.26136 | Arabic (scientific speech) | not stated | fine-tuned Qwen3-TTS | CER 0.071, SIM 0.72, best of the compared cloners |

Nobody documents multi-speaker training that keeps zero-shot cloning; everybody trains the x-vector-only layout the
official script provides.

## 4. Is 300 h across 8-10 speakers enough?

* **For the language: yes.** Every attempt above used 7-100 h; accent problems appeared at 7 h with one speaker.
  300 h of clean studio Urdu is more than the corpora single-language TTS models are trained on from scratch
  (LJSpeech 24 h, LibriTTS 585 h for a multi-speaker English model). The Qwen text tokenizer covers the Urdu script
  (0.6-0.75 tokens per character, no unknowns).
* **For cloning unseen voices: the risk is speaker diversity, not hours.** Ten speakers cannot teach a general
  voice space; cloning of new voices has to come from the pretrained model and survive the fine-tune. Measures taken:
  ICL-format training (a second clip of the same speaker as the prompt, 70% of examples) so the prompt-following
  pathway is exercised rather than bypassed; the speaker encoder stays frozen; the Qwen text embedding stays frozen;
  a held-out speaker is never trained and is scored for similarity; the Shehbaz clip (unseen speaker) and the Trump
  clip (English retention) are scored at every checkpoint; a LoRA config is available if the full fine-tune hurts
  either. If cloning of unseen speakers degrades, the levers are: fewer epochs, lower lr, LoRA, and adding speakers
  (even 30-50 min each of 20 more speakers matters more than more hours of the same ten).
* **Voice design: not covered by any recipe.** VoiceDesign is a separate checkpoint trained with text descriptions and
  a "thinking" prompt; there is no public fine-tuning path. The trainer supports the instruct layout
  (`instruct_field`) so the VoiceDesign checkpoint can be fine-tuned on Urdu with per-speaker descriptions as
  experiment 2, but with ten voices it can only learn ten descriptions; how much of its design ability survives in
  Urdu is unknown until measured.

## 5. Compute

Per 300 h epoch: ~13.5M codec frames + ~9M text tokens, doubled by the ICL references (the model attends over the
reference codes too) ≈ 35M tokens through a 1.7B model ≈ 3.6e17 FLOPs. Measured throughput decides the wall time
(docs/EXPERIMENTS.md); the RTX 3090 estimate is 5-6 h per epoch, an A100/H100 roughly 3-5x faster. Memory: full
fine-tune in bf16 with Kahan-summation AdamW ≈ 14 GB + activations (fits 24 GB with gradient checkpointing);
fp32-master weights need ~27 GB + activations (40-80 GB cards). Pure-bf16 AdamW without Kahan summation silently
loses updates smaller than bf16's resolution at lr ≤ 1e-5, which is why `torch-optimi` is used in the 24 GB config.

## Sources

- Qwen3-TTS technical report: https://arxiv.org/abs/2601.15621
- Official fine-tuning: https://github.com/QwenLM/Qwen3-TTS/tree/main/finetuning
- Speech speeds up per epoch: https://github.com/QwenLM/Qwen3-TTS/issues/179 and PR #178
- New-language threads: issues #27, #323; discussions #83, #189, #208
- KSA Arabic model card: https://huggingface.co/vadimbelsky/qwen3-TTS-KSA
- Indic LoRA adapters: https://huggingface.co/aguken-ai/Qwen3-TTS-0.6B-LoRA-Finetuned-Indic-Multilingual
- LoRA companion repo (loss fix): https://github.com/instavar/qwen3-tts-lora-finetuning
- vLLM-Omni speech API: https://docs.vllm.ai/projects/vllm-omni/en/latest/serving/speech_api/
