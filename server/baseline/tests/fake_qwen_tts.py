"""A CPU-only stand-in for qwen_tts.Qwen3TTSModel: the same method names and shapes the baseline uses, no weights.

Generation semantics mimic qwen-tts + HF generate: a row "naturally" ends after frames_for(text) codec frames (EOS);
generation stops at max_new_tokens, so a row returns min(natural, max_new_tokens) frames and each frame is exactly
1920 samples at 24 kHz. A text containing 'loop' never emits EOS (runaway). The fake raises if two threads call it
at once and records the thread of every call.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch

SPF = 1920
GENERATION_CONFIG = {"do_sample": True, "repetition_penalty": 1.05, "temperature": 0.9, "top_p": 1.0, "top_k": 50,
                     "subtalker_dosample": True, "subtalker_temperature": 0.9, "subtalker_top_p": 1.0,
                     "subtalker_top_k": 50, "max_new_tokens": 8192}


@dataclass
class FakePromptItem:
    ref_code: Any
    ref_spk_embedding: Any
    x_vector_only_mode: bool
    icl_mode: bool
    ref_text: str | None = None


class FakeTokenizer:
    def __call__(self, text, padding=False):
        return {"input_ids": list(range(max(1, len(str(text).split()))))}


class FakeProcessor:
    tokenizer = FakeTokenizer()


class FakeSpeechTokenizer:
    def get_decode_upsample_rate(self):
        return SPF

    def get_output_sample_rate(self):
        return 24000


def fake_embedding(audio: np.ndarray) -> torch.Tensor:
    """Deterministic 4-d 'speaker embedding' from robust audio features (peak, duration)."""
    peak = round(float(np.max(np.abs(audio))), 2)
    dur = round(len(audio) / 24000, 1)
    return torch.tensor([peak, 2 * peak, dur, 1.0], dtype=torch.float32)


class FakeModel:
    speaker_encoder_sample_rate = 24000

    def __init__(self, owner: "FakeTTS") -> None:
        self.owner = owner
        self.speech_tokenizer = FakeSpeechTokenizer()

    def get_supported_languages(self):
        return ["auto", "chinese", "english", "german", "italian", "portuguese", "spanish", "japanese", "korean",
                "french", "russian"]

    def extract_speaker_embedding(self, audio, sr):
        assert sr == 24000, "Only support 24kHz audio"
        self.owner._enter("extract")
        try:
            self.owner.embedding_calls += 1
            return fake_embedding(audio)
        finally:
            self.owner._exit()


class FakeTTS:
    def __init__(self, delay: float = 0.0, oom_above: int | None = None, loop_first_n: int | None = None) -> None:
        self.generate_defaults = dict(GENERATION_CONFIG)
        self.model = FakeModel(self)
        self.processor = FakeProcessor()
        self.delay = delay
        self.oom_above = oom_above          # raise an OOM when a generate call has more rows than this
        self.loop_first_n = loop_first_n    # 'maybe-loop' texts run away on their first n generations only
        self.calls: list[dict] = []
        self.prompt_calls: list[dict] = []
        self.embedding_calls = 0
        self.threads: set[int] = set()
        self._busy = threading.Lock()
        self._maybe_loop_seen = 0

    def _enter(self, what: str) -> None:
        if not self._busy.acquire(blocking=False):
            raise AssertionError(f"concurrent call into the model ({what})")
        self.threads.add(threading.get_ident())

    def _exit(self) -> None:
        self._busy.release()

    def frames_for(self, text: str) -> float:
        if "loop" in text and "maybe-loop" not in text:
            return float("inf")
        if "maybe-loop" in text:
            self._maybe_loop_seen += 1
            if self.loop_first_n is not None and self._maybe_loop_seen <= self.loop_first_n:
                return float("inf")
        return 3 * len(text.split())

    def create_voice_clone_prompt(self, ref_audio, ref_text=None, x_vector_only_mode=False):
        self._enter("prompt")
        try:
            audio, sr = ref_audio
            assert isinstance(audio, np.ndarray)
            if not x_vector_only_mode and not ref_text:
                raise ValueError("ref_text is required when x_vector_only_mode=False (ICL mode)")
            self.prompt_calls.append({"sr": sr, "n": len(audio), "ref_text": ref_text, "xvec": x_vector_only_mode})
            wav24 = audio
            if sr != 24000:
                import librosa

                wav24 = librosa.resample(y=audio, orig_sr=sr, target_sr=24000)
            frames = int(len(wav24) / SPF)
            code = None if x_vector_only_mode else torch.zeros((frames, 16), dtype=torch.long)
            return [FakePromptItem(code, fake_embedding(wav24), bool(x_vector_only_mode), not x_vector_only_mode,
                                   ref_text)]
        finally:
            self._exit()

    def generate_voice_clone(self, text, language=None, ref_audio=None, ref_text=None, x_vector_only_mode=False,
                             voice_clone_prompt=None, non_streaming_mode=False, **kwargs):
        self._enter("generate")
        try:
            texts = text if isinstance(text, list) else [text]
            langs = language if isinstance(language, list) else [language] * len(texts)
            if self.oom_above is not None and len(texts) > self.oom_above:
                raise torch.OutOfMemoryError("CUDA out of memory. Tried to allocate 2.00 GiB (fake)")
            for lang in langs:
                if str(lang).lower() not in self.model.get_supported_languages():
                    raise ValueError(f"Unsupported languages: {[lang]}")
            cap = kwargs["max_new_tokens"]
            self.calls.append({"texts": list(texts), "languages": list(langs), "items": list(voice_clone_prompt),
                               "non_streaming_mode": non_streaming_mode, "kwargs": dict(kwargs),
                               "rng": float(torch.rand(1))})
            if self.delay:
                time.sleep(self.delay)
            wavs = []
            for t in texts:
                frames = int(min(self.frames_for(t), cap))
                n = frames * SPF
                wavs.append((0.25 * np.sin(np.arange(n) * 2 * np.pi * 220 / 24000)).astype(np.float32))
            return wavs, 24000
        finally:
            self._exit()
