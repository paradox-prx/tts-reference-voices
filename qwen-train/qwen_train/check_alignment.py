#!/usr/bin/env python3
"""Prove the training layout matches inference before training anything.

The pretrained model already predicts speech codes from text + reference (that is what it was trained on). So under a
correct teacher-forced layout its next-frame accuracy on real data is high, and under a wrong one (labels off by one
frame, text embeddings without the projection) it collapses. This script measures both on a few hundred utterances:

    python -m qwen_train.check_alignment --data data/sample --model Qwen/Qwen3-TTS-12Hz-1.7B-Base --n 200

Reports codebook-0 top-1 accuracy and the code predictor's per-codebook accuracy for: the layout as trained (nsm and
streaming, with and without reference), the official script's label shift, and the official script's missing text
projection. Writes alignment.json next to the data.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from .data import CodesStore, DataConfig, TTSDataset, TokenBudgetSampler, load_manifest, make_collate
from .layout import SpecialIds, describe
from .model_utils import forward_losses, load_model


@torch.no_grad()
def run(core, loader, device, **kw) -> dict:
    tot = {"talker_loss": 0.0, "cp_loss": 0.0, "acc0": 0.0, "n": 0, "cp_acc": None, "frames": 0}
    for batch in loader:
        r = forward_losses(core, batch, device, **kw)
        n = r["n_labels"]
        tot["talker_loss"] += float(r["talker_loss"]) * n
        tot["acc0"] += float(r["acc0"]) * n
        tot["cp_loss"] += float(r["cp_loss"]) * r["n_frames"]
        tot["cp_acc"] = r["cp_acc"] * r["n_frames"] if tot["cp_acc"] is None else tot["cp_acc"] + r["cp_acc"] * r["n_frames"]
        tot["n"] += n
        tot["frames"] += r["n_frames"]
    return {"talker_loss": round(tot["talker_loss"] / tot["n"], 4), "acc0": round(tot["acc0"] / tot["n"], 4),
            "cp_loss": round(tot["cp_loss"] / max(1, tot["frames"]), 4),
            "cp_acc_mean": round(float(tot["cp_acc"].mean() / tot["frames"]), 4),
            "cp_acc": [round(float(x) / tot["frames"], 3) for x in tot["cp_acc"]], "labels": tot["n"], "frames": tot["frames"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    ap.add_argument("--split", default="train")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", default="bf16", choices=("bf16", "fp32"))
    ap.add_argument("--copy-test", action="store_true", help="also an ICL variant whose reference is the target itself")
    ap.add_argument("--language-id", type=int, default=None, help="also test the language-tag prefix with this row")
    a = ap.parse_args(argv)

    wrapper = load_model(a.model, a.device, torch.bfloat16 if a.dtype == "bf16" else torch.float32)
    core = wrapper.model.eval()
    ids = SpecialIds.from_config(core.config)
    store = CodesStore(Path(a.data) / "codes")
    rows = load_manifest(a.data, a.split)[:a.n]
    results = {}
    variants = [("nsm_xvec", DataConfig(icl_p=0.0, language_p=0.0)),
                ("nsm_icl", DataConfig(icl_p=1.0, language_p=0.0)),
                ("stream_icl", DataConfig(icl_p=1.0, language_p=0.0, stream_p=1.0))]
    if a.language_id is not None:
        variants.append(("nsm_icl_langtag", DataConfig(icl_p=1.0, language_p=1.0, language_id=a.language_id)))
    if a.copy_test:
        variants.append(("nsm_icl_selfref", DataConfig(icl_p=1.0, language_p=0.0, ref_self=True)))
    for name, cfg in variants:
        ds = TTSDataset(rows, store, wrapper.processor, ids, cfg, seed=1, deterministic=True)
        loader = DataLoader(ds, batch_sampler=TokenBudgetSampler(ds.approx_len, a.max_tokens, 8, shuffle=False),
                            collate_fn=make_collate(ids), num_workers=2)
        if name == "nsm_icl":
            print(describe(ds[0], ids, wrapper.processor.tokenizer, limit=14) + "\n   ...", flush=True)
        t0 = time.time()
        results[name] = run(core, loader, a.device)
        print(f"{name:18s} {results[name]} ({time.time() - t0:.0f}s)", flush=True)
        if name == "nsm_icl":
            results["official_label_shift"] = run(core, loader, a.device, label_shift=-1)
            print(f"{'official_label_shift':18s} {results['official_label_shift']}", flush=True)
            results["official_no_text_proj"] = run(core, loader, a.device, text_projection=False)
            print(f"{'official_no_text_proj':18s} {results['official_no_text_proj']}", flush=True)
    ok = results["nsm_icl"]["acc0"] > 2 * results["official_label_shift"]["acc0"] and \
        results["nsm_icl"]["acc0"] > 1.5 * results["official_no_text_proj"]["acc0"]
    results["verdict"] = "layout matches inference" if ok else "CHECK FAILED: the layout does not beat the wrong variants"
    print(results["verdict"])
    (Path(a.data) / "alignment.json").write_text(json.dumps(results, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
