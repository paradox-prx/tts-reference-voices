"""Higgs TTS 3 (bosonai/higgs-tts-3-4b) <-> GGUF: tensor naming, quantisation policy, reader and a vLLM loader.

Kept free of vLLM imports so the converter runs without vLLM; `higgs_gguf.vllm_loader` is the only vLLM-facing module.
"""
