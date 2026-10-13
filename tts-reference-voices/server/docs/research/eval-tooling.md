# Research: eval-tooling

_Quality-evaluation tooling for Qwen3-TTS outputs (English + Urdu): ASR/WER, text normalization, speaker similarity, loop/skip detection, retry-policy evaluation. Research plus CPU-only calibration on this box; nothing ran on the GPU. Scratch root: /tmp/claude-1013/-home-vector/60c91189-44d6-4cdb-b0f5-2bf4adb23fb3/scratchpad/research/eval-tooling/ (code in lab/, sha-verified models in models/, venvs asrvenv/ and venv/)._

Produced 2026-09-24 by a research subagent (workflow wf_6c83c01a-7e3). Confidence: verified-source = read in the
package source; verified-doc = official docs/issue text; reported = third-party claim; unverified = not checked.

## Findings

### 1. Recommended ASR: faster-whisper 1.2.1 + ctranslate2 4.8.2, model large-v3 (Systran/faster-whisper-large-v3 rev…

**Confidence:** verified-source

Recommended ASR: faster-whisper 1.2.1 + ctranslate2 4.8.2, model large-v3 (Systran/faster-whisper-large-v3 rev edaa852e, model.bin sha256 69f74147…), float16 on GPU, beam 5, WhisperModel.transcribe (sequential long-form, not BatchedInferencePipeline), language forced, condition_on_previous_text=False, vad_filter=False, word_timestamps=True. Run 2-4 num_workers from a thread pool for throughput. Use a separate venv without torch.

**Evidence:** faster_whisper-1.2.1 METADATA Requires-Dist lists ctranslate2, onnxruntime, av, tokenizers and huggingface-hub, and no torch. Tested end to end on CPU: lab/asr_eval.py on 11 real clips and 8 synthetic failure clips (outputs asr_refs_int8_v2.jsonl, asr_synth.jsonl). The model sha matches the HF LFS oid.

### 2. cuDNN is no longer needed for faster-whisper. The ctranslate2 4.8.2 Linux wheel only dlopens libcublas.so.12 (…

**Confidence:** verified-source

cuDNN is no longer needed for faster-whisper. The ctranslate2 4.8.2 Linux wheel only dlopens libcublas.so.12 (plus libcuda.so.1 and libnccl.so.2), links cudart statically, and ships sm_86 SASS. The faster-whisper README still says cuDNN 9, which is out of date.

**Evidence:** In libctranslate2-fd146744.so.4.8.2, readelf shows no CUDA NEEDED entries. `strings` finds libcublas.so.12, libcuda.so.1 and libnccl.so.2, and no 'cudnn' string at all. cuobjdump lists sm_53…sm_86. CTranslate2 CHANGELOG v4.6.3: 'Conv1d pure CUDA implementation (#1949), makes cuDNN an optional dependency'. faster-whisper METADATA lines 103-106 still list 'cuDNN 9 for CUDA 12'.

### 3. This box has cuBLAS 12 under /usr/local/cuda-12.8/lib64 and /usr/local/cuda-12.9/lib64, but neither is on the…

**Confidence:** verified-source

This box has cuBLAS 12 under /usr/local/cuda-12.8/lib64 and /usr/local/cuda-12.9/lib64, but neither is on the loader path (LD_LIBRARY_PATH is empty). ctranslate2 only adds DLL directories on Windows. Install with: `pip install faster-whisper==1.2.1 ctranslate2==4.8.2 nvidia-cublas-cu12==12.9.2.10 jiwer==4.0.0 soundfile regex more_itertools numpy`, then set LD_LIBRARY_PATH to the nvidia/cublas/lib directory (or to /usr/local/cuda-12.9/lib64). A dry run resolves cleanly (onnxruntime 1.30.0, av 18.1.0, tokenizers 0.23.2).

**Evidence:** `ls` of /usr/local/cuda-12.x/lib64 found libcublas.so.12.8.4.1 and 12.9.1.4. ctranslate2/__init__.py lines 4-21 are a Windows-only add_dll_directory block. `pip install --dry-run --report` output was checked.

### 4. Do not put ctranslate2 in the same venv as the default PyPI torch unless you also add cu12 cuBLAS. torch 2.11.…

**Confidence:** verified-source

