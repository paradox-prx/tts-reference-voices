"""Dataset / sampler / collate tests on the derived sample set (needs data/sample/codes from prepare.py)."""
from __future__ import annotations

import glob
import os
from pathlib import Path

import pytest
import torch

from qwen_train.data import CodesStore, DataConfig, TTSDataset, TokenBudgetSampler, load_manifest, make_collate
from qwen_train.layout import SpecialIds

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "sample"
MODEL = os.environ.get("QWEN_TTS_MODEL") or next(iter(glob.glob(
    os.path.expanduser("~/.cache/huggingface/hub/models--Qwen--Qwen3-TTS-12Hz-1.7B-Base/snapshots/*"))), None)
pytestmark = pytest.mark.skipif(MODEL is None or not (DATA / "codes").exists(), reason="sample codes not prepared")


@pytest.fixture(scope="module")
def ds():
    from qwen_tts.core.models.configuration_qwen3_tts import Qwen3TTSConfig
    from qwen_tts.core.models.processing_qwen3_tts import Qwen3TTSProcessor
    cfg = Qwen3TTSConfig.from_pretrained(MODEL)
    proc = Qwen3TTSProcessor.from_pretrained(MODEL)
    store = CodesStore(DATA / "codes")
    rows = load_manifest(DATA, "train")[:300]
    return TTSDataset(rows, store, proc, SpecialIds.from_config(cfg), DataConfig(icl_p=1.0, language_id=2080, language_p=1.0),
                      seed=3), SpecialIds.from_config(cfg)


def test_codes_match_manifest(ds):
    d, ids = ds
    for r in d.rows[:50]:
        frames = len(d.store.codes[r["id"]])
        assert abs(frames / 12.5 - r["duration"]) < 0.6, (r["id"], frames, r["duration"])
        assert d.store.xvec[r["id"]].shape == (2048,)


def test_items_are_icl_same_speaker(ds):
    d, ids = ds
    for i in range(20):
        l = d[i]
        assert l.meta["icl"] and l.meta["n_ref"] > 0 and l.meta["language_id"] == 2080
        assert l.labels[l.n_prompt - 1] == d.store.codes[d.rows[i]["id"]][0, 0]  # first target frame predicted at n_prompt-1
        assert int(l.labels[len(l) - 1]) == ids.codec_eos
        assert l.meta["xvec"].shape == (2048,)
    # the reference is another utterance of the same speaker: its frame count differs from the target's
    l = d[0]
    assert l.meta["n_ref"] != l.meta["n_target"] or len(d.by_speaker[d.rows[0]["speaker"]]) == 1


def test_epoch_changes_reference(ds):
    d, ids = ds
    a = d[5].meta["n_ref"]
    d.set_epoch(1)
    b = d[5].meta["n_ref"]
    d.set_epoch(0)
    assert a == d[5].meta["n_ref"]  # deterministic per (epoch, index)
    assert a != b or len(d.by_speaker[d.rows[5]["speaker"]]) < 3


def test_sampler_budget(ds):
    d, ids = ds
    s = TokenBudgetSampler(d.approx_len, max_tokens=3000, max_batch=8, seed=1, ref_overhead=0.5)
    seen = []
    for b in s:
        assert 1 <= len(b) <= 8
        assert max(int(d.approx_len[i] * 1.5) for i in b) * len(b) <= 3000 or len(b) == 1
        seen += b
    assert sorted(seen) == list(range(len(d)))
    first = list(s)[0]
    s.set_epoch(1)
    assert list(s)[0] != first


def test_collate_shapes(ds):
    d, ids = ds
    batch = make_collate(ids)([d[i] for i in range(4)])
    B, L = batch["text_ids"].shape
    assert B == 4 and batch["frame_codes"].shape == (4, L, 16) and batch["xvec"].shape == (4, 2048)
    assert batch["attention_mask"].sum(1).tolist() == [len(d[i]) for i in range(4)]
    assert (batch["labels"][batch["attention_mask"] == 0] == -100).all()
    assert batch["spk_pos"].tolist() == [d[i].spk_pos for i in range(4)]
