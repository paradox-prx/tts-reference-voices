# Scores: results/X4_length_cap

Scored 2026-09-25T11:02:34+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cap_off_shehbaz_prompts_c16_n43_nonstream_inline [shehbaz] | 43 | 43 | 0.372 | 0.172 | 0.373 | 0.173 | 0.768 | 0.811 | 0.980 | 0.958 | 10/43 0.233 [0.132, 0.377] | 16/43 0.372 [0.244, 0.521] | 16/43 0.372 [0.244, 0.521] | 6/33 0.182 [0.086, 0.344] |
| cap_on_shehbaz_prompts_c16_n43_nonstream_inline [shehbaz] | 42 | 42 | 0.361 | 0.163 | 0.362 | 0.163 | 0.768 | 0.806 | 0.978 | 0.962 | 8/42 0.191 [0.100, 0.333] | 11/42 0.262 [0.153, 0.411] | 11/42 0.262 [0.153, 0.411] | 3/34 0.088 [0.030, 0.230] |
| ALL | 85 | 43 | 0.367 | 0.168 | 0.367 | 0.168 | 0.768 | 0.808 | 0.979 | 0.960 | 18/85 0.212 [0.138, 0.310] | 27/85 0.318 [0.228, 0.423] | 27/85 0.318 [0.228, 0.423] | 9/67 0.134 [0.072, 0.236] |

Gate reasons (all runs): del_run>=8 11, char_ratio<0.85 8, repeat_excess>=6 6, word_gap>2 2, ins_run>=6 2, cer_nospace>0.35 1, unaligned_tail>3 1  
Bad reasons (all runs): del_run>=6 15, repeat_excess>=5 11, char_ratio<0.88 10, cer_nospace>0.3 4, word_gap>1.5 3, long_word>2 3, ins_run>=5 2, unaligned_tail>2 1, char_ratio>1.12 1, cr>2.4 1  

