# Quality: S2_mem080_seqs32

Stock Whisper large-v3 (language forced) WER / CER-nospace against the input text; SIM = cosine speaker similarity to the voice's reference clip (WavLM-Large seed-tts-eval scale / wavlm-base-plus-sv); pace = seconds per letter over the voice's calibrated pace; gate fail = the production QC verdict (pace + ASR + SIM + audio detectors), bad = the stricter offline label; rates with 95 % Wilson CIs (server/eval/score_run.py, thresholds in server/qc/tts_qc/policy.py).

| voice | size | stream | takes | audio h | WER | CER-ns | SIM-L | SIM-B | pace | gate fail | bad | bad reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| shehbaz | short | nonstream | 96 | 0.14 | 0.184 | 0.122 | 0.704 | 0.954 | 1.30 | 20.8% [14%, 30%] | 30.2% [22%, 40%] | pace 18, char_ratio 17, cer_nospace 12, del_run 4 |
| shehbaz | short | stream | 96 | 0.13 | 0.088 | 0.042 | 0.733 | 0.957 | 1.22 | 3.1% [1%, 9%] | 9.4% [5%, 17%] | pace 6, cer_nospace 2, char_ratio 1 |
| shehbaz | long | nonstream | 96 | 0.68 | 0.058 | 0.026 | 0.862 | 0.982 | 1.14 | 4.2% [2%, 10%] | 4.2% [2%, 10%] | char_ratio 2, del_run 2, lead_sil 1, pace 1 |
| shehbaz | xlong | nonstream | 96 | 0.90 | 0.168 | 0.134 | 0.853 | 0.976 | 0.96 | 41.7% [32%, 52%] | 42.7% [33%, 53%] | del_run 35, char_ratio 29, cer_nospace 16, pace 13 |
| shehbaz | xlong | stream | 96 | 0.88 | 0.171 | 0.138 | 0.855 | 0.979 | 0.94 | 37.5% [28%, 47%] | 40.6% [31%, 51%] | del_run 34, char_ratio 31, cer_nospace 19, pace 15 |
| trump | xlong | nonstream | 64 | 0.55 | 0.078 | 0.074 | 0.826 | 0.982 | 0.96 | 57.8% [46%, 69%] | 59.4% [47%, 71%] | del_run 37, wer 19, char_ratio 13, word_gap 2 |
| ALL | | | 544 | 3.28 | 0.127 | 0.090 | 0.804 | 0.971 | 1.10 | 25.7% [22%, 30%] | 29.4% [26%, 33%] | del_run 112, char_ratio 93, pace 54, cer_nospace 49 |