Do not put ctranslate2 in the same venv as the default PyPI torch unless you also add cu12 cuBLAS. torch 2.11.0 and 2.13.0 on PyPI now pull CUDA 13 (cuda-toolkit 13.0.x, nvidia-cudnn-cu13), which provides libcublas.so.13, not .so.12. torchaudio's last release is 2.11.0 (2026-03-23), so the SIM venv should pin torch==2.11.* with torchaudio==2.11.*.

**Evidence:** PyPI JSON requires_dist for torch 2.13.0: 'cuda-toolkit[...]==13.0.3', 'nvidia-cudnn-cu13==9.20.0.48'. torch 2.11.0: cuda-toolkit 13.0.2. torchaudio release list ends at 2.11.0 and its 2.11.0 wheels were uploaded 2026-03-23.

### 5. BatchedInferencePipeline does not batch across files. It VAD-chunks one audio into pieces of 30 s or less, for…

**Confidence:** verified-source

BatchedInferencePipeline does not batch across files. It VAD-chunks one audio into pieces of 30 s or less, forces condition_on_previous_text=False and does not seek. For thousands of 3-60 s takes, get throughput from num_workers instead: CTranslate2 inter_threads share one copy of the weights on the same GPU.

**Evidence:** faster_whisper/transcribe.py lines 386-470 (VAD chunking per single audio) and 545-551 (condition_on_previous_text=False). num_workers doc at lines 654-657. opennmt.net/CTranslate2/parallel.html: 'When the workers are running on the same device, the model weights are shared to save on memory'.

### 6. VRAM and speed. README figures (large-v2, RTX 3070 Ti, 13 min of audio): fp16 beam 5 takes 4525 MB and 63 s (~…

**Confidence:** unverified

VRAM and speed. README figures (large-v2, RTX 3070 Ti, 13 min of audio): fp16 beam 5 takes 4525 MB and 63 s (~12x realtime); with batch 8, 6090 MB and 17 s; int8 takes 2926 MB. large-v3 has the same 1550M parameters. Estimate for a 3090: ~4.5 GB per worker, ~6-8 GB with 4 workers, roughly 50-100x realtime aggregate, so a full matrix of ~6-7 h of audio takes ~5-10 min. Measured here on CPU (int8, 8 threads): ~2x realtime for Urdu including a language-ID pass, ~4x for English.

**Evidence:** faster-whisper METADATA lines 58-75. whisper-large-v3 model card parameter table. CPU timings are the asr_s fields in lab/asr_refs_int8.jsonl (8 shehbaz clips = 90 s of audio in 41.9 s; trump 23 s in 6.0 s). The 3090 figures are scaled estimates.

### 7. transformers Whisper is usable (batches across files, sequential or chunked long-form) but brings torch and tr…

**Confidence:** verified-source

transformers Whisper is usable (batches across files, sequential or chunked long-form) but brings torch and transformers into the eval venv (qwen-tts pins transformers 4.57.3; latest is 5.17.0). seed-tts-eval's English WER script needs two changes before we could use it. First, it truncates to a single 30 s window with greedy fp32 decoding and does no number normalization. Second, it imports jiwer.compute_measures, which no longer exists in jiwer 4.0.0.

**Evidence:** seed-tts-eval run_wer.py lines 21-25, 35-59, 88-96 (processor(wav) gives one 30 s input). grep finds no compute_measures anywhere in installed jiwer 4.0.0. Model card lines 191-208 and 311-328.

### 8. Reject vLLM Whisper for scoring. It pre-splits audio longer than 30 s into fixed chunks, and open bugs silentl…

**Confidence:** reported

Reject vLLM Whisper for scoring. It pre-splits audio longer than 30 s into fixed chunks, and open bugs silently drop audio. That under-counts exactly the loops and fillers we need to detect. Beam search is documented as 'highly inefficient' and verbose_json has no no_speech_prob.

**Evidence:** vllm issue #53144 (open, v0.27.1, 2026-08-20): 'Whisper transcription silently drops audio when the decoder stops early inside a chunk'. #58029 (open, 2026-09-21): verbose_json 'silently drops words after the last complete segment at every chunk cut'. PR #57769 (merged 2026-09-21) fixed an offline crash on clips over 30 s. docs.vllm.ai speech_to_text page.

