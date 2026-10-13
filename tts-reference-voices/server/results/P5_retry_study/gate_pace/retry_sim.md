# Retry-policy simulation: results/P5_retry_study/gate_pace/rp105.jsonl, results/P5_retry_study/gate_pace/rp110.jsonl, results/P5_retry_study/gate_pace/rp115.jsonl, results/P5_retry_study/gate_pace/rp120.jsonl

Cost = `audio_s`; bad = score_run's bad label; 95 % CIs bootstrap over prompts (2000 resamples). i.i.d. = f^(R+1), shown only for contrast. Takes are unseeded; settings pair by prompt.

## rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]

43 prompts x [6] takes; take bad rate 0.155 [0.116, 0.204], gate fail rate 0.031 [0.016, 0.060]; gate recall 0.2, precision 1.0, false-reject 0.0; prompts with any bad take 21, all takes bad 0.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.155 [0.097, 0.221] | 1.00 | -0.000 [-0.000, 0.000] | 0.031 | 0.1550 |
| retry R=1 | 0.136 [0.081, 0.199] | 1.03 | 0.035 [0.008, 0.074] | 0.005 | 0.0240 |
| retry R=2 | 0.135 [0.080, 0.197] | 1.04 | 0.041 [0.008, 0.092] | 0.001 | 0.0037 |
| retry R=3 | 0.135 [0.080, 0.196] | 1.04 | 0.042 [0.008, 0.095] | 0.000 | 0.0006 |
| best-of-2 | 0.102 [0.048, 0.164] | 2 | 1.000 | - | - |
| best-of-3 | 0.088 [0.035, 0.150] | 3 | 2.000 | - | - |

## rp1.05_trump_prompts_c16_n43_nonstream_inline [trump]

43 prompts x [1] takes; take bad rate 0.023 [0.004, 0.121], gate fail rate 0.000 [0.000, 0.082]; gate recall 0.0, precision None, false-reject 0.0; prompts with any bad take 1, all takes bad 1.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.023 [0.000, 0.070] | 1.00 | 0.000 [0.000, 0.000] | 0.000 | 0.0233 |

## rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]

43 prompts x [6] takes; take bad rate 0.163 [0.123, 0.213], gate fail rate 0.035 [0.018, 0.065]; gate recall 0.2143, precision 1.0, false-reject 0.0; prompts with any bad take 23, all takes bad 0.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.163 [0.105, 0.225] | 1.00 | 0.000 [-0.000, 0.000] | 0.035 | 0.1628 |
| retry R=1 | 0.135 [0.085, 0.196] | 1.03 | 0.034 [0.012, 0.058] | 0.002 | 0.0265 |
| retry R=2 | 0.133 [0.083, 0.193] | 1.04 | 0.036 [0.012, 0.061] | 0.000 | 0.0043 |
| retry R=3 | 0.133 [0.083, 0.193] | 1.04 | 0.036 [0.012, 0.061] | 0.000 | 0.0007 |
| best-of-2 | 0.093 [0.048, 0.150] | 2 | 1.000 | - | - |
| best-of-3 | 0.083 [0.033, 0.146] | 3 | 2.000 | - | - |

## rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]

43 prompts x [6] takes; take bad rate 0.159 [0.119, 0.208], gate fail rate 0.050 [0.030, 0.084]; gate recall 0.3171, precision 1.0, false-reject 0.0; prompts with any bad take 25, all takes bad 0.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.159 [0.105, 0.217] | 1.00 | 0.000 [-0.000, 0.000] | 0.050 | 0.1589 |
| retry R=1 | 0.116 [0.067, 0.172] | 1.05 | 0.050 [0.026, 0.074] | 0.002 | 0.0253 |
| retry R=2 | 0.115 [0.066, 0.171] | 1.05 | 0.051 [0.026, 0.079] | 0.000 | 0.0040 |
| retry R=3 | 0.115 [0.066, 0.171] | 1.05 | 0.051 [0.026, 0.079] | 0.000 | 0.0006 |
| best-of-2 | 0.082 [0.043, 0.127] | 2 | 1.000 | - | - |
| best-of-3 | 0.059 [0.023, 0.106] | 3 | 2.000 | - | - |

## rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]

43 prompts x [6] takes; take bad rate 0.147 [0.109, 0.196], gate fail rate 0.050 [0.030, 0.084]; gate recall 0.3421, precision 1.0, false-reject 0.0; prompts with any bad take 20, all takes bad 1.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.147 [0.085, 0.221] | 1.00 | 0.000 [-0.000, 0.000] | 0.050 | 0.1473 |
| retry R=1 | 0.111 [0.053, 0.186] | 1.05 | 0.052 [0.026, 0.082] | 0.003 | 0.0217 |
| retry R=2 | 0.108 [0.051, 0.183] | 1.05 | 0.055 [0.027, 0.089] | 0.000 | 0.0032 |
| retry R=3 | 0.108 [0.051, 0.183] | 1.05 | 0.055 [0.027, 0.089] | 0.000 | 0.0005 |
| best-of-2 | 0.096 [0.045, 0.166] | 2 | 1.000 | - | - |
| best-of-3 | 0.078 [0.028, 0.146] | 3 | 2.000 | - | - |

## rp1.20_trump_prompts_c16_n43_nonstream_inline [trump]

43 prompts x [1] takes; take bad rate 0.000 [0.000, 0.082], gate fail rate 0.000 [0.000, 0.082]; gate recall None, precision None, false-reject 0.0; prompts with any bad take 0, all takes bad 0.

| policy | final bad rate [95% CI] | mean attempts | extra compute [95% CI] | ships gate-fail | i.i.d. |
|---|---|---|---|---|---|
| retry R=0 | 0.000 [0.000, 0.000] | 1.00 | 0.000 [0.000, 0.000] | 0.000 | 0.0000 |

## Paired by prompt vs `rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz]`

| setting | R | shared prompts | bad (baseline) | bad (setting) | difference [95% CI] |
|---|---|---|---|---|---|
| rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 0 | 43 | 0.155 | 0.163 | 0.008 [-0.054, 0.066] |
| rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 1 | 43 | 0.136 | 0.135 | -0.002 [-0.060, 0.053] |
| rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 2 | 43 | 0.135 | 0.133 | -0.002 [-0.059, 0.052] |
| rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 3 | 43 | 0.135 | 0.133 | -0.002 [-0.059, 0.052] |
| rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 0 | 43 | 0.155 | 0.159 | 0.004 [-0.035, 0.043] |
| rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 1 | 43 | 0.136 | 0.116 | -0.020 [-0.058, 0.018] |
| rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 2 | 43 | 0.135 | 0.115 | -0.021 [-0.059, 0.017] |
| rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 3 | 43 | 0.135 | 0.115 | -0.020 [-0.058, 0.017] |
| rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 0 | 43 | 0.155 | 0.147 | -0.008 [-0.074, 0.054] |
| rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 1 | 43 | 0.136 | 0.111 | -0.026 [-0.091, 0.036] |
| rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 2 | 43 | 0.135 | 0.108 | -0.027 [-0.091, 0.033] |
| rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | 3 | 43 | 0.135 | 0.108 | -0.027 [-0.090, 0.034] |

