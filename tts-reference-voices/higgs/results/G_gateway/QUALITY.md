# Quality: G_gateway

Stock Whisper large-v3 (language forced) WER / CER-nospace against the input text; SIM = cosine speaker similarity to the voice's reference clip (WavLM-Large seed-tts-eval scale / wavlm-base-plus-sv); pace = seconds per letter over the voice's calibrated pace; gate fail = the production QC verdict (pace + ASR + SIM + audio detectors), bad = the stricter offline label; rates with 95 % Wilson CIs (server/eval/score_run.py, thresholds in server/qc/tts_qc/policy.py).

| tag | voice | size | stream | takes | audio h | WER | CER-ns | SIM-L | SIM-B | pace | gate fail | bad | bad reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G0 | shehbaz | xlong | nonstream | 24 | 0.20 | 0.275 | 0.247 | 0.784 | 0.936 | 0.85 | 66.7% [47%, 82%] | 70.8% [51%, 85%] | del_run 16, char_ratio 11, cer_nospace 7, pace 3 |
| G0 | shehbaz | xlong | stream | 16 | 0.15 | 0.083 | 0.065 | 0.861 | 0.979 | 0.96 | 18.8% [7%, 43%] | 31.2% [14%, 56%] | del_run 5, char_ratio 3, pace 1, cer_nospace 1 |
| G0 | shehbaz | xxlong | nonstream | 24 | 0.15 | 0.784 | 0.765 | 0.849 | 0.980 | 0.31 | 100.0% [86%, 100%] | 100.0% [86%, 100%] | pace 24, cer_nospace 24, char_ratio 24, del_run 24 |
| G0 | trump | xlong | nonstream | 16 | 0.14 | 0.039 | 0.040 | 0.822 | 0.978 | 0.98 | 43.8% [23%, 67%] | 43.8% [23%, 67%] | del_run 7, wer 3, char_ratio 2, repeat_excess 1 |
| G1 | shehbaz | xlong | nonstream | 24 | 0.29 | 0.071 | 0.043 | 0.868 | 0.978 | 1.22 | 25.0% [12%, 45%] | 25.0% [12%, 45%] | word_gap 5, del_run 4, char_ratio 3, pace 2 |
| G1 | shehbaz | xlong | stream | 16 | 0.18 | 0.036 | 0.012 | 0.879 | 0.986 | 1.16 | 0.0% [0%, 19%] | 0.0% [0%, 19%] | - |
| G1 | shehbaz | xxlong | nonstream | 24 | 0.56 | 0.093 | 0.066 | 0.887 | 0.986 | 1.18 | 41.7% [24%, 61%] | 45.8% [28%, 65%] | word_gap 8, del_run 8, char_ratio 4, lead_sil 1 |
| G1 | trump | xlong | nonstream | 16 | 0.18 | 0.003 | 0.002 | 0.868 | 0.988 | 1.23 | 0.0% [0%, 19%] | 0.0% [0%, 19%] | - |
| G2 | shehbaz | xlong | nonstream | 24 | 0.28 | 0.036 | 0.010 | 0.881 | 0.986 | 1.16 | 0.0% [0%, 14%] | 0.0% [0%, 14%] | - |
| G2 | shehbaz | xlong | stream | 16 | 0.18 | 0.030 | 0.010 | 0.884 | 0.986 | 1.13 | 0.0% [0%, 19%] | 0.0% [0%, 19%] | - |
| G2 | shehbaz | xxlong | nonstream | 24 | 0.56 | 0.036 | 0.011 | 0.895 | 0.989 | 1.17 | 0.0% [0%, 14%] | 4.2% [1%, 20%] | del_run 1, word_gap 1 |
| G2 | trump | xlong | nonstream | 16 | 0.17 | 0.004 | 0.002 | 0.870 | 0.987 | 1.22 | 0.0% [0%, 19%] | 6.2% [1%, 28%] | unaligned_tail 1 |
| ALL | | | | 240 | 3.05 | 0.142 | 0.123 | 0.862 | 0.979 | 1.03 | 27.5% [22%, 33%] | 30.0% [25%, 36%] | del_run 65, char_ratio 47, cer_nospace 33, pace 30 |
