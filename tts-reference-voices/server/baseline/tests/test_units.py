"""Units: WAV label parity with the gateway, the real repo voices, reference keys, codec budget, CLI defaults."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

import numpy as np
import pytest

import engine as eng
import qwen_tts_server as srv
from conftest import wav_bytes
from wavlabel import AI_LABEL, float_to_pcm16, pcm_to_wav, wav_comment, wav_pcm16

REPO = Path(__file__).resolve().parents[3]


def test_wav_label_roundtrip():
    pcm = float_to_pcm16(np.array([0.0, 0.5, -1.0, 2.0], dtype=np.float32))
    assert np.frombuffer(pcm, "<i2").tolist() == [0, 16384, -32767, 32767]   # clipped, round(x * 32767)
    wav = pcm_to_wav(pcm, 24000)
    assert wav_comment(wav) == AI_LABEL
    assert wav_pcm16(wav) == (pcm, 24000)
    assert AI_LABEL == "AI-generated speech (Qwen3-TTS voice clone). Not a real recording."


def test_wav_bytes_identical_to_gateway_helper():
    path = REPO / "server" / "gateway" / "tts_gateway" / "audio.py"
    if not path.is_file():
        pytest.skip("gateway package not present")
    spec = importlib.util.spec_from_file_location("gateway_audio", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for n in (0, 1, 2, 4801):
        pcm = bytes(range(256)) * (n // 256) + bytes(n % 256)
        pcm = pcm[: n - n % 2]
        assert pcm_to_wav(pcm, 24000) == mod.pcm_to_wav(pcm, 24000)
    assert AI_LABEL == mod.AI_LABEL


def test_real_repo_voices():
    voices = {v.id: v for v in eng.load_repo_voices(REPO / "voices")}
    assert {"trump", "shehbaz"} <= set(voices)
    t, s = voices["trump"], voices["shehbaz"]
    assert t.ref.language == "English" and s.ref.language == "Auto"
    assert t.sha256_ok is True and s.sha256_ok is True
    assert t.ref.sr == 24000 and s.ref.sr == 24000
    assert abs(t.ref.seconds - 23.21) < 0.05 and abs(s.ref.seconds - 28.04) < 0.05
    assert s.ref.ref_text.endswith("السلام علیکم۔")
    assert [c.name for c in t.clips] == ["trump_01.wav"]
    assert len(s.clips) == 8 and all(c.is_file() for c in s.clips)


def test_reference_keys():
    a = wav_bytes(2.0)
    r1 = eng.make_reference(a, "text one", False, "inline")
    r2 = eng.make_reference(a, " text one ", False, "inline")
    r3 = eng.make_reference(a, "text two", False, "inline")
    r4 = eng.make_reference(a, None, True, "inline")
    assert r1.key == r2.key != r3.key
    assert r4.key.endswith(":xvec") and r4.ref_text is None
    assert r1.as_x_vector_only().key == r4.key
    b = wav_bytes(2.0, amp=0.31)
    assert eng.make_reference(b, "text one", False, "inline").key != r1.key


def test_stereo_reference_is_downmixed():
    import io
    import soundfile as sf

    buf = io.BytesIO()
    sf.write(buf, np.stack([np.full(48000, 0.5), np.full(48000, -0.1)], axis=1).astype(np.float32), 24000,
             format="WAV", subtype="FLOAT")
    audio, sr = eng.decode_audio(buf.getvalue())
    assert audio.ndim == 1 and sr == 24000 and abs(float(audio.mean()) - 0.2) < 1e-6


@pytest.mark.parametrize("tokens, cap", [(0, 4096), (1, 192), (16, 192), (17, 204), (100, 1200), (400, 4096)])
def test_default_cap_matches_vllm_omni(tokens, cap):
    assert eng.Engine.default_cap(tokens) == cap


def test_cli_defaults():
    a = srv.build_parser().parse_args([])
    assert (a.host, a.port, a.model, a.device, a.dtype, a.attn) == (
        "127.0.0.1", 8093, "Qwen/Qwen3-TTS-12Hz-1.7B-Base", "cuda:0", "bfloat16", "sdpa")
    assert (a.max_batch, a.batch_window_ms, a.no_prompt_cache, a.avg_embedding) == (8, 20.0, False, False)
    assert a.voices_dir == REPO / "voices"
    with pytest.raises(SystemExit):
        srv.build_parser().parse_args(["--dtype", "float16"])


def test_json_formatter_local_time():
    rec = logging.LogRecord("qwen_tts_baseline", logging.INFO, __file__, 1, "request", None, None)
    rec.created = 0.0
    rec.fields = {"request_id": "r", "text": "اردو"}
    line = srv.JsonFormatter().format(rec)
    assert line.startswith('{"ts": "1970-01-01T05:00:00.000+05:00", "level": "info", "event": "request"')
    assert "اردو" in line
