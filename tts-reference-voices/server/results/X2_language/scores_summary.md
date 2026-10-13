# Scores: results/X2_language

Scored 2026-09-25T11:02:33+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lang_auto_trump_prompts_c16_n43_nonstream_inline [trump] | 43 | 43 | 0.011 | 0.006 | 0.011 | 0.006 | 0.850 | - | 0.986 | 1.013 | 2/43 0.046 [0.013, 0.155] | 4/43 0.093 [0.037, 0.216] | 4/43 0.093 [0.037, 0.216] | 2/41 0.049 [0.013, 0.161] |

Gate reasons (all runs): lead_sil>1 1, repeat_excess>=4 1, token_run>=3 1  
Bad reasons (all runs): repeat_excess>=3 2, ins_run>=3 1, lead_sil>1 1, token_run>=3 1  

