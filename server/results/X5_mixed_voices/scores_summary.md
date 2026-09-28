# Scores: results/X5_mixed_voices

Scored 2026-09-25T11:02:34+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mix_trump+shehbaz_short_c16_n32_nonstream_inline [shehbaz] | 32 | 32 | 0.333 | 0.155 | 0.341 | 0.159 | 0.720 | 0.758 | 0.961 | 1.072 | 4/32 0.125 [0.050, 0.281] | 6/32 0.188 [0.089, 0.353] | 6/32 0.188 [0.089, 0.353] | 2/28 0.071 [0.020, 0.227] |
| mix_trump+shehbaz_short_c16_n32_nonstream_inline [trump] | 32 | 32 | 0.003 | 0.001 | 0.003 | 0.001 | 0.680 | - | 0.948 | 1.158 | 1/32 0.031 [0.005, 0.157] | 3/32 0.094 [0.032, 0.242] | 3/32 0.094 [0.032, 0.242] | 2/31 0.065 [0.018, 0.207] |
| mix_trump+shehbaz_xlong_c16_n16_nonstream_inline [shehbaz] | 16 | 16 | 0.364 | 0.172 | 0.364 | 0.172 | 0.762 | 0.802 | 0.978 | 0.952 | 4/16 0.250 [0.102, 0.495] | 5/16 0.312 [0.142, 0.556] | 5/16 0.312 [0.142, 0.556] | 1/12 0.083 [0.015, 0.354] |
| mix_trump+shehbaz_xlong_c16_n16_nonstream_inline [trump] | 16 | 16 | 0.004 | 0.002 | 0.004 | 0.002 | 0.854 | - | 0.988 | 0.993 | 0/16 0.000 [0.000, 0.194] | 0/16 0.000 [0.000, 0.194] | 0/16 0.000 [0.000, 0.194] | 0/16 0.000 [0.000, 0.194] |
| ALL | 96 | 64 | 0.173 | 0.081 | 0.168 | 0.073 | 0.736 | 0.773 | 0.964 | 1.067 | 9/96 0.094 [0.050, 0.169] | 14/96 0.146 [0.089, 0.230] | 14/96 0.146 [0.089, 0.230] | 5/87 0.058 [0.025, 0.128] |

Gate reasons (all runs): char_ratio<0.85 5, cer_nospace>0.35 3, del_run>=8 3, repeat_excess>=6 1, word_gap>2 1, pace>1.8 1  
Bad reasons (all runs): cer_nospace>0.3 5, char_ratio<0.88 5, del_run>=6 3, pace>1.5 3, repeat_excess>=5 1, long_word>2 1, word_gap>1.5 1, pace<0.7 1, sim<0.4 1  

