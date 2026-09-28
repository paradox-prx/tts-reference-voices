# Scores: results/X8_split_nsm

Scored 2026-09-25T12:02:05+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| split60_nsm_shehbaz_xxlong_c8_n43_nonstream_server [shehbaz] | 43 | 43 | 0.341 | 0.151 | 0.341 | 0.152 | 0.862 | 0.894 | 0.989 | 1.074 | 13/43 0.302 [0.186, 0.451] | 16/43 0.372 [0.244, 0.521] | 16/43 0.372 [0.244, 0.521] | 3/30 0.100 [0.035, 0.256] |

Gate reasons (all runs): repeat_excess>=6 8, del_run>=8 5, word_gap>2 5, char_ratio<0.85 3  
Bad reasons (all runs): repeat_excess>=5 9, word_gap>1.5 7, del_run>=6 6, char_ratio<0.88 3, long_word>2 2, cer_nospace>0.3 1  

