"""Higgs Audio v3 inline control tags: the vocabulary, parsing, validation and placement.

A tag is `<|category:value|>` and is read at the start of a sentence. sfx tags must be followed directly by their
onomatopoeia (`<|sfx:laughter|>Haha`).
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass

VOCAB: dict[str, tuple[str, ...]] = {
    "emotion": ("affection", "amusement", "anger", "arousal", "awe", "bitterness", "confusion", "contemplation",
                "contentment", "determination", "disgust", "elation", "enthusiasm", "fear", "helplessness", "longing",
                "pride", "relief", "sadness", "shame", "surprise"),
    "prosody": ("speed_very_slow", "speed_slow", "speed_fast", "speed_very_fast", "pitch_low", "pitch_high",
                "expressive_high", "expressive_low", "pause", "long_pause"),
    "style": ("singing", "shouting", "whispering"),
    "sfx": ("cough", "laughter", "crying", "screaming", "burping", "humming", "sigh", "sniff", "sneeze"),
}
# default onomatopoeia inserted after an sfx tag (the user edits it)
SFX_SOUND = {"cough": "Ahem", "laughter": "Haha", "crying": "Huhuhu", "screaming": "Aaah", "burping": "Burp",
             "humming": "Hmm hmm", "sigh": "Haah", "sniff": "Sniff", "sneeze": "Achoo"}
# prosody tags that describe a state (carried into later parts); pause / long_pause are one-off events
PROSODY_GROUPS = {"speed": ("speed_very_slow", "speed_slow", "speed_fast", "speed_very_fast"),
                  "pitch": ("pitch_low", "pitch_high"), "expressive": ("expressive_high", "expressive_low")}
EVENT_TAGS = {("prosody", "pause"), ("prosody", "long_pause")}

TAG_RE = re.compile(r"<\|\s*([A-Za-z_]+)\s*:\s*([A-Za-z_]+)\s*\|>")
ANY_TAG_RE = re.compile(r"<\|[^|<>]*\|>")  # anything tag-shaped, valid or not


@dataclass(frozen=True)
class Tag:
    category: str
    value: str

    def __str__(self) -> str:
        return f"<|{self.category}:{self.value}|>"

    @property
    def slot(self) -> str:
        """The 'state' a tag sets: emotion, style, speed, pitch, expressive. Events (pause, sfx) have no slot."""
        if self.category == "prosody":
            for group, values in PROSODY_GROUPS.items():
                if self.value in values:
                    return group
            return ""
        return self.category if self.category in ("emotion", "style") else ""


class TagError(ValueError):
    pass


def parse_tag(token: str) -> Tag:
    m = TAG_RE.fullmatch(token.strip())
    if not m:
        raise TagError(f"not a tag: {token!r} (expected <|category:value|>)")
    cat, val = m.group(1).lower(), m.group(2).lower()
    if cat not in VOCAB:
        raise TagError(f"unknown tag category {cat!r} in {token!r}; valid: {', '.join(VOCAB)}")
    if val not in VOCAB[cat]:
        raise TagError(f"unknown {cat} value {val!r} in {token!r}; valid: {', '.join(VOCAB[cat])}")
    return Tag(cat, val)


def tag(category: str, value: str) -> Tag:
    return parse_tag(f"<|{category}:{value}|>")


def find_tags(text: str) -> list[tuple[int, int, str]]:
    """(start, end, token) of every tag-shaped token in text, valid or not."""
    return [(m.start(), m.end(), m.group(0)) for m in ANY_TAG_RE.finditer(text)]


def validate_text(text: str) -> list[str]:
    """Problems with the tags in a text (empty list = valid): unknown tags, malformed tokens, and sfx tags not followed
    by an onomatopoeia."""
    errors = []
    for start, end, tok in find_tags(text):
        try:
            t = parse_tag(tok)
        except TagError as e:
            errors.append(str(e))
            continue
        if t.category == "sfx":
            rest = text[end:]
            nxt = re.match(r"\s*(<\|[^|]*\|>)?\s*(\S?)", rest)
            if not rest.strip() or rest.lstrip().startswith("<|") or (nxt and not nxt.group(2)):
                errors.append(f"{tok} must be followed directly by its sound, e.g. {tok}{SFX_SOUND[t.value]}")
    return errors


def strip_tags(text: str) -> str:
    out = ANY_TAG_RE.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", out).strip()


def leading_tags(sentence: str) -> tuple[list[Tag], str]:
    """Valid tags at the very start of a sentence and the rest of it."""
    tags, rest = [], sentence.lstrip()
    while True:
        m = TAG_RE.match(rest)
        if not m:
            break
        try:
            t = parse_tag(m.group(0))
        except TagError:
            break
        if t.category == "sfx":  # an sfx tag belongs with its sound, so it stays in the body
            break
        tags.append(t)
        rest = rest[m.end():].lstrip()
    return tags, rest


def merge_state(state: dict[str, Tag], tags: list[Tag]) -> dict[str, Tag]:
    """Tags in force after applying `tags` on top of `state` (one per slot)."""
    new = dict(state)
    for t in tags:
        if t.slot:
            new[t.slot] = t
    return new


def render(tags: list[Tag]) -> str:
    return "".join(str(t) for t in tags)


def parse_tag_list(spec: str | list | None) -> list[Tag]:
    """'emotion:anger, prosody:speed_fast' or '<|emotion:anger|><|style:shouting|>' or a list of either."""
    if not spec:
        return []
    items = spec if isinstance(spec, list) else re.split(r"[,\s;]+|(?<=\|>)(?=<\|)", spec)
    out = []
    for it in items:
        it = str(it).strip()
        if not it:
            continue
        out.append(parse_tag(it if it.startswith("<|") else f"<|{it}|>"))
    return out


def random_tags(rng: random.Random, pool: list[Tag], k: int = 1) -> list[Tag]:
    """Up to k tags from the pool, at most one per slot, no sfx (sfx needs a sound)."""
    cands = [t for t in pool if t.category != "sfx"]
    rng.shuffle(cands)
    out, slots = [], set()
    for t in cands:
        key = t.slot or str(t)
        if key in slots:
            continue
        slots.add(key)
        out.append(t)
        if len(out) >= k:
            break
    return out
