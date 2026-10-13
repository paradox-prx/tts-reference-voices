"""vLLM model loader `higgs_gguf`: loads a Higgs GGUF into vLLM-Omni's stock Higgs TTS 3 stages.

vLLM 0.28 has no GGUF support at all (the GGUF loader and GGUF quantisation were removed upstream), and vLLM-Omni's
Higgs stages only read safetensors. This loader reads the GGUF, dequantises each tensor to the model dtype (bf16),
renames it back to the checkpoint name and hands the stream to the model's own `load_weights`, so the model code,
the deploy YAML and the API server stay stock. Consequence: the GGUF type changes disk size and the weights' values
(quantisation error), not VRAM: on the GPU the model is bf16 either way.

Select it per stage in the deploy YAML (`load_format: higgs_gguf`) after `register()` ran in every vLLM process;
harness/sitecustomize.py does that. The GGUF is the single *.gguf in the model directory, or
`model_loader_extra_config: {gguf_file: ...}`, or $HIGGS_GGUF_FILE.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import torch
from torch import nn

from vllm.config import ModelConfig
from vllm.config.load import LoadConfig
from vllm.logger import init_logger
from vllm.model_executor.model_loader.base_loader import BaseModelLoader

from . import names
from .reader import iter_checkpoint_tensors

logger = init_logger("vllm.higgs_gguf")  # vLLM only attaches handlers to the `vllm` namespace
LOAD_FORMAT = "higgs_gguf"


class HiggsGGUFModelLoader(BaseModelLoader):
    def __init__(self, load_config: LoadConfig):
        super().__init__(load_config)
        self.extra = dict(load_config.model_loader_extra_config or {})

    def _gguf_path(self, model_config: ModelConfig) -> Path:
        explicit = self.extra.get("gguf_file") or os.environ.get("HIGGS_GGUF_FILE")
        if explicit:
            p = Path(explicit)
        else:
            src = Path(model_config.model)
            found = [src] if src.suffix == ".gguf" else sorted(src.glob("*.gguf"))
            if len(found) != 1:
                raise FileNotFoundError(f"{LOAD_FORMAT}: expected exactly one *.gguf in {src}, found {len(found)}; "
                                        "set model_loader_extra_config.gguf_file or HIGGS_GGUF_FILE")
            p = found[0]
        if not p.is_file():
            raise FileNotFoundError(f"{LOAD_FORMAT}: {p} not found")
        return p

    def download_model(self, model_config: ModelConfig) -> None:
        self._gguf_path(model_config)

    def load_weights(self, model: nn.Module, model_config: ModelConfig) -> None:
        path = self._gguf_path(model_config)
        # Stage 1 (Code2Wav) only consumes the bundled codec; skip dequantising the 4B backbone there.
        prefix = names.CODEC_PREFIX if "Code2Wav" in type(model).__name__ else None
        t0 = time.perf_counter()
        n = 0

        def stream():
            nonlocal n
            for name, tensor in iter_checkpoint_tensors(path, model_config.dtype, prefix):
                n += 1
                yield name, tensor

        loaded = model.load_weights(stream())
        logger.info("%s: %s loaded %d tensors from %s (dtype %s%s) in %.1f s", LOAD_FORMAT, type(model).__name__, n,
                    path, model_config.dtype, f", only {prefix}*" if prefix else "", time.perf_counter() - t0)
        if loaded is not None:
            missing = {k for k, _ in model.named_parameters()} - set(loaded)
            if missing:
                raise ValueError(f"{LOAD_FORMAT}: {len(missing)} parameters not initialised from {path}: "
                                 f"{sorted(missing)[:10]}")


def register() -> None:
    from vllm.model_executor.model_loader import register_model_loader

    register_model_loader(LOAD_FORMAT)(HiggsGGUFModelLoader)
