#!/usr/bin/env python3
"""Fine-tune Qwen3-TTS-12Hz-*-Base on a prepared dataset.

    python -m qwen_train.train --config configs/full_24gb.yaml --set data_dir=data/urdu300 --set out_dir=runs/urdu_a

Single GPU. Two precision modes: `bf16` keeps the weights in bf16 and uses optimi's AdamW with Kahan summation (so
the small updates of a low learning rate are not rounded away; ~14 GB for 1.7B before activations), `fp32-master`
keeps fp32 weights with bf16 autocast (torch AdamW; ~27 GB before activations, for 40-80 GB cards). `mode: lora`
trains fp32 adapters on frozen bf16 weights. Checkpoints are servable model directories; --resume continues from one
(optimizer state included when it was saved).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader

from .data import CodesStore, DataConfig, TTSDataset, TokenBudgetSampler, load_manifest, make_collate
from .layout import SpecialIds
from .model_utils import (TrainablePolicy, add_language, forward_losses, load_model, save_checkpoint,
                          set_gradient_checkpointing, set_trainable)

DEFAULTS = {
    "model": "Qwen/Qwen3-TTS-12Hz-1.7B-Base", "data_dir": "data/sample", "out_dir": "runs/run",
    "mode": "full", "precision": "bf16", "attn": "sdpa",
    "lr": 5e-6, "weight_decay": 0.01, "betas": [0.9, 0.98], "warmup_steps": 200, "schedule": "cosine", "min_lr_ratio": 0.1,
    "epochs": 3, "max_steps": 0, "max_tokens": 8000, "max_batch": 16, "grad_accum": 4, "clip": 1.0, "cp_weight": 0.3,
    "grad_checkpointing": True, "train_text_embedding": False, "train_codec_head": True,
    "lora": {"r": 64, "alpha": 128, "dropout": 0.05},
    "language": {"name": "urdu", "row": 2080, "p": 0.8, "init": "mean"},
    "icl": {"p": 0.7, "ref_min_s": 3.0, "ref_max_s": 20.0, "train_on_ref": False},
    "stream_p": 0.0, "max_frames": 400, "max_seq": 1400, "instruct_field": None,
    "eval_every": 500, "eval_max_batches": 60, "save_every": 1000, "keep_last": 2, "save_optimizer": False,
    "log_every": 10, "seed": 1234, "num_workers": 4, "tensorboard": True,
}


def load_config(path: str | None, sets: list[str]) -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))
    if path:
        user = yaml.safe_load(open(path)) or {}
        for k, v in user.items():
            cfg[k] = {**cfg[k], **v} if isinstance(v, dict) and isinstance(cfg.get(k), dict) else v
    for s in sets:
        k, _, v = s.partition("=")
        try:
            v = yaml.safe_load(v)
        except yaml.YAMLError:
            pass
        d = cfg
        parts = k.split(".")
        for p in parts[:-1]:
            d = d.setdefault(p, {})
        d[parts[-1]] = v
    return cfg


def lr_at(step: int, cfg: dict, total: int) -> float:
    if step < cfg["warmup_steps"]:
        return cfg["lr"] * (step + 1) / cfg["warmup_steps"]
    if cfg["schedule"] == "constant" or total <= cfg["warmup_steps"]:
        return cfg["lr"]
    frac = min(1.0, (step - cfg["warmup_steps"]) / max(1, total - cfg["warmup_steps"]))
    lo = cfg["lr"] * cfg["min_lr_ratio"]
    if cfg["schedule"] == "linear":
        return cfg["lr"] + (lo - cfg["lr"]) * frac
    return lo + (cfg["lr"] - lo) * 0.5 * (1 + math.cos(math.pi * frac))


def make_optimizer(params, cfg: dict):
    if cfg["precision"] == "bf16" and cfg["mode"] == "full":
        from optimi import AdamW  # Kahan-summation AdamW: correct updates on bf16 weights
        return AdamW(params, lr=cfg["lr"], betas=tuple(cfg["betas"]), weight_decay=cfg["weight_decay"], kahan_sum=True)
    return torch.optim.AdamW(params, lr=cfg["lr"], betas=tuple(cfg["betas"]), weight_decay=cfg["weight_decay"], fused=True)


@torch.no_grad()
def evaluate(core, loader, device, cfg) -> dict:
    core.eval()
    tot = {"talker_loss": 0.0, "cp_loss": 0.0, "acc0": 0.0, "cp_acc": 0.0, "n": 0, "frames": 0}
    for i, batch in enumerate(loader):
        if i >= cfg["eval_max_batches"]:
            break
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=cfg["precision"] != "bf16"):
            r = forward_losses(core, batch, device, cfg["cp_weight"])
        n, f = r["n_labels"], r["n_frames"]
        tot["talker_loss"] += float(r["talker_loss"]) * n
        tot["acc0"] += float(r["acc0"]) * n
        tot["cp_loss"] += float(r["cp_loss"]) * f
        tot["cp_acc"] += float(r["cp_acc"].mean()) * f
        tot["n"] += n
        tot["frames"] += f
    core.train()
    n, f = max(1, tot["n"]), max(1, tot["frames"])
    return {"eval/talker_loss": tot["talker_loss"] / n, "eval/acc0": tot["acc0"] / n, "eval/cp_loss": tot["cp_loss"] / f,
            "eval/cp_acc": tot["cp_acc"] / f, "eval/loss": tot["talker_loss"] / n + cfg["cp_weight"] * tot["cp_loss"] / f}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override a config key (dotted)")
    ap.add_argument("--resume", default=None, help="checkpoint directory to continue from")
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args(argv)
    cfg = load_config(a.config, a.set)
    out = Path(cfg["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    json.dump(cfg, open(out / "config.json", "w"), indent=1)
    random.seed(cfg["seed"]); np.random.seed(cfg["seed"]); torch.manual_seed(cfg["seed"])
    device = a.device
    log = open(out / "train.log", "a")

    def say(msg: str) -> None:
        print(msg, flush=True)
        log.write(msg + "\n"); log.flush()

    say(f"== {time.strftime('%Y-%m-%d %H:%M:%S')} config: {json.dumps(cfg)}")

    # model
    dtype = torch.bfloat16 if cfg["precision"] == "bf16" or cfg["mode"] == "lora" else torch.float32
    model_path = a.resume or cfg["model"]
    wrapper = load_model(model_path, device, dtype, cfg["attn"])
    core = wrapper.model
    lang = cfg["language"]
    lang_id = None
    if lang and lang.get("name"):
        reinit = add_language(core, lang["name"], int(lang["row"]), lang.get("init", "mean"))
        lang_id = int(lang["row"])
        say(f"language tag {lang['name']} -> row {lang_id} ({'initialised from the mean of the language rows' if reinit else 'kept'})")
    policy = TrainablePolicy(mode=cfg["mode"], train_text_embedding=cfg["train_text_embedding"],
                             train_codec_head=cfg["train_codec_head"], lora_r=cfg["lora"]["r"],
                             lora_alpha=cfg["lora"]["alpha"], lora_dropout=cfg["lora"]["dropout"])
    _, summary = set_trainable(core, policy)
    say(f"trainable {summary['trainable'] / 1e6:.1f}M of {summary['total'] / 1e6:.1f}M params ({summary['mode']})")
    if cfg["grad_checkpointing"]:
        set_gradient_checkpointing(core, True)
    core.train()
    ids = SpecialIds.from_config(core.config)

    # data
    store = CodesStore(Path(cfg["data_dir"]) / "codes")
    dcfg = DataConfig(icl_p=cfg["icl"]["p"], ref_min_s=cfg["icl"]["ref_min_s"], ref_max_s=cfg["icl"]["ref_max_s"],
                      train_on_ref=cfg["icl"]["train_on_ref"], language_id=lang_id, language_p=lang["p"] if lang_id else 0.0,
                      stream_p=cfg["stream_p"], max_frames=cfg["max_frames"], max_seq=cfg["max_seq"],
                      instruct_field=cfg["instruct_field"])
    train_ds = TTSDataset(load_manifest(cfg["data_dir"], "train"), store, wrapper.processor, ids, dcfg, cfg["seed"])
    eval_rows = load_manifest(cfg["data_dir"], "eval")
    eval_ds = TTSDataset(eval_rows, store, wrapper.processor, ids, dcfg, cfg["seed"], deterministic=True) if eval_rows else None
    ref_overhead = cfg["icl"]["p"] * min(1.0, cfg["icl"]["ref_max_s"] * 12.5 / max(1, np.mean(train_ds.approx_len)))
    sampler = TokenBudgetSampler(train_ds.approx_len, cfg["max_tokens"], cfg["max_batch"], cfg["seed"], True, ref_overhead)
    collate = make_collate(ids)
    train_loader = DataLoader(train_ds, batch_sampler=sampler, collate_fn=collate, num_workers=cfg["num_workers"],
                              persistent_workers=cfg["num_workers"] > 0, prefetch_factor=4 if cfg["num_workers"] else None)
    eval_loader = DataLoader(eval_ds, batch_sampler=TokenBudgetSampler(eval_ds.approx_len, cfg["max_tokens"], cfg["max_batch"], 0, False, ref_overhead),
                             collate_fn=collate, num_workers=2) if eval_ds else None
    steps_per_epoch = math.ceil(len(sampler) / cfg["grad_accum"])
    total_steps = cfg["max_steps"] or steps_per_epoch * cfg["epochs"]
    say(f"{len(sampler)} batches/epoch, {steps_per_epoch} optimizer steps/epoch, {total_steps} total steps")

    # optimizer
    params = [p for p in core.parameters() if p.requires_grad]
    opt = make_optimizer(params, cfg)
    step, epoch, micro = 0, 0, 0
    if a.resume and (Path(a.resume) / "trainer_state.json").exists():
        st = json.load(open(Path(a.resume) / "trainer_state.json"))
        step, epoch = st["step"], st["epoch"]
        if (Path(a.resume) / "optimizer.pt").exists():
            opt.load_state_dict(torch.load(Path(a.resume) / "optimizer.pt", map_location="cpu"))
            say(f"resumed optimizer state at step {step}")
        say(f"resumed from {a.resume}: step {step}, epoch {epoch}")
    writer = None
    if cfg["tensorboard"]:
        from torch.utils.tensorboard import SummaryWriter
        writer = SummaryWriter(str(out / "tb"))

    def save(tag: str) -> None:
        d = out / tag
        save_checkpoint(core, d, extra_config={"tts_model_type": "base"})
        json.dump({"step": step, "epoch": epoch, "config": cfg}, open(d / "trainer_state.json", "w"), indent=1)
        if cfg["save_optimizer"]:
            torch.save(opt.state_dict(), d / "optimizer.pt")
        (out / "latest").unlink(missing_ok=True)
        os.symlink(tag, out / "latest")
        kept = sorted([p for p in out.glob("step_*") if p.is_dir()], key=lambda p: int(p.name.split("_")[1]))
        for old in kept[:-cfg["keep_last"]]:
            shutil.rmtree(old)
        say(f"saved {d}")

    # loop
    t0 = time.time()
    tokens_seen, win = 0, {"loss": 0.0, "talker": 0.0, "cp": 0.0, "acc0": 0.0, "cp_acc": 0.0, "n": 0}
    done = step >= total_steps
    while not done:
        train_ds.set_epoch(epoch)
        sampler.set_epoch(epoch)
        for batch in train_loader:
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=cfg["precision"] != "bf16"):
                r = forward_losses(core, batch, device, cfg["cp_weight"])
            (r["loss"] / cfg["grad_accum"]).backward()
            micro += 1
            tokens_seen += r["n_tokens"]
            for k, v in (("loss", r["loss"]), ("talker", r["talker_loss"]), ("cp", r["cp_loss"]), ("acc0", r["acc0"]),
                         ("cp_acc", r["cp_acc"].mean())):
                win[k] += float(v)
            win["n"] += 1
            if micro % cfg["grad_accum"]:
                continue
            for g in opt.param_groups:
                g["lr"] = lr_at(step, cfg, total_steps)
            gn = torch.nn.utils.clip_grad_norm_(params, cfg["clip"]) if cfg["clip"] else torch.tensor(0.0)
            opt.step()
            opt.zero_grad(set_to_none=True)
            step += 1
            if step % cfg["log_every"] == 0:
                n = max(1, win["n"])
                el = time.time() - t0
                msg = (f"step {step}/{total_steps} ep {epoch} loss {win['loss'] / n:.4f} talker {win['talker'] / n:.4f} "
                       f"cp {win['cp'] / n:.4f} acc0 {win['acc0'] / n:.3f} cp_acc {win['cp_acc'] / n:.3f} gn {float(gn):.2f} "
                       f"lr {opt.param_groups[0]['lr']:.2e} {tokens_seen / el:.0f} tok/s "
                       f"mem {torch.cuda.max_memory_allocated() / 2**30:.1f}G eta {el / step * (total_steps - step) / 3600:.2f}h")
                say(msg)
                if writer:
                    for k in ("loss", "talker", "cp", "acc0", "cp_acc"):
                        writer.add_scalar(f"train/{k}", win[k] / n, step)
                    writer.add_scalar("train/lr", opt.param_groups[0]["lr"], step)
                    writer.add_scalar("train/grad_norm", float(gn), step)
                win = {k: 0.0 for k in win}
            if eval_loader is not None and step % cfg["eval_every"] == 0:
                ev = evaluate(core, eval_loader, device, cfg)
                say(f"eval step {step}: " + " ".join(f"{k.split('/')[1]} {v:.4f}" for k, v in ev.items()))
                if writer:
                    for k, v in ev.items():
                        writer.add_scalar(k, v, step)
            if step % cfg["save_every"] == 0:
                save(f"step_{step}")
            if step >= total_steps:
                done = True
                break
        else:
            epoch += 1
            if not cfg["max_steps"] and epoch >= cfg["epochs"]:
                done = True
    if not (out / f"step_{step}").exists():
        save(f"step_{step}")
    if eval_loader is not None:
        ev = evaluate(core, eval_loader, device, cfg)
        say("final eval: " + " ".join(f"{k.split('/')[1]} {v:.4f}" for k, v in ev.items()))
        json.dump(ev, open(out / "final_eval.json", "w"), indent=1)
    say(f"done in {(time.time() - t0) / 3600:.2f} h, {tokens_seen / 1e6:.1f}M tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
