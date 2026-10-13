#!/usr/bin/env python3
"""Export a checkpoint as a self-contained servable model directory.

    python -m qwen_train.export --checkpoint runs/urdu_a/latest --out export/qwen3-tts-urdu-a [--copy-tokenizer]

Training checkpoints symlink `speech_tokenizer/` to the base model to save disk; --copy-tokenizer bundles it so the
directory can be moved to another machine. LoRA checkpoints (adapter/) are merged into full weights. The output
loads with `Qwen3TTSModel.from_pretrained(out)` and serves with `vllm serve <out> --omni` (or the tts-reference-voices
engine with TTS_ENGINE_MODEL=<out>).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

from .model_utils import load_model, save_checkpoint


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--copy-tokenizer", action="store_true")
    ap.add_argument("--device", default="cpu", help="cpu is enough for exporting")
    a = ap.parse_args(argv)
    ckpt = Path(a.checkpoint).resolve()
    wrapper = load_model(str(ckpt), a.device, torch.bfloat16)
    core = wrapper.model
    if (ckpt / "adapter").exists():
        from peft import PeftModel
        core.talker = PeftModel.from_pretrained(core.talker, str(ckpt / "adapter"))
        print("merging LoRA adapter")
    out = save_checkpoint(core, a.out, extra_config={"tts_model_type": "base"}, copy_tokenizer=a.copy_tokenizer)
    print(f"exported to {out}; languages: {core.config.talker_config.codec_language_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