### 9. Force language='ur' (and 'en'). Log auto-LID probabilities only as a drift diagnostic. On the speaker's real b…

**Confidence:** verified-source

Force language='ur' (and 'en'). Log auto-LID probabilities only as a drift diagnostic. On the speaker's real broadcast Urdu, auto-detect chose 'ur' for all 9 files, but p(ur) fell to 0.718 on shehbaz_07 (en 0.102, hi 0.099). Accented TTS Urdu will have less margin. Hindi and Urdu are the same spoken language, and the output script follows the language token.

**Evidence:** lab/auto_vs_forced.py output: p(ur) 0.718-0.996. github.com/openai/whisper/discussions/118 and /1662 describe Hindi/Urdu detection confusion and wrong-script output (the forced-language script bug seen with base was fixed in large models).

### 10. Whisper's own error on real Urdu makes the 0.22 WER rule from NOTES unusable for Urdu. Published figures: FLEU…

**Confidence:** verified-source

Whisper's own error on real Urdu makes the 0.22 WER rule from NOTES unusable for Urdu. Published figures: FLEURS Urdu WER is 22.6% (large-v2) and 25.0% (large). Zero-shot whisper-large on read Urdu is 24-26% WER (ARL 26.25, CSaLT 24.44) and 18.3% on conversational speech. On this speaker's 8 real clips, large-v3 with the proposed normalizer gives corpus WER 13.1%, CER 3.5% and CER-nospace 3.8%. Per clip, WER ranges 0-28.6% and CER-nospace 0-8.6%. 2 of the 8 real human clips would fail WER>0.22. This floor is optimistic, because those transcripts were hand-corrected starting from Whisper large-v3 output.

**Evidence:** Whisper paper arXiv 2212.04356, Table 13 (FLEURS), Urdu column. 'WER We Stand' arXiv 2409.11252, Table 3. Our run is in lab/asr_refs_int8.jsonl; the errors are mostly homophone spellings (ضیاع→زیاہ, پرعزم→پرعظم, وسطی→وستہ) and word splits (حتی المقدور→حد تل مقدور). The note on voices/shehbaz/clips.json says the transcripts came from Whisper large-v3 and were then hand-corrected.

### 11. Whisper large-v3 swallowed synthetic Urdu loops. When a 0.35 s syllable was spliced in 12 times, or a 2.5 s ph…

**Confidence:** verified-source

Whisper large-v3 swallowed synthetic Urdu loops. When a 0.35 s syllable was spliced in 12 times, or a 2.5 s phrase 3 times, into a real Urdu clip, the forced-'ur' transcript was identical to the clean clip (WER 0.056 unchanged). The same splice in English was transcribed (21-word insertion run, repeat_excess 12). So ASR text checks cannot be the only Urdu loop detector. What does catch the Urdu loops is word timing: the longest word timestamp stretches to 4.9-5.5 s and is 98-99% voiced. On real clips the longest word is 1.0-2.2 s. A 4 s pause also gives a long word (5.24 s), but only 26% voiced.

**Evidence:** lab/asr_synth.jsonl and lab/word_timing.py. The fields w_max_word_dur_s and w_max_word_voiced are from word_timing_checks() in lab/tts_checks.py. The synthetic cases are real recordings spliced together, not Qwen output.

### 12. Hallucination handling. With vad_filter=False, large-v3 did not hallucinate text into a 6 s digital-silence ta…

**Confidence:** verified-source

Hallucination handling. With vad_filter=False, large-v3 did not hallucinate text into a 6 s digital-silence tail or a 6 s tail of -50 dBFS noise; transcripts were unchanged. Both tails were still flagged: unaligned_tail_s was 6.43 s (0.09-0.49 s on real clips), and the digital-silence tail also showed trail_sil_s 6.0. The literature still reports large-v3 hallucinating on silence, and worse on low-resource languages. Keep condition_on_previous_text=False and the default fallback thresholds, measure silence from the waveform, and record seg_max_cr and seg_fallback.

**Evidence:** lab/asr_synth.jsonl. openai/whisper discussion #1762 (hallucinations in 'silent or music-only sections'). Careless Whisper, arXiv 2402.08021 (~1% of transcriptions contain invented phrases, linked to longer non-vocal durations). whisper-large-v3 model card lines 513-517.

