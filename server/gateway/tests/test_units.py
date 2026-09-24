from __future__ import annotations

import asyncio
import io
import json
import struct
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from pydantic import ValidationError

from conftest import write_voice
from tts_gateway import audio
from tts_gateway.admission import Admission, QueueFull, QueueTimeout
from tts_gateway.backends import create_backend
from tts_gateway.backends.stub import StubBackend
from tts_gateway.config import Settings
from tts_gateway.config import REPO_ROOT
from tts_gateway.textproc import (
    PaceBand,
    count_letters,
    count_words,
    detect_lang,
    language_band,
    max_new_tokens_for,
    split_for_ceiling,
    split_sentences,
    voice_band,
)
from tts_gateway.voices import VoiceRegistry, load_pace, normalize_language

REAL_VOICES = REPO_ROOT / "voices"


# ------------------------------------------------------------------------------------------------ textproc

def test_count_words_english_and_urdu() -> None:
    assert count_words("Hello, world! It's 2026 — really.") == 5
    assert count_words("السلام علیکم۔ آپ کیسے ہیں؟") == 5
    assert count_words("  ... — !!  ") == 0


def test_split_sentences() -> None:
    assert split_sentences("Hello world. How are you?\nFine! Pi is 3.14 today.") == [
        "Hello world.", "How are you?", "Fine!", "Pi is 3.14 today."]
    assert split_sentences("السلام علیکم۔ آپ کیسے ہیں؟ ٹھیک") == ["السلام علیکم۔", "آپ کیسے ہیں؟", "ٹھیک"]
    assert split_sentences('He said "stop." Then left.') == ['He said "stop."', "Then left."]


def test_detect_lang() -> None:
    assert detect_lang("Hello there") == "en"
    assert detect_lang("السلام علیکم") == "ur"
    assert detect_lang("你好") == "und"


def test_max_new_tokens_formula_and_clamp() -> None:
    assert max_new_tokens_for(1) == 96  # 72 frames, raised to the floor
    assert max_new_tokens_for(10) == 180  # 10 / 2.5 * 12.5 * 2.4 + 60
    assert max_new_tokens_for(1000) == 4096


def test_count_letters() -> None:
    assert count_letters("Hello, world! 2026") == 14
    assert count_letters("السلام علیکم۔") == 11  # the Urdu full stop and the space don't count
    assert count_letters("پُرعزم") == 5  # the damma (a combining mark) doesn't count


def test_language_band_keeps_the_absolute_seconds_per_word_limits() -> None:
    settings = Settings(auth_disabled=True)
    en = language_band("en", settings)
    assert en is not None and en.unit == "word" and language_band("und", settings) is None
    assert en.reason(en.ratio(0.4 * 10, 10, 50)) is None
    assert en.reason(en.ratio(0.1 * 10, 10, 50)) == "too_short" and en.reason(en.ratio(1.5 * 10, 10, 50)) == "too_long"
    assert en.ratio(0.18 * 10, 10, 50) * en.expected * 10 == pytest.approx(1.8)  # the band edge maps back exactly


def test_voice_band_is_relative_to_the_expected_pace() -> None:
    band = voice_band(0.088, Settings(auth_disabled=True))  # the shehbaz prior (s/letter)
    assert band == PaceBand("letter", 0.088, 0.6, 1.8)
    # the four known Kaggle Urdu failures (s/word 0.22, 0.25, 1.01, 1.01; 3.29 letters/word): the two long ones are
    # caught; the 15-25% truncations are not (they need the QC sidecar's ASR checks)
    ratios = [band.ratio(spw * 100, 100, 329) for spw in (0.22, 0.25, 1.01, 1.01)]
    assert [band.reason(r) for r in ratios] == [None, None, "too_long", "too_long"]
    assert band.reason(band.ratio(0.29 * 100, 100, 329)) is None  # a good take
    assert PaceBand.distance(1.1) < PaceBand.distance(0.5)


def test_split_for_ceiling() -> None:
    text = "One two three. Four five six. Seven eight."
    assert split_for_ceiling(text, 4) == ["One two three.", "Four five six.", "Seven eight."]
    assert split_for_ceiling(text, 6) == ["One two three. Four five six.", "Seven eight."]
    assert split_for_ceiling("a b c d e f g", 3) == ["a b c", "d e f", "g"]


