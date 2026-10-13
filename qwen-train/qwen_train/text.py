"""Urdu text normalisation for TTS training and inference: the same function must be applied to training transcripts
and to the text sent to the model at serving time.

What it does (all optional but on by default in derive.py):
  * Unicode NFC, Arabic presentation forms folded, tatweel removed, zero-width characters removed, whitespace collapsed.
  * Digits (Western 0-9 and Urdu ۰-۹, with optional decimals and thousands separators) spelled out in Urdu words.
  * Punctuation left as written (the transcripts mix "." "," "?" with "۔" "،" "؟"; both forms occur in the training set
    and the model treats them as tokens), except that repeated punctuation is collapsed and spacing is fixed.
  * Optional removal of diacritics (harakat), default off: the transcripts are essentially undiacritised already.
"""
from __future__ import annotations

import re
import unicodedata

ZERO_WIDTH = "​‌‍‎‏﻿⁠"
TATWEEL = "ـ"
HARAKAT = re.compile(r"[ً-ْٰٓ-ٕ]")
URDU_DIGITS = {ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")}
ARABIC_INDIC_DIGITS = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}
NUMBER = re.compile(r"(?<![\w؀-ۿ])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?![\w؀-ۿ])")
MULTI_SPACE = re.compile(r"[ \t ]+")
SPACE_BEFORE_PUNCT = re.compile(r"\s+([،۔؟,.?!;:])")
REPEATED_PUNCT = re.compile(r"([،۔؟,.?!])\1+")

# Urdu number words 0-99 (standard, as spoken in Pakistan)
ONES = ["صفر", "ایک", "دو", "تین", "چار", "پانچ", "چھ", "سات", "آٹھ", "نو", "دس", "گیارہ", "بارہ", "تیرہ", "چودہ",
        "پندرہ", "سولہ", "سترہ", "اٹھارہ", "انیس", "بیس", "اکیس", "بائیس", "تئیس", "چوبیس", "پچیس", "چھبیس", "ستائیس",
        "اٹھائیس", "انتیس", "تیس", "اکتیس", "بتیس", "تینتیس", "چونتیس", "پینتیس", "چھتیس", "سینتیس", "اڑتیس", "انتالیس",
        "چالیس", "اکتالیس", "بیالیس", "تینتالیس", "چوالیس", "پینتالیس", "چھیالیس", "سینتالیس", "اڑتالیس", "انچاس",
        "پچاس", "اکاون", "باون", "ترپن", "چون", "پچپن", "چھپن", "ستاون", "اٹھاون", "انسٹھ", "ساٹھ", "اکسٹھ", "باسٹھ",
        "تریسٹھ", "چونسٹھ", "پینسٹھ", "چھیاسٹھ", "سرسٹھ", "اڑسٹھ", "انہتر", "ستر", "اکہتر", "بہتر", "تہتر", "چوہتر",
        "پچہتر", "چھہتر", "ستتر", "اٹھہتر", "اناسی", "اسی", "اکیاسی", "بیاسی", "تراسی", "چوراسی", "پچاسی", "چھیاسی",
        "ستاسی", "اٹھاسی", "نواسی", "نوے", "اکانوے", "بانوے", "ترانوے", "چورانوے", "پچانوے", "چھیانوے", "ستانوے",
        "اٹھانوے", "ننانوے"]
HUNDRED, THOUSAND, LAKH, CRORE, ARAB = "سو", "ہزار", "لاکھ", "کروڑ", "ارب"


def _below_thousand(n: int) -> str:
    assert 0 <= n < 1000
    if n < 100:
        return ONES[n]
    h, r = divmod(n, 100)
    return f"{ONES[h]} {HUNDRED}" + (f" {ONES[r]}" if r else "")


def num2words_ur(n: int) -> str:
    """Integer to Urdu words with the South Asian grouping (hazar, lakh, crore, arab)."""
    if n < 0:
        return "منفی " + num2words_ur(-n)
    if n < 1000:
        return _below_thousand(n)
    parts = []
    for unit, name in ((10**9, ARAB), (10**7, CRORE), (10**5, LAKH), (10**3, THOUSAND)):
        q, n = divmod(n, unit)
        if q:
            parts.append(f"{_below_thousand(q) if q < 1000 else num2words_ur(q)} {name}")
    if n:
        parts.append(_below_thousand(n))
    return " ".join(parts)


def _number_to_words(match: re.Match) -> str:
    whole = int(match.group(1).replace(",", ""))
    words = num2words_ur(whole)
    if match.group(2):
        words += " اعشاریہ " + " ".join(ONES[int(d)] for d in match.group(2))
    return words


def normalize_urdu(text: str, spell_numbers: bool = True, strip_harakat: bool = False) -> str:
    text = unicodedata.normalize("NFKC", text)  # folds presentation forms (ﻻ etc.) and full-width punctuation
    text = text.translate(URDU_DIGITS).translate(ARABIC_INDIC_DIGITS)
    for ch in ZERO_WIDTH + TATWEEL:
        text = text.replace(ch, "")
    if strip_harakat:
        text = HARAKAT.sub("", text)
    if spell_numbers:
        text = NUMBER.sub(_number_to_words, text)
    text = text.replace("\n", " ").replace("\r", " ")
    text = MULTI_SPACE.sub(" ", text)
    text = SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = REPEATED_PUNCT.sub(r"\1", text)
    return unicodedata.normalize("NFC", text).strip()


URDU_LETTERS = re.compile(r"[؀-ۿ]")
LATIN_LETTERS = re.compile(r"[A-Za-z]")


def script_profile(text: str) -> dict:
    """Counts used by derive.py's filters: how much of the text is Arabic-script vs Latin vs other."""
    letters = [c for c in text if c.isalpha()]
    return {"letters": len(letters), "urdu": sum(bool(URDU_LETTERS.match(c)) for c in letters),
            "latin": sum(bool(LATIN_LETTERS.match(c)) for c in letters)}


if __name__ == "__main__":
    import sys
    for line in sys.stdin:
        print(normalize_urdu(line))
