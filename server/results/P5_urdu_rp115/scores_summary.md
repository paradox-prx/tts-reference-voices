# Scores: results/P5_urdu_rp115

Scored 2026-09-25T11:02:33+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 245 | 43 | 0.378 | 0.180 | 0.379 | 0.180 | 0.777 | 0.816 | 0.982 | 0.944 | 59/245 0.241 [0.192, 0.298] | 78/245 0.318 [0.263, 0.379] | 14/42 0.333 [0.210, 0.484] | 19/186 0.102 [0.066, 0.154] |

Gate reasons (all runs): del_run>=8 42, char_ratio<0.85 26, repeat_excess>=6 13, ins_run>=6 8, word_gap>2 7, cer_nospace>0.35 6, token_run>=4 4, long_word>2.5 2, char_ratio>1.15 2  
Bad reasons (all runs): del_run>=6 51, char_ratio<0.88 34, repeat_excess>=5 23, cer_nospace>0.3 18, ins_run>=5 10, word_gap>1.5 9, token_run>=4 4, long_word>2 4, char_ratio>1.12 3, cr>2.4 2, unaligned_tail>2 2  

