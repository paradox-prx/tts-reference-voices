# Scores: results/P9_baseline_b1

Scored 2026-09-25T11:02:34+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| shehbaz_short_c1_n8_nonstream_inline [shehbaz] | 8 | 8 | 0.363 | 0.179 | 0.381 | 0.187 | 0.709 | 0.739 | 0.968 | 1.057 | 0/8 0.000 [0.000, 0.324] | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] |
| shehbaz_short_c4_n8_nonstream_inline [shehbaz] | 8 | 8 | 0.301 | 0.139 | 0.346 | 0.164 | 0.662 | 0.700 | 0.961 | 1.069 | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] | 1/8 0.125 [0.022, 0.471] | 0/7 0.000 [0.000, 0.354] |
| shehbaz_xlong_c1_n4_nonstream_inline [shehbaz] | 4 | 4 | 0.528 | 0.377 | 0.535 | 0.387 | 0.679 | 0.698 | 0.904 | 1.199 | 3/4 0.750 [0.301, 0.954] | 3/4 0.750 [0.301, 0.954] | 3/4 0.750 [0.301, 0.954] | 0/1 0.000 [0.000, 0.793] |
| shehbaz_xlong_c4_n4_nonstream_inline [shehbaz] | 4 | 4 | 0.363 | 0.146 | 0.364 | 0.145 | 0.723 | 0.773 | 0.983 | 0.894 | 0/4 0.000 [0.000, 0.490] | 0/4 0.000 [0.000, 0.490] | 0/4 0.000 [0.000, 0.490] | 0/4 0.000 [0.000, 0.490] |
| trump_short_c1_n8_nonstream_inline [trump] | 8 | 8 | 0.000 | 0.000 | 0.000 | 0.000 | 0.753 | - | 0.963 | 1.088 | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] | 0/8 0.000 [0.000, 0.324] |
| trump_short_c4_n8_nonstream_inline [trump] | 8 | 8 | 0.021 | 0.007 | 0.013 | 0.004 | 0.705 | - | 0.960 | 1.240 | 0/8 0.000 [0.000, 0.324] | 2/8 0.250 [0.071, 0.591] | 2/8 0.250 [0.071, 0.591] | 2/8 0.250 [0.071, 0.591] |
| trump_xlong_c1_n4_nonstream_inline [trump] | 4 | 4 | 0.010 | 0.008 | 0.010 | 0.008 | 0.854 | - | 0.985 | 0.984 | 0/4 0.000 [0.000, 0.490] | 0/4 0.000 [0.000, 0.490] | 0/4 0.000 [0.000, 0.490] | 0/4 0.000 [0.000, 0.490] |
| trump_xlong_c4_n4_nonstream_inline [trump] | 4 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | 0.847 | - | 0.988 | 0.933 | 0/4 0.000 [0.000, 0.490] | 0/4 0.000 [0.000, 0.490] | 0/4 0.000 [0.000, 0.490] | 0/4 0.000 [0.000, 0.490] |
| ALL | 48 | 32 | 0.189 | 0.098 | 0.199 | 0.106 | 0.730 | 0.725 | 0.964 | 1.077 | 4/48 0.083 [0.033, 0.196] | 7/48 0.146 [0.072, 0.272] | 7/48 0.146 [0.072, 0.272] | 3/44 0.068 [0.024, 0.182] |

Gate reasons (all runs): cer_nospace>0.35 3, char_ratio<0.85 2, del_run>=8 2, repeat_excess>=6 1, pace>1.8 1, word_gap>2 1, unaligned_tail>3 1, sim<0.88 1  
Bad reasons (all runs): cer_nospace>0.3 4, pace>1.5 2, char_ratio<0.88 2, del_run>=6 2, wer>0.1 1, repeat_excess>=5 1, pace<0.7 1, long_word>2 1, word_gap>1.5 1, unaligned_tail>2 1, sim<0.5 1, sim_heldout<0.5 1  

