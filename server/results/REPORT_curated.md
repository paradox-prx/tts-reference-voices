## P2 matrix (+ P2_high_c)

**trump** (non-streaming, engine direct, gateway cap)

| size | c | n | errors | audio s/req | latency p50/p90/p99 s | x realtime (p90 wall) | x realtime (wall) | req/s | RTF p50 | GPU MiB |
|---|---|---|---|---|---|---|---|---|---|---|
| short | 1 | 8 | 0 | 3.6 | 0.79 / 1.00 / 1.01 | 5.0 | 5.0 | 1.39 | 0.20 | 19144 |
| short | 2 | 8 | 0 | 2.7 | 0.63 / 1.14 / 1.16 | 8.1 | 8.1 | 2.97 | 0.25 | 19147 |
| short | 4 | 8 | 0 | 3.0 | 0.89 / 1.21 / 1.39 | 10.6 | 10.6 | 3.55 | 0.35 | 19167 |
| short | 8 | 16 | 0 | 3.0 | 1.36 / 2.31 / 2.86 | 12.6 | 13.4 | 4.45 | 0.53 | 19195 |
| short | 16 | 32 | 0 | 2.9 | 2.40 / 3.99 / 4.49 | 14.8 | 16.1 | 5.57 | 0.91 | 19235 |
| short | 32 | 64 | 0 | 3.0 | 3.64 / 5.97 / 6.85 | 18.4 | 20.9 | 7.01 | 1.40 | 19463 |
| short | 48 | 96 | 0 | 3.0 | 5.73 / 9.42 / 11.43 | 18.9 | 20.9 | 7.06 | 2.12 | 19769 |
| short | 64 | 128 | 0 | 3.0 | 6.66 / 11.43 / 14.19 | 21.3 | 23.1 | 7.66 | 2.60 | 19849 |
| medium | 1 | 8 | 0 | 7.0 | 1.20 / 1.66 / 1.84 | 5.3 | 5.3 | 0.76 | 0.19 | 19810 |
| medium | 2 | 8 | 0 | 6.3 | 1.33 / 1.58 / 1.68 | 9.4 | 9.4 | 1.50 | 0.21 | 19802 |
| medium | 4 | 8 | 0 | 6.5 | 1.71 / 1.93 / 3.06 | 12.3 | 12.3 | 1.90 | 0.29 | 19802 |
| medium | 8 | 16 | 0 | 6.2 | 2.54 / 3.84 / 3.98 | 16.2 | 17.0 | 2.72 | 0.44 | 19810 |
| medium | 16 | 32 | 0 | 7.0 | 4.31 / 5.42 / 7.12 | 21.7 | 23.5 | 3.37 | 0.64 | 19818 |
| medium | 32 | 64 | 0 | 6.8 | 6.43 / 8.49 / 11.86 | 26.9 | 28.3 | 4.13 | 1.01 | 19811 |
| medium | 48 | 96 | 0 | 6.4 | 9.13 / 13.25 / 15.15 | 26.2 | 28.2 | 4.40 | 1.59 | 19849 |
| medium | 64 | 128 | 0 | 6.8 | 12.26 / 16.46 / 20.75 | 29.1 | 31.8 | 4.70 | 1.85 | 19883 |
| long | 1 | 4 | 0 | 15.3 | 3.03 / 3.05 / 3.05 | 5.5 | 5.5 | 0.36 | 0.18 | 19954 |
| long | 2 | 4 | 0 | 15.8 | 3.03 / 3.47 / 3.47 | 9.9 | 9.9 | 0.63 | 0.20 | 19942 |
| long | 4 | 4 | 0 | 15.7 | 4.23 / 4.26 / 4.26 | 14.7 | 14.7 | 0.94 | 0.26 | 19939 |
| long | 8 | 8 | 0 | 15.4 | 6.01 / 6.39 / 6.43 | 19.1 | 19.1 | 1.24 | 0.39 | 19941 |
| long | 16 | 16 | 0 | 16.4 | 9.10 / 9.88 / 10.03 | 24.6 | 26.2 | 1.59 | 0.56 | 19937 |
| long | 32 | 32 | 0 | 16.4 | 14.00 / 15.04 / 15.32 | 30.8 | 34.2 | 2.09 | 0.85 | 19940 |
| xlong | 1 | 6 | 0 | 32.2 | 5.52 / 5.84 / 6.31 | 5.6 | 5.6 | 0.17 | 0.18 | 20072 |
| xlong | 2 | 6 | 0 | 31.8 | 5.93 / 5.99 / 6.59 | 10.5 | 10.5 | 0.33 | 0.19 | 20072 |
| xlong | 4 | 6 | 0 | 31.4 | 7.48 / 7.73 / 8.12 | 13.5 | 13.5 | 0.43 | 0.25 | 20072 |
| xlong | 8 | 8 | 0 | 34.4 | 11.76 / 13.56 / 15.35 | 17.9 | 17.9 | 0.52 | 0.38 | 20072 |
| xlong | 16 | 16 | 0 | 31.6 | 16.44 / 17.66 / 17.77 | 26.6 | 28.5 | 0.90 | 0.52 | 20073 |
| xlong | 32 | 32 | 0 | 32.7 | 25.41 / 26.88 / 30.50 | 33.9 | 34.3 | 1.05 | 0.80 | 20072 |
| xlong | 64 | 64 | 0 | 32.3 | 45.70 / 48.02 / 49.53 | 38.1 | 40.3 | 1.25 | 1.44 | 20397 |
| xxlong | 1 | 4 | 0 | 63.1 | 11.15 / 11.97 / 11.97 | 5.7 | 5.7 | 0.09 | 0.18 | 20070 |
| xxlong | 2 | 4 | 0 | 61.8 | 11.66 / 11.74 / 11.74 | 10.6 | 10.6 | 0.17 | 0.19 | 20070 |
| xxlong | 4 | 4 | 0 | 62.1 | 15.37 / 16.15 / 16.15 | 15.4 | 15.4 | 0.25 | 0.25 | 20070 |
| xxlong | 8 | 8 | 0 | 61.3 | 22.67 / 23.49 / 23.68 | 20.7 | 20.7 | 0.34 | 0.37 | 20070 |
| xxlong | 16 | 16 | 0 | 64.4 | 31.80 / 35.72 / 38.32 | 26.2 | 26.9 | 0.42 | 0.52 | 20070 |
| xxlong | 32 | 32 | 0 | 63.6 | 49.46 / 51.45 / 56.00 | 34.8 | 36.3 | 0.57 | 0.79 | 20072 |

