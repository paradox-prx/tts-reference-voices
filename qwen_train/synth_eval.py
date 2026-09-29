#!/usr/bin/env python3
"""Synthesise evaluation audio with a checkpoint, the way the server does it (voice clone with a reference clip).

    python -m qwen_train.synth_eval --model runs/x/latest --data data/urdu300 --out runs/x/eval_step_N \
        --splits eval,holdout --per-speaker 6 [--refs voices.json] [--language urdu]

For each chosen utterance the reference is another utterance of the same speaker (3-20 s), so every generated clip
has a ground-truth recording (WER/CER and similarity in score.py are against the real speaker). --refs adds
external reference voices (json: [{"name", "audio", "text", "language", "sentences": [..]}]) such as the server's
Shehbaz and Trump clips, to measure unseen-speaker cloning and English retention. Writes wav files and synth.jsonl.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import soundfile as sf
import torch

from .data import load_manifest
from .model_utils import load_model


def pick(rows: list[dict], per_speaker: int, seed: int) -> list[tuple[dict, dict]]:
    rng = random.Random(seed)
    by = {}
    for r in rows:
        by.setdefault(r["speaker"], []).append(r)
    out = []
    for spk, rs in sorted(by.items()):
        refs = [r for r in rs if 3.0 <= r["duration"] <= 20.0] or rs
        targets = rng.sample(rs, min(per_speaker, len(rs)))
        for t in targets:
            cands = [r for r in refs if r["id"] != t["id"]] or refs
            out.append((t, rng.choice(cands)))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", default=None)
    ap.add_argument("--splits", default="eval,holdout")
    ap.add_argument("--per-speaker", type=int, default=6)
    ap.add_argument("--refs", default=None, help="json with external reference voices and their sentences")
    ap.add_argument("--out", required=True)
    ap.add_argument("--language", default="Auto", help="language tag to send (Auto, or urdu after fine-tuning)")
    ap.add_argument("--nsm", action="store_true", default=True, help="non_streaming_mode (the server's Urdu setting)")
    ap.add_argument("--xvec-only", action="store_true", help="x-vector only, no in-context reference codes")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--max-new-tokens", type=int, default=1200)
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    wrapper = load_model(a.model, a.device)
    jobs = []  # (name, text, ref_audio, ref_text, language, meta)
    if a.data:
        for split in a.splits.split(","):
            rows = load_manifest(a.data, split)
            if not rows:
                continue
            for t, ref in pick(rows, a.per_speaker, a.seed):
                jobs.append((f"{split}_{t['speaker']}_{Path(t['audio']).stem}", t["text"], ref["audio"], ref["text"], a.language,
                             {"split": split, "speaker": t["speaker"], "target_id": t["id"], "target_audio": t["audio"],
                              "ref_id": ref["id"], "lang": "ur"}))
    if a.refs:
        for v in json.load(open(a.refs, encoding="utf-8")):
            for i, s in enumerate(v["sentences"]):
                jobs.append((f"ref_{v['name']}_{i}", s, v["audio"], v["text"], v.get("language", a.language),
                             {"split": "external", "speaker": v["name"], "ref_audio": v["audio"], "lang": v.get("lang", "ur")}))
    print(f"{len(jobs)} clips to synthesise", flush=True)
    t0 = time.time()
    with open(out / "synth.jsonl", "w", encoding="utf-8") as f:
        for i, (name, text, ref_audio, ref_text, language, meta) in enumerate(jobs):
            t1 = time.time()
            try:
                wavs, sr = wrapper.generate_voice_clone(text=text, language=language, ref_audio=ref_audio, ref_text=ref_text,
                                                        x_vector_only_mode=a.xvec_only, non_streaming_mode=a.nsm,
                                                        max_new_tokens=a.max_new_tokens)
                wav = wavs[0]
                path = out / f"{name}.wav"
                sf.write(path, wav, sr)
                rec = meta | {"file": str(path), "text": text, "seconds": round(len(wav) / sr, 2),
                              "gen_s": round(time.time() - t1, 2), "language": language}
            except Exception as exc:  # noqa: BLE001 - a failed clip is a result
                rec = meta | {"file": None, "text": text, "error": str(exc)[:300], "language": language}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if (i + 1) % 10 == 0 or i + 1 == len(jobs):
                print(f"  {i + 1}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
