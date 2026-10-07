"""Sentence splitting, delivery-tag placement, duration estimates and part planning (shared by both consoles).

Higgs generates at most ~30 s per request, so longer texts are split at sentence boundaries into parts of at most
`max_part_s` estimated seconds. Tags in force at a part's start are restated at its beginning, so every part keeps the
delivery.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .tags import EVENT_TAGS, Tag, leading_tags, merge_state, render, strip_tags

# a sentence ends after . ! ? (followed by space/quote/end) or after Urdu ۔ ؟ and the Arabic ! ؛ (no space needed)
_SENT_END = re.compile(r"""(?:(?<=[.!?])(?=["'”’)\]]*(?:\s|$))|(?<=[۔؟؛]))["'”’)\]]*\s*""")
_CLAUSE_END = re.compile(r"(?<=[,،;:])\s+")
LETTER_RE = re.compile(r"\w", re.UNICODE)

DEFAULT_S_PER_LETTER = 0.075   # fallback when a voice's own pace is unknown (~13 letters/s)
SENTENCE_PAUSE_S = 0.25


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("‌", "").replace("​", "")
    return re.sub(r"[ \t]+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    """Sentences (with their punctuation and leading tags). Newlines also end a sentence."""
    out = []
    for line in normalize(text).split("\n"):
        line = line.strip()
        if not line:
            continue
        start = 0
        for m in _SENT_END.finditer(line):
            if m.end() <= start:
                continue
            piece = line[start:m.end()].strip()
            if strip_tags(piece):
                out.append(piece)
                start = m.end()
        tail = line[start:].strip()
        if tail:
            if out and not strip_tags(tail):  # dangling tags at the very end: attach to the previous sentence
                out[-1] += " " + tail
            else:
                out.append(tail)
    return out


def letters(text: str) -> int:
    return len(LETTER_RE.findall(strip_tags(text)))


def estimate_seconds(text: str, s_per_letter: float = DEFAULT_S_PER_LETTER, speed: float = 1.0) -> float:
    n_sent = max(1, len(split_sentences(text)))
    return (letters(text) * s_per_letter + (n_sent - 1) * SENTENCE_PAUSE_S) / max(0.3, speed)


SPEED_FACTOR = {"speed_very_slow": 0.7, "speed_slow": 0.85, "speed_fast": 1.15, "speed_very_fast": 1.3}


def speed_of(tags: dict[str, Tag]) -> float:
    t = tags.get("speed")
    return SPEED_FACTOR.get(t.value, 1.0) if t else 1.0


def apply_delivery(text: str, delivery: list[Tag], strength: str = "light") -> str:
    """Place delivery tags in a text.

    none   leave the text exactly as written (its own inline tags only)
    light  the delivery tags once, at the start of the first sentence (the text's own tags still change the mood)
    strong restate every tag in force (delivery + the text's own) at the start of every sentence
    """
    if strength not in ("none", "light", "strong"):
        raise ValueError(f"tag strength must be none, light or strong, not {strength!r}")
    sentences = split_sentences(text)
    if strength == "none" or not sentences:
        return " ".join(sentences)
    if strength == "light":
        if not delivery:
            return " ".join(sentences)
        own, rest = leading_tags(sentences[0])
        state = merge_state(merge_state({}, delivery), own)  # the text's own tags win over the preset
        events = [t for t in own if not t.slot]
        sentences[0] = (render(list(state.values()) + events) + rest).strip()
        return " ".join(sentences)
    out, state = [], merge_state({}, delivery)
    for s in sentences:
        own, rest = leading_tags(s)
        state = merge_state(state, own)
        events = [t for t in own if (t.category, t.value) in EVENT_TAGS]
        out.append((render(list(state.values()) + events) + rest).strip())
    return " ".join(out)


@dataclass
class Part:
    text: str                 # what is sent to the engine (tags in force restated at the start)
    est_s: float
    sentences: list[str] = field(default_factory=list)


def _split_long(sentence: str, max_s: float, spl: float) -> list[str]:
    """A sentence longer than max_s: split at clause punctuation, then at word boundaries."""
    if estimate_seconds(sentence, spl) <= max_s:
        return [sentence]
    pieces = [p for p in _CLAUSE_END.split(sentence) if p.strip()]
    if len(pieces) == 1:
        words, pieces, cur = sentence.split(), [], []
        for w in words:
            if cur and estimate_seconds(" ".join(cur + [w]), spl) > max_s:
                pieces.append(" ".join(cur))
                cur = []
            cur.append(w)
        if cur:
            pieces.append(" ".join(cur))
        return pieces
    out, cur = [], ""
    for p in pieces:
        cand = f"{cur} {p}".strip()
        if cur and estimate_seconds(cand, spl) > max_s:
            out.extend(_split_long(cur, max_s, spl))
            cur = p
        else:
            cur = cand
    if cur:
        out.extend(_split_long(cur, max_s, spl))
    return out


def plan_parts(text: str, max_part_s: float = 25.0, s_per_letter: float = DEFAULT_S_PER_LETTER) -> list[Part]:
    """Greedy packing of sentences into parts of at most max_part_s estimated seconds, restating the tags in force
    at each part's start. A single sentence over the limit is split at commas, then at word boundaries."""
    units: list[tuple[str, dict[str, Tag]]] = []  # (sentence body with its own leading tags, state before it)
    state: dict[str, Tag] = {}
    for s in split_sentences(text):
        own, rest = leading_tags(s)
        before = dict(state)
        state = merge_state(state, own)
        chunks = _split_long(s, max_part_s, s_per_letter)
        for i, c in enumerate(chunks):
            # a split sentence: later chunks start with the sentence's state, without its one-off events
            units.append((c if i == 0 else render(list(state.values())) + c, before if i == 0 else dict(state)))
    parts: list[Part] = []
    cur: list[str] = []
    cur_state: dict[str, Tag] = {}
    for body, before in units:
        cand = cur + [body]
        if cur and estimate_seconds(" ".join(cand), s_per_letter) > max_part_s:
            parts.append(_mk_part(cur, cur_state, s_per_letter))
            cur, cur_state = [body], before
        else:
            if not cur:
                cur_state = before
            cur = cand
    if cur:
        parts.append(_mk_part(cur, cur_state, s_per_letter))
    return parts


def _mk_part(sentences: list[str], state_before: dict[str, Tag], spl: float) -> Part:
    first_own, first_rest = leading_tags(sentences[0])
    carried = merge_state(state_before, first_own)
    events = [t for t in first_own if not t.slot]
    head = (render(list(carried.values()) + events) + first_rest).strip()
    text = " ".join([head] + sentences[1:])
    return Part(text=text, est_s=round(estimate_seconds(text, spl), 2), sentences=sentences)