**shehbaz** (non-streaming, engine direct, gateway cap)

| size | c | n | errors | audio s/req | latency p50/p90/p99 s | x realtime (p90 wall) | x realtime (wall) | req/s | RTF p50 | GPU MiB |
|---|---|---|---|---|---|---|---|---|---|---|
| short | 1 | 8 | 0 | 5.1 | 1.05 / 1.22 / 1.35 | 5.1 | 5.1 | 1.01 | 0.20 | 19675 |
| short | 2 | 8 | 0 | 3.6 | 0.94 / 1.06 / 1.18 | 8.0 | 8.0 | 2.23 | 0.24 | 19670 |
| short | 4 | 8 | 0 | 5.1 | 1.48 / 1.84 / 2.26 | 11.4 | 11.4 | 2.21 | 0.30 | 19678 |
| short | 8 | 16 | 0 | 3.9 | 1.82 / 2.69 / 3.39 | 13.7 | 14.9 | 3.79 | 0.50 | 19678 |
| short | 16 | 32 | 0 | 4.4 | 2.68 / 4.79 / 5.88 | 17.8 | 19.6 | 4.49 | 0.75 | 19670 |
| short | 32 | 64 | 0 | 4.1 | 4.36 / 7.52 / 9.27 | 21.4 | 22.5 | 5.49 | 1.26 | 19811 |
| short | 48 | 96 | 0 | 4.2 | 6.98 / 11.33 / 14.57 | 21.7 | 23.8 | 5.66 | 1.93 | 19889 |
| short | 64 | 128 | 0 | 4.0 | 7.79 / 13.11 / 16.27 | 23.0 | 24.7 | 6.11 | 2.39 | 20135 |
| medium | 1 | 8 | 0 | 10.8 | 2.27 / 2.59 / 2.67 | 5.4 | 5.4 | 0.50 | 0.18 | 19813 |
| medium | 2 | 8 | 0 | 10.3 | 2.07 / 2.44 / 2.93 | 9.1 | 9.1 | 0.88 | 0.20 | 19810 |
| medium | 4 | 8 | 0 | 9.7 | 2.54 / 3.00 / 3.37 | 13.1 | 13.0 | 1.35 | 0.28 | 19805 |
| medium | 8 | 16 | 0 | 9.6 | 3.94 / 4.92 / 5.03 | 17.2 | 17.1 | 1.78 | 0.42 | 19805 |
| medium | 16 | 32 | 0 | 9.5 | 5.63 / 7.00 / 7.40 | 22.1 | 23.9 | 2.51 | 0.61 | 19805 |
| medium | 32 | 64 | 0 | 10.4 | 9.13 / 12.20 / 13.79 | 28.3 | 30.9 | 2.97 | 0.95 | 19948 |
| medium | 48 | 96 | 0 | 10.0 | 13.48 / 18.45 / 20.91 | 28.6 | 30.4 | 3.03 | 1.49 | 20135 |
| medium | 64 | 128 | 0 | 9.9 | 15.72 / 21.91 / 27.79 | 32.2 | 34.1 | 3.45 | 1.75 | 20399 |
| long | 1 | 4 | 0 | 22.3 | 4.25 / 4.38 / 4.38 | 5.6 | 5.6 | 0.25 | 0.18 | 19928 |
| long | 2 | 4 | 0 | 22.1 | 4.14 / 4.77 / 4.77 | 10.1 | 10.1 | 0.45 | 0.19 | 19928 |
| long | 4 | 4 | 0 | 22.6 | 5.98 / 6.08 / 6.08 | 14.8 | 14.8 | 0.66 | 0.26 | 19928 |
| long | 8 | 8 | 0 | 22.1 | 8.51 / 8.91 / 9.00 | 19.6 | 19.6 | 0.89 | 0.38 | 19928 |
| long | 16 | 16 | 0 | 22.3 | 12.28 / 12.72 / 12.85 | 26.0 | 27.7 | 1.24 | 0.54 | 19928 |
| long | 32 | 32 | 0 | 22.1 | 17.79 / 19.57 / 20.30 | 31.8 | 34.7 | 1.57 | 0.82 | 20072 |
| xlong | 1 | 6 | 0 | 32.2 | 5.89 / 6.23 / 6.26 | 5.6 | 5.6 | 0.17 | 0.18 | 20072 |
| xlong | 2 | 6 | 0 | 34.1 | 6.25 / 6.99 / 7.01 | 10.1 | 10.1 | 0.30 | 0.19 | 20072 |
| xlong | 4 | 6 | 0 | 32.3 | 7.79 / 8.92 / 9.04 | 13.6 | 13.6 | 0.42 | 0.25 | 20072 |
| xlong | 8 | 8 | 0 | 35.3 | 13.48 / 13.82 / 14.41 | 19.6 | 19.6 | 0.55 | 0.38 | 20072 |
| xlong | 16 | 16 | 1 | 31.9 | 16.61 / 18.00 / 18.30 | 26.1 | 20.6 | 0.65 | 0.53 | 20070 |
| xlong | 32 | 32 | 0 | 32.8 | 26.49 / 28.04 / 28.66 | 33.3 | 36.6 | 1.11 | 0.80 | 20070 |
| xlong | 64 | 64 | 2 | 34.2 | 47.83 / 51.88 / 55.27 | 36.3 | 34.5 | 1.01 | 1.43 | 20407 |
| xxlong | 1 | 4 | 4 | – | – / – / – | 0.0 | 0.0 | 0.00 | – | 20072 |
| xxlong | 2 | 4 | 2 | 39.8 | 7.31 / 7.76 / 7.76 | 2.2 | 2.2 | 0.05 | 0.19 | 20071 |
| xxlong | 4 | 4 | 1 | 43.6 | 10.87 / 11.23 / 11.23 | 5.4 | 5.4 | 0.12 | 0.25 | 20071 |
| xxlong | 8 | 8 | 1 | 56.0 | 15.96 / 25.05 / 25.71 | 12.1 | 12.1 | 0.22 | 0.38 | 20071 |
| xxlong | 16 | 16 | 10 | 55.5 | 27.30 / 36.28 / 42.27 | 5.5 | 5.4 | 0.10 | 0.51 | 20071 |
| xxlong | 32 | 32 | 13 | 49.6 | 33.91 / 51.23 / 57.88 | 12.1 | 12.0 | 0.24 | 0.80 | 20259 |

