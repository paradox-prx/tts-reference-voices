"""PCM16 mono helpers: WAV/FLAC encoding with an AI-generated label, WAV parsing, durations."""

from __future__ import annotations

import io
import struct

import numpy as np
import soundfile as sf

AI_LABEL = "AI-generated speech (Qwen3-TTS voice clone). Not a real recording."
SAMPLE_WIDTH = 2  # PCM16
STREAM_SIZE = 0xFFFFFFFF  # RIFF/data size of a WAV whose length is unknown up front
MEDIA_TYPES = {"wav": "audio/wav", "pcm": "audio/pcm", "flac": "audio/flac"}


def _info_chunk(comment: str) -> bytes:
    text = comment.encode() + b"\0"
    text += b"\0" * (len(text) & 1)
    info = b"INFO" + b"ICMT" + struct.pack("<I", len(text)) + text
    return b"LIST" + struct.pack("<I", len(info)) + info


def wav_header(sample_rate: int, data_bytes: int | None = None, comment: str = AI_LABEL) -> bytes:
    """RIFF/WAVE header through the data chunk header, with a LIST/INFO ICMT label before the data.
    data_bytes=None gives a streaming header (sizes 0xFFFFFFFF)."""
    fmt = struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate * SAMPLE_WIDTH, SAMPLE_WIDTH, 8 * SAMPLE_WIDTH)
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + _info_chunk(comment)
    if data_bytes is None:
        riff_size = data_size = STREAM_SIZE
    else:
        data_size = data_bytes
        riff_size = len(body) + 8 + data_bytes + (data_bytes & 1)
    return b"RIFF" + struct.pack("<I", riff_size) + body + b"data" + struct.pack("<I", data_size)


def pcm_to_wav(pcm: bytes, sample_rate: int, comment: str = AI_LABEL) -> bytes:
    return b"".join((wav_header(sample_rate, len(pcm), comment), pcm, b"\0" * (len(pcm) & 1)))


def pcm_to_flac(pcm: bytes, sample_rate: int, comment: str = AI_LABEL) -> bytes:
    buf = io.BytesIO()
    with sf.SoundFile(buf, "w", samplerate=sample_rate, channels=1, format="FLAC", subtype="PCM_16") as f:
        f.comment = comment  # Vorbis comment
        f.write(np.frombuffer(pcm, dtype="<i2"))
    return buf.getvalue()


def encode(pcm: bytes, sample_rate: int, fmt: str) -> bytes:
    if fmt == "wav":
        return pcm_to_wav(pcm, sample_rate)
    if fmt == "flac":
        return pcm_to_flac(pcm, sample_rate)
    if fmt == "pcm":
        return pcm
    raise ValueError(f"unsupported format {fmt!r}")


def wav_to_pcm(data: bytes) -> tuple[bytes, int]:
    """(PCM16 mono bytes, sample rate) of a WAV payload; tolerates streaming (0xFFFFFFFF) sizes."""
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("not a WAV payload")
    pos, sample_rate = 12, None
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        body = pos + 8
        if cid == b"fmt ":
            tag, channels, sample_rate = struct.unpack("<HHI", data[body:body + 8])
            bits = struct.unpack("<H", data[body + 14:body + 16])[0]
            if (tag, channels, bits) != (1, 1, 16):
                raise ValueError(f"expected PCM16 mono WAV, got format {tag}, {channels} ch, {bits} bit")
        elif cid == b"data":
            if sample_rate is None:
                raise ValueError("WAV data chunk before fmt chunk")
            end = len(data) if size == STREAM_SIZE else min(len(data), body + size)
            pcm = data[body:end]
            return pcm[:len(pcm) - len(pcm) % SAMPLE_WIDTH], sample_rate
        pos = body + size + (size & 1)
    raise ValueError("no data chunk in WAV payload")


def duration_s(pcm_bytes: int, sample_rate: int) -> float:
    return pcm_bytes / (SAMPLE_WIDTH * sample_rate)


def silence(seconds: float, sample_rate: int) -> bytes:
    return bytes(SAMPLE_WIDTH * round(seconds * sample_rate))
