#!/usr/bin/env python3
"""Score synthesised clips: intelligibility (Whisper large-v3 CER/WER against the text) and speaker similarity
(WavLM-base-plus-sv cosine against the reference recording), plus pace vs the ground-truth recording.

    python -m qwen_train.score --synth runs/x/eval_step_N/synth.jsonl [--asr large-v3] [--sim microsoft/wavlm-base-plus-sv]

Writes scores.jsonl and summary.json (per split / speaker: CER, WER, SIM, failures). Whisper is accented on Urdu
even for real recordings (the same scorer gives ~0.04 CER-nospace on this project's real clips vs ~0.14 on the
pretrained model's Urdu), so compare against the ground-truth row that score.py also transcribes (--score-gt).
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from .qc import cer, wer


def load_16k(path: str) -> np.ndarray:
    x, sr = sf.read(path, dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr == 16000:
        return x
    try:
        import soxr
        return soxr.resample(x, sr, 16000, quality="HQ").astype(np.float32)
    except ImportError:
        pass
    try:
        import librosa
        return librosa.resample(x, orig_sr=sr, target_sr=16000)
    except ImportError:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(sr, 16000)
        return resample_poly(x, 16000 // g, sr // g).astype(np.float32)


class Sim:
    def __init__(self, model: str, device: str):
        from transformers import AutoFeatureExtractor, WavLMForXVector
        self.fe = AutoFeatureExtractor.from_pretrained(model)
        self.m = WavLMForXVector.from_pretrained(model).to(device).eval()
        self.device = device
        self.cache = {}

    @torch.inference_mode()
    def embed(self, path: str) -> torch.Tensor:
        if path not in self.cache:
            x = load_16k(path)[: 16000 * 40]
            inp = self.fe(x, sampling_rate=16000, return_tensors="pt").to(self.device)
            e = self.m(**inp).embeddings[0]
            self.cache[path] = torch.nn.functional.normalize(e, dim=-1).cpu()
        return self.cache[path]

    def __call__(self, a: str, b: str) -> float:
        return float((self.embed(a) * self.embed(b)).sum())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--synth", required=True)
    ap.add_argument("--asr", default="large-v3")
    ap.add_argument("--asr-compute", default="float16")
    ap.add_argument("--beam", type=int, default=5)
    ap.add_argument("--sim", default="microsoft/wavlm-base-plus-sv", help="'' to skip similarity")
    ap.add_argument("--score-gt", action="store_true", help="also transcribe the ground-truth recordings")
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args(argv)

    rows = [json.loads(l) for l in open(a.synth, encoding="utf-8")]
    out_dir = Path(a.synth).parent
    from faster_whisper import WhisperModel
    asr = WhisperModel(a.asr, device=a.device, compute_type=a.asr_compute)
    sim = Sim(a.sim, a.device) if a.sim else None

    def transcribe(path: str, lang: str) -> str:
        segs, _ = asr.transcribe(path, language=lang, beam_size=a.beam, vad_filter=False, condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segs)

    scored = []
    for r in rows:
        s = dict(r)
        if r.get("file"):
            lang = r.get("lang", "ur")
            hyp = transcribe(r["file"], lang)
            s |= {"asr": hyp, "cer": round(cer(r["text"], hyp), 4), "wer": round(wer(r["text"], hyp), 4)}
            ref = r.get("target_audio") or r.get("ref_audio")
            if sim and ref:
                s["sim"] = round(sim(r["file"], ref), 4)
            if r.get("target_audio"):
                gt_len = sf.info(r["target_audio"]).duration
                s["pace_ratio"] = round(r["seconds"] / gt_len, 3)
                if a.score_gt:
                    hyp_gt = transcribe(r["target_audio"], lang)
                    s["gt_cer"] = round(cer(r["text"], hyp_gt), 4)
                    if sim and r.get("ref_id"):
                        s["gt_sim"] = None  # filled below when the reference recording is known
        scored.append(s)
    with open(out_dir / "scores.jsonl", "w", encoding="utf-8") as f:
        for s in scored:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    def agg(items):
        vals = lambda k: [x[k] for x in items if isinstance(x.get(k), (int, float))]  # noqa: E731
        d = {"n": len(items), "failed": sum(1 for x in items if not x.get("file"))}
        for k in ("cer", "wer", "sim", "pace_ratio", "gt_cer"):
            v = vals(k)
            if v:
                d[k + "_mean"] = round(float(np.mean(v)), 4)
                d[k + "_median"] = round(float(np.median(v)), 4)
        v = vals("cer")
        if v:
            d["severe_frac"] = round(float(np.mean([x > 0.5 for x in v])), 3)  # garbled / skipped
        return d
    groups = collections.defaultdict(list)
    for s in scored:
        groups[s.get("split", "?")].append(s)
        groups[f"{s.get('split', '?')}/{s.get('speaker', '?')}"].append(s)
    summary = {k: agg(v) for k, v in groups.items()}
    summary["all"] = agg(scored)
    json.dump(summary, open(out_dir / "summary.json", "w"), indent=1)
    for k, v in summary.items():
        if "/" not in k:
            print(k, v)
    return 0


if __name__ == "__main__":
    sys.exit(main())
