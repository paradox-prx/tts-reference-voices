"""Speaker similarity: cosine of L2-normalized speaker embeddings of 16 kHz mono audio (eval-tooling.md 18-24).

Backends (models/eval/<dir>, sha256 in models/eval/SHA256SUMS):
  base   microsoft/wavlm-base-plus-sv (transformers WavLMForXVector). The scale of the Kaggle numbers ("WavLM 0.974",
         gate "< 0.88"): same speaker >= 0.975, cross speaker 0.75-0.80 on these voices. Cheap: the sidecar default.
  large  seed-tts-eval SIM: UniSpeech WavLM-Large + ECAPA-TDNN (prj-beatrice torch-native port, local remote code).
         The papers' scale (human ground truth 0.73, Qwen3-TTS English 0.775): same speaker 0.87-0.95, cross 0.11-0.18.
         Primary metric offline.

Two fixes make the port run in this venv (torch 2.13, transformers 5.17): its WavLMAttention patch has the 4.x
signature (output_attentions), which 5.x removed, so each layer is re-patched with an adapter that merges the padding
mask into the position bias exactly like the port does; and it imports torchaudio.functional only to resample, which
never happens here (input is always 16 kHz), so a stub that raises if called stands in for torchaudio (no build for
torch 2.13 exists). Embeddings are computed one clip at a time (batch 1, no padding), as the lab calibration did.
"""
from __future__ import annotations

import importlib.machinery
import os
import sys
import threading
import time
import types
import warnings
from contextlib import contextmanager
from pathlib import Path

import numpy as np

MODEL_DIRS = {"base": "wavlm-base-plus-sv", "large": "beatrice"}
MIN_SECONDS = 0.5          # below this there is nothing to embed (the port needs >= 720 samples)
# wavlm-base-plus-sv passes a padding mask of another dtype than the attention bias; harmless, once per call
warnings.filterwarnings("ignore", message="Support for mismatched key_padding_mask and attn_mask")


@contextmanager
def _torchaudio_stub():
    """While the port's remote code is imported: a stand-in torchaudio whose resample() raises. Removed again right
    after, so transformers' own probes (find_spec) keep seeing torchaudio as not installed."""
    try:
        import torchaudio.functional  # noqa: F401
        installed = True
    except ImportError:
        installed = False
    if installed:
        yield
        return

    def resample(*_args, **_kwargs):
        raise RuntimeError("torchaudio is not installed: pass 16 kHz audio (tts_qc.audio.to_16k)")

    pkg = types.ModuleType("torchaudio")
    fn = types.ModuleType("torchaudio.functional")
    pkg.__spec__ = importlib.machinery.ModuleSpec("torchaudio", None, is_package=True)
    fn.__spec__ = importlib.machinery.ModuleSpec("torchaudio.functional", None)
    fn.resample, pkg.functional, pkg.__path__ = resample, fn, []
    added = {"torchaudio": pkg, "torchaudio.functional": fn}
    sys.modules.update(added)
    try:
        yield
    finally:
        for name, mod in added.items():
            if sys.modules.get(name) is mod:
                del sys.modules[name]


class Embedder:
    """One speaker-embedding model. Thread-safe: calls are serialized with a lock (one forward at a time)."""

    def __init__(self, backend: str, models_dir: str | Path, device: str = "cuda", device_index: int = 0) -> None:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        import torch

        if backend not in MODEL_DIRS:
            raise ValueError(f"unknown SIM backend {backend!r} (base, large)")
        self.backend = backend
        self.device = f"cuda:{device_index}" if device == "cuda" else "cpu"
        self.path = Path(models_dir) / MODEL_DIRS[backend]
        self._lock = threading.Lock()
        self._torch = torch
        t0 = time.perf_counter()
        if backend == "base":
            from transformers import Wav2Vec2FeatureExtractor, WavLMForXVector

            self.fe = Wav2Vec2FeatureExtractor.from_pretrained(self.path)
            self.model = WavLMForXVector.from_pretrained(self.path).eval().to(self.device)
        else:
            import inspect
            from types import MethodType

            from transformers import AutoModel
            from transformers.models.wavlm.modeling_wavlm import WavLMAttention

            with _torchaudio_stub():
                self.model = AutoModel.from_pretrained(self.path, trust_remote_code=True).eval().to(self.device)
            if "output_attentions" not in inspect.signature(WavLMAttention.torch_multi_head_self_attention).parameters:
                orig = WavLMAttention.torch_multi_head_self_attention

                def adapter(att, hidden_states, attention_mask, gated_position_bias):
                    if attention_mask is not None:
                        keep = attention_mask.bool()
                        b, n = keep.shape
                        pad = hidden_states.new_zeros((b, 1, 1, n)).masked_fill_(~keep[:, None, None, :], -torch.inf)
                        gated_position_bias = (gated_position_bias.view(b, att.num_heads, n, n) + pad).view(
                            b * att.num_heads, n, n)
                    return orig(att, hidden_states, None, gated_position_bias)

                for layer in self.model.wavlm.encoder.layers:
                    layer.attention.torch_multi_head_self_attention = MethodType(adapter, layer.attention)
        self.load_s = time.perf_counter() - t0

    def __call__(self, wav16: np.ndarray) -> np.ndarray:
        """float32 mono 16 kHz -> unit-norm embedding (float32 numpy)."""
        torch = self._torch
        with self._lock, torch.inference_mode():
            if self.backend == "base":
                x = self.fe(wav16, sampling_rate=16000, return_tensors="pt").to(self.device)
                e = self.model(**x).embeddings[0]
            else:
                w = torch.from_numpy(np.ascontiguousarray(wav16, dtype=np.float32)).to(self.device)
                e = self.model(w[None], sampling_rate=16000,
                               input_lengths=torch.tensor([w.numel()], device=self.device)).embeddings[0]
            e = torch.nn.functional.normalize(e.float(), dim=-1)
            return e.cpu().numpy()


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def centroid(embeddings: list[np.ndarray]) -> np.ndarray | None:
    """Mean of unit embeddings, renormalized (None for an empty list)."""
    if not embeddings:
        return None
    c = np.mean(embeddings, axis=0)
    return c / (np.linalg.norm(c) + 1e-12)
