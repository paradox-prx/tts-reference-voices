"""Which GGML type each tensor is stored as, per output type.

Policy (llama.cpp-like, conservative for the audio path):
  - 1-D tensors (norms, biases, snake alphas, codebook counters) -> F32 (exact upcast of the BF16 originals);
  - transformer block projections (q/k/v/o, gate/up/down)      -> the requested type;
  - token_embd / output (text embedding + head)                -> the requested type, but Q8_0 for 4/5-bit types;
  - audio_embd / audio_head (8 codebooks x 1026)               -> BF16 unless --quantize-audio (then Q8_0);
  - the bundled codec (convs, RVQ, HuBERT)                     -> BF16, never quantised (it is ~0.6 GB and turns
    tokens into waveform; quantisation noise there is audible and saves little).
A tensor whose rows are not a multiple of the block size falls back to BF16.
"""

from __future__ import annotations

from gguf import GGML_QUANT_SIZES, GGMLQuantizationType as T, LlamaFileType as FT

from . import names

OUTTYPES: dict[str, tuple[T, FT]] = {
    "bf16": (T.BF16, FT.MOSTLY_BF16),
    "q8_0": (T.Q8_0, FT.MOSTLY_Q8_0),
    "q5_1": (T.Q5_1, FT.MOSTLY_Q5_1),
    "q5_0": (T.Q5_0, FT.MOSTLY_Q5_0),
    "q4_1": (T.Q4_1, FT.MOSTLY_Q4_1),
    "q4_0": (T.Q4_0, FT.MOSTLY_Q4_0),
}
_LOW_BIT = {T.Q5_1, T.Q5_0, T.Q4_1, T.Q4_0}


def _fits(qtype: T, shape: tuple[int, ...]) -> bool:
    block, _ = GGML_QUANT_SIZES[qtype]
    return len(shape) >= 2 and shape[-1] % block == 0


def choose(hf_name: str, shape: tuple[int, ...], outtype: str, quantize_audio: bool = False) -> T:
    want, _ = OUTTYPES[outtype]
    if len(shape) <= 1:
        return T.F32
    if hf_name.startswith(names.CODEC_PREFIX):
        return T.BF16
    if hf_name in (names.AUDIO_EMBED, names.AUDIO_HEAD):
        q = T.Q8_0 if quantize_audio and want != T.BF16 else T.BF16
    elif hf_name in (names.TEXT_EMBED, names.TEXT_HEAD):
        q = T.Q8_0 if want in _LOW_BIT else want
    elif names.is_backbone_matrix(hf_name):
        q = want
    else:
        q = T.BF16
    return q if q in (T.BF16, T.F32) or _fits(q, shape) else T.BF16


def nbytes(qtype: T, shape: tuple[int, ...]) -> int:
    block, size = GGML_QUANT_SIZES[qtype]
    n = 1
    for d in shape:
        n *= d
    assert n % block == 0, (qtype, shape)
    return n // block * size
