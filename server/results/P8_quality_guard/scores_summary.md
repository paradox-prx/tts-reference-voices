# Scores: results/P8_quality_guard

Scored 2026-09-25T11:02:33+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| guard_shehbaz_prompts_c16_n43_nonstream_server [shehbaz] | 43 | 43 | 0.389 | 0.172 | 0.391 | 0.174 | 0.772 | 0.813 | 0.981 | 0.984 | 11/43 0.256 [0.149, 0.402] | 16/43 0.372 [0.244, 0.521] | 16/43 0.372 [0.244, 0.521] | 5/32 0.156 [0.069, 0.318] |
| guard_trump_prompts_c16_n43_nonstream_server [trump] | 43 | 43 | 0.013 | 0.006 | 0.013 | 0.006 | 0.854 | - | 0.987 | 1.003 | 1/43 0.023 [0.004, 0.121] | 2/43 0.046 [0.013, 0.155] | 2/43 0.046 [0.013, 0.155] | 1/42 0.024 [0.004, 0.123] |
| ALL | 86 | 86 | 0.201 | 0.089 | 0.181 | 0.074 | 0.813 | 0.813 | 0.984 | 0.994 | 12/86 0.140 [0.082, 0.228] | 18/86 0.209 [0.137, 0.307] | 18/86 0.209 [0.137, 0.307] | 6/74 0.081 [0.038, 0.166] |

Gate reasons (all runs): repeat_excess>=6 6, del_run>=8 3, long_word>2.5 3, word_gap>2 2, ins_run>=6 2, repeat_excess>=4 1, token_run>=3 1, char_ratio<0.85 1, cer_nospace>0.35 1, token_run>=4 1  
Bad reasons (all runs): repeat_excess>=5 9, del_run>=6 4, long_word>2 4, repeat_excess>=3 2, char_ratio<0.88 2, word_gap>1.5 2, ins_run>=5 2, wer>0.1 1, token_run>=3 1, pace>1.5 1, cer_nospace>0.3 1, char_ratio>1.12 1, token_run>=4 1  

