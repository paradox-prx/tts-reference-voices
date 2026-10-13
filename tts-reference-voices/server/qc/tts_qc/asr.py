"""Whisper large-v3 through faster-whisper / CTranslate2 (eval-tooling.md findings 1-13).

Settings (fixed; they are part of the metric definition): stock Systran/faster-whisper-large-v3, language forced to
'en' or 'ur' (auto-LID confuses Urdu with Hindi), beam 5, sequential long-form decoding (not BatchedInferencePipeline,
which VAD-chunks one file and hides loops), condition_on_previous_text=False (one bad window's repetition must not seed
the next), vad_filter=False (silence is measured on the waveform instead), word_timestamps=True (the loop detector),
default temperature fallback and thresholds. float16 on GPU, int8 on CPU. Throughput comes from `workers`
CTranslate2 replicas that share one copy of the weights on the same GPU; callers use it from several threads.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .checks import Word

WHISPER_LANG = {"en": "en", "ur": "ur"}


@dataclass
class AsrResult:
    text: str
    words: list[Word]
    diag: dict = field(default_factory=dict)     # seg_max_cr, seg_fallback, seg_min_logprob, seg_max_nospeech
    seconds: float = 0.0


class Asr:
    def __init__(self, model_dir: str | Path, device: str = "cuda", compute_type: str | None = None,
                 workers: int = 2, cpu_threads: int = 8, beam: int = 5, device_index: int = 0) -> None:
        from faster_whisper import WhisperModel

        self.model_dir, self.device, self.beam = str(model_dir), device, beam
        self.compute_type = compute_type or ("float16" if device == "cuda" else "int8")
        self.workers = max(1, workers)
        t0 = time.perf_counter()
        self.model = WhisperModel(self.model_dir, device=device, device_index=device_index,
                                  compute_type=self.compute_type, num_workers=self.workers,
                                  cpu_threads=cpu_threads if device == "cpu" else 0, local_files_only=True)
        self.load_s = time.perf_counter() - t0

    def describe(self) -> dict:
        return {"model": Path(self.model_dir).name, "device": self.device, "compute_type": self.compute_type,
                "workers": self.workers, "beam": self.beam}

    def transcribe(self, wav16: np.ndarray, lang: str) -> AsrResult:
        """wav16: float32 mono at 16 kHz (audio.to_16k). lang: 'en' or 'ur'."""
        t0 = time.perf_counter()
        segments, _info = self.model.transcribe(
            wav16, language=WHISPER_LANG[lang], task="transcribe", beam_size=self.beam,
            condition_on_previous_text=False, vad_filter=False, word_timestamps=True)
        segs = list(segments)
        words = [Word(float(w.start), float(w.end), w.word, float(w.probability))
                 for s in segs for w in (s.words or [])]
        diag = {
            # zlib ratio of the segment text's UTF-8 bytes: real Urdu 1.17-1.79, English lower, loops 14-18
            "seg_max_cr": round(max((s.compression_ratio for s in segs), default=0.0), 2),
            "seg_fallback": sum(1 for s in segs if (s.temperature or 0) > 0),     # decodes that needed T > 0
            "seg_min_logprob": round(min((s.avg_logprob for s in segs), default=0.0), 3),
            "seg_max_nospeech": round(max((s.no_speech_prob for s in segs), default=0.0), 3),
            "n_segments": len(segs),
        }
        return AsrResult(" ".join(s.text.strip() for s in segs).strip(), words, diag, time.perf_counter() - t0)
