# Retry-policy simulation: results/P5_retry_study/gate_pace/nsm.jsonl

Cost = `audio_s`; bad = score_run's bad label; 95 % CIs bootstrap over prompts (2000 resamples). i.i.d. = f^(R+1), shown only for contrast. Takes are unseeded; settings pair by prompt.

## nsm_rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]

43 prompts x [6] takes; take bad rate 0.077 [0.051, 0.117], gate fail rate 0.019 [0.008, 0.045]; gate recall 0.25, precision 1.0, false-reject 0.0; prompts with any bad take 15, all takes bad 0.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.077 [0.043, 0.116] | 1.00 | 0.000 [-0.000, 0.000] | 0.019 | 0.0775 |
| retry R=1 | 0.058 [0.027, 0.097] | 1.02 | 0.020 [0.004, 0.036] | 0.000 | 0.0060 |
| retry R=2 | 0.058 [0.027, 0.097] | 1.02 | 0.020 [0.004, 0.036] | 0.000 | 0.0005 |
| best-of-2 | 0.029 [0.008, 0.056] | 2 | 1.000 | - | - |
| best-of-3 | 0.021 [0.002, 0.044] | 3 | 2.000 | - | - |

