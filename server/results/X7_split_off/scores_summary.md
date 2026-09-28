# Scores: results/X7_split_off

Scored 2026-09-25T11:02:34+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| split_off_shehbaz_xxlong_c8_n43_nonstream_server [shehbaz] | 25 | 25 | 0.566 | 0.409 | 0.569 | 0.412 | 0.745 | 0.786 | 0.980 | 0.660 | 22/25 0.880 [0.700, 0.958] | 22/25 0.880 [0.700, 0.958] | 22/25 0.880 [0.700, 0.958] | 0/3 0.000 [0.000, 0.561] |
| split_off_trump_xxlong_c8_n43_nonstream_server [trump] | 43 | 43 | 0.013 | 0.007 | 0.013 | 0.007 | 0.840 | - | 0.984 | 0.975 | 5/43 0.116 [0.051, 0.245] | 7/43 0.163 [0.081, 0.300] | 7/43 0.163 [0.081, 0.300] | 2/38 0.053 [0.015, 0.173] |
| ALL | 68 | 68 | 0.216 | 0.155 | 0.190 | 0.123 | 0.805 | 0.786 | 0.983 | 0.859 | 27/68 0.397 [0.289, 0.516] | 29/68 0.426 [0.316, 0.545] | 29/68 0.426 [0.316, 0.545] | 2/41 0.049 [0.013, 0.161] |

Gate reasons (all runs): del_run>=8 19, cer_nospace>0.35 18, char_ratio<0.85 18, pace<0.6 16, repeat_excess>=4 5, repeat_excess>=6 3, ins_run>=6 2, token_run>=3 2, char_ratio>1.15 1, word_gap>2 1, long_word>2.5 1  
Bad reasons (all runs): del_run>=6 20, cer_nospace>0.3 19, pace<0.7 18, char_ratio<0.88 18, repeat_excess>=3 7, repeat_excess>=5 3, ins_run>=5 2, token_run>=3 2, char_ratio>1.12 1, word_gap>1.5 1, ins_run>=3 1, long_word>2 1, cr>2.4 1  

