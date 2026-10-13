# Scores: results/X7_split_60

Scored 2026-09-25T11:02:34+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| split_60_shehbaz_xxlong_c8_n43_nonstream_server [shehbaz] | 43 | 43 | 0.371 | 0.172 | 0.370 | 0.172 | 0.822 | 0.855 | 0.991 | 1.005 | 20/43 0.465 [0.325, 0.611] | 23/43 0.535 [0.389, 0.675] | 23/43 0.535 [0.389, 0.675] | 3/23 0.130 [0.045, 0.321] |
| split_60_trump_xxlong_c8_n43_nonstream_server [trump] | 43 | 43 | 0.010 | 0.007 | 0.010 | 0.007 | 0.869 | - | 0.987 | 1.016 | 3/43 0.070 [0.024, 0.186] | 5/43 0.116 [0.051, 0.245] | 5/43 0.116 [0.051, 0.245] | 2/40 0.050 [0.014, 0.165] |
| ALL | 86 | 86 | 0.190 | 0.089 | 0.170 | 0.074 | 0.846 | 0.855 | 0.989 | 1.010 | 23/86 0.267 [0.185, 0.369] | 28/86 0.326 [0.236, 0.430] | 28/86 0.326 [0.236, 0.430] | 5/63 0.079 [0.034, 0.173] |

Gate reasons (all runs): del_run>=8 13, word_gap>2 8, repeat_excess>=6 6, char_ratio<0.85 4, repeat_excess>=4 2, long_word>2.5 1, cer_nospace>0.35 1, token_run>=4 1, token_run>=3 1  
Bad reasons (all runs): repeat_excess>=5 15, del_run>=6 14, word_gap>1.5 9, char_ratio<0.88 5, repeat_excess>=3 3, cer_nospace>0.3 2, long_word>2 1, token_run>=4 1, ins_run>=3 1, token_run>=3 1  

