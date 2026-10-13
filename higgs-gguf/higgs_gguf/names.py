"""Tensor names: Higgs TTS 3 checkpoint (HF safetensors) <-> GGUF.

The Qwen3 backbone uses llama.cpp's tensor names (token_embd, blk.N.attn_q, ...), so any ggml/GGUF tool reads it
the usual way. The audio parts get `audio_embd` / `audio_head`, and the bundled codec (DAC-style decoder, RVQ,
HuBERT semantic encoder) lives under `codec.` with abbreviated paths because GGUF names are limited to 63 bytes.

The authoritative mapping is stored in every file as two aligned string arrays (KEY_MAP_GGUF / KEY_MAP_HF), so a
reader never has to re-derive the abbreviations.
"""

from __future__ import annotations

import hashlib
import re

ARCH = "higgs-tts3"
GGUF_NAME_MAX = 63  # GGML_MAX_NAME is 64 including the NUL

# metadata keys written by the converter
KEY_MAP_GGUF = "higgs.tensor_map.gguf"
KEY_MAP_HF = "higgs.tensor_map.hf"
KEY_ALIAS_HF = "higgs.alias.hf"      # checkpoint tensors not stored because they equal another tensor...
KEY_ALIAS_SRC = "higgs.alias.src"    # ...namely this one (aligned arrays)
KEY_CONFIG_JSON = "higgs.hf.config_json"
KEY_TOKENIZER_JSON = "higgs.hf.tokenizer_json"
KEY_TOKENIZER_CONFIG_JSON = "higgs.hf.tokenizer_config_json"
KEY_CHAT_TEMPLATE = "higgs.hf.chat_template"
KEY_SOURCE_REPO = "higgs.source.repo"
KEY_SOURCE_REVISION = "higgs.source.revision"
KEY_CONVERTER_VERSION = "higgs.converter.version"
CONVERTER_VERSION = "1"

# files a vLLM model directory needs next to the weights, and the metadata key that carries each
HF_SIDE_FILES = {
    "config.json": KEY_CONFIG_JSON,
    "tokenizer.json": KEY_TOKENIZER_JSON,
    "tokenizer_config.json": KEY_TOKENIZER_CONFIG_JSON,
    "chat_template.jinja": KEY_CHAT_TEMPLATE,
}

TEXT_EMBED = "tied.embedding.text_embedding.weight"
TEXT_HEAD = "tied.head.text_head.weight"
AUDIO_EMBED = "tied.embedding.modality_embeddings.0.embedding.weight"
AUDIO_HEAD = "tied.head.modality_heads.0.weight"
CODEC_PREFIX = "tied.embedding.modality_embeddings.0.model."  # same constant as vllm_omni's higgs_audio_v3
# output heads the checkpoint stores as copies of the input embeddings (tie_word_embeddings / tie_modality_embeddings)
TIED_HEADS = {TEXT_HEAD: TEXT_EMBED, AUDIO_HEAD: AUDIO_EMBED}

_FIXED = {
    TEXT_EMBED: "token_embd.weight",
    TEXT_HEAD: "output.weight",
    "body.norm.weight": "output_norm.weight",
    AUDIO_EMBED: "audio_embd.weight",
    AUDIO_HEAD: "audio_head.weight",
}

_LAYER = {
    "input_layernorm": "attn_norm",
    "post_attention_layernorm": "ffn_norm",
    "self_attn.q_proj": "attn_q",
    "self_attn.k_proj": "attn_k",
    "self_attn.v_proj": "attn_v",
    "self_attn.o_proj": "attn_output",
    "self_attn.q_norm": "attn_q_norm",
    "self_attn.k_norm": "attn_k_norm",
    "mlp.gate_proj": "ffn_gate",
    "mlp.up_proj": "ffn_up",
    "mlp.down_proj": "ffn_down",
}
_LAYER_RE = re.compile(r"^body\.layers\.(\d+)\.(.+)\.(weight|bias)$")

# codec path abbreviations, applied in order (longest first where they overlap)
_CODEC_ABBREV = [
    ("parametrizations.weight.original", "wn"),
    ("quantizer.quantizers.", "rvq."),
    ("acoustic_decoder.", "adec."),
    ("acoustic_encoder.", "aenc."),
    ("decoder_semantic.", "sdec."),
    ("encoder_semantic.", "senc."),
    ("semantic_model.", "sem."),
    ("feature_extractor.", "fext."),
    ("feature_projection.", "fproj."),
    ("pos_conv_embed.", "pce."),
    ("conv_layers.", "cl."),
    ("conv_blocks.", "cb."),
    ("res_units.", "ru."),
    ("res_unit", "ru"),
    ("intermediate_dense", "ff_in"),
    ("output_dense", "ff_out"),
    ("feed_forward.", "ff."),
    ("final_layer_norm", "fln"),
    ("layer_norm", "ln"),
    ("attention.", "attn."),
    ("encoder.", "enc."),
    ("codebook.", "cbk."),
    ("project_in", "pin"),
    ("project_out", "pout"),
]


def hf_to_gguf(name: str) -> str:
    """GGUF tensor name for a checkpoint tensor name (deterministic, <= 63 bytes)."""
    if name in _FIXED:
        return _FIXED[name]
    m = _LAYER_RE.match(name)
    if m and m.group(2) in _LAYER:
        return f"blk.{m.group(1)}.{_LAYER[m.group(2)]}.{m.group(3)}"
    if name.startswith(CODEC_PREFIX):
        short = name[len(CODEC_PREFIX):]
        for long, abbr in _CODEC_ABBREV:
            short = short.replace(long, abbr)
        out = "codec." + short
    else:
        out = "x." + name  # unknown tensor: keep it, readers resolve it through the stored map
    if len(out.encode()) > GGUF_NAME_MAX:
        out = out[: GGUF_NAME_MAX - 9] + "." + hashlib.sha1(name.encode()).hexdigest()[:8]
    return out


def is_backbone_matrix(name: str) -> bool:
    """A 2-D projection inside a transformer block (the bulk of the parameters, where quantisation pays off)."""
    m = _LAYER_RE.match(name)
    return bool(m) and m.group(3) == "weight" and m.group(2) in _LAYER_MATRICES


_LAYER_MATRICES = {k for k in _LAYER if k.endswith("_proj")}
