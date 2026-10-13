# Scores: results/X6_nsm_long_urdu

Scored 2026-09-25T11:02:34+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nsm_false_shehbaz_xxlong_c16_n43_nonstream_inline [shehbaz] | 27 | 27 | 0.566 | 0.401 | 0.568 | 0.404 | 0.738 | 0.774 | 0.978 | 0.763 | 26/27 0.963 [0.817, 0.993] | 26/27 0.963 [0.817, 0.993] | 26/27 0.963 [0.817, 0.993] | 0/1 0.000 [0.000, 0.793] |
| nsm_true_shehbaz_xxlong_c16_n43_nonstream_inline [shehbaz] | 43 | 43 | 0.360 | 0.170 | 0.360 | 0.171 | 0.759 | 0.801 | 0.979 | 0.980 | 19/43 0.442 [0.304, 0.589] | 25/43 0.581 [0.433, 0.716] | 25/43 0.581 [0.433, 0.716] | 6/24 0.250 [0.120, 0.449] |
| nsm_true_trump_xxlong_c16_n43_nonstream_inline [trump] | 43 | 43 | 0.012 | 0.006 | 0.011 | 0.006 | 0.841 | - | 0.984 | 1.002 | 4/43 0.093 [0.037, 0.216] | 4/43 0.093 [0.037, 0.216] | 4/43 0.093 [0.037, 0.216] | 0/39 0.000 [0.000, 0.090] |
| ALL | 113 | 86 | 0.277 | 0.163 | 0.254 | 0.141 | 0.785 | 0.791 | 0.981 | 0.937 | 49/113 0.434 [0.346, 0.526] | 55/113 0.487 [0.397, 0.578] | 55/113 0.487 [0.397, 0.578] | 6/64 0.094 [0.044, 0.190] |

Gate reasons (all runs): del_run>=8 27, cer_nospace>0.35 19, char_ratio<0.85 19, repeat_excess>=6 19, pace<0.6 14, word_gap>2 10, ins_run>=6 9, long_word>2.5 4, repeat_excess>=4 4, token_run>=4 3, token_run>=3 2, unaligned_tail>3 1, char_ratio>1.15 1, pause>2 1  
Bad reasons (all runs): del_run>=6 32, repeat_excess>=5 25, cer_nospace>0.3 22, char_ratio<0.88 21, pace<0.7 17, word_gap>1.5 12, ins_run>=5 10, cr>2.4 4, long_word>2 4, repeat_excess>=3 4, token_run>=4 3, token_run>=3 2, char_ratio>1.12 2, unaligned_tail>2 1, pace>1.5 1, pause>2 1  

