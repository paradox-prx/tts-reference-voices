# Scores: results/P8_quality_raw

Scored 2026-09-25T11:02:33+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| raw_shehbaz_prompts_c16_n43_nonstream_server [shehbaz] | 41 | 41 | 0.378 | 0.174 | 0.378 | 0.174 | 0.769 | 0.812 | 0.980 | 0.976 | 8/41 0.195 [0.102, 0.340] | 11/41 0.268 [0.157, 0.419] | 11/41 0.268 [0.157, 0.419] | 3/33 0.091 [0.031, 0.236] |
| raw_trump_prompts_c16_n43_nonstream_server [trump] | 43 | 43 | 0.014 | 0.008 | 0.014 | 0.007 | 0.850 | - | 0.987 | 1.019 | 6/43 0.140 [0.066, 0.273] | 6/43 0.140 [0.066, 0.273] | 6/43 0.140 [0.066, 0.273] | 0/37 0.000 [0.000, 0.094] |
| ALL | 84 | 84 | 0.192 | 0.089 | 0.171 | 0.073 | 0.811 | 0.812 | 0.984 | 0.998 | 14/84 0.167 [0.102, 0.261] | 17/84 0.202 [0.130, 0.300] | 17/84 0.202 [0.130, 0.300] | 3/70 0.043 [0.015, 0.119] |

Gate reasons (all runs): repeat_excess>=4 4, del_run>=8 4, token_run>=3 2, word_gap>2 2, char_ratio<0.85 2, repeat_excess>=6 2, del_run>=3 1, ins_run>=6 1, long_word>2.5 1  
Bad reasons (all runs): del_run>=6 7, char_ratio<0.88 5, repeat_excess>=3 4, ins_run>=3 2, token_run>=3 2, word_gap>1.5 2, repeat_excess>=5 2, ins_run>=5 2, del_run>=3 1, pace>1.5 1, cer_nospace>0.3 1, long_word>2 1  

