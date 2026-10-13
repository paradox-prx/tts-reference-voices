# Scores: results/T8_mnbt512_adaptive

Scored 2026-09-28T17:18:57+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ttfa_shehbaz_medium_c16_n96_stream_server [shehbaz] | 96 | 96 | 0.362 | 0.146 | 0.357 | 0.144 | 0.798 | 0.832 | 0.975 | 1.151 | 1/96 0.010 [0.002, 0.057] | 7/96 0.073 [0.036, 0.143] | 7/96 0.073 [0.036, 0.143] | 6/95 0.063 [0.029, 0.131] |
| ttfa_shehbaz_medium_c1_n8_stream_server [shehbaz] | 8 | 8 | 0.289 | 0.130 | 0.295 | 0.128 | 0.800 | 0.833 | 0.976 | 1.162 | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] |
| ttfa_shehbaz_medium_c32_n192_stream_server [shehbaz] | 192 | 145 | 0.340 | 0.140 | 0.341 | 0.142 | 0.792 | 0.827 | 0.975 | 1.123 | 9/192 0.047 [0.025, 0.087] | 17/192 0.088 [0.056, 0.137] | 17/192 0.088 [0.056, 0.137] | 8/183 0.044 [0.022, 0.084] |
| ttfa_shehbaz_medium_c8_n48_stream_server [shehbaz] | 48 | 48 | 0.349 | 0.143 | 0.347 | 0.143 | 0.793 | 0.829 | 0.975 | 1.138 | 0/48 0.000 [0.000, 0.074] | 2/48 0.042 [0.011, 0.140] | 2/48 0.042 [0.011, 0.140] | 2/48 0.042 [0.011, 0.140] |
| ttfa_shehbaz_short_c16_n96_stream_server [shehbaz] | 96 | 96 | 0.355 | 0.134 | 0.332 | 0.134 | 0.703 | 0.741 | 0.960 | 1.156 | 9/96 0.094 [0.050, 0.169] | 12/96 0.125 [0.073, 0.206] | 12/96 0.125 [0.073, 0.206] | 3/87 0.035 [0.012, 0.097] |
| ttfa_shehbaz_short_c1_n8_stream_server [shehbaz] | 8 | 8 | 0.315 | 0.149 | 0.324 | 0.148 | 0.718 | 0.750 | 0.953 | 1.102 | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] |
| ttfa_shehbaz_short_c32_n192_stream_server [shehbaz] | 192 | 192 | 0.362 | 0.145 | 0.365 | 0.148 | 0.715 | 0.748 | 0.959 | 1.128 | 13/192 0.068 [0.040, 0.112] | 34/192 0.177 [0.130, 0.237] | 34/192 0.177 [0.130, 0.237] | 21/179 0.117 [0.078, 0.173] |
| ttfa_shehbaz_short_c8_n48_stream_server [shehbaz] | 48 | 48 | 0.312 | 0.126 | 0.325 | 0.136 | 0.716 | 0.751 | 0.956 | 1.186 | 3/48 0.062 [0.021, 0.168] | 6/48 0.125 [0.059, 0.247] | 6/48 0.125 [0.059, 0.247] | 3/45 0.067 [0.023, 0.179] |
| ALL | 688 | 344 | 0.349 | 0.141 | 0.346 | 0.143 | 0.753 | 0.788 | 0.967 | 1.139 | 35/688 0.051 [0.037, 0.070] | 78/688 0.113 [0.092, 0.139] | 78/688 0.113 [0.092, 0.139] | 43/653 0.066 [0.049, 0.087] |

Gate reasons (all runs): char_ratio<0.85 20, cer_nospace>0.35 14, pace>1.8 4, lead_sil>1 3, repeat_excess>=6 2, del_run>=8 2, word_gap>2 1, long_word>2.5 1  
Bad reasons (all runs): char_ratio<0.88 37, cer_nospace>0.3 27, pace>1.5 18, del_run>=6 4, lead_sil>1 3, char_ratio>1.12 3, repeat_excess>=5 2, word_gap>1.5 2, pace<0.7 1, long_word>2 1  

