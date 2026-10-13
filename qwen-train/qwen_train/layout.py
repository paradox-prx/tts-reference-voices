"""The token layout of one training example, mirroring Qwen3TTSForConditionalGeneration.generate() exactly.

The talker's input at every position is the sum of a text-channel embedding and a codec-channel embedding:

    position kind        text channel (through talker.text_projection)   codec channel
    instruct tokens      <|im_start|>user\\n{instruct}<|im_end|>\\n          nothing                (VoiceDesign only)
    role (3)             <|im_start|> assistant \\n                         nothing
    prefix               tts_pad ...                                       [nothink, think_bos, think_eos]        (no language)
                                                                           [think, think_bos, LANG, think_eos]    (with language)
    speaker slot         tts_pad                                           speaker embedding (x-vector)  (omitted for VoiceDesign)
    pad                  tts_bos                                           codec_pad
    -- non-streaming layout (non_streaming_mode=True) --
    text                 [ref text] target text, tts_eos                   codec_pad each
    bos                  tts_pad                                           codec_bos
    frames               tts_pad                                           sum of the 16 codebook embeddings of the frame
    -- streaming layout (non_streaming_mode=False) --
    bos                  first text token                                  codec_bos
    frames               next text token, ..., tts_eos, then tts_pad       sum of the 16 codebook embeddings of the frame

Frames are the reference clip's codes first (in-context cloning, ICL) then the target clip's codes. Every position
whose *next* position is a frame predicts that frame: its label is the frame's codebook-0 token (codec_eos after the
last target frame), and its hidden state feeds the code predictor for the frame's codebooks 1-15. Reference frames
are prompt: their labels are masked unless train_on_ref.

This module is pure tensor bookkeeping (no model); train.py turns a Layout into embeddings, and check_alignment.py
verifies with the pretrained model that the bookkeeping matches inference (teacher-forced accuracy).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import torch

NUM_GROUPS = 16


@dataclass
class SpecialIds:
    """The ids the layout needs, read from the model config (see from_config)."""
    tts_pad: int
    tts_bos: int
    tts_eos: int
    codec_pad: int
    codec_bos: int
    codec_eos: int
    codec_think: int
    codec_nothink: int
    codec_think_bos: int
    codec_think_eos: int

    @classmethod
    def from_config(cls, config) -> "SpecialIds":
        t = config.talker_config
        return cls(tts_pad=config.tts_pad_token_id, tts_bos=config.tts_bos_token_id, tts_eos=config.tts_eos_token_id,
                   codec_pad=t.codec_pad_id, codec_bos=t.codec_bos_id, codec_eos=t.codec_eos_token_id,
                   codec_think=t.codec_think_id, codec_nothink=t.codec_nothink_id,
                   codec_think_bos=t.codec_think_bos_id, codec_think_eos=t.codec_think_eos_id)


@dataclass
class Example:
    role_ids: torch.Tensor                    # [3]   <|im_start|> assistant \n
    text_ids: torch.Tensor                    # [n]   target text tokens (template stripped)
    codes: torch.Tensor                       # [T, 16] target frames
    xvec: torch.Tensor | None = None          # [D] speaker embedding of the reference clip
    ref_text_ids: torch.Tensor | None = None  # [m] reference text tokens (ICL)
    ref_codes: torch.Tensor | None = None     # [Tr, 16] reference frames (ICL)
    language_id: int | None = None
    instruct_ids: torch.Tensor | None = None  # [k] full instruct template (VoiceDesign)
    streaming: bool = False
    train_on_ref: bool = False
    id: str = ""


@dataclass
class Layout:
    """One example laid out position by position (before batching)."""
    text_ids: torch.Tensor      # [L] text-channel token id or -1
    codec_ids: torch.Tensor     # [L] single codec-channel token id or -1
    spk_pos: int                # position of the speaker embedding, or -1
    frame_codes: torch.Tensor   # [L, 16] the frame at frame positions (0 elsewhere)
    frame_mask: torch.Tensor    # [L] bool
    labels: torch.Tensor        # [L] codebook-0 label of the next position, -100 elsewhere
    cp_codes: torch.Tensor      # [L, 16] the 16 codes the code predictor must produce from this position's hidden state
    cp_mask: torch.Tensor       # [L] bool
    n_prompt: int               # positions before the first predicted target frame (for accuracy reporting)
    meta: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return int(self.text_ids.shape[0])


def build(ex: Example, ids: SpecialIds) -> Layout:
    text_col: list[int] = []
    codec_col: list[int] = []
    frames: list[torch.Tensor | None] = []  # per position: a [16] tensor or None
    spk_pos = -1

    def push(text: int, codec: int, frame: torch.Tensor | None = None) -> None:
        text_col.append(text)
        codec_col.append(codec)
        frames.append(frame)

    if ex.instruct_ids is not None:
        for t in ex.instruct_ids.tolist():
            push(t, -1)
    for t in ex.role_ids.tolist():
        push(t, -1)
    if ex.language_id is None:
        prefix = [ids.codec_nothink, ids.codec_think_bos, ids.codec_think_eos]
    else:
        prefix = [ids.codec_think, ids.codec_think_bos, int(ex.language_id), ids.codec_think_eos]
    for c in prefix:
        push(ids.tts_pad, c)
    if ex.xvec is not None:
        spk_pos = len(text_col)
        push(ids.tts_pad, -1)  # the speaker embedding is added by the model code at spk_pos
    push(ids.tts_bos, ids.codec_pad)

    icl = ex.ref_codes is not None
    text_seq = ([] if not icl else ex.ref_text_ids.tolist()) + ex.text_ids.tolist() + [ids.tts_eos]
    all_frames = torch.cat([ex.ref_codes, ex.codes], dim=0) if icl else ex.codes
    n_ref = int(ex.ref_codes.shape[0]) if icl else 0
    assert all_frames.shape[1] == NUM_GROUPS, all_frames.shape

    if not ex.streaming:
        for t in text_seq:
            push(t, ids.codec_pad)
        push(ids.tts_pad, ids.codec_bos)
        for f in all_frames:
            push(ids.tts_pad, -1, f)
    else:
        # position i pairs codec [bos, frames...][i] with text_seq[i] (tts_pad once the text is used up)
        codec_seq = [None] + list(all_frames)
        for i, f in enumerate(codec_seq):
            t = text_seq[i] if i < len(text_seq) else ids.tts_pad
            push(t, ids.codec_bos if f is None else -1, f)

    L = len(text_col)
    frame_mask = torch.tensor([f is not None for f in frames], dtype=torch.bool)
    frame_codes = torch.zeros((L, NUM_GROUPS), dtype=torch.long)
    for i, f in enumerate(frames):
        if f is not None:
            frame_codes[i] = f
    labels = torch.full((L,), -100, dtype=torch.long)
    cp_codes = torch.zeros((L, NUM_GROUPS), dtype=torch.long)
    cp_mask = torch.zeros((L,), dtype=torch.bool)
    frame_positions = torch.nonzero(frame_mask).flatten().tolist()
    bos_pos = frame_positions[0] - 1
    # position p predicts the frame at p+1: bos -> frame 0, frame j -> frame j+1, last target frame -> eos
    for j, pos in enumerate(frame_positions):
        prev = bos_pos if j == 0 else frame_positions[j - 1]
        is_target = j >= n_ref
        if is_target or ex.train_on_ref:
            labels[prev] = int(all_frames[j, 0])
            cp_codes[prev] = all_frames[j]
            cp_mask[prev] = True
    labels[frame_positions[-1]] = ids.codec_eos
    n_prompt = frame_positions[n_ref] if n_ref < len(frame_positions) else L
    return Layout(text_ids=torch.tensor(text_col), codec_ids=torch.tensor(codec_col), spk_pos=spk_pos,
                  frame_codes=frame_codes, frame_mask=frame_mask, labels=labels, cp_codes=cp_codes, cp_mask=cp_mask,
                  n_prompt=n_prompt, meta={"id": ex.id, "icl": icl, "streaming": ex.streaming, "n_ref": n_ref,
                                           "n_target": int(ex.codes.shape[0]), "language_id": ex.language_id})


def collate(layouts: list[Layout], pad_text: int) -> dict:
    """Right-pad a list of layouts into batch tensors."""
    B, L = len(layouts), max(len(l) for l in layouts)
    out = {"text_ids": torch.full((B, L), -1, dtype=torch.long), "codec_ids": torch.full((B, L), -1, dtype=torch.long),
           "frame_codes": torch.zeros((B, L, NUM_GROUPS), dtype=torch.long),
           "frame_mask": torch.zeros((B, L), dtype=torch.bool), "labels": torch.full((B, L), -100, dtype=torch.long),
           "cp_codes": torch.zeros((B, L, NUM_GROUPS), dtype=torch.long), "cp_mask": torch.zeros((B, L), dtype=torch.bool),
           "attention_mask": torch.zeros((B, L), dtype=torch.long),
           "spk_pos": torch.tensor([l.spk_pos for l in layouts], dtype=torch.long),
           "n_prompt": torch.tensor([l.n_prompt for l in layouts], dtype=torch.long), "meta": [l.meta for l in layouts]}
    for i, l in enumerate(layouts):
        n = len(l)
        out["text_ids"][i, :n] = l.text_ids
        out["codec_ids"][i, :n] = l.codec_ids
        out["frame_codes"][i, :n] = l.frame_codes
        out["frame_mask"][i, :n] = l.frame_mask
        out["labels"][i, :n] = l.labels
        out["cp_codes"][i, :n] = l.cp_codes
        out["cp_mask"][i, :n] = l.cp_mask
        out["attention_mask"][i, :n] = 1
    out["text_ids"][out["text_ids"] < 0] = pad_text  # padded/none positions embed pad_text and are masked out below
    out["text_present"] = torch.zeros((B, L), dtype=torch.bool)
    for i, l in enumerate(layouts):
        out["text_present"][i, :len(l)] = l.text_ids >= 0
    return out


def describe(l: Layout, ids: SpecialIds, tok=None, limit: int = 40) -> str:
    """Human-readable dump of the first positions (for tests and docs)."""
    names = {ids.tts_pad: "tts_pad", ids.tts_bos: "tts_bos", ids.tts_eos: "tts_eos"}
    cnames = {ids.codec_pad: "c_pad", ids.codec_bos: "c_bos", ids.codec_eos: "c_eos", ids.codec_think: "think",
              ids.codec_nothink: "nothink", ids.codec_think_bos: "think_bos", ids.codec_think_eos: "think_eos"}
    lines = []
    for p in range(min(len(l), limit)):
        t = int(l.text_ids[p]); c = int(l.codec_ids[p])
        tn = names.get(t, (tok.decode([t]) if tok is not None and t >= 0 else str(t)))
        cn = "SPK" if p == l.spk_pos else (cnames.get(c, str(c)) if c >= 0 else ("frame" if l.frame_mask[p] else "-"))
        lab = int(l.labels[p])
        lines.append(f"{p:4d} text={tn!s:12.12} codec={cn:10s} label={'-' if lab < 0 else lab} cp={'y' if l.cp_mask[p] else '-'}")
    return "\n".join(lines)
