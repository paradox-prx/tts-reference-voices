"""Audio helpers shared by both consoles: decode, edge-silence trim, join, loudness, resample, encode, QC measures, and
fitting a long reference clip (+ its transcript) under the engine's 30 s reference limit."""
from __future__ import annotations

import io
import re
import subprocess
from dataclasses import dataclass

import numpy as np
import soundfile as sf

SR = 24000  # Higgs output: 24 kHz mono 16-bit


def decode(data: bytes | str, sr: int = SR) -> np.ndarray:
    """Any audio file (bytes or path; WAV/MP3/OGG/Opus/M4A/FLAC via ffmpeg) -> float32 mono at sr."""
    src = "pipe:0" if isinstance(data, (bytes, bytearray)) else data
    p = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", str(sr),
                        "-f", "f32le", "pipe:1"], input=data if src == "pipe:0" else None, capture_output=True)
    if p.returncode != 0:
        raise ValueError(f"cannot decode audio: {p.stderr.decode(errors='replace').strip()[:200]}")
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


def read_wav_bytes(data: bytes) -> tuple[np.ndarray, int]:
    x, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
    return x.mean(axis=1), sr


def wav_bytes(x: np.ndarray, sr: int = SR) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, np.clip(x, -1.0, 1.0), sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def mp3_bytes(x: np.ndarray, sr: int = SR, bitrate: str = "128k") -> bytes:
    p = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "s16le", "-ar", str(sr), "-ac", "1",
                        "-i", "pipe:0", "-b:a", bitrate, "-f", "mp3", "pipe:1"],
                       input=(np.clip(x, -1, 1) * 32767).astype("<i2").tobytes(), capture_output=True, check=True)
    return p.stdout


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return x
    import soxr
    return soxr.resample(x, sr_in, sr_out, quality="HQ").astype(np.float32)


def frame_db(x: np.ndarray, sr: int = SR, frame_s: float = 0.02) -> np.ndarray:
    n = max(1, int(sr * frame_s))
    k = len(x) // n
    if k == 0:
        return np.array([-120.0])
    f = x[:k * n].reshape(k, n)
    return 20 * np.log10(np.sqrt((f.astype(np.float64) ** 2).mean(axis=1)) + 1e-9)


def trim_silence(x: np.ndarray, sr: int = SR, thresh_db: float = -45.0, pad_s: float = 0.06) -> np.ndarray:
    """Cut leading/trailing silence (frames below thresh_db relative to full scale), keeping pad_s on each side."""
    db = frame_db(x, sr)
    voiced = np.where(db > thresh_db)[0]
    if len(voiced) == 0:
        return x[:0]
    n = int(sr * 0.02)
    a = max(0, voiced[0] * n - int(pad_s * sr))
    b = min(len(x), (voiced[-1] + 1) * n + int(pad_s * sr))
    return x[a:b]


def join(parts: list[np.ndarray], gap_s: float = 0.3, sr: int = SR) -> np.ndarray:
    gap = np.zeros(int(gap_s * sr), dtype=np.float32)
    out = []
    for i, p in enumerate(parts):
        if i:
            out.append(gap)
        out.append(p.astype(np.float32))
    return np.concatenate(out) if out else np.zeros(0, np.float32)


def loudness_lufs(x: np.ndarray, sr: int = SR) -> float:
    import pyloudnorm as pyln
    if len(x) < int(0.4 * sr):
        return float("-inf")
    return float(pyln.Meter(sr).integrated_loudness(x.astype(np.float64)))


def normalize_loudness(x: np.ndarray, sr: int = SR, target_lufs: float | None = -20.0,
                       peak_db: float = -1.0) -> np.ndarray:
    """Gain to target integrated loudness (BS.1770), then a peak ceiling. target None: peak ceiling only."""
    if len(x) == 0:
        return x
    y = x.astype(np.float32)
    if target_lufs is not None:
        cur = loudness_lufs(y, sr)
        if np.isfinite(cur):
            y = y * np.float32(10 ** ((target_lufs - cur) / 20))
    peak = float(np.abs(y).max()) if len(y) else 0.0
    ceiling = 10 ** (peak_db / 20)
    if peak > ceiling:
        y = y * np.float32(ceiling / peak)
    return y


@dataclass
class QC:
    seconds: float
    expected_s: float
    pace_ratio: float          # seconds produced / seconds expected from the text
    max_gap_s: float           # longest internal silence
    clip_frac: float
    rms_db: float
    ok: bool
    reasons: list[str]

    def as_dict(self) -> dict:
        return {"seconds": round(self.seconds, 2), "expected_s": round(self.expected_s, 2),
                "pace_ratio": round(self.pace_ratio, 3), "max_gap_s": round(self.max_gap_s, 2),
                "clip_frac": round(self.clip_frac, 5), "rms_db": round(self.rms_db, 1), "ok": self.ok,
                "reasons": self.reasons}


