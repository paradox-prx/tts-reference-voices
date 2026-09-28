# Scores: ../higgs/results/Q_prompts

Scored 2026-09-28T20:32:35+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1_t08_shehbaz_prompts_c8_n43_k2_nonstream_inline [shehbaz] | 86 | 43 | 0.146 | 0.114 | 0.149 | 0.117 | 0.851 | 0.852 | 0.978 | 0.961 | 31/86 0.360 [0.267, 0.466] | 33/86 0.384 [0.288, 0.489] | 18/43 0.419 [0.284, 0.567] | 2/55 0.036 [0.010, 0.123] |
| Q1_t08_trump_prompts_c8_n43_k2_nonstream_inline [trump] | 86 | 43 | 0.088 | 0.082 | 0.094 | 0.091 | 0.830 | - | 0.983 | 0.960 | 57/86 0.663 [0.558, 0.754] | 57/86 0.663 [0.558, 0.754] | 31/43 0.721 [0.573, 0.833] | 0/29 0.000 [0.000, 0.117] |
| Q2_t10_shehbaz_prompts_c8_n43_k2_nonstream_inline [shehbaz] | 86 | 43 | 0.232 | 0.195 | 0.237 | 0.201 | 0.864 | 0.865 | 0.981 | 0.862 | 43/86 0.500 [0.397, 0.603] | 48/86 0.558 [0.453, 0.658] | 25/43 0.581 [0.433, 0.716] | 5/43 0.116 [0.051, 0.245] |
| Q3_ref25_shehbaz_prompts_c8_n43_k2_nonstream_inline [shehbaz] | 86 | 43 | 0.166 | 0.135 | 0.170 | 0.140 | 0.861 | 0.874 | 0.979 | 0.961 | 39/86 0.454 [0.352, 0.558] | 44/86 0.512 [0.408, 0.615] | 22/43 0.512 [0.367, 0.654] | 5/47 0.106 [0.046, 0.226] |
| Q4_expr_plain_shehbaz_prompts_c8_n43_k2_nonstream_inline [shehbaz] | 86 | 43 | 0.193 | 0.162 | 0.197 | 0.166 | 0.862 | 0.863 | 0.979 | 0.896 | 39/86 0.454 [0.352, 0.558] | 40/86 0.465 [0.363, 0.570] | 21/43 0.488 [0.346, 0.632] | 1/47 0.021 [0.004, 0.111] |
| Q4_expr_tags_shehbaz_prompts_c8_n43_k2_nonstream_inline [shehbaz] | 86 | 43 | 0.234 | 0.200 | 0.234 | 0.201 | 0.810 | 0.804 | 0.963 | 0.966 | 49/86 0.570 [0.464, 0.669] | 52/86 0.605 [0.499, 0.701] | 25/43 0.581 [0.433, 0.716] | 3/37 0.081 [0.028, 0.213] |
| ALL | 516 | 86 | 0.176 | 0.148 | 0.177 | 0.148 | 0.846 | 0.852 | 0.977 | 0.934 | 258/516 0.500 [0.457, 0.543] | 274/516 0.531 [0.488, 0.574] | 142/258 0.550 [0.489, 0.610] | 16/258 0.062 [0.038, 0.098] |

Gate reasons (all runs): del_run>=8 183, char_ratio<0.85 156, cer_nospace>0.35 72, del_run>=3 55, pace<0.6 33, ins_run>=6 11, word_gap>2 8, repeat_excess>=6 8, lead_sil>1 7, char_ratio>1.15 6, unaligned_tail>3 4, wer>0.2 4, repeat_excess>=4 2, token_run>=4 2, ins_run>=4 1, token_run>=3 1, pause>2 1, char_run>=1 1, sim<0.88 1, pace>1.8 1  
Bad reasons (all runs): del_run>=6 197, char_ratio<0.88 179, cer_nospace>0.3 92, pace<0.7 61, del_run>=3 55, wer>0.1 27, ins_run>=5 12, repeat_excess>=5 10, unaligned_tail>2 9, word_gap>1.5 8, lead_sil>1 7, char_ratio>1.12 7, cr>2.4 5, pace>1.5 3, repeat_excess>=3 2, token_run>=4 2, ins_run>=3 1, token_run>=3 1, pause>2 1, char_run>=1 1, sim<0.5 1, sim_heldout<0.5 1  

