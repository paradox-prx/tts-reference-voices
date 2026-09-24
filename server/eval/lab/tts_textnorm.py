"""Text normalizers for scoring TTS output with ASR (WER / CER).

English: OpenAI Whisper's EnglishTextNormalizer (numbers -> digits, contractions, UK->US spelling,
punctuation), applied to BOTH reference and hypothesis.

Urdu: UrduNormalizer below. Whisper's BasicTextNormalizer is NOT used for Urdu because
  * default (remove_diacritics=False) replaces every combining mark (Unicode category M*) with a SPACE,
    so a reference word with a harakat such as "پُرعزم" splits into two tokens ("پ رعزم");
  * remove_diacritics=True runs NFKD first, which decomposes ئ into Arabic ي (U+064A) + hamza and drops
    the hamza, and turns آ into ا, ۓ into ے, ۂ into ہ; it also does nothing about ك/ک, ه/ہ, ي/ی.
"""
from __future__ import annotations

import re
import unicodedata

# ------------------------------------------------------------------------------------------------ Urdu

# harakat / Quranic annotation marks: dropped (they are optional in Urdu orthography and Whisper rarely emits them)
_UR_DIACRITICS = re.compile(
    "[ؐ-ؚ"        # Arabic honorific / small high signs
    "ً-ٟ"          # fathatan .. (incl. zabar/zer/pesh, shadda, sukun, free-standing hamza above/below)
    "ٰ"                 # superscript (dagger) alef, e.g. وسطیٰ
    "ۖ-ۜ۟-۪ۨ-ۭ]"  # Quranic marks
)
# invisible format characters: ZWNJ/ZWJ/ZWSP/BOM/bidi marks/Arabic letter mark; tatweel (kashida)
_UR_INVISIBLE = re.compile("[​-‏‪-‮⁦-⁩﻿؜ـ]")

_UR_LETTERS = str.maketrans({
    "ي": "ی",  # ي Arabic yeh        -> ی Urdu (Farsi) yeh
    "ى": "ی",  # ى alef maksura      -> ی
    "ك": "ک",  # ك Arabic kaf        -> ک keheh
    "ڪ": "ک",  # ڪ swash kaf         -> ک
    "ه": "ہ",  # ه Arabic heh        -> ہ heh goal (NOT ھ; see FINDINGS caveat)
    "ە": "ہ",  # ە ae                -> ہ
    "ۀ": "ہ",  # ۀ heh + yeh above   -> ہ (izafat marker dropped, like zer-e-izafat)
    "ۂ": "ہ",  # ۂ heh goal + hamza  -> ہ
    "ة": "ۃ",  # ة teh marbuta       -> ۃ teh marbuta goal
    "أ": "ا",  # أ                    -> ا
    "إ": "ا",  # إ                    -> ا
    "ٱ": "ا",  # ٱ alef wasla         -> ا
    "ۓ": "ئے",  # ۓ (ے + hamza) -> ئے, the standard spelling (گۓ -> گئے)
    # digits: Arabic-Indic and Extended (Urdu/Persian) -> ASCII
    **{chr(0x0660 + i): str(i) for i in range(10)},
    **{chr(0x06F0 + i): str(i) for i in range(10)},
})


# Optional "phonetic" level: letters that standard Urdu pronounces identically. A TTS model cannot make them
# audible, so an ASR choosing a different one of them is a spelling choice, not a TTS error.
_UR_HOMOPHONES = str.maketrans({
    "ذ": "ز", "ض": "ز", "ظ": "ز",   # ذ ض ظ -> ز   /z/
    "ص": "س", "ث": "س",                       # ص ث   -> س   /s/
    "ط": "ت", "ۃ": "ت",                       # ط ۃ   -> ت   /t/
    "ح": "ہ",                                           # ح     -> ہ   /h/
    "ع": "ا",                                           # ع     -> ا   (usually a vowel / silent)
})


class UrduNormalizer:
    """Deterministic Urdu normalizer for WER/CER. Idempotent. Apply to reference AND hypothesis.
    phonetic=True additionally folds homophone letters (for a 'phonetic CER' diagnostic, not the headline)."""

    def __init__(self, phonetic: bool = False) -> None:
        self.phonetic = phonetic

    def __call__(self, s: str) -> str:
        s = self._base(s)
        return s.translate(_UR_HOMOPHONES) if self.phonetic else s

    def _base(self, s: str) -> str:
        s = unicodedata.normalize("NFKC", s)            # compose آ ۂ ۓ ئ ؤ; fold presentation forms (FB50-FEFF)
        s = s.replace("یٔ", "ئ")          # ی + hamza above -> ئ  (before hamza stripping)
        s = s.replace("ئ", "ئ")
        s = s.translate(_UR_LETTERS)
        s = _UR_INVISIBLE.sub("", s)
        s = _UR_DIACRITICS.sub("", s)
        s = re.sub(r"(?<=\d)[٫٬,.](?=\d)", "", s)   # 1,000 / ۱٬۰۰۰ -> 1000 (separators inside numbers)
        s = s.lower()                                      # Latin code-switches
        # every punctuation (P*) and symbol (S*) character -> space: ۔ ، ؟ ؛ « » ٪ " ' ! etc.
        s = "".join(" " if unicodedata.category(c)[0] in "PS" else c for c in s)
        return re.sub(r"\s+", " ", s).strip()


def nospace(s: str) -> str:
    """For space-insensitive CER: Urdu word segmentation varies (صورتحال / صورت حال, دہشتگردی / دہشت گردی)."""
    return re.sub(r"\s+", "", s)


# ------------------------------------------------------------------------------------------------ scripts

_SCRIPTS = {
    "arabic": re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]"),
    "devanagari": re.compile(r"[ऀ-ॿ]"),
    "latin": re.compile(r"[A-Za-z]"),
}


def script_fractions(s: str) -> dict:
    letters = [c for c in s if c.isalpha()]
    n = max(1, len(letters))
    return {k: round(sum(bool(r.match(c)) for c in letters) / n, 3) for k, r in _SCRIPTS.items()}