## P3 streaming

| voice | size | c | n | errors | TTFA p50/p90/p99 s | total p50/p90/p99 s | x realtime (p90 wall) |
|---|---|---|---|---|---|---|---|
| trump | short | 1 | 8 | 0 | 0.116 / 0.126 / 0.143 | 0.73 / 0.99 / 1.00 | 5.0 |
| trump | short | 2 | 8 | 0 | 0.169 / 0.190 / 0.191 | 0.55 / 1.08 / 1.25 | 7.8 |
| trump | short | 4 | 8 | 0 | 0.358 / 0.361 / 0.363 | 0.91 / 1.23 / 1.41 | 10.2 |
| trump | short | 8 | 16 | 0 | 0.430 / 0.659 / 0.660 | 1.45 / 2.62 / 3.25 | 12.4 |
| trump | short | 16 | 32 | 0 | 0.807 / 1.257 / 1.264 | 2.31 / 3.74 / 4.42 | 15.6 |
| trump | short | 32 | 64 | 0 | 1.768 / 2.456 / 2.466 | 3.76 / 6.41 / 7.14 | 18.5 |
| trump | xlong | 1 | 6 | 0 | 0.118 / 0.120 / 0.125 | 5.52 / 5.97 / 6.01 | 5.6 |
| trump | xlong | 2 | 6 | 0 | 0.134 / 0.196 / 0.197 | 5.96 / 6.43 / 6.58 | 10.1 |
| trump | xlong | 4 | 6 | 0 | 0.353 / 0.356 / 0.356 | 7.44 / 7.90 / 8.20 | 13.2 |
| trump | xlong | 8 | 8 | 0 | 0.654 / 0.658 / 0.659 | 11.34 / 13.40 / 15.18 | 17.5 |
| trump | xlong | 16 | 16 | 0 | 1.244 / 1.252 / 1.255 | 16.81 / 17.83 / 18.04 | 26.5 |
| trump | xlong | 32 | 32 | 0 | 2.417 / 2.435 / 2.443 | 25.63 / 27.81 / 31.04 | 33.0 |
| trump | xxlong | 1 | 4 | 0 | 0.126 / 0.132 / 0.132 | 10.92 / 11.24 / 11.24 | 5.7 |
| trump | xxlong | 8 | 8 | 0 | 0.639 / 0.642 / 0.642 | 23.26 / 23.76 / 23.76 | 21.0 |
| shehbaz | short | 1 | 8 | 0 | 0.121 / 0.123 / 0.134 | 1.06 / 1.31 / 1.54 | 5.2 |
| shehbaz | short | 2 | 8 | 0 | 0.142 / 0.195 / 0.197 | 0.92 / 1.13 / 1.14 | 8.0 |
| shehbaz | short | 4 | 8 | 0 | 0.365 / 0.371 / 0.375 | 1.56 / 2.08 / 2.54 | 11.7 |
| shehbaz | short | 8 | 16 | 0 | 0.370 / 0.695 / 0.697 | 1.91 / 2.90 / 3.24 | 14.1 |
| shehbaz | short | 16 | 32 | 0 | 0.460 / 1.298 / 1.310 | 2.61 / 4.43 / 5.75 | 17.1 |
| shehbaz | short | 32 | 64 | 0 | 1.016 / 2.531 / 2.547 | 4.43 / 7.41 / 9.02 | 21.4 |
| shehbaz | xlong | 1 | 6 | 0 | 0.122 / 0.135 / 0.137 | 5.69 / 5.99 / 6.17 | 5.6 |
| shehbaz | xlong | 2 | 6 | 1 | 0.157 / 0.216 / 0.216 | 5.91 / 6.44 / 6.44 | 6.7 |
| shehbaz | xlong | 4 | 6 | 1 | 0.354 / 0.359 / 0.359 | 8.55 / 9.01 / 9.01 | 8.3 |
| shehbaz | xlong | 8 | 8 | 0 | 0.694 / 0.701 / 0.711 | 13.10 / 14.12 / 15.04 | 19.0 |
| shehbaz | xlong | 16 | 16 | 0 | 1.247 / 1.267 / 1.275 | 17.33 / 18.46 / 18.48 | 26.1 |
| shehbaz | xlong | 32 | 32 | 2 | 2.532 / 2.563 / 2.580 | 27.20 / 29.07 / 30.48 | 32.8 |
| shehbaz | xxlong | 1 | 4 | 1 | 0.130 / 0.131 / 0.131 | 6.87 / 8.80 / 8.80 | 2.5 |
| shehbaz | xxlong | 8 | 8 | 3 | 0.682 / 0.693 / 0.693 | 14.84 / 26.46 / 26.46 | 5.2 |

## P4 voice-prompt cache