### 13. faster-whisper computes the compression ratio on UTF-8 bytes, so ordinary Urdu compresses more than English: m…

**Confidence:** verified-source

faster-whisper computes the compression ratio on UTF-8 bytes, so ordinary Urdu compresses more than English: median 1.45 vs 1.23 (medium), 1.91 vs 1.57 (long), 2.11 vs 1.83 (xlong, whole text). Real Urdu segments scored 1.17-1.79. Loops score 14-18. The 2.4 default still separates loops, but Urdu sits closer to it.

**Evidence:** faster_whisper/transcribe.py lines 1879-1881. Measured with zlib on bench/pools/{en,ur}.json. seg_max_cr values in lab/asr_refs_int8.jsonl.

### 14. For English, apply OpenAI Whisper's EnglishTextNormalizer to both reference and hypothesis. It maps spelled nu…

**Confidence:** verified-source

For English, apply OpenAI Whisper's EnglishTextNormalizer to both reference and hypothesis. It maps spelled numbers and digits to the same form and handles contractions and spelling. Vendored in lab/whisper_normalizers/ from openai-whisper 20250625 so torch is not needed. jiwer 4.0 defaults do not lowercase or strip punctuation, and its RemovePunctuation deletes characters rather than replacing them with spaces, so normalize first.

**Evidence:** Checked by running: 'thirty million' and '30 million' both become '30000000' (WER 0). 'gonna'/'100 percent' and 'going to'/'100%' match. 'twenty-five … nineteen ninety nine' equals '25 … 1999'. whisper/normalizers/english.py lines 465-525. jiwer/transformations.py lines 40-46 and transforms.py lines 418-437. The English pools contain no digits or abbreviations.

### 15. Whisper's BasicTextNormalizer should not be used for Urdu. In default mode it turns every combining mark into…

**Confidence:** verified-source

Whisper's BasicTextNormalizer should not be used for Urdu. In default mode it turns every combining mark into a space, so 'پُرعزم' becomes 'پ رعزم'; 7 of our 619 Urdu texts gain 15 spurious tokens this way. With remove_diacritics it runs NFKD and maps ئ to Arabic ي (ہوئے becomes ہويے), ۓ to ے (گۓ becomes گے) and آ to ا, and it still leaves ك/ک, ي/ی and ه/ہ unfolded. whisper-normalizer 0.1.15's ArabicTextNormalizer folds toward Arabic forms, which is the wrong direction for Urdu.

**Evidence:** whisper/normalizers/basic.py lines 27-80, confirmed by running on our texts (lab/test_norm.py). whisper_normalizer/international.py lines 86-97. The same mechanism as the Indic lost-matras problem in Manohar & Pillai, EMNLP 2024 (aclanthology 2024.emnlp-main.607).

### 16. Proposed UrduNormalizer (lab/tts_textnorm.py), applied to both sides. Steps: NFKC; rewrite ی/ي + hamza as ئ; f…

**Confidence:** verified-source

Proposed UrduNormalizer (lab/tts_textnorm.py), applied to both sides. Steps: NFKC; rewrite ی/ي + hamza as ئ; fold ي/ى to ی, ك/ڪ to ک, ه/ە/ۀ/ۂ to ہ, ة to ۃ, أ/إ/ٱ to ا, and ۓ to ئے; convert Arabic-Indic and Extended digits to 0-9; drop ZWSP/ZWNJ/ZWJ/bidi marks/tatweel; strip harakat (U+0610-061A, U+064B-065F, U+0670, U+06D6-06ED); replace all P*/S* characters (۔ ، ؟ …) with spaces. It keeps ے/ی, ھ/ہ, ں/ن and آ/ا distinct. It is idempotent on all 619 texts. On the reference transcript against a simulated orthographic-variant hypothesis, WER is 0.500 with no normalization, 0.462 with Whisper basic, 0.421 with basic+remove_diacritics, and 0.000 with UrduNormalizer.

**Evidence:** lab/test_norm.py and lab/test_norm2.py outputs.

### 17. For Urdu, report WER, CER and CER-nospace, and gate on CER-nospace. Word segmentation varies freely: the repo'…

**Confidence:** verified-source