# ------------------------------------------------------------------------------------------------ audio

def _chunks(wav: bytes) -> dict[bytes, bytes]:
    pos, out = 12, {}
    while pos + 8 <= len(wav):
        cid, size = wav[pos:pos + 4], struct.unpack("<I", wav[pos + 4:pos + 8])[0]
        out[cid] = wav[pos + 8:pos + 8 + size]
        pos += 8 + size + (size & 1)
    return out


def test_wav_roundtrip_with_label() -> None:
    pcm = (np.arange(4800, dtype="<i2") % 100).tobytes()
    wav = audio.pcm_to_wav(pcm, 24000)
    assert struct.unpack("<I", wav[4:8])[0] == len(wav) - 8
    chunks = _chunks(wav)
    assert list(chunks) == [b"fmt ", b"LIST", b"data"]  # the label comes before the data
    assert audio.AI_LABEL.encode() in chunks[b"LIST"]
    data, sr = sf.read(io.BytesIO(wav), dtype="int16")
    assert sr == 24000 and data.tobytes() == pcm
    assert audio.wav_to_pcm(wav) == (pcm, 24000)


def test_streaming_wav_header() -> None:
    header = audio.wav_header(24000)
    assert header[:4] == b"RIFF" and struct.unpack("<I", header[4:8])[0] == audio.STREAM_SIZE
    assert header[-8:-4] == b"data" and struct.unpack("<I", header[-4:])[0] == audio.STREAM_SIZE
    assert b"ICMT" in header
    pcm = bytes(960)
    assert audio.wav_to_pcm(header + pcm) == (pcm, 24000)


def test_flac_label_and_duration() -> None:
    pcm = np.zeros(12000, dtype="<i2").tobytes()
    flac = audio.encode(pcm, 24000, "flac")
    with sf.SoundFile(io.BytesIO(flac)) as f:
        assert f.format == "FLAC" and f.frames == 12000 and f.comment == audio.AI_LABEL
    assert audio.duration_s(len(pcm), 24000) == 0.5
    assert audio.silence(0.1, 24000) == bytes(4800)


# ------------------------------------------------------------------------------------------------ voices

def test_registry_loads_and_validates(tmp_path: Path) -> None:
    root = tmp_path / "voices"
    write_voice(root, "good", "en", "Reference text.")
    write_voice(root, "urdu", "ur", "حوالہ۔")
    write_voice(root, "badsha", "en", "Text.", sha256="0" * 64)
    write_voice(root, "tooshort", "en", "Text.", seconds=0.5)
    write_voice(root, "BadName", "en", "Text.")
    nokey = write_voice(root, "nokey", "en", "Text.")
    (nokey / "references" / "references.json").write_text(json.dumps({"higgs-v3": {}}))
    reg = VoiceRegistry.load(root)
    assert sorted(v.id for v in reg) == ["good", "urdu"]
    assert set(reg.errors) == {"badsha", "tooshort", "BadName", "nokey"}
    assert "sha256 mismatch" in reg.errors["badsha"]
    good, urdu = reg.get("good"), reg.get("URDU")
    assert good and urdu
    assert good.language == "English" and urdu.language == "Auto"
    assert good.data_url.startswith("data:audio/wav;base64,") and good.ref_seconds == 2.0
    assert good.ref_audio == (root / "good" / "references" / "qwen3-tts.wav").read_bytes()


def test_normalize_language() -> None:
    assert normalize_language("en") == "English"
    assert normalize_language("Urdu") == "Auto"
    assert normalize_language("german") == "German"


@pytest.mark.skipif(not REAL_VOICES.is_dir(), reason="reference voices not present")
def test_real_voices_load() -> None:
    reg = VoiceRegistry.load(REAL_VOICES)
    trump, shehbaz = reg.get("trump"), reg.get("shehbaz")
    assert trump and shehbaz and not reg.errors
    assert trump.language == "English" and shehbaz.language == "Auto"
    assert trump.pace_source == "reference" and trump.pace == pytest.approx(0.0795, abs=1e-3)
    calibrated = VoiceRegistry.load(REAL_VOICES, load_pace(REPO_ROOT / "server" / "calibration" / "pace.json"))
    shehbaz = calibrated.get("shehbaz")
    assert shehbaz and shehbaz.pace_source == "calibration" and shehbaz.pace < 0.12  # not the slow clip's 0.183