| voice | reference | stream | c | n | latency p50/p90/p99 s | TTFA p50/p90/p99 s | x realtime |
|---|---|---|---|---|---|---|---|
| trump | upload |  | 1 | 8 | 0.78 / 0.98 / 0.99 | – | 5.1 |
| trump | upload |  | 8 | 16 | 1.35 / 2.56 / 2.78 | – | 11.4 |
| trump | upload |  | 32 | 32 | 3.76 / 4.58 / 4.78 | – | 17.6 |
| shehbaz | upload |  | 1 | 8 | 0.90 / 1.17 / 1.60 | – | 5.2 |
| shehbaz | upload |  | 8 | 16 | 2.19 / 2.91 / 3.02 | – | 14.1 |
| shehbaz | upload |  | 32 | 32 | 4.20 / 5.92 / 6.25 | – | 19.2 |
| trump | inline |  | 1 | 8 | 0.72 / 1.14 / 1.21 | – | 5.0 |
| trump | inline |  | 8 | 16 | 1.17 / 2.56 / 2.67 | – | 11.7 |
| trump | inline |  | 32 | 32 | 3.89 / 4.77 / 4.80 | – | 17.3 |
| shehbaz | inline |  | 1 | 8 | 1.04 / 1.15 / 1.30 | – | 5.1 |
| shehbaz | inline |  | 8 | 16 | 2.01 / 2.90 / 3.27 | – | 14.0 |
| shehbaz | inline |  | 32 | 32 | 4.54 / 5.66 / 6.19 | – | 20.3 |
| trump | nocache |  | 1 | 8 | 0.86 / 1.00 / 1.07 | – | 4.6 |
| trump | nocache |  | 8 | 16 | 1.82 / 2.78 / 3.63 | – | 9.4 |
| trump | nocache |  | 32 | 32 | 6.19 / 7.32 / 7.61 | – | 11.5 |
| shehbaz | nocache |  | 1 | 8 | 1.15 / 1.22 / 1.48 | – | 4.8 |
| shehbaz | nocache |  | 8 | 16 | 2.47 / 3.78 / 4.04 | – | 11.4 |
| shehbaz | nocache |  | 32 | 32 | 7.35 / 9.13 / 9.75 | – | 12.8 |
| trump | inline | yes | 1 | 8 | 0.74 / 0.97 / 1.01 | 0.114 / 0.121 / 0.122 | 5.0 |
| trump | inline | yes | 8 | 16 | 1.42 / 2.46 / 2.85 | 0.500 / 0.652 / 0.654 | 11.2 |
| trump | inline | yes | 32 | 32 | 3.73 / 4.65 / 4.83 | 2.354 / 2.371 / 2.385 | 17.4 |
| shehbaz | inline | yes | 1 | 8 | 1.01 / 1.29 / 1.59 | 0.118 / 0.122 / 0.127 | 5.2 |
| shehbaz | inline | yes | 8 | 16 | 2.10 / 3.12 / 3.54 | 0.319 / 0.685 / 0.689 | 13.5 |
| shehbaz | inline | yes | 32 | 32 | 4.88 / 5.71 / 6.37 | 2.485 / 2.516 / 2.527 | 19.4 |
| trump | nocache | yes | 1 | 8 | 0.79 / 1.02 / 1.07 | 0.274 / 0.290 / 0.293 | 4.5 |
| trump | nocache | yes | 8 | 16 | 1.78 / 2.78 / 3.51 | 1.448 / 1.472 / 1.642 | 9.2 |
| trump | nocache | yes | 32 | 32 | 6.24 / 7.46 / 7.76 | 6.174 / 6.196 / 6.233 | 11.2 |
| shehbaz | nocache | yes | 1 | 8 | 1.04 / 1.25 / 1.65 | 0.313 / 0.319 / 0.340 | 4.8 |
| shehbaz | nocache | yes | 8 | 16 | 2.64 / 3.73 / 3.87 | 0.660 / 1.760 / 1.957 | 11.2 |
| shehbaz | nocache | yes | 32 | 32 | 7.43 / 9.07 / 9.64 | 7.339 / 7.364 / 7.410 | 12.9 |

## P9 qwen-tts baseline vs vLLM-Omni (P2)

| voice | size | c | RTF p50 qwen-tts | RTF p50 vLLM-Omni | latency qwen-tts p50/p90/p99 | latency vLLM-Omni p50/p90/p99 | x realtime qwen-tts | x realtime vLLM-Omni | errors qwen-tts | errors vLLM-Omni |
|---|---|---|---|---|---|---|---|---|---|---|
| trump | short | 1 | 0.64 | 0.20 | 2.27 / 3.35 / 3.37 | 0.79 / 1.00 / 1.01 | 1.6 | 5.0 | 0/8 | 0/8 |
| trump | short | 2 | 0.94 | 0.25 | 3.20 / 3.56 / 3.56 | 0.63 / 1.14 / 1.16 | 2.2 | 8.1 | 0/8 | 0/8 |
| trump | short | 4 | 1.01 | 0.35 | 4.23 / 4.23 / 4.23 | 0.89 / 1.21 / 1.39 | 3.9 | 10.6 | 0/8 | 0/8 |
| trump | short | 8 | 2.06 | 0.53 | 4.47 / 7.63 / 7.63 | 1.36 / 2.31 / 2.86 | 3.7 | 12.6 | 0/16 | 0/16 |
| trump | short | 16 | 2.58 | 0.91 | 8.12 / 8.13 / 8.13 | 2.40 / 3.99 / 4.49 | 5.0 | 14.8 | 0/32 | 0/32 |
| trump | xlong | 1 | 0.58 | 0.18 | 19.64 / 20.46 / 20.46 | 5.52 / 5.84 / 6.31 | 1.7 | 5.6 | 0/4 | 0/6 |
| trump | xlong | 2 | 0.64 | 0.19 | 21.00 / 21.00 / 21.00 | 5.93 / 5.99 / 6.59 | 3.2 | 10.5 | 0/4 | 0/6 |
| trump | xlong | 4 | 0.67 | 0.25 | 20.64 / 20.64 / 20.64 | 7.48 / 7.73 / 8.12 | 6.2 | 13.5 | 0/4 | 0/6 |
| trump | xlong | 8 | 0.75 | 0.38 | 22.75 / 22.76 / 22.76 | 11.76 / 13.56 / 15.35 | 11.0 | 17.9 | 0/8 | 0/8 |
| trump | xlong | 16 | 1.78 | 0.52 | 56.18 / 78.52 / 78.53 | 16.44 / 17.66 / 17.77 | 6.3 | 26.6 | 0/16 | 0/16 |
| trump | xxlong | 1 | 0.58 | 0.18 | 35.26 / 40.96 / 40.96 | 11.15 / 11.97 / 11.97 | 1.7 | 5.7 | 0/2 | 0/4 |
| trump | xxlong | 2 | – | 0.19 | – | 11.66 / 11.74 / 11.74 | – | 10.6 | – | 0/4 |
| trump | xxlong | 4 | – | 0.25 | – | 15.37 / 16.15 / 16.15 | – | 15.4 | – | 0/4 |
| trump | xxlong | 8 | 0.71 | 0.37 | 42.90 / 42.90 / 42.90 | 22.67 / 23.49 / 23.68 | 11.6 | 20.7 | 0/8 | 0/8 |
| trump | xxlong | 16 | – | 0.52 | – | 31.80 / 35.72 / 38.32 | – | 26.2 | – | 0/16 |
| shehbaz | short | 1 | 0.62 | 0.20 | 3.14 / 3.52 / 4.52 | 1.05 / 1.22 / 1.35 | 1.6 | 5.1 | 0/8 | 0/8 |
| shehbaz | short | 2 | 0.72 | 0.24 | 2.81 / 3.42 / 3.42 | 0.94 / 1.06 / 1.18 | 2.7 | 8.0 | 0/8 | 0/8 |
| shehbaz | short | 4 | 0.88 | 0.30 | 5.67 / 5.67 / 5.67 | 1.48 / 1.84 / 2.26 | 4.3 | 11.4 | 0/8 | 0/8 |
| shehbaz | short | 8 | 1.36 | 0.50 | 4.92 / 6.50 / 6.50 | 1.82 / 2.69 / 3.39 | 5.3 | 13.7 | 0/16 | 0/16 |
| shehbaz | short | 16 | 2.83 | 0.75 | 11.09 / 13.47 / 13.52 | 2.68 / 4.79 / 5.88 | 5.2 | 17.8 | 0/32 | 0/32 |
| shehbaz | xlong | 1 | 0.59 | 0.18 | 19.13 / 19.55 / 19.55 | 5.89 / 6.23 / 6.26 | 1.7 | 5.6 | 0/4 | 0/6 |
| shehbaz | xlong | 2 | 0.66 | 0.19 | 21.69 / 51.48 / 51.48 | 6.25 / 6.99 / 7.01 | 1.4 | 10.1 | 1/4 | 0/6 |
| shehbaz | xlong | 4 | 0.62 | 0.25 | 20.52 / 20.52 / 20.52 | 7.79 / 8.92 / 9.04 | 6.4 | 13.6 | 0/4 | 0/6 |
| shehbaz | xlong | 8 | 0.83 | 0.38 | 26.25 / 26.25 / 26.26 | 13.48 / 13.82 / 14.41 | 9.9 | 19.6 | 0/8 | 0/8 |
| shehbaz | xlong | 16 | 1.40 | 0.53 | 40.29 / 62.26 / 62.27 | 16.61 / 18.00 / 18.30 | 7.2 | 26.1 | 0/16 | 1/16 |
| shehbaz | xxlong | 1 | 0.58 | – | 28.55 / 94.92 / 94.92 | – / – / – | 1.7 | 0.0 | 0/2 | 4/4 |
| shehbaz | xxlong | 2 | – | 0.19 | – | 7.31 / 7.76 / 7.76 | – | 2.2 | – | 2/4 |
| shehbaz | xxlong | 4 | – | 0.25 | – | 10.87 / 11.23 / 11.23 | – | 5.4 | – | 1/4 |
| shehbaz | xxlong | 8 | 1.15 | 0.38 | 152.81 / 152.82 / 152.83 | 15.96 / 25.05 / 25.71 | 3.2 | 12.1 | 0/8 | 1/8 |
| shehbaz | xxlong | 16 | – | 0.51 | – | 27.30 / 36.28 / 42.27 | – | 5.5 | – | 10/16 |

