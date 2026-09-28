# Scores: results/X1_nsm

Scored 2026-09-25T11:02:33+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nsm_true_shehbaz_prompts_c16_n43_nonstream_inline [shehbaz] | 43 | 43 | 0.354 | 0.156 | 0.354 | 0.155 | 0.797 | 0.833 | 0.979 | 1.001 | 9/43 0.209 [0.114, 0.352] | 14/43 0.326 [0.205, 0.475] | 14/43 0.326 [0.205, 0.475] | 5/34 0.147 [0.065, 0.301] |

Gate reasons (all runs): del_run>=8 4, repeat_excess>=6 4, char_ratio<0.85 3, word_gap>2 3  
Bad reasons (all runs): repeat_excess>=5 7, del_run>=6 5, word_gap>1.5 4, char_ratio<0.88 3, long_word>2 1  

