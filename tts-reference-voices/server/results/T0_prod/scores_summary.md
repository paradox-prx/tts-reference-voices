# Scores: results/T0_prod

Scored 2026-09-28T17:09:26+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ttfa_shehbaz_medium_c16_n96_stream_server [shehbaz] | 96 | 96 | 0.347 | 0.142 | 0.347 | 0.142 | 0.789 | 0.823 | 0.974 | 1.109 | 5/96 0.052 [0.022, 0.116] | 9/96 0.094 [0.050, 0.169] | 9/96 0.094 [0.050, 0.169] | 4/91 0.044 [0.017, 0.108] |
| ttfa_shehbaz_medium_c1_n8_stream_server [shehbaz] | 8 | 8 | 0.303 | 0.131 | 0.316 | 0.139 | 0.775 | 0.799 | 0.968 | 1.048 | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] |
| ttfa_shehbaz_medium_c32_n192_stream_server [shehbaz] | 192 | 145 | 0.348 | 0.143 | 0.349 | 0.145 | 0.793 | 0.828 | 0.976 | 1.125 | 5/192 0.026 [0.011, 0.059] | 15/192 0.078 [0.048, 0.125] | 15/192 0.078 [0.048, 0.125] | 10/187 0.053 [0.029, 0.096] |
| ttfa_shehbaz_medium_c8_n48_stream_server [shehbaz] | 48 | 48 | 0.345 | 0.147 | 0.347 | 0.149 | 0.787 | 0.826 | 0.974 | 1.120 | 2/48 0.042 [0.011, 0.140] | 5/48 0.104 [0.045, 0.222] | 5/48 0.104 [0.045, 0.222] | 3/46 0.065 [0.022, 0.175] |
| ttfa_shehbaz_short_c16_n96_stream_server [shehbaz] | 96 | 96 | 0.315 | 0.131 | 0.311 | 0.137 | 0.699 | 0.738 | 0.955 | 1.155 | 13/96 0.135 [0.081, 0.218] | 19/96 0.198 [0.131, 0.289] | 19/96 0.198 [0.131, 0.289] | 6/83 0.072 [0.034, 0.149] |
| ttfa_shehbaz_short_c1_n8_stream_server [shehbaz] | 8 | 8 | 0.210 | 0.114 | 0.219 | 0.115 | 0.694 | 0.724 | 0.957 | 1.074 | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] |
| ttfa_shehbaz_short_c32_n192_stream_server [shehbaz] | 192 | 192 | 0.358 | 0.149 | 0.364 | 0.152 | 0.707 | 0.740 | 0.958 | 1.117 | 14/192 0.073 [0.044, 0.119] | 31/192 0.162 [0.116, 0.220] | 31/192 0.162 [0.116, 0.220] | 17/178 0.096 [0.060, 0.148] |
| ttfa_shehbaz_short_c8_n48_stream_server [shehbaz] | 48 | 48 | 0.336 | 0.139 | 0.342 | 0.145 | 0.700 | 0.739 | 0.959 | 1.124 | 5/48 0.104 [0.045, 0.222] | 8/48 0.167 [0.087, 0.296] | 8/48 0.167 [0.087, 0.296] | 3/43 0.070 [0.024, 0.186] |
| ALL | 688 | 344 | 0.343 | 0.142 | 0.346 | 0.145 | 0.747 | 0.782 | 0.966 | 1.123 | 44/688 0.064 [0.048, 0.085] | 87/688 0.127 [0.104, 0.153] | 87/688 0.127 [0.104, 0.153] | 43/644 0.067 [0.050, 0.089] |

Gate reasons (all runs): char_ratio<0.85 26, cer_nospace>0.35 14, pace>1.8 3, char_ratio>1.15 3, lead_sil>1 2, repeat_excess>=6 2, ins_run>=6 1, sim<0.88 1, del_run>=8 1  
Bad reasons (all runs): char_ratio<0.88 43, cer_nospace>0.3 27, pace>1.5 15, char_ratio>1.12 6, word_gap>1.5 4, del_run>=6 3, lead_sil>1 2, sim<0.4 2, sim<0.5 2, sim_heldout<0.5 2, repeat_excess>=5 2, sim_heldout<0.4 1, ins_run>=5 1, pace<0.7 1, long_word>2 1  