## P6 Auralis pools

| run | c | n | errors | too short/too long | pace ratio p50 | latency p50/p90/p99 s | x realtime |
|---|---|---|---|---|---|---|---|
| n20c20_shehbaz_short_c20_n20_nonstream_inline | 20 | 20 | 0 | 0/0 | 1.02 | 3.19 / 3.43 / 3.47 | 17.1 |
| n20c20_shehbaz_medium_c20_n20_nonstream_inline | 20 | 20 | 0 | 0/0 | 0.99 | 5.13 / 5.28 / 5.35 | 19.5 |
| n20c20_shehbaz_long_c20_n20_nonstream_inline | 20 | 20 | 0 | 0/0 | 0.94 | 11.21 / 11.78 / 12.31 | 24.3 |
| sweep_shehbaz_short_c1_n8_nonstream_inline | 1 | 8 | 0 | 0/0 | 1.09 | 0.69 / 0.78 / 0.80 | 4.9 |
| sweep_shehbaz_short_c4_n8_nonstream_inline | 4 | 8 | 0 | 0/0 | 0.95 | 1.09 / 1.17 / 1.46 | 11.1 |
| sweep_shehbaz_short_c8_n8_nonstream_inline | 8 | 8 | 0 | 0/0 | 0.98 | 1.65 / 1.76 / 1.82 | 14.2 |
| sweep_shehbaz_short_c16_n16_nonstream_inline | 16 | 16 | 0 | 0/0 | 0.95 | 2.55 / 2.84 / 2.87 | 17.4 |
| sweep_shehbaz_short_c32_n32_nonstream_inline | 32 | 32 | 0 | 0/0 | 0.99 | 4.28 / 4.68 / 4.77 | 20.4 |
| sweep_shehbaz_medium_c1_n8_nonstream_inline | 1 | 8 | 0 | 0/0 | 1.01 | 0.80 / 1.34 / 1.50 | 5.2 |
| sweep_shehbaz_medium_c4_n8_nonstream_inline | 4 | 8 | 0 | 0/0 | 1.03 | 1.97 / 2.24 / 2.25 | 13.8 |
| sweep_shehbaz_medium_c8_n8_nonstream_inline | 8 | 8 | 0 | 0/0 | 1.01 | 3.02 / 3.11 / 3.25 | 17.1 |
| sweep_shehbaz_medium_c16_n16_nonstream_inline | 16 | 16 | 0 | 0/0 | 1.06 | 4.45 / 4.83 / 5.04 | 21.7 |
| sweep_shehbaz_medium_c32_n32_nonstream_inline | 32 | 32 | 0 | 0/0 | 1.04 | 7.14 / 7.80 / 7.94 | 26.8 |
| sweep_shehbaz_long_c1_n8_nonstream_inline | 1 | 8 | 0 | 0/0 | 0.90 | 2.95 / 3.36 / 3.61 | 5.5 |
| sweep_shehbaz_long_c4_n8_nonstream_inline | 4 | 8 | 0 | 0/0 | 1.02 | 4.35 / 4.65 / 4.76 | 14.4 |
| sweep_shehbaz_long_c8_n8_nonstream_inline | 8 | 8 | 0 | 0/0 | 0.94 | 6.57 / 7.15 / 7.58 | 18.1 |
| sweep_shehbaz_long_c16_n16_nonstream_inline | 16 | 16 | 0 | 0/0 | 0.92 | 8.75 / 9.38 / 9.77 | 24.6 |
| sweep_shehbaz_long_c32_n32_nonstream_inline | 32 | 32 | 0 | 0/0 | 0.95 | 13.97 / 14.84 / 15.24 | 30.9 |
| gw_n20c20_shehbaz_short_c20_n20_nonstream_server | 20 | 20 | 0 | 0/0 | 1.02 | 3.19 / 3.39 / 3.44 | 17.1 |
| gw_n20c20_shehbaz_medium_c20_n20_nonstream_server | 20 | 20 | 0 | 0/0 | 0.95 | 4.87 / 5.14 / 5.20 | 19.9 |
| gw_n20c20_shehbaz_long_c20_n20_nonstream_server | 20 | 20 | 0 | 0/0 | 0.93 | 11.16 / 11.59 / 12.31 | 24.3 |

