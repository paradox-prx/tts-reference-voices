# Scores: eval/calibration/synth_manifest.jsonl

Scored 2026-09-25T04:00:08+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| eval/calibration/synth_manifest.jsonl [shehbaz] | 6 | 1 | 0.130 | 0.077 | 0.130 | 0.077 | 0.890 | 0.933 | 0.983 | - | 6/6 1.000 [0.610, 1.000] | 6/6 1.000 [0.610, 1.000] | 6/6 1.000 [0.610, 1.000] | - |
| eval/calibration/synth_manifest.jsonl [trump] | 2 | 1 | 0.183 | 0.174 | 0.183 | 0.174 | 0.989 | - | 0.998 | - | 2/2 1.000 [0.342, 1.000] | 2/2 1.000 [0.342, 1.000] | 2/2 1.000 [0.342, 1.000] | - |
| ALL | 8 | 2 | 0.143 | 0.101 | 0.158 | 0.134 | 0.915 | 0.933 | 0.987 | - | 8/8 1.000 [0.676, 1.000] | 8/8 1.000 [0.676, 1.000] | 8/8 1.000 [0.676, 1.000] | - |

Gate reasons (all runs): unaligned_tail>3 2, long_word>2.5 2, char_ratio<0.85 2, trail_sil>1.5 1, cer_nospace>0.15 1, del_run>=4 1, pause>2 1, word_gap>2 1, wer>0.2 1, del_run>=3 1  
Bad reasons (all runs): unaligned_tail>2 2, long_word>2 2, char_ratio<0.9 2, del_run>=3 2, trail_sil>1.5 1, cer_nospace>0.1 1, pause>2 1, word_gap>1.5 1, wer>0.1 1  

