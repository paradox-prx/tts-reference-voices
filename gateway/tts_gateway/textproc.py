"""Text helpers for English and Urdu: word count, sentence split, length cap, seconds-per-word band."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .config import Settings

CODEC_HZ = 12.5  # Qwen3-TTS-12Hz codec frames per second of audio
MIN_NEW_TOKENS, MAX_NEW_TOKENS = 96, 4096

_HAS_WORD = re.compile(r"[^\W_]")  # a letter or digit in any script
# a sentence ends at . ! ? (Latin), ۔ (Urdu full stop), ؟ (Arabic question mark), optionally followed by a closing
# quote or bracket, then whitespace; newlines always end one. "3.14" and "e.g.x" stay whole.
_SENTENCE_END = re.compile(r"(?<=[.!?۔؟])\s+|(?<=[.!?۔؟][\"'”’)\]])\s+|\s*\n\s*")
_ARABIC_SCRIPT = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
_LATIN = re.compile(r"[A-Za-z]")


def count_words(text: str) -> int:
    """Whitespace-separated tokens that contain a letter or digit (Urdu separates words with spaces too)."""
    return sum(1 for token in text.split() if _HAS_WORD.search(token))


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


def detect_lang(text: str) -> str:
    """'ur' for Arabic-script text, 'en' for Latin script, 'und' otherwise (no band: suspect check and cap off)."""
    arabic, latin = len(_ARABIC_SCRIPT.findall(text)), len(_LATIN.findall(text))
    if arabic or latin:
        return "ur" if arabic >= latin else "en"
    return "und"


def max_new_tokens_for(words: int) -> int:
    """Codec-frame budget: 2.5 words/s, 2.4x headroom, +60 frames, clamped to 96..4096."""
    frames = math.ceil(words / 2.5 * CODEC_HZ * 2.4 + 60)
    return max(MIN_NEW_TOKENS, min(MAX_NEW_TOKENS, frames))


@dataclass(frozen=True)
class SpwBand:
    """Plausible seconds of audio per word for a language. Outside it the take is suspect: skipped or cut-short
    text below, a loop or padding above."""

    lo: float
    hi: float

    @property
    def target(self) -> float:
        """Geometric centre of the band: the 'median' a take is compared against."""
        return math.sqrt(self.lo * self.hi)

    def reason(self, spw: float) -> str | None:
        """None when inside the band, else 'too_short' or 'too_long'."""
        if spw < self.lo:
            return "too_short"
        return "too_long" if spw > self.hi else None

    def distance(self, spw: float) -> float:
        return abs(math.log(spw / self.target)) if spw > 0 else math.inf


def spw_band(lang: str, settings: Settings) -> SpwBand | None:
    bands = {"en": settings.spw_en, "ur": settings.spw_ur}
    return SpwBand(*bands[lang]) if lang in bands else None


def split_for_ceiling(text: str, max_words: int) -> list[str]:
    """Pack whole sentences into parts of at most max_words words, for backends with a per-call audio ceiling.
    A sentence longer than that is cut at word boundaries."""
    parts: list[str] = []
    current: list[str] = []
    n = 0
    for sentence in split_sentences(text):
        words = count_words(sentence)
        if words > max_words:
            if current:
                parts.append(" ".join(current))
                current, n = [], 0
            tokens = sentence.split()
            parts.extend(" ".join(tokens[i:i + max_words]) for i in range(0, len(tokens), max_words))
            continue
        if current and n + words > max_words:
            parts.append(" ".join(current))
            current, n = [], 0
        current.append(sentence)
        n += words
    if current:
        parts.append(" ".join(current))
    return [p for p in parts if count_words(p)]