## P7 gateway

| run | c | n | errors | too short/too long | pace ratio p50 | latency p50/p90/p99 s | x realtime | retries_total |
|---|---|---|---|---|---|---|---|---|
| direct_trump_short_c1_n8_nonstream_inline | 1 | 8 | 0 | 0/1 | 1.06 | 0.71 / 1.00 / 1.14 | 5.0 | 0 |
| direct_trump_short_c16_n32_nonstream_inline | 16 | 32 | 0 | 0/1 | 1.11 | 2.22 / 3.71 / 4.33 | 15.2 | 0 |
| direct_shehbaz_short_c1_n8_nonstream_inline | 1 | 8 | 0 | 0/0 | 1.17 | 1.00 / 1.04 / 1.20 | 5.2 | 0 |
| direct_shehbaz_short_c16_n32_nonstream_inline | 16 | 32 | 0 | 0/0 | 1.05 | 2.70 / 5.10 / 6.11 | 19.2 | 0 |
| gw_r0_trump_short_c1_n8_nonstream_server | 1 | 8 | 0 | 0/1 | 0.95 | 0.71 / 1.00 / 1.05 | 5.0 | 0 |
| gw_r0_trump_short_c16_n32_nonstream_server | 16 | 32 | 0 | 0/0 | 1.12 | 2.15 / 3.58 / 4.40 | 15.9 | 0 |
| gw_r0_shehbaz_short_c1_n8_nonstream_server | 1 | 8 | 0 | 0/0 | 0.98 | 1.03 / 1.12 / 1.30 | 5.1 | 0 |
| gw_r0_shehbaz_short_c16_n32_nonstream_server | 16 | 32 | 0 | 0/0 | 1.04 | 2.73 / 4.36 / 5.56 | 18.9 | 0 |
| direct_shehbaz_long_c32_n64_nonstream_inline | 32 | 64 | 0 | 0/0 | 0.99 | 18.51 / 20.83 / 21.74 | 32.9 | 0 |
| gw_r1_shehbaz_long_c32_n64_nonstream_server | 32 | 64 | 0 | 0/0 | 0.97 | 18.34 / 21.13 / 24.59 | 32.8 | 1 |

## X4 length cap

| run | c | n | errors | too short/too long | pace ratio p50 | latency p50/p90/p99 s | x realtime | engine_builtin_retries |
|---|---|---|---|---|---|---|---|---|
| cap_on_shehbaz_prompts_c16_n43_nonstream_inline | 16 | 43 | 1 | 0/0 | 0.94 | 17.31 / 19.48 / 28.02 | 24.5 | 5 |
| cap_off_shehbaz_prompts_c16_n43_nonstream_inline | 16 | 43 | 0 | 0/0 | 0.96 | 17.81 / 132.53 / 147.22 | 9.0 | 5 |

## X6 non_streaming_mode, long texts

| run | c | n | errors | too short/too long | pace ratio p50 | latency p50/p90/p99 s | x realtime |
|---|---|---|---|---|---|---|---|
| nsm_false_shehbaz_xxlong_c16_n43_nonstream_inline | 16 | 43 | 16 | 14/0 | 0.59 | 21.73 / 40.27 / 53.66 | 10.1 |
| nsm_true_shehbaz_xxlong_c16_n43_nonstream_inline | 16 | 43 | 0 | 0/0 | 0.97 | 36.12 / 41.50 / 61.08 | 25.0 |
| nsm_true_trump_xxlong_c16_n43_nonstream_inline | 16 | 43 | 0 | 0/0 | 1.00 | 33.69 / 36.35 / 49.55 | 25.4 |

## X7 sentence splitting

| run | c | n | errors | too short/too long | pace ratio p50 | latency p50/p90/p99 s | x realtime |
|---|---|---|---|---|---|---|---|
| split_off_shehbaz_xxlong_c8_n43_nonstream_server | 8 | 43 | 18 | 16/0 | 0.57 | 15.66 / 23.99 / 34.39 | 6.7 |
| split_off_trump_xxlong_c8_n43_nonstream_server | 8 | 43 | 0 | 0/0 | 0.97 | 23.00 / 25.59 / 33.55 | 20.0 |

| run | c | n | errors | too short/too long | pace ratio p50 | latency p50/p90/p99 s | x realtime |
|---|---|---|---|---|---|---|---|
| split_60_shehbaz_xxlong_c8_n43_nonstream_server | 8 | 43 | 0 | 0/0 | 1.01 | 16.83 / 18.81 / 21.11 | 31.7 |
| split_60_trump_xxlong_c8_n43_nonstream_server | 8 | 43 | 0 | 0/0 | 1.01 | 14.26 / 16.55 / 52.29 | 30.5 |

## P8 quality phases (load view)

| run | c | n | errors | too short/too long | pace ratio p50 | latency p50/p90/p99 s | x realtime | retries_total | qc_pass | qc_fail | qc_error |
|---|---|---|---|---|---|---|---|---|---|---|---|
| raw_trump_prompts_c16_n43_nonstream_server | 16 | 43 | 0 | 0/0 | 1.01 | 16.50 / 19.29 / 26.45 | 26.0 | 0 | 0 | 0 | 0 |
| raw_shehbaz_prompts_c16_n43_nonstream_server | 16 | 43 | 2 | 0/0 | 0.95 | 17.68 / 20.13 / 31.50 | 24.4 | 0 | 0 | 0 | 0 |

| run | c | n | errors | too short/too long | pace ratio p50 | latency p50/p90/p99 s | x realtime | retries_total | qc_pass | qc_fail | qc_error |
|---|---|---|---|---|---|---|---|---|---|---|---|
| guard_trump_prompts_c16_n43_nonstream_server | 16 | 43 | 0 | 0/0 | 0.99 | 41.88 / 50.06 / 56.21 | 10.3 | 1 | 26 | 0 | 17 |
| guard_shehbaz_prompts_c16_n43_nonstream_server | 16 | 43 | 0 | 0/0 | 0.96 | 49.52 / 53.51 / 112.86 | 8.9 | 3 | 0 | 0 | 43 |

