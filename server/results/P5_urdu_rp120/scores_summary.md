# Scores: results/P5_urdu_rp120

Scored 2026-09-25T11:02:33+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 246 | 43 | 0.381 | 0.179 | 0.382 | 0.180 | 0.784 | 0.821 | 0.981 | 0.945 | 60/246 0.244 [0.194, 0.301] | 85/246 0.345 [0.289, 0.407] | 16/43 0.372 [0.244, 0.521] | 25/186 0.134 [0.093, 0.191] |
| rp1.20_trump_prompts_c16_n43_nonstream_inline [trump] | 43 | 43 | 0.013 | 0.007 | 0.013 | 0.007 | 0.853 | - | 0.987 | 1.003 | 4/43 0.093 [0.037, 0.216] | 5/43 0.116 [0.051, 0.245] | 5/43 0.116 [0.051, 0.245] | 1/39 0.026 [0.004, 0.132] |
| ALL | 289 | 86 | 0.327 | 0.153 | 0.316 | 0.144 | 0.794 | 0.821 | 0.981 | 0.954 | 64/289 0.222 [0.177, 0.273] | 90/289 0.311 [0.261, 0.367] | 21/86 0.244 [0.166, 0.345] | 26/225 0.116 [0.080, 0.164] |

Gate reasons (all runs): del_run>=8 43, char_ratio<0.85 29, repeat_excess>=6 20, word_gap>2 8, cer_nospace>0.35 5, token_run>=4 2, token_run>=3 2, repeat_excess>=4 2, pace<0.6 1, ins_run>=6 1, long_word>2.5 1, del_run>=3 1  
Bad reasons (all runs): del_run>=6 53, char_ratio<0.88 35, repeat_excess>=5 32, cer_nospace>0.3 14, word_gap>1.5 10, long_word>2 4, repeat_excess>=3 4, pace<0.7 2, token_run>=4 2, unaligned_tail>2 2, ins_run>=5 2, token_run>=3 2, del_run>=3 1  

