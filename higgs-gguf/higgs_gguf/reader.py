"""Read a Higgs GGUF back as checkpoint-named torch tensors (what vLLM-Omni's `load_weights` expects).

Quantised tensors are dequantised on the fly: Q8_0 with a torch fast path, every other GGML type through gguf-py's
numpy dequantiser. BF16 / F16 / F32 tensors are reinterpreted from the memory-mapped bytes, so a BF16 GGUF
reproduces the original checkpoint bit for bit.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import torch
from gguf import GGMLQuantizationType as T, GGUFReader
from gguf.quants import dequantize

from . import names

_RAW = {T.F32: torch.float32, T.F16: torch.float16, T.BF16: torch.bfloat16}


def field_value(reader: GGUFReader, key: str):
    f = reader.get_field(key)
    return None if f is None else f.contents()


def tensor_map(reader: GGUFReader) -> dict[str, str]:
    """GGUF name -> checkpoint name, from the map stored in the file (falls back to the static rules)."""
    g, h = field_value(reader, names.KEY_MAP_GGUF), field_value(reader, names.KEY_MAP_HF)
    if g and h:
        if len(g) != len(h):
            raise ValueError("corrupt GGUF: tensor-map arrays differ in length")
        return dict(zip(g, h))
    raise ValueError("not a Higgs GGUF (no higgs.tensor_map.*); convert it with scripts/convert_higgs_to_gguf.py")


def _q8_0(raw: np.ndarray, shape: tuple[int, ...]) -> torch.Tensor:
    blocks = torch.from_numpy(np.array(raw, copy=True).reshape(-1, 34))   # 2-byte fp16 scale + 32 int8 (copy: mmap is read-only)
    d = blocks[:, :2].contiguous().view(torch.float16).to(torch.float32)
    q = blocks[:, 2:].contiguous().view(torch.int8).to(torch.float32)
    return (q * d).reshape(shape)


def to_torch(t, dtype: torch.dtype | None = None) -> torch.Tensor:
    """One ReaderTensor -> torch tensor in numpy/torch dimension order, cast to `dtype` (None keeps the stored dtype,
    float32 for quantised types)."""
    shape = tuple(int(x) for x in reversed(t.shape.tolist()))
    raw = np.asarray(t.data)
    if t.tensor_type in _RAW:
        out = torch.from_numpy(raw.view(np.uint8).reshape(-1).copy()).view(_RAW[t.tensor_type]).reshape(shape)
    elif t.tensor_type == T.Q8_0:
        out = _q8_0(raw, shape)
    else:
        out = torch.from_numpy(np.ascontiguousarray(dequantize(raw, t.tensor_type), dtype=np.float32)).reshape(shape)
    return out if dtype is None else out.to(dtype)


def aliases(reader: GGUFReader) -> dict[str, list[str]]:
    """source checkpoint name -> checkpoint names the converter dropped as bit-identical copies of it."""
    out: dict[str, list[str]] = {}
    for dup, src in zip(field_value(reader, names.KEY_ALIAS_HF) or [], field_value(reader, names.KEY_ALIAS_SRC) or []):
        out.setdefault(src, []).append(dup)
    return out


def iter_checkpoint_tensors(path: str | Path, dtype: torch.dtype | None = torch.bfloat16,
                            prefix: str | None = None) -> Iterator[tuple[str, torch.Tensor]]:
    """Yield (checkpoint name, tensor) for every tensor of the original checkpoint, optionally only names under
    `prefix`. Tensors dropped as copies (tied heads) are re-emitted right after their source."""
    reader = GGUFReader(str(path), "r")
    gmap = tensor_map(reader)
    dups = aliases(reader)
    for t in reader.tensors:
        hf = gmap.get(t.name)
        if hf is None:
            raise ValueError(f"GGUF tensor {t.name!r} is not in the stored tensor map")
        wanted = [n for n in [hf, *dups.get(hf, [])] if not prefix or n.startswith(prefix)]
        if not wanted:
            continue
        x = to_torch(t, dtype)
        for n in wanted:
            yield n, x


def write_side_files(gguf_path: str | Path, out_dir: str | Path | None = None, overwrite: bool = False) -> list[Path]:
    """Write config.json / tokenizer files embedded in the GGUF next to it (or into out_dir), for vLLM."""
    reader = GGUFReader(str(gguf_path), "r")
    out = Path(out_dir or Path(gguf_path).parent)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for fname, key in names.HF_SIDE_FILES.items():
        val = field_value(reader, key)
        p = out / fname
        if val is None or (p.exists() and not overwrite):
            continue
        p.write_text(val, encoding="utf-8")
        written.append(p)
    return written
