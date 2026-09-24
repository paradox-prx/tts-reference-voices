# Scores: eval/calibration/refs_manifest.jsonl

Scored 2026-09-25T04:00:07+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| eval/calibration/refs_manifest.jsonl [shehbaz] | 9 | 9 | 0.114 | 0.035 | 0.126 | 0.040 | 0.924 | 0.937 | 0.987 | - | 0/9 0.000 [0.000, 0.299] | 0/9 0.000 [0.000, 0.299] | 0/9 0.000 [0.000, 0.299] | 0/9 0.000 [0.000, 0.299] |
| eval/calibration/refs_manifest.jsonl [trump] | 2 | 1 | 0.008 | 0.002 | 0.008 | 0.002 | 1.000 | - | 1.000 | - | 0/2 0.000 [0.000, 0.658] | 0/2 0.000 [0.000, 0.658] | 0/2 0.000 [0.000, 0.658] | 0/2 0.000 [0.000, 0.658] |
| ALL | 11 | 10 | 0.095 | 0.029 | 0.079 | 0.023 | 0.938 | 0.937 | 0.989 | - | 0/11 0.000 [0.000, 0.259] | 0/11 0.000 [0.000, 0.259] | 0/11 0.000 [0.000, 0.259] | 0/11 0.000 [0.000, 0.259] |

Gate reasons (all runs): none  
Bad reasons (all runs): none  

