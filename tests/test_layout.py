"""Layout tests: the position table must match what Qwen3TTSForConditionalGeneration.generate() builds.

These run on CPU with only the model config and tokenizer (no weights)."""
from __future__ import annotations

import glob
import os

import pytest
import torch

from qwen_train.layout import Example, SpecialIds, build, collate, describe

MODEL = os.environ.get("QWEN_TTS_MODEL") or next(iter(glob.glob(
    os.path.expanduser("~/.cache/huggingface/hub/models--Qwen--Qwen3-TTS-12Hz-1.7B-Base/snapshots/*"))), None)
pytestmark = pytest.mark.skipif(MODEL is None, reason="Base model not in the HF cache")


@pytest.fixture(scope="module")
def cfg_tok():
    from qwen_tts.core.models.configuration_qwen3_tts import Qwen3TTSConfig
    from qwen_tts.core.models.processing_qwen3_tts import Qwen3TTSProcessor
    return Qwen3TTSConfig.from_pretrained(MODEL), Qwen3TTSProcessor.from_pretrained(MODEL)


def tokens(proc, text: str, template: str) -> torch.Tensor:
    return proc(text=template.format(text=text), return_tensors="pt")["input_ids"][0]


def make(cfg_tok, *, icl=False, lang=None, streaming=False, xvec=True, instruct=None, T=5, Tr=3):
    cfg, proc = cfg_tok
    full = tokens(proc, "یہ ایک آزمائش ہے", "<|im_start|>assistant\n{text}<|im_end|>\n<|im_start|>assistant\n")
    role, text = full[:3], full[3:-5]
    ex = Example(role_ids=role, text_ids=text, codes=torch.arange(T * 16).view(T, 16) % 2048,
                 xvec=torch.zeros(2048) if xvec else None, language_id=lang, streaming=streaming, id="t")
    if icl:
        ex.ref_text_ids = tokens(proc, "حوالہ", "<|im_start|>assistant\n{text}<|im_end|>\n")[3:-2]
        ex.ref_codes = 100 + torch.arange(Tr * 16).view(Tr, 16) % 1000
    if instruct:
        ex.instruct_ids = tokens(proc, instruct, "<|im_start|>user\n{text}<|im_end|>\n")
    return ex, cfg, proc


def test_template_slices(cfg_tok):
    """The inference code strips 5 trailing / 2 trailing template tokens; check those counts hold for Urdu text."""
    cfg, proc = cfg_tok
    full = tokens(proc, "کیا ریٹ مل رہا ہے.", "<|im_start|>assistant\n{text}<|im_end|>\n<|im_start|>assistant\n")
    assert proc.tokenizer.decode(full[:3]) == "<|im_start|>assistant\n"
    assert proc.tokenizer.decode(full[-5:]) == "<|im_end|>\n<|im_start|>assistant\n"
    ref = tokens(proc, "کیا ریٹ مل رہا ہے.", "<|im_start|>assistant\n{text}<|im_end|>\n")
    assert proc.tokenizer.decode(ref[-2:]) == "<|im_end|>\n"
    assert torch.equal(full[3:-5], ref[3:-2])


def test_nsm_xvector_layout(cfg_tok):
    ex, cfg, proc = make(cfg_tok)
    ids = SpecialIds.from_config(cfg)
    l = build(ex, ids)
    n = len(ex.text_ids)
    # role(3) + prefix(3) + spk(1) + pad/bos(1) + text(n) + eos(1) + bos(1) + frames(T)
    assert len(l) == 3 + 3 + 1 + 1 + n + 1 + 1 + 5
    assert l.codec_ids[:3].tolist() == [-1, -1, -1] and l.text_ids[:3].tolist() == ex.role_ids.tolist()
    assert l.codec_ids[3:6].tolist() == [ids.codec_nothink, ids.codec_think_bos, ids.codec_think_eos]
    assert l.spk_pos == 6 and l.codec_ids[6] == -1 and l.text_ids[6] == ids.tts_pad
    assert l.text_ids[7] == ids.tts_bos and l.codec_ids[7] == ids.codec_pad
    assert l.text_ids[8:8 + n].tolist() == ex.text_ids.tolist() and set(l.codec_ids[8:8 + n].tolist()) == {ids.codec_pad}
    assert l.text_ids[8 + n] == ids.tts_eos and l.codec_ids[8 + n] == ids.codec_pad
    bos = 8 + n + 1
    assert l.text_ids[bos] == ids.tts_pad and l.codec_ids[bos] == ids.codec_bos
    assert l.frame_mask[bos + 1:].all() and not l.frame_mask[:bos + 1].any()
    # labels: bos predicts frame 0, frame j predicts frame j+1, last frame predicts eos; nothing else
    assert l.labels[bos] == ex.codes[0, 0]
    for j in range(4):
        assert l.labels[bos + 1 + j] == ex.codes[j + 1, 0]
    assert l.labels[bos + 5] == ids.codec_eos
    assert (l.labels[:bos] == -100).all()
    # code predictor: same positions minus the eos one, with the full 16 codes of the predicted frame
    assert l.cp_mask[bos:bos + 5].all() and not l.cp_mask[bos + 5] and not l.cp_mask[:bos].any()
    assert torch.equal(l.cp_codes[bos], ex.codes[0]) and torch.equal(l.cp_codes[bos + 3], ex.codes[3])
    assert l.n_prompt == bos + 1


