# Scores: results/P5_urdu_rp110

Scored 2026-09-25T11:02:33+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 250 | 43 | 0.390 | 0.192 | 0.390 | 0.192 | 0.778 | 0.819 | 0.981 | 0.950 | 71/250 0.284 [0.232, 0.343] | 90/250 0.360 [0.303, 0.421] | 16/42 0.381 [0.250, 0.532] | 19/179 0.106 [0.069, 0.160] |

Gate reasons (all runs): del_run>=8 43, char_ratio<0.85 26, repeat_excess>=6 25, cer_nospace>0.35 12, word_gap>2 12, ins_run>=6 6, token_run>=4 5, long_word>2.5 3, unaligned_tail>3 3, pace<0.6 1  
Bad reasons (all runs): del_run>=6 52, char_ratio<0.88 38, repeat_excess>=5 36, cer_nospace>0.3 19, word_gap>1.5 12, ins_run>=5 7, token_run>=4 5, unaligned_tail>2 5, long_word>2 3, pace<0.7 2  