For Urdu, report WER, CER and CER-nospace, and gate on CER-nospace. Word segmentation varies freely: the repo's own transcripts use both صورتحال and دہشتگردی forms. Two spacing variants in a 38-word sentence cost WER 0.105 but CER-nospace 0.000. An optional 'phonetic' fold of homophone letters (ذضظ→ز, صث→س, ط/ۃ→ت, ح→ہ, ع→ا) lowered the real-clip corpus CER-nospace from 3.8% to 3.3%. Use it as a diagnostic only, because it can hide real mispronunciations. Suggested initial Urdu gate: CER-nospace > 0.15, about 2x the worst real clip, then recalibrate on good takes.

**Evidence:** lab/test_norm2.py. Phonetic comparison run on lab/asr_refs_int8.jsonl. The 0.15 threshold is a proposal.

### 18. NOTES' 'WavLM ≈ 0.974' and '<0.88' were almost certainly cosines from microsoft/wavlm-base-plus-sv (WavLMForXV…

**Confidence:** unverified

NOTES' 'WavLM ≈ 0.974' and '<0.88' were almost certainly cosines from microsoft/wavlm-base-plus-sv (WavLMForXVector), not the seed-tts-eval WavLM-large model. Measured here with base-plus-sv: real same-speaker pairs 0.975-0.994, trump vs shehbaz 0.746-0.799, a 2 s crop 0.951. On the WavLM-large (seed-tts) scale the same-speaker pairs score 0.87-0.95 and cross-speaker 0.11-0.18. Human ground truth on seed-tts-eval is 0.73, and Qwen3-TTS reports 0.775 for English, so 0.974 does not fit that scale.

**Evidence:** lab/sim_eval.py --calibrate on CPU. The wavlm-base-plus-sv model card uses 'threshold = 0.86'. HF API: that model has 266k downloads, wavlm-base-sv 14k. F5-TTS arXiv 2410.06885: ground truth SIM-o 0.73 / 0.76. Qwen3-TTS report arXiv 2601.15621 Table 6: English SIM 0.775 from 'a WavLM-based speaker verification model'. The identity of the Kaggle model is inferred, because no scoring code is in the repo.

### 19. Primary speaker-similarity metric: seed-tts-eval SIM, which is UniSpeech WavLM-Large + ECAPA-TDNN (wavlm_large…

**Confidence:** verified-source

Primary speaker-similarity metric: seed-tts-eval SIM, which is UniSpeech WavLM-Large + ECAPA-TDNN (wavlm_large_finetune.pth; UniSpeech table EER Vox1-O 0.431%). Its Azure download link expired (SAS se=2024-12-03). Two independent HF mirrors serve an identical 1,301,926,579-byte file with sha256 51f07e3b94d9e0262a6a675ef5a087be3dd09e8c62e9d886827f44f82fe7f94b: bezzam/wavlm_large_finetune_seed_tts_eval and hidoba/wavlm_large_finetune. The reference code resamples to 16 kHz, does not trim, and scores each output against the prompt audio (SIM-o).

**Evidence:** seed-tts-eval README line 15. thirdparty/UniSpeech/.../README.md lines 16 and 57. verification.py lines 12-79. get_wav_res_ref_text.py lines 15-40. models/ecapa_tdnn.py line 197 uses torch.hub s3prl. HF API tree listings give the LFS oids.

### 20. The torch-native port prj-beatrice/unispeech-wavlm-large-ecapa-tdnn-torch-native (safetensors sha 559b8708…, t…

**Confidence:** verified-source

The torch-native port prj-beatrice/unispeech-wavlm-large-ecapa-tdnn-torch-native (safetensors sha 559b8708…, trust_remote_code, no network calls in its code) crashes on transformers 5.17.0. It patches WavLMAttention.torch_multi_head_self_attention with the 4.x signature that includes output_attentions, which 5.x removed. lab/sim_eval.py re-patches it with an adapter, and results match the expected scale. Either pin transformers<5 in the SIM venv, or use the adapter with batch size 1. Equivalence with the original seed-tts-eval/s3prl path was not re-checked here.

**Evidence:** Traceback observed: TypeError '_wavlm_attention_with_padding_bias() missing … output_attentions'. transformers 5.17 modeling_wavlm.py lines 186-197. The port's README claims torch.testing.assert_close equality with seed-tts-eval verification().

### 21. WavLM-large SIM calibration on these voices (CPU). shehbaz held-out clips vs prompt: 0.896-0.939. Leave-one-ou…

