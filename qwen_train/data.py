"""Training data: manifest + codec shards -> layouts -> padded batches.

Every item is one target utterance. With probability icl.p it gets an in-context reference (another utterance of the
same speaker, ref_min_s..ref_max_s long: its text, codes and x-vector go into the prompt exactly as the server's
voice-clone request does); otherwise only the x-vector of another utterance conditions the voice. With probability
language.p the Urdu language tag is in the prefix (the rest train the "Auto" form the server sends today).
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset, Sampler

from .layout import Example, Layout, SpecialIds, build, collate

TEMPLATE = "<|im_start|>assistant\n{text}<|im_end|>\n<|im_start|>assistant\n"
REF_TEMPLATE = "<|im_start|>assistant\n{text}<|im_end|>\n"
INSTRUCT_TEMPLATE = "<|im_start|>user\n{text}<|im_end|>\n"


@dataclass
class DataConfig:
    icl_p: float = 0.7
    ref_min_s: float = 3.0
    ref_max_s: float = 20.0
    train_on_ref: bool = False
    language_id: int | None = None
    language_p: float = 0.8
    english_id: int | None = 2050   # tag for rows that are mostly Latin script (urdu_frac < latin_threshold)
    latin_threshold: float = 0.5
    stream_p: float = 0.0
    max_frames: int = 400          # drop utterances longer than this (32 s at 12.5 Hz)
    max_seq: int = 1400            # drop examples whose layout is longer (ref + target)
    instruct_field: str | None = None  # manifest field holding a VoiceDesign instruction (then no x-vector)
    ref_self: bool = False         # debug: the reference is the target itself (check_alignment copy test)


class CodesStore:
    """All shards of prepare.py in memory: id -> (codes int16 [T,16], xvec float16 [D] | None, seconds)."""

    def __init__(self, codes_dir: str | Path):
        self.codes, self.xvec, self.seconds = {}, {}, {}
        for f in sorted(Path(codes_dir).glob("shard_*.npz")):
            z = np.load(f)
            ids, offsets, codes = z["ids"], z["offsets"], z["codes"]
            xv = z["xvec"] if z["xvec"].size else None
            for i, uid in enumerate(ids):
                self.codes[str(uid)] = codes[offsets[i]:offsets[i + 1]]
                self.seconds[str(uid)] = float(z["seconds"][i])
                if xv is not None:
                    self.xvec[str(uid)] = xv[i]
        if not self.codes:
            raise FileNotFoundError(f"no shard_*.npz under {codes_dir}: run python -m qwen_train.prepare first")

    def __contains__(self, uid: str) -> bool:
        return uid in self.codes

    def __len__(self) -> int:
        return len(self.codes)


def load_manifest(data_dir: str | Path, split: str | None = None) -> list[dict]:
    d = Path(data_dir)
    path = d / "manifest_qc.jsonl" if (d / "manifest_qc.jsonl").exists() else d / "manifest.jsonl"
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    return [r for r in rows if split is None or r["split"] == split]


class TTSDataset(Dataset):
    def __init__(self, rows: list[dict], store: CodesStore, processor, ids: SpecialIds, cfg: DataConfig,
                 seed: int = 0, deterministic: bool = False):
        self.store, self.proc, self.ids, self.cfg, self.seed, self.deterministic = store, processor, ids, cfg, seed, deterministic
        self.rows = [r for r in rows if r["id"] in store and len(store.codes[r["id"]]) <= cfg.max_frames]
        skipped = len(rows) - len(self.rows)
        self.by_speaker: dict[str, list[int]] = {}   # reference pool: clips whose speaker label is trusted
        for i, r in enumerate(self.rows):
            if r.get("ref_ok", True):
                self.by_speaker.setdefault(r["speaker"], []).append(i)
        role_full = self._tok(TEMPLATE.format(text="x"))
        self.role_ids = role_full[:3]
        self.text_ids = [self._tok(TEMPLATE.format(text=r["text"]))[3:-5] for r in self.rows]
        self.ref_text_ids = [self._tok(REF_TEMPLATE.format(text=r["text"]))[3:-2] for r in self.rows]
        self.instruct_ids = None
        if cfg.instruct_field:
            self.instruct_ids = [self._tok(INSTRUCT_TEMPLATE.format(text=r[cfg.instruct_field])) for r in self.rows]
        self.approx_len = [8 + len(t) + len(store.codes[r["id"]]) for t, r in zip(self.text_ids, self.rows)]
        self.epoch = 0
        print(f"dataset: {len(self.rows)} utterances ({skipped} skipped: no codes or > {cfg.max_frames} frames), "
              f"{len(self.by_speaker)} speakers, {sum(self.approx_len) / 1e6:.2f}M tokens without references")

    def _tok(self, text: str) -> torch.Tensor:
        return self.proc(text=text, return_tensors="pt")["input_ids"][0]

    def __len__(self) -> int:
        return len(self.rows)

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def _rng(self, idx: int) -> random.Random:
        key = f"{self.seed}:{0 if self.deterministic else self.epoch}:{idx}"
        return random.Random(int(hashlib.md5(key.encode()).hexdigest()[:12], 16))

    def _language(self, r: dict) -> int | None:
        if self.cfg.english_id is not None and r.get("urdu_frac", 1.0) < self.cfg.latin_threshold:
            return self.cfg.english_id
        return self.cfg.language_id

    def _pick_ref(self, idx: int, rng: random.Random, min_s: float, max_s: float) -> int:
        pool = self.by_speaker.get(self.rows[idx]["speaker"], [])
        cands = [j for j in pool if j != idx and min_s <= self.store.seconds[self.rows[j]["id"]] <= max_s]
        if not cands:
            cands = [j for j in pool if j != idx] or [idx]  # no trusted clip of this voice: its own x-vector only
        return rng.choice(cands)

    def __getitem__(self, idx: int) -> Layout:
        r = self.rows[idx]
        rng = self._rng(idx)
        codes = torch.from_numpy(self.store.codes[r["id"]].astype(np.int64))
        icl = rng.random() < self.cfg.icl_p
        ref = idx if self.cfg.ref_self else self._pick_ref(idx, rng, self.cfg.ref_min_s, self.cfg.ref_max_s)
        ref_id = self.rows[ref]["id"]
        ex = Example(role_ids=self.role_ids, text_ids=self.text_ids[idx], codes=codes, id=r["id"],
                     language_id=self._language(r) if rng.random() < self.cfg.language_p else None,
                     streaming=rng.random() < self.cfg.stream_p, train_on_ref=self.cfg.train_on_ref)
        if self.instruct_ids is not None:
            ex.instruct_ids = self.instruct_ids[idx]  # VoiceDesign: the instruction conditions the voice, no x-vector
        else:
            ex.xvec = torch.from_numpy(self.store.xvec[ref_id].astype(np.float32))
        if ref == idx and not self.cfg.ref_self:
            icl = False  # the clip's own audio as its "reference" would leak the answer
        if icl and self.instruct_ids is None:
            ex.ref_text_ids = self.ref_text_ids[ref]
            ex.ref_codes = torch.from_numpy(self.store.codes[ref_id].astype(np.int64))
        layout = build(ex, self.ids)
        if len(layout) > self.cfg.max_seq and icl:  # too long with the reference: fall back to x-vector only
            ex.ref_text_ids, ex.ref_codes = None, None
            layout = build(ex, self.ids)
        layout.meta["xvec"] = ex.xvec
        return layout


class TokenBudgetSampler(Sampler[list[int]]):
    """Batches of similar-length items whose (approximate) token total stays under max_tokens."""

    def __init__(self, lengths: list[int], max_tokens: int, max_batch: int, seed: int = 0, shuffle: bool = True,
                 ref_overhead: float = 1.0):
        self.lengths = [int(l * (1 + ref_overhead)) for l in lengths]  # a reference roughly doubles the frames
        self.max_tokens, self.max_batch, self.seed, self.shuffle = max_tokens, max_batch, seed, shuffle
        self.epoch = 0
        self.batches = self._make(0)

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch
        self.batches = self._make(epoch)

    def _make(self, epoch: int) -> list[list[int]]:
        order = sorted(range(len(self.lengths)), key=lambda i: self.lengths[i])
        rng = random.Random(self.seed + epoch)
        if self.shuffle:  # keep length order but jitter within windows so batches vary between epochs
            window = 64
            chunks = [order[i:i + window] for i in range(0, len(order), window)]
            for c in chunks:
                rng.shuffle(c)
            order = [i for c in chunks for i in c]
        batches, cur, cur_max = [], [], 0
        for i in order:
            l = self.lengths[i]
            if cur and (max(cur_max, l) * (len(cur) + 1) > self.max_tokens or len(cur) >= self.max_batch):
                batches.append(cur)
                cur, cur_max = [], 0
            cur.append(i)
            cur_max = max(cur_max, l)
        if cur:
            batches.append(cur)
        if self.shuffle:
            rng.shuffle(batches)
        return batches

    def __iter__(self):
        return iter(self.batches)

    def __len__(self) -> int:
        return len(self.batches)


def make_collate(ids: SpecialIds):
    def collate_fn(layouts: list[Layout]) -> dict:
        batch = collate(layouts, pad_text=ids.tts_pad)
        xv = [l.meta.get("xvec") for l in layouts]
        if any(x is not None for x in xv):
            dim = next(x.shape[0] for x in xv if x is not None)
            batch["xvec"] = torch.stack([x if x is not None else torch.zeros(dim) for x in xv])
        return batch
    return collate_fn