def test_language_tag_and_no_speaker(cfg_tok):
    ex, cfg, proc = make(cfg_tok, lang=2080, xvec=False, instruct="A calm female voice")
    ids = SpecialIds.from_config(cfg)
    l = build(ex, ids)
    k = len(ex.instruct_ids)
    assert l.text_ids[:k].tolist() == ex.instruct_ids.tolist() and (l.codec_ids[:k] == -1).all()
    assert l.codec_ids[k + 3:k + 7].tolist() == [ids.codec_think, ids.codec_think_bos, 2080, ids.codec_think_eos]
    assert l.spk_pos == -1 and l.text_ids[k + 7] == ids.tts_bos and l.codec_ids[k + 7] == ids.codec_pad


def test_icl_layout(cfg_tok):
    ex, cfg, proc = make(cfg_tok, icl=True, T=4, Tr=3)
    ids = SpecialIds.from_config(cfg)
    l = build(ex, ids)
    m, n = len(ex.ref_text_ids), len(ex.text_ids)
    assert l.text_ids[8:8 + m].tolist() == ex.ref_text_ids.tolist()
    assert l.text_ids[8 + m:8 + m + n].tolist() == ex.text_ids.tolist()
    bos = 8 + m + n + 1
    assert l.codec_ids[bos] == ids.codec_bos
    # ref frames are prompt: bos and ref frames 0,1 have no label; the last ref frame predicts target frame 0
    assert l.labels[bos] == -100 and l.labels[bos + 1] == -100 and l.labels[bos + 2] == -100
    assert l.labels[bos + 3] == ex.codes[0, 0] and torch.equal(l.cp_codes[bos + 3], ex.codes[0])
    assert l.labels[bos + 3 + 4] == ids.codec_eos and l.cp_mask[bos + 3:bos + 3 + 4].all() and not l.cp_mask[:bos + 3].any()
    assert l.n_prompt == bos + 3 + 1
    l2 = build(Example(**{**ex.__dict__, "train_on_ref": True}), ids)
    assert l2.labels[bos] == ex.ref_codes[0, 0] and l2.labels[bos + 1] == ex.ref_codes[1, 0]


def test_streaming_layout(cfg_tok):
    ex, cfg, proc = make(cfg_tok, streaming=True, T=6)
    ids = SpecialIds.from_config(cfg)
    l = build(ex, ids)
    n = len(ex.text_ids)
    bos = 8
    # first text token over codec_bos, then the next text tokens over the frames, tts_eos, then tts_pad
    assert l.codec_ids[bos] == ids.codec_bos and l.text_ids[bos] == ex.text_ids[0]
    seq = ex.text_ids.tolist()[1:] + [ids.tts_eos]
    for j in range(6):
        expected = seq[j] if j < len(seq) else ids.tts_pad
        assert l.text_ids[bos + 1 + j] == expected and l.frame_mask[bos + 1 + j]
    assert l.labels[bos] == ex.codes[0, 0] and l.labels[bos + 6] == ids.codec_eos


def test_collate_pads(cfg_tok):
    ex1, cfg, proc = make(cfg_tok, T=3)
    ex2, _, _ = make(cfg_tok, T=7, icl=True)
    ids = SpecialIds.from_config(cfg)
    b = collate([build(ex1, ids), build(ex2, ids)], pad_text=ids.tts_pad)
    assert b["attention_mask"].sum(1).tolist() == [len(build(ex1, ids)), len(build(ex2, ids))]
    assert (b["labels"][0, b["attention_mask"][0] == 0] == -100).all()
    assert b["text_present"][0, :3].all() and not b["text_present"][0, -1]
    print(describe(build(ex2, ids), ids, proc.tokenizer, limit=20))
