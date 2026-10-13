# Quality: B0_baseline_flash_attn

Stock Whisper large-v3 (language forced) WER / CER-nospace against the input text; SIM = cosine speaker similarity to the voice's reference clip (WavLM-Large seed-tts-eval scale / wavlm-base-plus-sv); pace = seconds per letter over the voice's calibrated pace; gate fail = the production QC verdict (pace + ASR + SIM + audio detectors), bad = the stricter offline label; rates with 95 % Wilson CIs (server/eval/score_run.py, thresholds in server/qc/tts_qc/policy.py).

| voice | size | stream | takes | audio h | WER | CER-ns | SIM-L | SIM-B | pace | gate fail | bad | bad reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| shehbaz | short | nonstream | 72 | 0.11 | 0.117 | 0.081 | 0.706 | 0.950 | 1.46 | 12.5% [7%, 22%] | 27.8% [19%, 39%] | pace 11, char_ratio 9, cer_nospace 4, long_word 3 |
| shehbaz | short | stream | 64 | 0.09 | 0.059 | 0.031 | 0.742 | 0.958 | 1.20 | 1.6% [0%, 8%] | 9.4% [4%, 19%] | pace 6, cer_nospace 1, char_ratio 1, ins_run 1 |
| shehbaz | medium | nonstream | 72 | 0.22 | 0.034 | 0.011 | 0.839 | 0.979 | 1.18 | 0.0% [0%, 5%] | 1.4% [0%, 7%] | pace 1 |
| shehbaz | long | nonstream | 72 | 0.51 | 0.047 | 0.019 | 0.858 | 0.981 | 1.13 | 5.6% [2%, 13%] | 5.6% [2%, 13%] | pause 2, del_run 2, char_ratio 1 |
| shehbaz | long | stream | 64 | 0.47 | 0.058 | 0.033 | 0.847 | 0.971 | 1.17 | 6.2% [2%, 15%] | 7.8% [3%, 17%] | char_ratio 2, del_run 2, pace 2, ins_run 1 |
| shehbaz | xlong | nonstream | 72 | 0.70 | 0.128 | 0.097 | 0.853 | 0.977 | 0.99 | 38.9% [28%, 50%] | 43.1% [32%, 55%] | del_run 27, char_ratio 20, cer_nospace 6, pace 3 |
| shehbaz | xlong | stream | 64 | 0.58 | 0.158 | 0.131 | 0.859 | 0.979 | 0.92 | 39.1% [28%, 51%] | 43.8% [32%, 56%] | del_run 26, char_ratio 20, cer_nospace 12, pace 7 |
| shehbaz | xxlong | nonstream | 72 | 0.37 | 0.832 | 0.813 | 0.822 | 0.973 | 0.26 | 100.0% [95%, 100%] | 100.0% [95%, 100%] | pace 72, cer_nospace 72, char_ratio 72, del_run 72 |
| trump | short | nonstream | 24 | 0.02 | 0.000 | 0.000 | 0.703 | 0.957 | 1.26 | 4.2% [1%, 20%] | 8.3% [2%, 26%] | pace 2 |
| trump | short | stream | 24 | 0.02 | 0.008 | 0.006 | 0.704 | 0.959 | 1.30 | 4.2% [1%, 20%] | 20.8% [9%, 40%] | pace 4, wer 1 |
| trump | xlong | nonstream | 24 | 0.21 | 0.064 | 0.060 | 0.827 | 0.981 | 0.97 | 66.7% [47%, 82%] | 66.7% [47%, 82%] | del_run 16, wer 5, char_ratio 4 |
| trump | xlong | stream | 24 | 0.20 | 0.064 | 0.063 | 0.830 | 0.982 | 0.95 | 66.7% [47%, 82%] | 66.7% [47%, 82%] | del_run 15, wer 4, char_ratio 2, ins_run 1 |
| ALL | | | 648 | 3.49 | 0.161 | 0.137 | 0.808 | 0.971 | 1.05 | 27.3% [24%, 31%] | 31.8% [28%, 35%] | del_run 160, char_ratio 131, pace 109, cer_nospace 96 |