def test_pace_file_and_overrides(tmp_path: Path) -> None:
    pace_file = tmp_path / "pace.json"
    pace_file.write_text(json.dumps({"_doc": "comment", "alice": {"s_per_letter": 0.07}, "bilal": 0.09}))
    assert load_pace(pace_file, {"bilal": 0.1}) == {"alice": (0.07, "calibration"), "bilal": (0.1, "override")}
    assert load_pace(tmp_path / "missing.json") == {}
    root = tmp_path / "voices"
    write_voice(root, "alice", "en", "This is a reference sentence.", seconds=2.4)
    write_voice(root, "carol", "en", "Twelve letters", seconds=1.2)
    reg = VoiceRegistry.load(root, load_pace(pace_file))
    alice, carol = reg.get("alice"), reg.get("carol")
    assert alice and alice.pace == 0.07 and alice.pace_source == "calibration"
    assert carol and carol.pace == pytest.approx(1.2 / 13) and carol.pace_source == "reference"
    assert Settings(auth_disabled=True, pace="Alice=0.08, bilal=0.1").pace == {"alice": 0.08, "bilal": 0.1}
    with pytest.raises(ValidationError):
        Settings(auth_disabled=True, pace="alice=0")
    with pytest.raises(ValidationError):
        Settings(auth_disabled=True, pace="alice")


# ------------------------------------------------------------------------------------------------ admission

async def test_admission_queue_full_timeout_and_cancel() -> None:
    adm = Admission(max_inflight=1, max_queue=1, timeout_s=0.2)
    first = await adm.acquire()
    assert adm.inflight == 1
    waiter = asyncio.create_task(adm.acquire())
    await asyncio.sleep(0.01)
    assert adm.waiting == 1
    with pytest.raises(QueueFull) as full:
        await adm.acquire()
    assert full.value.retry_after_s >= 1
    waiter.cancel()  # a cancelled waiter leaves no trace
    with pytest.raises(asyncio.CancelledError):
        await waiter
    assert adm.waiting == 0
    with pytest.raises(QueueTimeout):
        await adm.acquire()
    assert adm.waiting == 0
    first.release()
    first.release()  # idempotent
    assert adm.inflight == 0
    async with adm.slot() as slot:
        assert adm.inflight == 1 and slot.waited_s < 0.1
    assert adm.inflight == 0


# ------------------------------------------------------------------------------------------------ config

def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TTS_API_KEY", "a, b ,")
    monkeypatch.setenv("TTS_SPW_UR", "0.2,1.2")
    monkeypatch.setenv("TTS_RETRY_ON", "suspect")
    monkeypatch.setenv("TTS_DEFAULT_TEMPERATURE", "none")
    s = Settings()
    assert s.api_keys == ["a", "b"] and s.spw_ur == (0.2, 1.2) and s.retry_on == {"suspect"}
    assert s.default_temperature is None and s.spw_en == (0.18, 0.9)


def test_settings_require_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="TTS_API_KEY"):
        Settings()
    monkeypatch.setenv("TTS_RETRY_ON", "suspect,sometimes")
    with pytest.raises(ValidationError, match="unknown retry reasons"):
        Settings(auth_disabled=True)


# ------------------------------------------------------------------------------------------------ backends

def test_backend_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TTS_STUB_SUSPECT_TAKES", "2")
    monkeypatch.setenv("TTS_STUB_MAX_SECONDS_PER_CALL", "30")
    stub = create_backend(Settings(auth_disabled=True, backend="stub"), VoiceRegistry([]))
    assert isinstance(stub, StubBackend)
    assert stub.suspect_takes == 2 and stub.capabilities.max_seconds_per_call == 30
    with pytest.raises(NotImplementedError, match="Higgs"):
        create_backend(Settings(auth_disabled=True, backend="higgs_sglang"), VoiceRegistry([]))
