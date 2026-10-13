import random

import pytest

from studio.jobs import merge_config, row_text
from studio.tags import TagError


def cfg(**tags):
    return merge_config({"tags": tags})


def test_keep_mode_applies_the_rows_tags_column():
    row = {"text": "First one. Second one.", "tags_in": "emotion:sadness"}
    text, applied = row_text(row, cfg(mode="keep", strength="light"), random.Random(0))
    assert text == "<|emotion:sadness|>First one. Second one."
    assert applied == "emotion:sadness"


def test_keep_mode_strong_repeats_on_every_sentence():
    row = {"text": "First one. Second one.", "tags_in": "emotion:sadness"}
    text, _ = row_text(row, cfg(mode="keep", strength="strong"), random.Random(0))
    assert text == "<|emotion:sadness|>First one. <|emotion:sadness|>Second one."


def test_none_mode_ignores_tags_column_but_keeps_inline_tags():
    row = {"text": "<|emotion:anger|>Stop it.", "tags_in": "emotion:sadness"}
    text, applied = row_text(row, cfg(mode="none"), random.Random(0))
    assert text == "<|emotion:anger|>Stop it." and applied == ""


def test_strip_mode_removes_inline_tags():
    text, applied = row_text({"text": "<|emotion:anger|>Stop it.", "tags_in": ""}, cfg(mode="strip"), random.Random(0))
    assert text == "Stop it." and applied == ""


def test_random_mode_draws_from_pool_and_is_reproducible():
    c = cfg(mode="random", random_pct=100, pool=["emotion:relief", "style:whispering"])
    a = row_text({"text": "Hello there.", "tags_in": ""}, c, random.Random("7:3"))
    b = row_text({"text": "Hello there.", "tags_in": ""}, c, random.Random("7:3"))
    assert a == b and a[1] in ("emotion:relief", "style:whispering")


def test_invalid_tags_raise():
    with pytest.raises(TagError):
        row_text({"text": "x", "tags_in": "emotion:sleepy"}, cfg(mode="keep"), random.Random(0))