def measure(x: np.ndarray, expected_s: float, sr: int = SR, *, check_duration: bool = True,
            check_silence: bool = True, check_clipping: bool = True, pace_band: tuple[float, float] = (0.55, 1.8),
            max_gap_s: float = 2.5, max_clip_frac: float = 0.002) -> QC:
    secs = len(x) / sr
    db = frame_db(x, sr)
    voiced = db > -45.0
    best = run = 0
    if voiced.any():
        first, last = np.argmax(voiced), len(voiced) - np.argmax(voiced[::-1])
        for v in voiced[first:last]:
            run = 0 if v else run + 1
            best = max(best, run)
    gap = best * 0.02
    clip = float((np.abs(x) >= 0.999).mean()) if len(x) else 0.0
    rms = float(20 * np.log10(np.sqrt(np.mean(x.astype(np.float64) ** 2)) + 1e-9)) if len(x) else -120.0
    ratio = secs / expected_s if expected_s > 0 else 1.0
    reasons = []
    if check_duration and not (pace_band[0] <= ratio <= pace_band[1]):
        reasons.append(f"duration {secs:.1f}s vs ~{expected_s:.1f}s expected (x{ratio:.2f})")
    if check_silence and gap > max_gap_s:
        reasons.append(f"silence of {gap:.1f}s inside the take")
    if check_silence and rms < -45:
        reasons.append("near-silent take")
    if check_clipping and clip > max_clip_frac:
        reasons.append(f"clipping ({clip:.2%} of samples)")
    return QC(secs, expected_s, ratio, gap, clip, rms, not reasons, reasons)


# ---- reference clips ------------------------------------------------------------------------------------------------

_SENT_RE = re.compile(r"(?<=[.!?۔؟])\s+|(?<=[۔؟])")


def speech_seconds(x: np.ndarray, sr: int = SR) -> float:
    return float((frame_db(x, sr) > -45.0).sum() * 0.02)


@dataclass
class FittedRef:
    audio: np.ndarray
    text: str
    seconds: float
    trimmed: bool
    note: str = ""


def fit_reference(x: np.ndarray, text: str, max_s: float = 29.5, sr: int = SR) -> FittedRef:
    """Fit a reference under max_s seconds (the engine rejects > 30 s). Short clips pass unchanged. Longer clips are
    cut at a pause that matches a sentence end (or, with no punctuation, a word end) by text position: the share of
    letters up to the boundary is mapped onto the share of voiced time, and the cut must land on a real pause within
    0.5 s of that estimate. The transcript is cut at the same boundary."""
    x = trim_silence(x, sr)
    dur = len(x) / sr
    if dur <= max_s:
        return FittedRef(x, text.strip(), dur, False)
    db = frame_db(x, sr)
    voiced = db > -45.0
    cum_voiced = np.cumsum(voiced) * 0.02
    total_voiced = cum_voiced[-1] if len(cum_voiced) else 0.0
    # pauses: runs of >= 0.16 s unvoiced frames -> their centre time
    pauses, run_start = [], None
    for i, v in enumerate(voiced):
        if not v and run_start is None:
            run_start = i
        elif v and run_start is not None:
            if (i - run_start) * 0.02 >= 0.16:
                pauses.append(((run_start + i) / 2 * 0.02, (i - run_start) * 0.02))
            run_start = None
    pauses = np.array(pauses) if pauses else np.zeros((0, 2))

    def boundaries(pattern: str):
        idx = [m.end() for m in re.finditer(pattern, text)]
        return [i for i in idx if 0 < i < len(text)]

    total_letters = max(1, len(re.findall(r"\w", text)))
    best = None
    for kind, cuts in (("sentence", boundaries(r"[.!?۔؟]+[\"'”)]*\s*")), ("word", boundaries(r"\s+"))):
        for c in cuts:
            frac = len(re.findall(r"\w", text[:c])) / total_letters
            target_voiced = frac * total_voiced
            t_est = float(np.searchsorted(cum_voiced, target_voiced) * 0.02)
            if t_est > max_s or len(pauses) == 0:
                continue
            d = np.abs(pauses[:, 0] - t_est)
            j = int(np.argmin(d))
            if d[j] <= 0.5 and pauses[j, 0] <= max_s:
                score = (pauses[j, 0], -d[j])  # prefer the latest boundary, then the closest pause
                if best is None or score > best[0]:
                    best = (score, c, pauses[j, 0], kind, d[j])
        if best is not None and best[3] == kind and best[2] >= 8.0:
            break  # a sentence boundary of >= 8 s is good enough; only fall back to words otherwise
    if best is None:
        cut_t = max_s
        return FittedRef(x[:int(cut_t * sr)], text.strip(), cut_t, True,
                         "no pause matched the text: hard cut, transcript NOT cut (check it)")
    _, c, cut_t, kind, dist = best
    y = trim_silence(x[:int(cut_t * sr)], sr)
    return FittedRef(y, text[:c].strip(), len(y) / sr, True,
                     f"cut at a {kind} boundary {cut_t:.1f}s (pause {dist:.2f}s from the text estimate)")


def peaks(x: np.ndarray, n: int = 400) -> list[float]:
    """Waveform overview: n max-abs values."""
    if len(x) == 0:
        return [0.0] * n
    k = max(1, len(x) // n)
    m = len(x) // k
    return [round(float(v), 3) for v in np.abs(x[:m * k]).reshape(m, k).max(axis=1)]
