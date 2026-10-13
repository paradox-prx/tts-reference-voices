from studio.tags import parse_tag, strip_tags, validate_text, TagError, leading_tags
from studio.text import split_sentences, plan_parts, apply_delivery, estimate_seconds
from studio.tags import tag
import pytest


def test_split_latin_and_urdu():
    s = split_sentences("Hello there. How are you? Fine! آپ کیسے ہیں؟ میں ٹھیک ہوں۔ شکریہ!")
    assert s == ["Hello there.", "How are you?", "Fine!", "آپ کیسے ہیں؟", "میں ٹھیک ہوں۔", "شکریہ!"]


def test_split_keeps_decimals_and_no_space_urdu():
    assert split_sentences("Price is 3.5 dollars. Ok") == ["Price is 3.5 dollars.", "Ok"]
    assert split_sentences("پہلا جملہ۔دوسرا جملہ؟") == ["پہلا جملہ۔", "دوسرا جملہ؟"]


def test_split_newlines_and_tags_stay_with_sentence():
    s = split_sentences("<|emotion:anger|>Stop it. <|prosody:pause|>Now\nNext line")
    assert s == ["<|emotion:anger|>Stop it.", "<|prosody:pause|>Now", "Next line"]


def test_mixed_rtl_with_latin_words():
    s = split_sentences("آپ کا package unlimited ہے۔ Thank you sir!")
    assert s == ["آپ کا package unlimited ہے۔", "Thank you sir!"]


def test_tag_validation():
    assert validate_text("<|emotion:anger|>Hi.") == []
    assert any("unknown emotion" in e for e in validate_text("<|emotion:angry|>Hi."))
    assert any("unknown tag category" in e for e in validate_text("<|mood:happy|>Hi."))
    assert any("followed directly" in e for e in validate_text("Well <|sfx:laughter|>"))
    assert validate_text("<|sfx:laughter|>Haha that was good.") == []
    with pytest.raises(TagError):
        parse_tag("<|prosody:speed_ultra|>")
    assert strip_tags("<|emotion:joy|>Hi <|sfx:cough|>Ahem there.") == "Hi Ahem there."


def test_leading_tags():
    tags, rest = leading_tags("<|emotion:anger|><|prosody:speed_fast|>Go now.")
    assert [str(t) for t in tags] == ["<|emotion:anger|>", "<|prosody:speed_fast|>"] and rest == "Go now."


def test_delivery_strength():
    tx = "First one. <|emotion:sadness|>Second one. Third one."
    d = [tag("emotion", "elation"), tag("prosody", "speed_fast")]
    assert apply_delivery(tx, d, "none") == tx
    light = apply_delivery(tx, d, "light")
    assert light.startswith("<|emotion:elation|><|prosody:speed_fast|>First one.") and light.count("<|") == 3
    assert apply_delivery(tx, d, "strong") == (
        "<|emotion:elation|><|prosody:speed_fast|>First one. "
        "<|emotion:sadness|><|prosody:speed_fast|>Second one. "
        "<|emotion:sadness|><|prosody:speed_fast|>Third one.")


def test_plan_parts_limits_and_carries_tags():
    sent = "This sentence takes a little while to say out loud. "
    text = "<|emotion:sadness|><|style:whispering|>" + sent * 12 + "<|prosody:pause|>" + sent * 4
    parts = plan_parts(text, max_part_s=10, s_per_letter=0.08)
    assert len(parts) > 2
    assert all(p.est_s <= 10.5 for p in parts)
    for p in parts:  # every part restates the state in force
        assert p.text.startswith("<|") and "<|emotion:sadness|>" in p.text and "<|style:whispering|>" in p.text
    # the one-off pause is not carried
    assert sum(p.text.count("<|prosody:pause|>") for p in parts) == 1
    joined = " ".join(strip_tags(s) for p in parts for s in p.sentences)
    assert joined.count("This sentence") == 16


def test_plan_parts_splits_one_long_sentence():
    long = ("word " * 120).strip() + "."
    parts = plan_parts(long, max_part_s=8, s_per_letter=0.08)
    assert len(parts) >= 3 and all(p.est_s <= 9 for p in parts)
    assert sum(len(strip_tags(p.text).split()) for p in parts) == 120


def test_estimate_scales_with_text():
    assert 0 < estimate_seconds("short.") < estimate_seconds("a much longer sentence than the short one.")
