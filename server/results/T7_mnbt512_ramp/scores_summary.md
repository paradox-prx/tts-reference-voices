# Scores: results/T7_mnbt512_ramp

Scored 2026-09-28T17:14:10+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ttfa_shehbaz_medium_c16_n96_stream_server [shehbaz] | 96 | 96 | 0.357 | 0.147 | 0.358 | 0.149 | 0.797 | 0.828 | 0.977 | 1.110 | 6/96 0.062 [0.029, 0.130] | 7/96 0.073 [0.036, 0.143] | 7/96 0.073 [0.036, 0.143] | 1/90 0.011 [0.002, 0.060] |
| ttfa_shehbaz_medium_c1_n8_stream_server [shehbaz] | 8 | 8 | 0.366 | 0.145 | 0.363 | 0.146 | 0.801 | 0.835 | 0.974 | 1.061 | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] |
| ttfa_shehbaz_medium_c32_n192_stream_server [shehbaz] | 192 | 145 | 0.348 | 0.145 | 0.349 | 0.148 | 0.801 | 0.836 | 0.975 | 1.121 | 6/192 0.031 [0.014, 0.067] | 15/192 0.078 [0.048, 0.125] | 15/192 0.078 [0.048, 0.125] | 9/186 0.048 [0.026, 0.089] |
| ttfa_shehbaz_medium_c8_n48_stream_server [shehbaz] | 48 | 48 | 0.327 | 0.136 | 0.331 | 0.138 | 0.789 | 0.827 | 0.976 | 1.132 | 0/48 0.000 [0.000, 0.074] | 2/48 0.042 [0.011, 0.140] | 2/48 0.042 [0.011, 0.140] | 2/48 0.042 [0.011, 0.140] |
| ttfa_shehbaz_short_c16_n96_stream_server [shehbaz] | 96 | 96 | 0.354 | 0.143 | 0.352 | 0.149 | 0.705 | 0.741 | 0.955 | 1.113 | 7/96 0.073 [0.036, 0.143] | 16/96 0.167 [0.105, 0.254] | 16/96 0.167 [0.105, 0.254] | 9/89 0.101 [0.054, 0.181] |
| ttfa_shehbaz_short_c1_n8_stream_server [shehbaz] | 8 | 8 | 0.207 | 0.093 | 0.209 | 0.093 | 0.671 | 0.704 | 0.962 | 1.181 | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] | 0/7 0.000 [0.000, 0.354] |
| ttfa_shehbaz_short_c32_n192_stream_server [shehbaz] | 192 | 192 | 0.367 | 0.151 | 0.367 | 0.151 | 0.708 | 0.741 | 0.958 | 1.130 | 14/192 0.073 [0.044, 0.119] | 38/192 0.198 [0.148, 0.260] | 38/192 0.198 [0.148, 0.260] | 24/178 0.135 [0.092, 0.193] |
| ttfa_shehbaz_short_c8_n48_stream_server [shehbaz] | 48 | 48 | 0.326 | 0.134 | 0.338 | 0.145 | 0.707 | 0.744 | 0.960 | 1.138 | 4/48 0.083 [0.033, 0.196] | 5/48 0.104 [0.045, 0.222] | 5/48 0.104 [0.045, 0.222] | 1/44 0.023 [0.004, 0.118] |
| ALL | 688 | 344 | 0.351 | 0.145 | 0.351 | 0.147 | 0.752 | 0.786 | 0.967 | 1.123 | 38/688 0.055 [0.041, 0.075] | 84/688 0.122 [0.100, 0.149] | 84/688 0.122 [0.100, 0.149] | 46/650 0.071 [0.053, 0.093] |

Gate reasons (all runs): char_ratio<0.85 20, cer_nospace>0.35 15, repeat_excess>=6 4, char_ratio>1.15 3, pace>1.8 2, word_gap>2 2, speech_ratio<0.6 1, lead_sil>1 1, long_word>2.5 1, del_run>=8 1  
Bad reasons (all runs): char_ratio<0.88 40, cer_nospace>0.3 36, pace>1.5 15, char_ratio>1.12 5, repeat_excess>=5 4, long_word>2 3, del_run>=6 2, word_gap>1.5 2, speech_ratio<0.6 1, lead_sil>1 1, ins_run>=5 1  

