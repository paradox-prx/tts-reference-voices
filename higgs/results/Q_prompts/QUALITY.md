# Quality: Q_prompts

Stock Whisper large-v3 (language forced) WER / CER-nospace against the input text; SIM = cosine speaker similarity to the voice's reference clip (WavLM-Large seed-tts-eval scale / wavlm-base-plus-sv); pace = seconds per letter over the voice's calibrated pace; gate fail = the production QC verdict (pace + ASR + SIM + audio detectors), bad = the stricter offline label; rates with 95 % Wilson CIs (server/eval/score_run.py, thresholds in server/qc/tts_qc/policy.py).

| tag | voice | takes | audio h | WER | CER-ns | SIM-L | SIM-B | pace | gate fail | bad | bad reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1_t08 | shehbaz | 86 | 0.80 | 0.146 | 0.114 | 0.851 | 0.978 | 0.96 | 36.0% [27%, 47%] | 38.4% [29%, 49%] | del_run 29, char_ratio 27, cer_nospace 11, pace 7 |
| Q1_t08 | trump | 86 | 0.73 | 0.088 | 0.082 | 0.830 | 0.983 | 0.96 | 66.3% [56%, 75%] | 66.3% [56%, 75%] | del_run 55, wer 27, char_ratio 18, pace 2 |
| Q2_t10 | shehbaz | 86 | 0.72 | 0.232 | 0.195 | 0.864 | 0.981 | 0.86 | 50.0% [40%, 60%] | 55.8% [45%, 66%] | del_run 44, char_ratio 37, cer_nospace 23, pace 17 |
| Q3_ref25 | shehbaz | 86 | 0.80 | 0.166 | 0.135 | 0.861 | 0.979 | 0.96 | 45.3% [35%, 56%] | 51.2% [41%, 61%] | del_run 43, char_ratio 29, cer_nospace 12, pace 7 |
| Q4_expr_plain | shehbaz | 86 | 0.75 | 0.193 | 0.162 | 0.862 | 0.979 | 0.90 | 45.3% [35%, 56%] | 46.5% [36%, 57%] | del_run 38, char_ratio 36, cer_nospace 23, pace 16 |
| Q4_expr_tags | shehbaz | 86 | 0.81 | 0.234 | 0.200 | 0.810 | 0.963 | 0.97 | 57.0% [46%, 67%] | 60.5% [50%, 70%] | del_run 43, char_ratio 39, cer_nospace 23, pace 15 |
| ALL | | 516 | 4.61 | 0.176 | 0.148 | 0.846 | 0.977 | 0.93 | 50.0% [46%, 54%] | 53.1% [49%, 57%] | del_run 252, char_ratio 186, cer_nospace 92, pace 64 |
