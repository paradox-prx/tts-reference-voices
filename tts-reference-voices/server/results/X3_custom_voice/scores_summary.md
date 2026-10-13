# Scores: results/X3_custom_voice

Scored 2026-09-25T11:02:33+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| avg_shehbaz_prompts_c16_n43_nonstream_server-avg [shehbaz-avg] | 41 | 41 | 0.371 | 0.183 | 0.370 | 0.182 | 0.769 | 0.811 | 0.982 | 0.953 | 10/41 0.244 [0.138, 0.393] | 11/41 0.268 [0.157, 0.419] | 11/41 0.268 [0.157, 0.419] | 1/31 0.032 [0.006, 0.162] |
| prompt_shehbaz_prompts_c16_n43_nonstream_server-prompt [shehbaz-prompt] | 42 | 42 | 0.374 | 0.182 | 0.372 | 0.181 | 0.769 | 0.812 | 0.983 | 0.958 | 11/42 0.262 [0.153, 0.411] | 16/42 0.381 [0.250, 0.532] | 16/42 0.381 [0.250, 0.532] | 5/31 0.161 [0.071, 0.326] |
| ALL | 83 | 42 | 0.373 | 0.183 | 0.371 | 0.181 | 0.769 | 0.812 | 0.982 | 0.955 | 21/83 0.253 [0.172, 0.356] | 27/83 0.325 [0.234, 0.432] | 27/83 0.325 [0.234, 0.432] | 6/62 0.097 [0.045, 0.196] |

Gate reasons (all runs): del_run>=8 14, char_ratio<0.85 9, repeat_excess>=6 5, token_run>=4 2, cer_nospace>0.35 2, word_gap>2 2, unaligned_tail>3 1, ins_run>=6 1, long_word>2.5 1  
Bad reasons (all runs): del_run>=6 15, char_ratio<0.88 11, repeat_excess>=5 9, cer_nospace>0.3 6, long_word>2 2, token_run>=4 2, word_gap>1.5 2, unaligned_tail>2 1, ins_run>=5 1  

