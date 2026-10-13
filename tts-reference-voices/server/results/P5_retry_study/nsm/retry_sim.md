# Retry-policy simulation: results/P5_urdu_rp105/takes_all.jsonl, results/P5_urdu_nsm/takes_all.jsonl

Cost = `audio_s`; bad = score_run's bad label; 95 % CIs bootstrap over prompts (2000 resamples). i.i.d. = f^(R+1), shown only for contrast. Takes are unseeded; settings pair by prompt.

## nsm_rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]

43 prompts x [6] takes; take bad rate 0.077 [0.051, 0.117], gate fail rate 0.143 [0.106, 0.191]; gate recall 1.0, precision 0.5405, false-reject 0.0714; prompts with any bad take 15, all takes bad 0.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.077 [0.043, 0.116] | 1.00 | 0.000 [-0.000, 0.000] | 0.143 | 0.0775 |
| retry R=1 | 0.019 [0.006, 0.033] | 1.14 | 0.146 [0.087, 0.212] | 0.045 | 0.0060 |
| retry R=2 | 0.005 [0.000, 0.013] | 1.19 | 0.192 [0.106, 0.290] | 0.014 | 0.0005 |
| retry R=3 | 0.002 [0.000, 0.005] | 1.20 | 0.207 [0.111, 0.318] | 0.003 | 0.0000 |
| best-of-2 | 0.019 [0.006, 0.033] | 2 | 1.000 | - | - |
| best-of-3 | 0.005 [0.000, 0.013] | 3 | 2.000 | - | - |

## rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]

43 prompts x [6] takes; take bad rate 0.155 [0.116, 0.204], gate fail rate 0.306 [0.253, 0.365]; gate recall 1.0, precision 0.5063, false-reject 0.1789; prompts with any bad take 21, all takes bad 0.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.155 [0.097, 0.221] | 1.00 | -0.000 [-0.000, 0.000] | 0.306 | 0.1550 |
| retry R=1 | 0.088 [0.036, 0.152] | 1.31 | 0.311 [0.221, 0.409] | 0.166 | 0.0240 |
| retry R=2 | 0.072 [0.017, 0.141] | 1.47 | 0.481 [0.309, 0.673] | 0.121 | 0.0037 |
| retry R=3 | 0.067 [0.006, 0.141] | 1.59 | 0.606 [0.359, 0.896] | 0.098 | 0.0006 |
| best-of-2 | 0.088 [0.036, 0.152] | 2 | 1.000 | - | - |
| best-of-3 | 0.072 [0.017, 0.141] | 3 | 2.000 | - | - |

## rp1.05_trump_prompts_c16_n43_nonstream_inline [trump]

43 prompts x [1] takes; take bad rate 0.023 [0.004, 0.121], gate fail rate 0.093 [0.037, 0.216]; gate recall 1.0, precision 0.25, false-reject 0.0714; prompts with any bad take 1, all takes bad 1.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.023 [0.000, 0.070] | 1.00 | 0.000 [0.000, 0.000] | 0.093 | 0.0233 |

## Paired by prompt vs `nsm_rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]`

| setting | R | shared prompts | bad (baseline) | bad (setting) | difference [95% CI] |
|---|---|---|---|---|---|
| rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 0 | 43 | 0.077 | 0.155 | 0.077 [0.000, 0.151] |
| rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 1 | 43 | 0.019 | 0.088 | 0.070 [0.014, 0.135] |
| rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 2 | 43 | 0.005 | 0.072 | 0.067 [0.013, 0.136] |
| rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 3 | 43 | 0.002 | 0.067 | 0.065 [0.005, 0.141] |