**Confidence:** verified-source

WavLM-large SIM calibration on these voices (CPU). shehbaz held-out clips vs prompt: 0.896-0.939. Leave-one-out vs held-out centroid: 0.927-0.951. Prompt vs held-out centroid: 0.952. trump half vs half: 0.908. Cross-speaker: 0.106-0.182. SIM depends strongly on duration: crops of shehbaz_02 score 0.676 (2 s), 0.733 (3 s) and 0.807 (5 s), against 0.903 for the full 10 s. Skip SIM below 2-3 s and bucket thresholds by duration. As an initial gate, flag below ~0.5 (5 s or longer) and recalibrate to about the 1st percentile of good takes. Same-session real audio scores higher than seed-tts ground truth (0.73), which is cross-session.

**Evidence:** lab/sim_eval.py --calibrate output. The thresholds are proposals.

### 22. Compute two SIM references. SIM-prompt compares against voices/<id>/references/qwen3-tts.wav (seed-tts convent…

**Confidence:** verified-source

Compute two SIM references. SIM-prompt compares against voices/<id>/references/qwen3-tts.wav (seed-tts convention, comparable with papers). SIM-heldout compares against the centroid of clips not used in the prompt: shehbaz 02-06, since the prompt uses 07, 08 and 01. trump has one clip, which is the prompt, so no held-out score exists for him; use trump half-vs-half (0.908 large, 0.994 base) as his ceiling. Trim silence before embedding. SIM does not detect loops; its job is catching voice drift, the wrong speaker or garbled audio.

