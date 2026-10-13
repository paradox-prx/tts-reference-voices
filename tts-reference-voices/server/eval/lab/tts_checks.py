"""Loop / skip / padding detectors for TTS takes. Pure numpy + jiwer; no GPU.

text_checks(): compares the normalized input text with the normalized ASR transcript.
audio_checks(): energy-based silence analysis of the waveform (no model needed).
"""
from __future__ import annotations

import re
from collections import Counter

import jiwer
import numpy as np


# ------------------------------------------------------------------------------------------------ text side

def _ngram_counts(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def repeat_excess(ref_tokens: list[str], hyp_tokens: list[str], nmax: int = 4) -> tuple[int, str]:
    """Largest (count in hyp - count in ref) over all n-grams, n=1..nmax, weighted by n (so a repeated
    4-gram counts more than a repeated word). Catches 'ایک ایک ایک…' and phrase loops that ASR transcribes."""
    best, what = 0, ""
    for n in range(1, nmax + 1):
        rc, hc = _ngram_counts(ref_tokens, n), _ngram_counts(hyp_tokens, n)
        for g, c in hc.items():
            if c < 2:                                  # a new n-gram created by a skip is not a repetition
                continue
            ex = (c - max(rc.get(g, 0), 1)) * n
            if ex > best:
                best, what = ex, " ".join(g)
    return best, what


def max_consecutive_repeat(tokens: list[str]) -> int:
    """Longest run of the same token in a row (e.g. 'ایک ایک ایک ایک' -> 4)."""
    best = run = 1 if tokens else 0
    for a, b in zip(tokens, tokens[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    return best


_CHAR_RUN = re.compile(r"(\S)\1{3,}")          # same letter >= 4 times: 'آآآآ', 'ممممم'


def text_checks(ref_norm: str, hyp_norm: str) -> dict:
    r, h = ref_norm.split(), hyp_norm.split()
    out = jiwer.process_words(ref_norm, hyp_norm) if r else None
    longest_del = longest_ins = 0
    if out is not None:
        for ch in out.alignments[0]:
            if ch.type == "delete":
                longest_del = max(longest_del, ch.ref_end_idx - ch.ref_start_idx)
            elif ch.type == "insert":
                longest_ins = max(longest_ins, ch.hyp_end_idx - ch.hyp_start_idx)
    rc, hc = len(ref_norm.replace(" ", "")), len(hyp_norm.replace(" ", ""))
    rex, rex_what = repeat_excess(r, h)
    return {
        "wer": round(out.wer, 4) if out else None,
        "sub": out.substitutions if out else 0, "del": out.deletions if out else 0, "ins": out.insertions if out else 0,
        "longest_del_run": longest_del,              # skipped span, in words
        "longest_ins_run": longest_ins,              # made-up filler / loop, in words
        "char_ratio": round(hc / rc, 3) if rc else None,   # hyp/ref letters: <~0.85 skip, >~1.15 loop/filler
        "repeat_excess": rex, "repeat_what": rex_what,
        "max_token_run": max_consecutive_repeat(h),
        "char_runs": len(_CHAR_RUN.findall(hyp_norm)),
    }


# ------------------------------------------------------------------------------------------------ audio side

def speech_mask(wav: np.ndarray, sr: int, frame_ms: float = 20.0, rel_db: float = -35.0, abs_floor_db: float = -60.0) -> np.ndarray:
    """Per-frame boolean speech mask (same rule as audio_checks)."""
    x = wav.astype(np.float64)
    if np.issubdtype(wav.dtype, np.integer):
        x = x / float(np.iinfo(wav.dtype).max)
    n = int(sr * frame_ms / 1000)
    frames = x[: len(x) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-10)
    return db > max(abs_floor_db, np.percentile(db, 95) + rel_db)


def word_timing_checks(words: list, wav: np.ndarray, sr: int) -> dict:
    """words: faster-whisper Word objects. Whisper (esp. Urdu) often transcribes a looped span as ONE clean word
    whose timestamp stretches over the loop, and absorbs pauses into neighbouring words. The longest word and
    how much of it is voiced separate 'loop/garble' (voiced) from 'long pause' (silent)."""
    if not words:
        return {"max_word_dur_s": None, "max_word_voiced": None, "aligned_chars_per_s": None}
    w = max(words, key=lambda w: w.end - w.start)
    m = speech_mask(wav, sr)
    a, b = int(w.start / 0.02), max(int(w.start / 0.02) + 1, int(w.end / 0.02))
    span = words[-1].end - words[0].start
    chars = sum(len(x.word.strip()) for x in words)
    return {"max_word_dur_s": round(w.end - w.start, 2), "max_word": w.word.strip(),
            "max_word_voiced": round(float(m[a:b].mean()) if b > a and a < len(m) else 0.0, 2),
            "aligned_chars_per_s": round(chars / span, 2) if span > 0 else None}


def audio_checks(wav: np.ndarray, sr: int, frame_ms: float = 20.0, rel_db: float = -35.0, abs_floor_db: float = -60.0) -> dict:
    """Energy VAD. A frame is 'speech' when its RMS is above max(abs_floor_db, p95_rms_db + rel_db).
    Returns leading/trailing/longest-internal silence, speech ratio and clipping."""
    x = wav.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if np.issubdtype(wav.dtype, np.integer):
        x = x / float(np.iinfo(wav.dtype).max)
    n = int(sr * frame_ms / 1000)
    frames = x[: len(x) // n * n].reshape(-1, n) if len(x) >= n else x.reshape(1, -1)
    rms_db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-10)
    thr = max(abs_floor_db, np.percentile(rms_db, 95) + rel_db)
    speech = rms_db > thr
    dur, fs = len(x) / sr, frame_ms / 1000
    if not speech.any():
        return {"duration_s": round(dur, 3), "speech_ratio": 0.0, "lead_sil_s": round(dur, 3), "trail_sil_s": round(dur, 3),
                "max_internal_sil_s": 0.0, "n_internal_sil_gt1s": 0, "clip_frac": 0.0, "thr_db": round(thr, 1)}
    idx = np.flatnonzero(speech)
    lead, trail = idx[0] * fs, (len(speech) - 1 - idx[-1]) * fs
    inner = speech[idx[0]: idx[-1] + 1]
    gaps, run = [], 0
    for s in inner:
        if not s:
            run += 1
        elif run:
            gaps.append(run * fs)
            run = 0
    return {
        "duration_s": round(dur, 3),
        "speech_ratio": round(float(speech.mean()), 3),
        "lead_sil_s": round(float(lead), 3), "trail_sil_s": round(float(trail), 3),
        "max_internal_sil_s": round(max(gaps, default=0.0), 3),
        "n_internal_sil_gt1s": sum(g > 1.0 for g in gaps),
        "clip_frac": round(float((np.abs(x) >= 0.999).mean()), 5),
        "thr_db": round(float(thr), 1),
    }
