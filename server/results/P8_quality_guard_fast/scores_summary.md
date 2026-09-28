# Scores: results/P8_quality_guard_fast

Scored 2026-09-25T11:02:33+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| guardfast_shehbaz_prompts_c16_n43_nonstream_server [shehbaz] | 43 | 43 | 0.362 | 0.168 | 0.363 | 0.169 | 0.778 | 0.818 | 0.981 | 0.969 | 9/43 0.209 [0.114, 0.352] | 14/43 0.326 [0.205, 0.475] | 14/43 0.326 [0.205, 0.475] | 5/34 0.147 [0.065, 0.301] |
| guardfast_trump_prompts_c16_n43_nonstream_server [trump] | 43 | 43 | 0.012 | 0.006 | 0.012 | 0.006 | 0.855 | - | 0.987 | 0.999 | 2/43 0.046 [0.013, 0.155] | 2/43 0.046 [0.013, 0.155] | 2/43 0.046 [0.013, 0.155] | 0/41 0.000 [0.000, 0.086] |
| ALL | 86 | 86 | 0.187 | 0.087 | 0.167 | 0.072 | 0.816 | 0.818 | 0.984 | 0.984 | 11/86 0.128 [0.073, 0.215] | 16/86 0.186 [0.118, 0.281] | 16/86 0.186 [0.118, 0.281] | 5/75 0.067 [0.029, 0.147] |

Gate reasons (all runs): repeat_excess>=6 5, del_run>=8 3, cer_nospace>0.35 3, ins_run>=6 2, repeat_excess>=4 1, token_run>=3 1, del_run>=3 1, char_ratio<0.85 1, long_word>2.5 1, char_ratio>1.15 1, unaligned_tail>3 1  
Bad reasons (all runs): repeat_excess>=5 8, del_run>=6 6, cer_nospace>0.3 3, cr>2.4 3, char_ratio<0.88 2, ins_run>=5 2, repeat_excess>=3 1, token_run>=3 1, del_run>=3 1, word_gap>1.5 1, long_word>2 1, char_ratio>1.12 1, unaligned_tail>2 1  

