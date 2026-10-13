# Scores: results/P5_urdu_nsm

Scored 2026-09-25T12:02:05+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nsm_rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 253 | 43 | 0.342 | 0.152 | 0.342 | 0.152 | 0.798 | 0.832 | 0.981 | 1.005 | 32/253 0.127 [0.091, 0.173] | 63/253 0.249 [0.200, 0.306] | 8/43 0.186 [0.097, 0.326] | 31/221 0.140 [0.101, 0.192] |

Gate reasons (all runs): del_run>=8 16, repeat_excess>=6 13, char_ratio<0.85 12, word_gap>2 11, cer_nospace>0.35 5, long_word>2.5 2, ins_run>=6 2, sim<0.88 1, char_ratio>1.15 1, token_run>=4 1  
Bad reasons (all runs): repeat_excess>=5 35, del_run>=6 22, char_ratio<0.88 19, word_gap>1.5 16, cer_nospace>0.3 8, long_word>2 4, char_ratio>1.12 2, ins_run>=5 2, sim<0.5 1, sim_heldout<0.5 1, cr>2.4 1, token_run>=4 1  