| run | c | n | errors | too short/too long | pace ratio p50 | latency p50/p90/p99 s | x realtime | retries_total | qc_pass | qc_fail | qc_error |
|---|---|---|---|---|---|---|---|---|---|---|---|
| guardfast_trump_prompts_c16_n43_nonstream_server | 16 | 43 | 0 | 0/0 | 1.00 | 36.20 / 54.20 / 63.46 | 12.0 | 1 | 43 | 0 | 0 |
| guardfast_shehbaz_prompts_c16_n43_nonstream_server | 16 | 43 | 0 | 0/0 | 0.96 | 125.74 / 188.25 / 269.40 | 3.7 | 50 | 20 | 20 | 3 |

## Quality (eval/score_run.py)

| phase | run | takes | WER | CER-nospace | SIM-large | SIM-base | gate fail | bad |
|---|---|---|---|---|---|---|---|---|
| P2_high_c | shehbaz_medium_c48_n96_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_high_c | shehbaz_medium_c64_n128_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_high_c | shehbaz_short_c48_n96_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_high_c | shehbaz_short_c64_n128_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_high_c | shehbaz_xlong_c64_n64_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_high_c | trump_medium_c48_n96_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_high_c | trump_medium_c64_n128_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_high_c | trump_short_c48_n96_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_high_c | trump_short_c64_n128_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_high_c | trump_xlong_c64_n64_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_long_c16_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_long_c1_n4_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_long_c2_n4_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_long_c32_n32_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_long_c4_n4_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_long_c8_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_medium_c16_n32_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_medium_c1_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_medium_c2_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_medium_c32_n64_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_medium_c4_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_medium_c8_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_short_c16_n32_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_short_c1_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_short_c2_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_short_c32_n64_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_short_c4_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_short_c8_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_xlong_c16_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_xlong_c1_n6_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_xlong_c2_n6_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_xlong_c32_n32_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_xlong_c4_n6_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_xlong_c8_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_xxlong_c16_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_xxlong_c2_n4_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_xxlong_c32_n32_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_xxlong_c4_n4_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | shehbaz_xxlong_c8_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P2_matrix | trump_long_c16_n16_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_long_c1_n4_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_long_c2_n4_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_long_c32_n32_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_long_c4_n4_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_long_c8_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_medium_c16_n32_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_medium_c1_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_medium_c2_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_medium_c32_n64_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_medium_c4_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_medium_c8_n16_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_short_c16_n32_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_short_c1_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_short_c2_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_short_c32_n64_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_short_c4_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_short_c8_n16_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_xlong_c16_n16_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_xlong_c1_n6_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_xlong_c2_n6_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_xlong_c32_n32_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_xlong_c4_n6_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_xlong_c8_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_xxlong_c16_n16_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_xxlong_c1_n4_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_xxlong_c2_n4_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_xxlong_c32_n32_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_xxlong_c4_n4_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P2_matrix | trump_xxlong_c8_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_short_c16_n32_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_short_c1_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_short_c2_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_short_c32_n64_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_short_c4_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_short_c8_n16_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_xlong_c16_n16_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_xlong_c1_n6_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_xlong_c2_n6_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_xlong_c32_n32_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_xlong_c4_n6_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_xlong_c8_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_xxlong_c1_n4_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | shehbaz_xxlong_c8_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P3_stream | trump_short_c16_n32_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_short_c1_n8_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_short_c2_n8_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_short_c32_n64_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_short_c4_n8_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_short_c8_n16_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_xlong_c16_n16_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_xlong_c1_n6_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_xlong_c2_n6_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_xlong_c32_n32_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_xlong_c4_n6_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_xlong_c8_n8_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_xxlong_c1_n4_stream_inline [trump] | None | – | – | – | – | – | – |
| P3_stream | trump_xxlong_c8_n8_stream_inline [trump] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c1_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c1_n8_nonstream_nocache [shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c1_n8_nonstream_upload [bench-shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c1_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c1_n8_stream_nocache [shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c32_n32_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c32_n32_nonstream_nocache [shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c32_n32_nonstream_upload [bench-shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c32_n32_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c32_n32_stream_nocache [shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c8_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c8_n16_nonstream_nocache [shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c8_n16_nonstream_upload [bench-shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c8_n16_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | shehbaz_short_c8_n16_stream_nocache [shehbaz] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c1_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c1_n8_nonstream_nocache [trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c1_n8_nonstream_upload [bench-trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c1_n8_stream_inline [trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c1_n8_stream_nocache [trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c32_n32_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c32_n32_nonstream_nocache [trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c32_n32_nonstream_upload [bench-trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c32_n32_stream_inline [trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c32_n32_stream_nocache [trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c8_n16_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c8_n16_nonstream_nocache [trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c8_n16_nonstream_upload [bench-trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c8_n16_stream_inline [trump] | None | – | – | – | – | – | – |
| P4_voice_cache | trump_short_c8_n16_stream_nocache [trump] | None | – | – | – | – | – | – |
| P5_urdu_nsm | nsm_rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P5_urdu_rp105 | rp1.05_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P5_urdu_rp105 | rp1.05_trump_prompts_c16_n43_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P5_urdu_rp110 | rp1.10_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P5_urdu_rp115 | rp1.15_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P5_urdu_rp120 | rp1.20_shehbaz_prompts_c16_n43_k6_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P5_urdu_rp120 | rp1.20_trump_prompts_c16_n43_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P6_auralis | gw_n20c20_shehbaz_long_c20_n20_nonstream_server [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | gw_n20c20_shehbaz_medium_c20_n20_nonstream_server [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | gw_n20c20_shehbaz_short_c20_n20_nonstream_server [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | n20c20_shehbaz_long_c20_n20_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | n20c20_shehbaz_medium_c20_n20_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | n20c20_shehbaz_short_c20_n20_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_long_c16_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_long_c1_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_long_c32_n32_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_long_c4_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_long_c8_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_medium_c16_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_medium_c1_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_medium_c32_n32_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_medium_c4_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_medium_c8_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_short_c16_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_short_c1_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_short_c32_n32_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_short_c4_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P6_auralis | sweep_shehbaz_short_c8_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P7_gateway | direct_shehbaz_long_c32_n64_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P7_gateway | direct_shehbaz_short_c16_n32_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P7_gateway | direct_shehbaz_short_c1_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P7_gateway | direct_trump_short_c16_n32_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P7_gateway | direct_trump_short_c1_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P7_gateway | gw_r0_shehbaz_short_c16_n32_nonstream_server [shehbaz] | None | – | – | – | – | – | – |
| P7_gateway | gw_r0_shehbaz_short_c1_n8_nonstream_server [shehbaz] | None | – | – | – | – | – | – |
| P7_gateway | gw_r0_trump_short_c16_n32_nonstream_server [trump] | None | – | – | – | – | – | – |
| P7_gateway | gw_r0_trump_short_c1_n8_nonstream_server [trump] | None | – | – | – | – | – | – |
| P7_gateway | gw_r1_shehbaz_long_c32_n64_nonstream_server [shehbaz] | None | – | – | – | – | – | – |
| P8_quality_guard | guard_shehbaz_prompts_c16_n43_nonstream_server [shehbaz] | None | – | – | – | – | – | – |
| P8_quality_guard | guard_trump_prompts_c16_n43_nonstream_server [trump] | None | – | – | – | – | – | – |
| P8_quality_guard_fast | guardfast_shehbaz_prompts_c16_n43_nonstream_server [shehbaz] | None | – | – | – | – | – | – |
| P8_quality_guard_fast | guardfast_trump_prompts_c16_n43_nonstream_server [trump] | None | – | – | – | – | – | – |
| P8_quality_raw | raw_shehbaz_prompts_c16_n43_nonstream_server [shehbaz] | None | – | – | – | – | – | – |
| P8_quality_raw | raw_trump_prompts_c16_n43_nonstream_server [trump] | None | – | – | – | – | – | – |
| P9_baseline_b1 | shehbaz_short_c1_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b1 | shehbaz_short_c4_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b1 | shehbaz_xlong_c1_n4_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b1 | shehbaz_xlong_c4_n4_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b1 | trump_short_c1_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b1 | trump_short_c4_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b1 | trump_xlong_c1_n4_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b1 | trump_xlong_c4_n4_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b8 | shehbaz_short_c16_n32_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b8 | shehbaz_short_c1_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b8 | shehbaz_short_c2_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b8 | shehbaz_short_c4_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b8 | shehbaz_short_c8_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b8 | shehbaz_xlong_c16_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b8 | shehbaz_xlong_c1_n4_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b8 | shehbaz_xlong_c2_n4_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b8 | shehbaz_xlong_c4_n4_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b8 | shehbaz_xlong_c8_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b8 | shehbaz_xxlong_c1_n2_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b8 | shehbaz_xxlong_c8_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_b8 | trump_short_c16_n32_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b8 | trump_short_c1_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b8 | trump_short_c2_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b8 | trump_short_c4_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b8 | trump_short_c8_n16_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b8 | trump_xlong_c16_n16_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b8 | trump_xlong_c1_n4_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b8 | trump_xlong_c2_n4_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b8 | trump_xlong_c4_n4_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b8 | trump_xlong_c8_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b8 | trump_xxlong_c1_n2_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_b8 | trump_xxlong_c8_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_nocache | shehbaz_short_c1_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_nocache | shehbaz_short_c8_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_nocache | shehbaz_xlong_c1_n4_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_nocache | shehbaz_xlong_c8_n8_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| P9_baseline_nocache | trump_short_c1_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_nocache | trump_short_c8_n16_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_nocache | trump_xlong_c1_n4_nonstream_inline [trump] | None | – | – | – | – | – | – |
| P9_baseline_nocache | trump_xlong_c8_n8_nonstream_inline [trump] | None | – | – | – | – | – | – |
| X1_nsm | nsm_true_shehbaz_prompts_c16_n43_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| X2_language | lang_auto_trump_prompts_c16_n43_nonstream_inline [trump] | None | – | – | – | – | – | – |
| X3_custom_voice | avg_shehbaz_prompts_c16_n43_nonstream_server-avg [shehbaz-avg] | None | – | – | – | – | – | – |
| X3_custom_voice | prompt_shehbaz_prompts_c16_n43_nonstream_server-prompt [shehbaz-prompt] | None | – | – | – | – | – | – |
| X4_length_cap | cap_off_shehbaz_prompts_c16_n43_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| X4_length_cap | cap_on_shehbaz_prompts_c16_n43_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| X5_mixed_voices | mix_trump+shehbaz_short_c16_n32_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| X5_mixed_voices | mix_trump+shehbaz_short_c16_n32_nonstream_inline [trump] | None | – | – | – | – | – | – |
| X5_mixed_voices | mix_trump+shehbaz_xlong_c16_n16_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| X5_mixed_voices | mix_trump+shehbaz_xlong_c16_n16_nonstream_inline [trump] | None | – | – | – | – | – | – |
| X6_nsm_long_urdu | nsm_false_shehbaz_xxlong_c16_n43_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| X6_nsm_long_urdu | nsm_true_shehbaz_xxlong_c16_n43_nonstream_inline [shehbaz] | None | – | – | – | – | – | – |
| X6_nsm_long_urdu | nsm_true_trump_xxlong_c16_n43_nonstream_inline [trump] | None | – | – | – | – | – | – |
| X7_split_60 | split_60_shehbaz_xxlong_c8_n43_nonstream_server [shehbaz] | None | – | – | – | – | – | – |
| X7_split_60 | split_60_trump_xxlong_c8_n43_nonstream_server [trump] | None | – | – | – | – | – | – |
| X7_split_off | split_off_shehbaz_xxlong_c8_n43_nonstream_server [shehbaz] | None | – | – | – | – | – | – |
| X7_split_off | split_off_trump_xxlong_c8_n43_nonstream_server [trump] | None | – | – | – | – | – | – |
| X8_split_nsm | split60_nsm_shehbaz_xxlong_c8_n43_nonstream_server [shehbaz] | None | – | – | – | – | – | – |
| X9_nsm_stream | nsm_default_shehbaz_short_c1_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| X9_nsm_stream | nsm_default_shehbaz_short_c8_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| X9_nsm_stream | nsm_default_shehbaz_xlong_c1_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| X9_nsm_stream | nsm_default_shehbaz_xlong_c8_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| X9_nsm_stream | nsm_true_shehbaz_short_c1_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| X9_nsm_stream | nsm_true_shehbaz_short_c8_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| X9_nsm_stream | nsm_true_shehbaz_xlong_c1_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |
| X9_nsm_stream | nsm_true_shehbaz_xlong_c8_n8_stream_inline [shehbaz] | None | – | – | – | – | – | – |

