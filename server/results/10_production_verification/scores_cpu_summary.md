# Scores: /tmp/claude-1000/-home-vector-Documents-abdullah-workspace-qwen-server/d59b2ed1-2682-45ec-83a8-99dff9b0c49c/scratchpad/prod_manifest.jsonl

Scored 2026-09-25T12:05:43+05:00; gate SIM model `base`, bad SIM model `large`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = total edits / total reference length.

| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| /tmp/claude-1000/-home-vector-Documents-abdullah-workspace-qwen-server/d59b2ed1-2682-45ec-83a8-99dff9b0c49c/scratchpad/prod_manifest.jsonl [shehbaz] | 1 | 1 | 0.297 | 0.143 | 0.297 | 0.143 | 0.860 | 0.881 | 0.987 | 1.032 | 0/1 0.000 [0.000, 0.793] | 0/1 0.000 [0.000, 0.793] | 0/1 0.000 [0.000, 0.793] | 0/1 0.000 [0.000, 0.793] |
| /tmp/claude-1000/-home-vector-Documents-abdullah-workspace-qwen-server/d59b2ed1-2682-45ec-83a8-99dff9b0c49c/scratchpad/prod_manifest.jsonl [trump] | 1 | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.136 | - | 0.267 | 0.944 | 1/1 1.000 [0.206, 1.000] | 1/1 1.000 [0.206, 1.000] | 1/1 1.000 [0.206, 1.000] | - |
| ALL | 2 | 2 | 0.148 | 0.071 | 0.284 | 0.133 | 0.498 | 0.881 | 0.627 | 0.988 | 1/2 0.500 [0.095, 0.905] | 1/2 0.500 [0.095, 0.905] | 1/2 0.500 [0.095, 0.905] | 0/1 0.000 [0.000, 0.793] |

Gate reasons (all runs): sim<0.85 1  
Bad reasons (all runs): sim<0.4 1  

