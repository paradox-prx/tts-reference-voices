# Scores: results/P5_urdu_rp105

Scored 2026-09-25T11:02:33+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 251 | 43 | 0.382 | 0.181 | 0.383 | 0.182 | 0.774 | 0.814 | 0.980 | 0.940 | 72/251 0.287 [0.234, 0.346] | 92/251 0.366 [0.309, 0.428] | 15/41 0.366 [0.236, 0.519] | 20/179 0.112 [0.073, 0.166] |
| rp1.05_trump_prompts_c16_n43_nonstream_inline [trump] | 43 | 43 | 0.016 | 0.007 | 0.015 | 0.007 | 0.833 | - | 0.983 | 1.002 | 4/43 0.093 [0.037, 0.216] | 6/43 0.140 [0.066, 0.273] | 6/43 0.140 [0.066, 0.273] | 2/39 0.051 [0.014, 0.169] |
| ALL | 294 | 86 | 0.329 | 0.156 | 0.318 | 0.147 | 0.782 | 0.814 | 0.981 | 0.949 | 76/294 0.259 [0.212, 0.311] | 98/294 0.333 [0.282, 0.389] | 21/84 0.250 [0.170, 0.352] | 22/218 0.101 [0.068, 0.148] |

Gate reasons (all runs): del_run>=8 47, char_ratio<0.85 30, repeat_excess>=6 24, word_gap>2 10, cer_nospace>0.35 7, token_run>=4 7, ins_run>=6 4, repeat_excess>=4 2, pace<0.6 1, long_word>2.5 1, unaligned_tail>3 1, char_ratio>1.15 1, lead_sil>1 1, del_run>=3 1, token_run>=3 1, sim<0.88 1  
Bad reasons (all runs): del_run>=6 54, char_ratio<0.88 39, repeat_excess>=5 37, cer_nospace>0.3 15, word_gap>1.5 13, ins_run>=5 7, token_run>=4 7, cr>2.4 5, repeat_excess>=3 4, unaligned_tail>2 3, pace<0.7 2, long_word>2 1, char_ratio>1.12 1, lead_sil>1 1, del_run>=3 1, wer>0.1 1, token_run>=3 1, sim<0.5 1  

