"""Normalizers, detectors and audio I/O (no models)."""
from __future__ import annotations

import base64

import numpy as np
import pytest

from tts_qc import paths
from tts_qc.audio import AudioError, pcm16_from_b64, read_wav, to_16k, trim_16k
from tts_qc.checks import Vad, Word, audio_checks, text_checks, word_timing_checks
from tts_qc.textnorm import UrduNormalizer, count_letters, normalizer, nospace, script_fractions
from tts_qc.voices import resolve_voice

SR = 24_000


def tone(seconds: float, sr: int = SR, amp: float = 0.3) -> np.ndarray:
    t = np.arange(int(seconds * sr)) / sr
    return (amp * 32767 * np.sin(2 * np.pi * 220 * t)).astype(np.int16)


def silence(seconds: float, sr: int = SR) -> np.ndarray:
    return np.zeros(int(seconds * sr), np.int16)


def test_urdu_normalizer_folds_variants_and_is_idempotent() -> None:
    un = UrduNormalizer()
    assert un("پُرعزم") == "پرعزم"                        # harakat stripped, word not split
    assert un("كيا") == un("کیا")                          # Arabic kaf / yeh folded to Urdu
    assert un("گۓ") == "گئے"
    assert un("۱۲۳، ٹھیک ہے۔") == "123 ٹھیک ہے"
    text = "بدقسمتی سے پورا خطہ، بشمول ایران اور مشرقِ وسطیٰ، اس وقت شدید جنگی صورتحال کی لپیٹ میں ہے۔"
    assert un(un(text)) == un(text)
    assert nospace("صورت حال") == nospace("صورتحال")


def test_english_normalizer_numbers() -> None:
    en = normalizer("en")
    assert en("The Prime Minister said thirty million lives.") == en("the prime minister said 30 million lives")
    with pytest.raises(ValueError):
        normalizer("fr")


def test_letters_and_scripts() -> None:
    assert count_letters("Hello, world! 42") == 12
    assert count_letters("پُرعزم۔") == 5                   # the zamma is a combining mark, not a letter
    assert script_fractions("یہ test ہے")["latin"] == pytest.approx(4 / 8)


def test_text_checks_catch_loop_and_skip() -> None:
    un = UrduNormalizer()
    ref = un("میں آج ایک نہایت سنجیدہ صورتحال کے بارے میں آپ سے مخاطب ہوں اور یہ بہت اہم ہے۔")
    good = text_checks(ref, ref)
    assert (good["del_run"], good["ins_run"], good["repeat_excess"], good["char_ratio"]) == (0, 0, 0, 1.0)
    loop = text_checks(ref, un("میں آج ایک ایک ایک ایک ایک ایک نہایت سنجیدہ صورتحال کے بارے میں آپ سے مخاطب ہوں آآآآآ"))
    assert loop["token_run"] == 6 and loop["repeat_excess"] >= 4 and loop["char_runs"] == 1
    skip = text_checks(ref, un("میں آج ایک نہایت سنجیدہ اور یہ بہت اہم ہے"))
    assert skip["del_run"] >= 4 and skip["char_ratio"] < 0.85


def test_audio_checks_measure_silences() -> None:
    wav = np.concatenate([silence(1.2), tone(2), silence(3), tone(2), silence(2)])
    a = audio_checks(wav, SR)
    assert a["lead_sil_s"] == pytest.approx(1.2, abs=0.05)
    assert a["max_internal_sil_s"] == pytest.approx(3.0, abs=0.05)
    assert a["trail_sil_s"] == pytest.approx(2.0, abs=0.05)
    assert a["speech_ratio"] == pytest.approx(4 / 10.2, abs=0.02)
    assert audio_checks(silence(1), SR)["speech_ratio"] == 0.0


def test_word_timing_separates_voiced_loop_from_pause() -> None:
    wav = np.concatenate([tone(6), silence(4), tone(1)])
    vad = Vad.compute(wav, SR)
    loop = word_timing_checks([Word(0.0, 0.5, " a"), Word(0.5, 5.5, " b"), Word(10.0, 10.8, " c")], vad)
    pause = word_timing_checks([Word(0.0, 2.0, " a"), Word(2.0, 5.5, " b"), Word(5.5, 10.5, " c"),
                                Word(10.5, 11.0, " d")], vad)
    assert loop["max_word_s"] == 5.0 and loop["max_word_voiced"] > 0.9
    assert pause["max_word_s"] == 5.0 and pause["max_word_voiced"] < 0.3
    # an English-style skipped loop: no word covers 1.0-5.5 s although it is voiced
    skipped = word_timing_checks([Word(0.0, 1.0, " a"), Word(5.5, 6.0, " b"), Word(10.0, 11.0, " c")], vad)
    assert skipped["max_gap_s"] == 4.5 and skipped["max_gap_voiced"] > 0.9 and skipped["max_gap_at_s"] == 1.0
    assert pause["max_gap_s"] == 0.0


def test_pcm_b64_validation() -> None:
    pcm = tone(0.1)
    assert np.array_equal(pcm16_from_b64(base64.b64encode(pcm.tobytes()).decode()), pcm)
    with pytest.raises(AudioError):
        pcm16_from_b64("not base64 !!")
    with pytest.raises(AudioError):
        pcm16_from_b64(base64.b64encode(b"\x00\x01\x02").decode())


def test_resampler_matches_faster_whisper_decode_audio() -> None:
    """HTTP PCM and bench WAV files reach Whisper as the same 16 kHz array faster-whisper builds from a file."""
    from faster_whisper import decode_audio

    path = paths.voices_dir() / "shehbaz" / "shehbaz_01.wav"           # 48 kHz
    pcm, sr = read_wav(path)
    ours = to_16k(pcm, sr)
    ref = decode_audio(str(path), sampling_rate=16000)
    assert sr == 48000 and abs(len(ours) - len(ref)) <= 16
    n = min(len(ours), len(ref))
    assert np.abs(ours[:n] - ref[:n]).max() < 1e-3
    assert len(trim_16k(ours, 1.0, 1.0)) == len(ours) - 2 * int(0.9 * 16000)


def test_engine_voice_names_resolve_to_repo_voices() -> None:
    known = ["trump", "shehbaz"]
    assert resolve_voice("trump", known) == "trump"
    assert resolve_voice("trump-avg", known) == "trump" and resolve_voice("shehbaz-prompt", known) == "shehbaz"
    assert resolve_voice("shehbaz-3f9a0c1b2d", known) == "shehbaz"
    assert resolve_voice("trump-avg-3f9a0c1b2d", known) == "trump"
    assert resolve_voice("trumpet", known) is None and resolve_voice("", known) is None
    assert resolve_voice("nobody-avg", known) is None and resolve_voice("trump-xyz", known) is None
