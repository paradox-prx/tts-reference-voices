"""Loop / skip / padding detectors for TTS takes (eval-tooling.md findings 11, 12, 26). Pure numpy + jiwer; no model.

text_checks():        normalized input text vs normalized ASR transcript (skips, fillers, repeats).
Vad / audio_checks(): energy-based silence analysis of the waveform: leading / trailing / internal silence.
word_timing_checks(): Whisper (especially forced-'ur') often transcribes a looped span as ONE clean word whose
                      timestamp stretches over the loop; the longest word and how much of it is voiced separate a
                      loop/garble (voiced) from a long pause (silent).
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

import jiwer
import numpy as np

# energy VAD defaults (calibrated on the real clips: rel -35 dB keeps the longest natural pause <= 1.5 s)
FRAME_MS = 20.0
REL_DB = -35.0
ABS_FLOOR_DB = -60.0


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


def max_consecutive_repeat(tokens: Sequence[str]) -> int:
    """Longest run of the same token in a row (e.g. 'ایک ایک ایک ایک' -> 4)."""
    best = run = 1 if tokens else 0
    for a, b in zip(tokens, tokens[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    return best


_CHAR_RUN = re.compile(r"(\S)\1{3,}")          # same letter >= 4 times: 'آآآآ', 'ممممم'


def text_checks(ref_norm: str, hyp_norm: str) -> dict:
    """Both strings already normalized (textnorm.normalizer(lang)). Keys:
    sub/del/ins      word-level edit counts;  del_run / ins_run  longest deleted / inserted span, in words
    char_ratio       hyp letters / ref letters (<~0.85 skip or cut short, >~1.15 loop or filler)
    repeat_excess    n-gram repetition beyond the reference (see repeat_excess());  repeat_what  that n-gram
    token_run(_ref)  longest run of one repeated token in the hyp (ref);  char_runs(_ref)  letters repeated >= 4x"""
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
        "sub": out.substitutions if out else 0, "del": out.deletions if out else 0,
        "ins": out.insertions if out else 0,
        "del_run": longest_del, "ins_run": longest_ins,
        "char_ratio": round(hc / rc, 3) if rc else None,
        "repeat_excess": rex, "repeat_what": rex_what,
        "token_run": max_consecutive_repeat(h), "token_run_ref": max_consecutive_repeat(r),
        "char_runs": len(_CHAR_RUN.findall(hyp_norm)), "char_runs_ref": len(_CHAR_RUN.findall(ref_norm)),
    }


# ------------------------------------------------------------------------------------------------ audio side

def to_float(wav: np.ndarray) -> np.ndarray:
    """Mono float64 in [-1, 1] from int16/int32/float input (channels averaged)."""
    x = wav.astype(np.float64)
    if np.issubdtype(wav.dtype, np.integer):
        x = x / float(np.iinfo(wav.dtype).max)
    return x.mean(axis=1) if x.ndim > 1 else x


@dataclass(frozen=True)
class Vad:
    """Per-frame energy VAD: a frame is speech when its RMS is above max(abs_floor_db, p95_rms_db + rel_db)."""
    speech: np.ndarray        # bool per frame
    frame_s: float
    thr_db: float
    duration_s: float

    @classmethod
    def compute(cls, wav: np.ndarray, sr: int, frame_ms: float = FRAME_MS, rel_db: float = REL_DB,
                abs_floor_db: float = ABS_FLOOR_DB) -> "Vad":
        x = to_float(wav)
        n = max(1, int(sr * frame_ms / 1000))
        frames = x[: len(x) // n * n].reshape(-1, n) if len(x) >= n else x.reshape(1, -1)
        if frames.size == 0:
            return cls(np.zeros(0, dtype=bool), frame_ms / 1000, abs_floor_db, 0.0)
        rms_db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-10)
        thr = max(abs_floor_db, float(np.percentile(rms_db, 95)) + rel_db)
        return cls(rms_db > thr, frame_ms / 1000, thr, len(x) / sr)

    def voiced_fraction(self, start_s: float, end_s: float) -> float:
        a = int(start_s / self.frame_s)
        b = max(a + 1, int(end_s / self.frame_s))
        return float(self.speech[a:b].mean()) if a < len(self.speech) else 0.0


def audio_checks(wav: np.ndarray, sr: int, frame_ms: float = FRAME_MS, rel_db: float = REL_DB,
                 abs_floor_db: float = ABS_FLOOR_DB, vad: Vad | None = None) -> dict:
    """Leading / trailing / longest internal silence, speech ratio, clipping (seconds, fractions)."""
    vad = vad or Vad.compute(wav, sr, frame_ms, rel_db, abs_floor_db)
    speech, fs, dur = vad.speech, vad.frame_s, vad.duration_s
    x = to_float(wav)
    clip = round(float((np.abs(x) >= 0.999).mean()), 5) if len(x) else 0.0
    if not speech.any():
        return {"duration_s": round(dur, 3), "speech_ratio": 0.0, "lead_sil_s": round(dur, 3),
                "trail_sil_s": round(dur, 3), "max_internal_sil_s": 0.0, "n_internal_sil_gt1s": 0,
                "speech_span_s": 0.0, "clip_frac": clip, "thr_db": round(vad.thr_db, 1)}
    idx = np.flatnonzero(speech)
    lead, trail = idx[0] * fs, (len(speech) - 1 - idx[-1]) * fs
    gaps, run = [], 0
    for s in speech[idx[0]: idx[-1] + 1]:
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
        "speech_span_s": round(float((idx[-1] - idx[0] + 1) * fs), 3),
        "clip_frac": clip,
        "thr_db": round(float(vad.thr_db), 1),
    }


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    word: str
    probability: float = 1.0


def word_timing_checks(words: Sequence[Word], vad: Vad) -> dict:
    """Loops the ASR did not transcribe leave one of two marks in the word timestamps (make_synth.py cases):
      max_word_s / max_word_voiced   Urdu: one word stretched over the loop (4.9-5.5 s, 98-99 % voiced); a long pause
                                     absorbed into a word is mostly silent (5.2 s, 26 % voiced)
      max_gap_s / max_gap_voiced     English: a voiced stretch between two words (or before the first) that no word
                                     covers (a 3 x 3 s phrase loop: 9.0 s, 97 % voiced; real clips <= 0.68 s voiced)
    aligned_chars_per_s: transcript letters per second of aligned span."""
    if not words:
        return {"max_word_s": None, "max_word": None, "max_word_voiced": None, "max_gap_s": None,
                "max_gap_voiced": None, "max_gap_at_s": None, "aligned_chars_per_s": None, "n_words_asr": 0}
    w = max(words, key=lambda w: w.end - w.start)
    spans = [(0.0, words[0].start)] + [(a.end, b.start) for a, b in zip(words, words[1:])]
    g0, g1 = max(spans, key=lambda g: g[1] - g[0])
    span = words[-1].end - words[0].start
    chars = sum(len(x.word.strip()) for x in words)
    return {"max_word_s": round(w.end - w.start, 2), "max_word": w.word.strip(),
            "max_word_voiced": round(vad.voiced_fraction(w.start, w.end), 2),
            "max_gap_s": round(max(0.0, g1 - g0), 2),
            "max_gap_voiced": round(vad.voiced_fraction(g0, g1), 2) if g1 > g0 else 0.0,
            "max_gap_at_s": round(g0, 2),
            "aligned_chars_per_s": round(chars / span, 2) if span > 0 else None,
            "n_words_asr": len(words)}
