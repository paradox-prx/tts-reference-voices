"""Audio I/O shared by the sidecar (base64 PCM16 in the request) and the offline scorer (bench WAV files).

Both paths end in the same arrays: mono int16 PCM at the take's own rate (for the energy VAD, durations and
clipping) and float32 at 16 kHz (for Whisper and the speaker embedders). The 16 kHz resampler is libswresample via
PyAV with the exact settings faster_whisper.decode_audio uses (s16, mono, 16 kHz, then / 32768), so transcribing a
WAV file and transcribing the same PCM sent over HTTP give the same input to the model.
"""
from __future__ import annotations

import base64
import binascii
from pathlib import Path

import numpy as np

ASR_RATE = 16_000


class AudioError(ValueError):
    """Unusable audio in a request or a file (bad base64, odd byte count, empty, too long)."""


def pcm16_from_b64(pcm_b64: str) -> np.ndarray:
    """base64 PCM16 little-endian mono -> int16 array."""
    try:
        raw = base64.b64decode(pcm_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AudioError(f"pcm_b64 is not valid base64: {exc}") from exc
    if len(raw) % 2:
        raise AudioError(f"PCM16 needs an even number of bytes, got {len(raw)}")
    return np.frombuffer(raw, dtype="<i2").astype(np.int16, copy=False)


def read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Any file libsndfile reads (bench_tts.py's labelled RIFF with a LIST/INFO chunk included) -> (mono int16, rate).
    Channels are averaged."""
    import soundfile as sf

    data, sr = sf.read(str(path), dtype="int16", always_2d=True)
    if data.shape[1] > 1:
        data = data.mean(axis=1).round().astype(np.int16)
    else:
        data = data[:, 0]
    return np.ascontiguousarray(data), int(sr)


def to_16k(pcm: np.ndarray, sr: int) -> np.ndarray:
    """mono int16 at `sr` -> float32 in [-1, 1) at 16 kHz (faster_whisper.decode_audio's resampler)."""
    pcm = np.ascontiguousarray(pcm, dtype=np.int16)
    if sr == ASR_RATE or not len(pcm):
        return pcm.astype(np.float32) / 32768.0
    import av

    resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=ASR_RATE)
    frame = av.AudioFrame.from_ndarray(pcm.reshape(1, -1), format="s16", layout="mono")
    frame.sample_rate = sr
    chunks = [f.to_ndarray() for f in resampler.resample(frame)]
    chunks += [f.to_ndarray() for f in resampler.resample(None)]      # flush the filter's tail
    out = np.concatenate(chunks, axis=1).reshape(-1) if chunks else np.zeros(0, np.int16)
    return out.astype(np.float32) / 32768.0


def trim_16k(wav16: np.ndarray, lead_s: float, trail_s: float, margin_s: float = 0.1) -> np.ndarray:
    """Cut leading/trailing silence (measured by the energy VAD at the original rate) off the 16 kHz signal, keeping
    `margin_s` on each side, before speaker embedding (the lab's sim_eval trim: 5 frames of 20 ms before, 5 after)."""
    n = len(wav16)
    a = max(0, int((lead_s - margin_s) * ASR_RATE))
    b = min(n, n - int(max(0.0, trail_s - margin_s) * ASR_RATE))
    return wav16[a:b] if b - a > 0 else wav16
