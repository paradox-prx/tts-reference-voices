# Scores: results/X9_nsm_stream

Scored 2026-09-25T12:02:05+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nsm_default_shehbaz_short_c1_n8_stream_inline [shehbaz] | 8 | 8 | 0.225 | 0.098 | 0.257 | 0.111 | 0.700 | 0.740 | 0.958 | 1.075 | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] |
| nsm_default_shehbaz_short_c8_n8_stream_inline [shehbaz] | 8 | 8 | 0.227 | 0.143 | 0.244 | 0.160 | 0.694 | 0.724 | 0.950 | 1.072 | 0/8 0.000 [0.000, 0.324] | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] |
| nsm_default_shehbaz_xlong_c1_n8_stream_inline [shehbaz] | 7 | 7 | 0.327 | 0.138 | 0.327 | 0.138 | 0.783 | 0.828 | 0.984 | 0.976 | 0/7 0.000 [0.000, 0.354] | 0/7 0.000 [0.000, 0.354] | 0/7 0.000 [0.000, 0.354] | 0/7 0.000 [0.000, 0.354] |
| nsm_default_shehbaz_xlong_c8_n8_stream_inline [shehbaz] | 8 | 8 | 0.348 | 0.151 | 0.348 | 0.153 | 0.784 | 0.820 | 0.980 | 0.938 | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] | 0/7 0.000 [0.000, 0.354] |
| nsm_true_shehbaz_short_c1_n8_stream_inline [shehbaz] | 8 | 8 | 0.322 | 0.132 | 0.305 | 0.130 | 0.677 | 0.718 | 0.964 | 1.161 | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] |
| nsm_true_shehbaz_short_c8_n8_stream_inline [shehbaz] | 8 | 8 | 0.214 | 0.087 | 0.269 | 0.111 | 0.697 | 0.738 | 0.963 | 1.172 | 0/8 0.000 [0.000, 0.324] | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] |
| nsm_true_shehbaz_xlong_c1_n8_stream_inline [shehbaz] | 8 | 8 | 0.355 | 0.165 | 0.355 | 0.165 | 0.787 | 0.827 | 0.979 | 0.956 | 2/8 0.250 [0.071, 0.591] | 2/8 0.250 [0.071, 0.591] | 2/8 0.250 [0.071, 0.591] | 0/6 0.000 [0.000, 0.390] |
| nsm_true_shehbaz_xlong_c8_n8_stream_inline [shehbaz] | 8 | 8 | 0.297 | 0.138 | 0.292 | 0.136 | 0.785 | 0.824 | 0.982 | 1.032 | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] | 0/7 0.000 [0.000, 0.354] |
| ALL | 63 | 16 | 0.289 | 0.131 | 0.324 | 0.146 | 0.738 | 0.776 | 0.970 | 1.049 | 4/63 0.064 [0.025, 0.152] | 6/63 0.095 [0.044, 0.193] | 6/63 0.095 [0.044, 0.193] | 2/59 0.034 [0.009, 0.115] |

Gate reasons (all runs): del_run>=8 4, char_ratio<0.85 2, unaligned_tail>3 1, word_gap>2 1  
Bad reasons (all runs): del_run>=6 4, char_ratio<0.88 3, cer_nospace>0.3 2, unaligned_tail>2 1, word_gap>1.5 1  

