"""PCM16 mono WAV helpers with the AI-generated label.

Byte-for-byte the same WAV layout as server/gateway/tts_gateway/audio.py (RIFF, fmt, LIST/INFO/ICMT label, data), copied
rather than imported so the baseline runs in its own venv (server/venvs/qwentts) without the gateway package.
tests/test_units.py checks that the two stay identical when the gateway package is importable.
"""

from __future__ import annotations

import struct

import numpy as np

AI_LABEL = "AI-generated speech (Qwen3-TTS voice clone). Not a real recording."
SAMPLE_WIDTH = 2  # PCM16


def _info_chunk(comment: str) -> bytes:
    text = comment.encode() + b"\0"
    text += b"\0" * (len(text) & 1)
    info = b"INFO" + b"ICMT" + struct.pack("<I", len(text)) + text
    return b"LIST" + struct.pack("<I", len(info)) + info


def wav_header(sample_rate: int, data_bytes: int, comment: str = AI_LABEL) -> bytes:
    """RIFF/WAVE header through the data chunk header, with a LIST/INFO ICMT label before the data."""
    fmt = struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate * SAMPLE_WIDTH, SAMPLE_WIDTH, 8 * SAMPLE_WIDTH)
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + _info_chunk(comment)
    riff_size = len(body) + 8 + data_bytes + (data_bytes & 1)
    return b"RIFF" + struct.pack("<I", riff_size) + body + b"data" + struct.pack("<I", data_bytes)


def pcm_to_wav(pcm: bytes, sample_rate: int, comment: str = AI_LABEL) -> bytes:
    return b"".join((wav_header(sample_rate, len(pcm), comment), pcm, b"\0" * (len(pcm) & 1)))


def float_to_pcm16(wav: np.ndarray) -> bytes:
    """float waveform in [-1, 1] (clipped) -> PCM16 little-endian bytes."""
    x = np.clip(np.asarray(wav, dtype=np.float32), -1.0, 1.0)
    return (np.round(x * 32767.0)).astype("<i2").tobytes()


def wav_chunks(data: bytes) -> dict[bytes, bytes]:
    """{chunk id: body} of a RIFF/WAVE payload (first occurrence of each id; LIST bodies keyed as b'LIST')."""
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("not a WAV payload")
    out: dict[bytes, bytes] = {}
    pos = 12
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        out.setdefault(cid, data[pos + 8:pos + 8 + size])
        pos += 8 + size + (size & 1)
    return out


def wav_comment(data: bytes) -> str | None:
    """The LIST/INFO ICMT comment of a WAV payload, or None."""
    info = wav_chunks(data).get(b"LIST", b"")
    if info[:4] != b"INFO":
        return None
    pos = 4
    while pos + 8 <= len(info):
        cid, size = info[pos:pos + 4], struct.unpack("<I", info[pos + 4:pos + 8])[0]
        if cid == b"ICMT":
            return info[pos + 8:pos + 8 + size].rstrip(b"\0").decode("utf-8", "replace")
        pos += 8 + size + (size & 1)
    return None


def wav_pcm16(data: bytes) -> tuple[bytes, int]:
    """(PCM bytes, sample rate) of a PCM16 mono WAV payload."""
    chunks = wav_chunks(data)
    fmt = chunks.get(b"fmt ")
    if fmt is None or b"data" not in chunks:
        raise ValueError("WAV payload without fmt or data chunk")
    tag, channels, sample_rate = struct.unpack("<HHI", fmt[:8])
    bits = struct.unpack("<H", fmt[14:16])[0]
    if (tag, channels, bits) != (1, 1, 16):
        raise ValueError(f"expected PCM16 mono WAV, got format {tag}, {channels} ch, {bits} bit")
    return chunks[b"data"], sample_rate
