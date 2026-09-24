"""Text normalizers for scoring TTS output with ASR (WER / CER), and letter counting for pace.

English: OpenAI Whisper's EnglishTextNormalizer (numbers -> digits, contractions, UK->US spelling, punctuation),
vendored in tts_qc/whisper_normalizers (openai-whisper 20250625, MIT) so no torch/whisper install is needed. Applied
to BOTH reference and hypothesis (eval-tooling.md finding 14).

Urdu: UrduNormalizer below (finding 16). Whisper's BasicTextNormalizer is NOT used for Urdu (finding 15) because
  * default (remove_diacritics=False) replaces every combining mark (Unicode category M*) with a SPACE,
    so a reference word with a harakat such as "پُرعزم" splits into two tokens ("پ رعزم");
  * remove_diacritics=True runs NFKD first, which decomposes ئ into Arabic ي (U+064A) + hamza and drops
    the hamza, and turns آ into ا, ۓ into ے, ۂ into ہ; it also does nothing about ك/ک, ه/ہ, ي/ی.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Callable

# ------------------------------------------------------------------------------------------------ Urdu

# harakat / Quranic annotation marks: dropped (they are optional in Urdu orthography and Whisper rarely emits them)
_UR_DIACRITICS = re.compile(
    "[ؐ-ؚ"          # Arabic honorific / small high signs
    "ً-ٟ"           # fathatan .. (zabar/zer/pesh, shadda, sukun, free-standing hamza above/below)
    "ٰ"                  # superscript (dagger) alef, e.g. وسطیٰ
    "ۖ-ۜ۟-۪ۨ-ۭ]"  # Quranic marks
)
# invisible format characters: ZWSP/ZWNJ/ZWJ/LRM/RLM, bidi embeddings and isolates, BOM, Arabic letter mark; tatweel
_UR_INVISIBLE = re.compile("[​-‏‪-‮⁦-⁩﻿؜ـ]")

_UR_LETTERS = str.maketrans({
    "ي": "ی",  # ي Arabic yeh        -> ی Urdu (Farsi) yeh
    "ى": "ی",  # ى alef maksura      -> ی
    "ك": "ک",  # ك Arabic kaf        -> ک keheh
    "ڪ": "ک",  # ڪ swash kaf         -> ک
    "ه": "ہ",  # ه Arabic heh        -> ہ heh goal (NOT ھ; see eval-tooling.md risks)
    "ە": "ہ",  # ە ae                -> ہ
    "ۀ": "ہ",  # ۀ heh + yeh above   -> ہ (izafat marker dropped, like zer-e-izafat)
    "ۂ": "ہ",  # ۂ heh goal + hamza  -> ہ
    "ة": "ۃ",  # ة teh marbuta       -> ۃ teh marbuta goal
    "أ": "ا",  # أ                   -> ا
    "إ": "ا",  # إ                   -> ا
    "ٱ": "ا",  # ٱ alef wasla        -> ا
    "ۓ": "ئے",  # ۓ (ے + hamza) -> ئے, the standard spelling (گۓ -> گئے)
    # digits: Arabic-Indic and Extended (Urdu/Persian) -> ASCII
    **{chr(0x0660 + i): str(i) for i in range(10)},
    **{chr(0x06F0 + i): str(i) for i in range(10)},
})

# Optional "phonetic" level: letters that standard Urdu pronounces identically. A TTS model cannot make them
# audible, so an ASR choosing a different one of them is a spelling choice, not a TTS error. Diagnostic only
# (finding 17): it can hide real mispronunciations.
_UR_HOMOPHONES = str.maketrans({
    "ذ": "ز", "ض": "ز", "ظ": "ز",   # ذ ض ظ -> ز   /z/
    "ص": "س", "ث": "س",                       # ص ث   -> س   /s/
    "ط": "ت", "ۃ": "ت",                       # ط ۃ   -> ت   /t/
    "ح": "ہ",                                           # ح     -> ہ   /h/
    "ع": "ا",                                           # ع     -> ا   (usually a vowel / silent)
})


class UrduNormalizer:
    """Deterministic Urdu normalizer for WER/CER. Idempotent. Apply to reference AND hypothesis.
    NFKC; ی/ي + hamza -> ئ; fold ي/ى->ی, ك/ڪ->ک, ه/ە/ۀ/ۂ->ہ, ة->ۃ, أ/إ/ٱ->ا, ۓ->ئے; Arabic-Indic/Extended digits
    -> 0-9; drop ZW*/bidi marks/tatweel; strip harakat; every P*/S* character (۔ ، ؟ …) -> space. Keeps ے/ی, ھ/ہ,
    ں/ن and آ/ا distinct. phonetic=True additionally folds homophone letters (a diagnostic, not the headline)."""

    def __init__(self, phonetic: bool = False) -> None:
        self.phonetic = phonetic

    def __call__(self, s: str) -> str:
        s = self._base(s)
        return s.translate(_UR_HOMOPHONES) if self.phonetic else s

    @staticmethod
    def _base(s: str) -> str:
        s = unicodedata.normalize("NFKC", s)         # compose آ ۂ ۓ ئ ؤ; fold presentation forms (FB50-FEFF)
        s = s.replace("یٔ", "ئ")      # ی + hamza above -> ئ  (before hamza stripping)
        s = s.replace("ئ", "ئ")      # ي + hamza above -> ئ
        s = s.translate(_UR_LETTERS)
        s = _UR_INVISIBLE.sub("", s)
        s = _UR_DIACRITICS.sub("", s)
        s = re.sub(r"(?<=\d)[٫٬,.](?=\d)", "", s)   # 1,000 / ۱٬۰۰۰ -> 1000 (separators inside numbers)
        s = s.lower()                                          # Latin code-switches
        # every punctuation (P*) and symbol (S*) character -> space: ۔ ، ؟ ؛ « » ٪ " ' ! etc.
        s = "".join(" " if unicodedata.category(c)[0] in "PS" else c for c in s)
        return re.sub(r"\s+", " ", s).strip()


def nospace(s: str) -> str:
    """For space-insensitive CER: Urdu word segmentation varies (صورتحال / صورت حال, دہشتگردی / دہشت گردی)."""
    return re.sub(r"\s+", "", s)


_NORMALIZERS: dict[str, Callable[[str], str]] = {}


def normalizer(lang: str) -> Callable[[str], str]:
    """The scoring normalizer for 'en' or 'ur' (cached; both are stateless and thread-safe)."""
    if lang not in _NORMALIZERS:
        if lang == "en":
            from .whisper_normalizers import EnglishTextNormalizer
            _NORMALIZERS[lang] = EnglishTextNormalizer()
        elif lang == "ur":
            _NORMALIZERS[lang] = UrduNormalizer()
        else:
            raise ValueError(f"no normalizer for language {lang!r} (en, ur)")
    return _NORMALIZERS[lang]


# ------------------------------------------------------------------------------------------------ counts

def count_letters(text: str) -> int:
    """Letters and digits in any script (str.isalnum; combining marks, spaces and punctuation don't count). The same
    definition as the gateway (tts_gateway.textproc.count_letters) and server/calibration/pace.json."""
    return sum(1 for ch in text if ch.isalnum())


def count_words(text: str) -> int:
    """Whitespace-separated tokens containing a letter or digit (same as the gateway)."""
    return sum(1 for token in text.split() if re.search(r"[^\W_]", token))


# ------------------------------------------------------------------------------------------------ scripts

_SCRIPTS = {
    "arabic": re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]"),
    "devanagari": re.compile(r"[ऀ-ॿ]"),
    "latin": re.compile(r"[A-Za-z]"),
}


def script_fractions(s: str) -> dict:
    """Share of letters per script: an Urdu take transcribed as Devanagari/Latin means the language drifted."""
    letters = [c for c in s if c.isalpha()]
    n = max(1, len(letters))
    return {k: round(sum(bool(r.match(c)) for c in letters) / n, 3) for k, r in _SCRIPTS.items()}
