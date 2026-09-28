# Retry-policy simulation: results/P5_urdu_rp105/takes_all.jsonl, results/P5_urdu_rp110/takes_all.jsonl, results/P5_urdu_rp115/takes_all.jsonl, results/P5_urdu_rp120/takes_all.jsonl

Cost = `audio_s`; bad = score_run's bad label; 95 % CIs bootstrap over prompts (2000 resamples). i.i.d. = f^(R+1), shown only for contrast. Takes are unseeded; settings pair by prompt.

## rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]

43 prompts x [6] takes; take bad rate 0.155 [0.116, 0.204], gate fail rate 0.306 [0.253, 0.365]; gate recall 1.0, precision 0.5063, false-reject 0.1789; prompts with any bad take 21, all takes bad 0.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.155 [0.097, 0.221] | 1.00 | -0.000 [-0.000, 0.000] | 0.306 | 0.1550 |
| retry R=1 | 0.088 [0.036, 0.152] | 1.31 | 0.311 [0.221, 0.409] | 0.166 | 0.0240 |
| retry R=2 | 0.072 [0.017, 0.141] | 1.47 | 0.481 [0.309, 0.673] | 0.121 | 0.0037 |
| retry R=3 | 0.067 [0.006, 0.141] | 1.59 | 0.606 [0.359, 0.896] | 0.098 | 0.0006 |
| best-of-3 | 0.072 [0.017, 0.141] | 3 | 2.000 | - | - |

## rp1.05_trump_prompts_c16_n43_nonstream_inline [trump]

43 prompts x [1] takes; take bad rate 0.023 [0.004, 0.121], gate fail rate 0.093 [0.037, 0.216]; gate recall 1.0, precision 0.25, false-reject 0.0714; prompts with any bad take 1, all takes bad 1.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.023 [0.000, 0.070] | 1.00 | 0.000 [0.000, 0.000] | 0.093 | 0.0233 |

## rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]

43 prompts x [6] takes; take bad rate 0.163 [0.123, 0.213], gate fail rate 0.306 [0.253, 0.365]; gate recall 1.0, precision 0.5316, false-reject 0.1713; prompts with any bad take 23, all takes bad 0.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.163 [0.105, 0.225] | 1.00 | 0.000 [-0.000, 0.000] | 0.306 | 0.1628 |
| retry R=1 | 0.062 [0.028, 0.107] | 1.31 | 0.311 [0.224, 0.408] | 0.152 | 0.0265 |
| retry R=2 | 0.035 [0.007, 0.071] | 1.46 | 0.465 [0.308, 0.648] | 0.097 | 0.0043 |
| retry R=3 | 0.022 [0.000, 0.048] | 1.55 | 0.563 [0.351, 0.823] | 0.071 | 0.0007 |
| best-of-3 | 0.035 [0.007, 0.071] | 3 | 2.000 | - | - |

## rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]

43 prompts x [6] takes; take bad rate 0.159 [0.119, 0.208], gate fail rate 0.279 [0.228, 0.337]; gate recall 1.0, precision 0.5694, false-reject 0.1429; prompts with any bad take 25, all takes bad 0.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.159 [0.105, 0.217] | 1.00 | 0.000 [-0.000, 0.000] | 0.279 | 0.1589 |
| retry R=1 | 0.065 [0.029, 0.105] | 1.28 | 0.280 [0.207, 0.360] | 0.115 | 0.0253 |
| retry R=2 | 0.034 [0.009, 0.065] | 1.39 | 0.396 [0.271, 0.542] | 0.057 | 0.0040 |
| retry R=3 | 0.019 [0.003, 0.040] | 1.45 | 0.454 [0.294, 0.645] | 0.029 | 0.0006 |
| best-of-3 | 0.034 [0.009, 0.065] | 3 | 2.000 | - | - |

## rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]

43 prompts x [6] takes; take bad rate 0.147 [0.109, 0.196], gate fail rate 0.279 [0.228, 0.337]; gate recall 1.0, precision 0.5278, false-reject 0.1545; prompts with any bad take 20, all takes bad 1.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.147 [0.085, 0.221] | 1.00 | 0.000 [-0.000, 0.000] | 0.279 | 0.1473 |
| retry R=1 | 0.074 [0.025, 0.141] | 1.28 | 0.282 [0.196, 0.377] | 0.141 | 0.0217 |
| retry R=2 | 0.046 [0.007, 0.109] | 1.42 | 0.424 [0.271, 0.605] | 0.095 | 0.0032 |
| retry R=3 | 0.034 [0.002, 0.093] | 1.52 | 0.519 [0.310, 0.781] | 0.073 | 0.0005 |
| best-of-3 | 0.046 [0.007, 0.109] | 3 | 2.000 | - | - |

## rp1.20_trump_prompts_c16_n43_nonstream_inline [trump]

43 prompts x [1] takes; take bad rate 0.000 [0.000, 0.082], gate fail rate 0.093 [0.037, 0.216]; gate recall None, precision 0.0, false-reject 0.093; prompts with any bad take 0, all takes bad 0.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.000 [0.000, 0.000] | 1.00 | 0.000 [0.000, 0.000] | 0.093 | 0.0000 |

## Paired by prompt vs `rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]`

| setting | R | shared prompts | bad (baseline) | bad (setting) | difference [95% CI] |
|---|---|---|---|---|---|
| rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 0 | 43 | 0.155 | 0.163 | 0.008 [-0.054, 0.066] |
| rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 1 | 43 | 0.088 | 0.062 | -0.026 [-0.091, 0.026] |
| rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 2 | 43 | 0.072 | 0.035 | -0.037 [-0.108, 0.020] |
| rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 3 | 43 | 0.067 | 0.022 | -0.045 [-0.118, 0.012] |
| rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 0 | 43 | 0.155 | 0.159 | 0.004 [-0.035, 0.043] |
| rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 1 | 43 | 0.088 | 0.065 | -0.023 [-0.070, 0.017] |
| rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 2 | 43 | 0.072 | 0.034 | -0.038 [-0.100, 0.014] |
| rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 3 | 43 | 0.067 | 0.019 | -0.048 [-0.121, 0.012] |
| rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 0 | 43 | 0.155 | 0.147 | -0.008 [-0.074, 0.054] |
| rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 1 | 43 | 0.088 | 0.074 | -0.014 [-0.091, 0.053] |
| rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 2 | 43 | 0.072 | 0.046 | -0.026 [-0.107, 0.050] |
| rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 3 | 43 | 0.067 | 0.034 | -0.033 [-0.122, 0.048] |

