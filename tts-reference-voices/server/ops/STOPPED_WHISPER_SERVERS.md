# Whisper vLLM servers stopped to free the GPUs for Qwen3-TTS

Stopped 2026-09-24 by Claude Code at the user's request ("kill the whisper ones"). Both were started by user `vector`,
each held 75% of one RTX 3090 (~18.5 GB), and they had served 271 (:8000, 6 days) and 130 (:8012, 4 days) requests.
Environment variables were not captured, so check each service's `.env` / run script before restarting.

## :8000 (GPU 0, pid 2275321, EngineCore 2275458), upstream of whisper_proxy_server on :8003

```bash
cd /home/serveradmin/services/punjabi_STT_latest/punjabi-stt
nohup vllm_venv/bin/python3 -m vllm.entrypoints.openai.api_server \
  --model /home/serveradmin/services/punjabi_STT_latest/punjabi-stt/scripts/models/punjabi-test-ckpt-meer/ \
  --served-model-name whisper --dtype half --max-model-len 448 --max-num-seqs 80 --max-num-batched-tokens 16384 \
  --gpu-memory-utilization 0.75 --compilation-config '{"compile_mm_encoder": true}' --host 0.0.0.0 --port 8000 &
```

## :8012 (GPU 1, pid 3258275, EngineCore 3258388)

```bash
cd /home/serveradmin/services/punjabi_STT_latest/punjabi-stt-gpu-110-setup-copy
nohup vllm_venv/bin/python3 -m vllm.entrypoints.openai.api_server \
  --model /home/serveradmin/services/punjabi_STT_latest/punjabi-stt-gpu-110-setup-copy/scripts/models/Punjabi-STT/ \
  --served-model-name whisper --dtype half --max-model-len 448 --max-num-seqs 80 --max-num-batched-tokens 16384 \
  --gpu-memory-utilization 0.75 --compilation-config '{"compile_mm_encoder": true}' --host 0.0.0.0 --port 8012 &
```

To bring them back next to the TTS service, pin each to a GPU with `CUDA_VISIBLE_DEVICES` and lower
`--gpu-memory-utilization` (for example 0.25 is ~6 GB). vLLM's utilization is a fraction of the *whole* card, so it
must leave room for whatever else is on that GPU.
