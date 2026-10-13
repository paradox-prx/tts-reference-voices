# Scores: /home/vector/Documents/abdullah_workspace/qwen-server/higgs-gguf/results/05_quality/manifest.jsonl

Scored 2026-10-09T16:17:59+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a | 39 | 5 | 0.111 | 0.067 | 0.106 | 0.065 | - | - | - | - | 4/39 0.103 [0.041, 0.236] | 4/39 0.103 [0.041, 0.236] | 4/39 0.103 [0.041, 0.236] | 0/35 0.000 [0.000, 0.099] |
| b | 39 | 5 | 0.048 | 0.024 | 0.040 | 0.018 | - | - | - | - | 0/39 0.000 [0.000, 0.090] | 0/39 0.000 [0.000, 0.090] | 0/39 0.000 [0.000, 0.090] | 0/39 0.000 [0.000, 0.090] |
| ALL | 78 | 5 | 0.079 | 0.046 | 0.073 | 0.042 | - | - | - | - | 4/78 0.051 [0.020, 0.125] | 4/78 0.051 [0.020, 0.125] | 4/78 0.051 [0.020, 0.125] | 0/74 0.000 [0.000, 0.049] |

Gate reasons (all runs): wer>0.2 2, char_ratio<0.85 2, del_run>=3 2, word_gap>2 2, pause>2 1  
Bad reasons (all runs): wer>0.1 2, char_ratio<0.88 2, del_run>=3 2, word_gap>1.5 2, pause>2 1  