**Evidence:** voices/*/references/references.json clip lists. lab/sim_eval.py implements both references and the energy trim.

### 23. Secondary and optional SIM models. Keep wavlm-base-plus-sv as a secondary for continuity with the Kaggle numbe…

**Confidence:** verified-source

Secondary and optional SIM models. Keep wavlm-base-plus-sv as a secondary for continuity with the Kaggle numbers; its range is compressed (cross-speaker 0.75-0.80 vs same-speaker ≥0.975 here). SpeechBrain spkrec-ecapa-voxceleb (EER 0.80%, default threshold 0.25, soundfile I/O in 1.1.1) is an optional independent-architecture check. Do not use Resemblyzer; its README says it 'currently works best on English language only'.

**Evidence:** speechbrain model card EER table. speechbrain 1.1.1 inference/speaker.py line 62 and dataio/audio_io.py lines 2-5. Resemblyzer 0.1.4 METADATA line 63.

### 24. Speaker similarity can run entirely on CPU. With 8 torch threads, base-plus-sv ran at 37.8x realtime and WavLM…

**Confidence:** verified-source

Speaker similarity can run entirely on CPU. With 8 torch threads, base-plus-sv ran at 37.8x realtime and WavLM-large SV at 15x realtime, so ~6.6 h of audio takes ~26 min for WavLM-large. No GPU is needed for SIM. On GPU the WavLM-large model is ~1.3 GB of fp32 weights; peak ≤~3 GB for 60 s clips is an estimate.

**Evidence:** sim_eval.py calibration output (x_realtime fields). The GPU memory figure is not measured.

### 25. The current bench_tts.py 'suspect' duration band misses all 4 known Kaggle Urdu failures. Their seconds-per-wo…

**Confidence:** verified-source

The current bench_tts.py 'suspect' duration band misses all 4 known Kaggle Urdu failures. Their seconds-per-word are 0.22, 0.25, 1.01 and 1.01, all inside the 0.18-1.1 band. Good Qwen Urdu runs ~0.25-0.33 s/word (3-4 words/s). Replace the band with a voice-relative one (flag below 0.6x or above 1.8x the voice's median s/char), and add ASR coverage and audio checks, because a 15-25% truncation cannot be told apart from pace by duration alone.

**Evidence:** Word counts come from benchmarks/shehbaz_ur.json samples 01, 17, 19 and 38 (98/95/103/98 words), with durations from NOTES.md. SPW_BAND is in bench/bench_tts.py.

### 26. Loop/skip detector suite in lab/tts_checks.py and asr_eval.py. Proposed initial flags: char_ratio (hyp letters…

**Confidence:** verified-source

Loop/skip detector suite in lab/tts_checks.py and asr_eval.py. Proposed initial flags: char_ratio (hyp letters / ref letters) below 0.85 or above 1.15; longest deletion run ≥4 words (ur) or ≥3 (en); longest insertion run ≥4; n-gram repeat_excess ≥4; token run ≥3 or char run (letter repeated ≥4 times) ≥1; max_word_dur_s above 2.5 s with over 80% voiced (loop the ASR swallowed); unaligned_tail_s above 3 s; energy-VAD internal pause above 2.0 s, trailing silence above 1.5 s, leading silence above 1.0 s, speech_ratio below 0.6; output tokens at the max_new_tokens cap. Calibration on real clips (-35 dB relative VAD): longest natural pause ≤0.78 s for most clips, 1.48 s in shehbaz_08, 1.5 s in qwen3-tts.wav; longest word 1.0-2.22 s; unaligned tail 0.09-0.49 s. Synthetic tests: truncation detected (del_run 7 / 21, char_ratio 0.65 / 0.66), 4 s gap (3.98 s), trailing tails (6.43 s), Urdu loops only via max_word_dur (4.9-5.5 s, 98-99% voiced).

**Evidence:** lab/test_checks3.py, lab/asr_refs_int8_v2.jsonl, lab/asr_synth.jsonl. The flag values are initial proposals to recalibrate on real takes.

### 27. How to evaluate a retry policy offline. Generate K=6 seeded takes per prompt per setting; bench_tts.py --takes…

**Confidence:** verified-source

How to evaluate a retry policy offline. Generate K=6 seeded takes per prompt per setting; bench_tts.py --takes/--seed uses seed B+100·idx+take, so seeds pair across repetition_penalty settings. Label gate_pass as what production computes online, and label 'bad' independently (human listening on every gate-fail plus ~10-15% of passes). Estimate 'retry up to R' exactly by averaging over every ordered choice of R+1 of the K takes. Report final bad rate, attempts, and extra compute weighted by audio or GPU seconds (failed loops are long), with 95% CIs from bootstrapping prompts, plus gate recall, precision and false-reject rate. lab/retry_sim.py implements this and a best-of-N variant. Retries only apply to non-streaming responses.

**Evidence:** lab/retry_sim.py was run on synthetic data. bench_tts.py lines 250-257 contain the seed formula and take fields.

### 28. Do not predict retry benefit with f^(R+1). Failures cluster on hard prompts, and the gate misses some. In a sy…

**Confidence:** verified-source

Do not predict retry benefit with f^(R+1). Failures cluster on hard prompts, and the gate misses some. In a synthetic check (43 prompts × 6 takes, 9.3% bad takes concentrated in 4 prompts, gate recall 0.75): R=1 gave 5.4% bad (CI 1.2-10.6) at +14.5% compute, R=2 4.8%, R=3 4.7%. The i.i.d. formula predicts 0.87%, 0.08% and 0.01%. Best-of-2 gave 4.2% at 2x compute.

**Evidence:** lab/retry_sim.py __main__ output.

### 29. Sample size. The Kaggle Urdu failure rate of 5/46 has a 95% Wilson CI of 4.7-23%. Detecting a drop from 11% to…

**Confidence:** verified-source

Sample size. The Kaggle Urdu failure rate of 5/46 has a 95% Wilson CI of 4.7-23%. Detecting a drop from 11% to 4% with 80% power (α=0.05, two-sided) needs ~221 takes per arm; 11% to 5.5% needs ~392. So use at least 43 xlong prompts × K=6 per repetition_penalty value (1.05/1.10/1.15/1.20), analysed as paired data by prompt. Also measure the cost of each setting on passing takes: CER-nospace, SIM and pace (s/char).

**Evidence:** Computed with the two-proportion power formula and the Wilson interval.

### 30. Models are already downloaded and sha-verified in scratch, so the future GPU run can skip ~4.7 GB of slow down…

**Confidence:** verified-source

Models are already downloaded and sha-verified in scratch, so the future GPU run can skip ~4.7 GB of slow downloads. Locations: models/faster-whisper-large-v3 (model.bin sha 69f74147…), models/wavlm-base-plus-sv (pytorch_model.bin sha e906bce2…), models/beatrice (model.safetensors sha 559b8708…). Each matches its HF LFS oid. Tested venvs: asrvenv (faster-whisper 1.2.1, ctranslate2 4.8.2) and venv (torch 2.11.0+cpu, transformers 5.17.0, jiwer 4.0.0). The GPU box needs cu12 cuBLAS in asrvenv and a CUDA torch build for SIM.

**Evidence:** sha256sum outputs compared with HF API tree oids. Paths are under /tmp/claude-1013/-home-vector/60c91189-44d6-4cdb-b0f5-2bf4adb23fb3/scratchpad/research/eval-tooling/.

### 31. The eval scripts can read bench_tts.py's AI-labelled WAVs (RIFF, fmt, LIST/INFO, data). asr_eval.py and sim_ev…

**Confidence:** verified-source

The eval scripts can read bench_tts.py's AI-labelled WAVs (RIFF, fmt, LIST/INFO, data). asr_eval.py and sim_eval.py consume results/<ts>/requests.jsonl rows with 'file' and 'text' directly. Run the evaluation after the load tests, never alongside them, so it does not skew latency on the shared GPUs.

**Evidence:** Tested with labelled_wav() from the current bench_tts.py: the Python wave module read 24000 Hz and 24000 frames.

## Risks

- Whisper large-v3 in forced-'ur' mode swallowed spliced Urdu loops and returned the clean transcript. Without the word-timing and duration checks, ASR-based gates will under-count Urdu loops, which were the main Kaggle failure mode. The synthetic splices may also not look like real Qwen loops.
- The Urdu ASR floor (corpus WER 13.1%, CER-nospace 3.8%) is optimistic, because the reference transcripts were hand-corrected starting from Whisper large-v3 output. Accented Qwen Urdu will score worse.
- The absolute gates in NOTES (WER>0.22, SIM<0.88) are on the wrong scale or metric for Urdu and for WavLM-large. Applying them unchanged would reject good Urdu takes (2 of 8 real human clips fail WER>0.22) or mis-set the SIM threshold.
- The torch-native WavLM-large port breaks on transformers 5.x. My adapter was only exercised with batch size 1 and no padding, and equivalence with the original seed-tts-eval s3prl path was not re-checked here.
- Calibration used CPU int8 (ASR) and CPU fp32 (SIM). GPU float16 numbers may differ slightly. The GPU VRAM and throughput figures are estimates.
- Human labels are needed as the independent 'bad' oracle for the retry study. Without them the study only measures whether the gate agrees with itself.
- Folding ه→ہ is wrong for informal text that writes ه for ھ, and the homophone fold can hide real mispronunciations. Keep the phonetic fold as a diagnostic only.
- vLLM Whisper bug status may change, but it was open as of 2026-09-21.
- The identity of the Kaggle SIM model (wavlm-base-plus-sv) is inferred from value ranges and was not confirmed from code.
- Any eval on the GPU must wait for a free GPU and must not run alongside the TTS benchmarks. ASR and SIM both run on CPU (SIM at 15-38x realtime, ASR int8 at ~2-4x realtime with 8 threads) if the GPU stays busy.

## Open questions

- How much worse Whisper large-v3 transcribes Qwen's accented Urdu than broadcast Urdu. This decides the final Urdu CER-nospace gate; calibrate on the first batch of good takes.
- Whether real Qwen Urdu loops, such as 'آآآ' or 'ایک ایک…', are also swallowed by the ASR like the synthetic splices, and whether max_word_dur_s above 2.5 s with more than 80% voiced catches them without false positives on slow, calm takes.
- Mapping between the Kaggle base-plus-sv 0.88 gate and a WavLM-large SIM threshold; fit it on the first scored batch (e.g. a quantile map).
- Whether vLLM-Omni honours a per-request 'seed', which the paired repetition_penalty design depends on. Also whether repetition_penalty 1.1-1.2 changes pace or prosody, and not just the loop rate.
- Whether Whisper Urdu hypotheses contain Arabic ه/ي/ك code points. This decides whether a lenient ھ/ہ fold is needed; check a codepoint histogram of the first batch.
- Whether to add a second Urdu ASR (Seamless-M4T or MMS beat Whisper on read Urdu in arXiv 2409.11252) so the gate is less biased toward Whisper.
- How big a human-listening budget is available for the retry oracle; roughly all gate-fails plus 10-15% of passes.
