"""Long clips are embedded in ~30 s windows (WavLM attention is quadratic in length); short ones whole."""

import numpy as np

from tts_qc import sim


def _fake(calls: list[int]):
    emb = sim.Embedder.__new__(sim.Embedder)

    def embed(wav: np.ndarray) -> np.ndarray:
        calls.append(len(wav))
        v = np.zeros(4, np.float32)
        v[len(calls) % 4] = 1.0
        return v

    emb._embed = embed
    return emb


def test_short_clip_is_embedded_whole() -> None:
    calls: list[int] = []
    out = _fake(calls)(np.zeros(35 * 16000, np.float32))
    assert calls == [35 * 16000] and np.isclose(np.linalg.norm(out), 1.0)


def test_long_clip_is_embedded_in_windows_and_averaged() -> None:
    calls: list[int] = []
    out = _fake(calls)(np.zeros(95 * 16000, np.float32))
    assert len(calls) == 4 and sum(calls) == 95 * 16000 and max(calls) <= 30 * 16000
    assert np.isclose(np.linalg.norm(out), 1.0) and out.dtype == np.float32
