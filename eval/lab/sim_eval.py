#!/usr/bin/env python3
"""Speaker-similarity half of the TTS quality evaluation.

Backends (cosine similarity of L2-normalized speaker embeddings, 16 kHz mono input):
  base  = microsoft/wavlm-base-plus-sv (transformers WavLMForXVector)      -> continuity with NOTES' "WavLM 0.974 / <0.88"
  large = seed-tts-eval SIM: UniSpeech WavLM-Large + ECAPA-TDNN (torch-native port, trust_remote_code, pinned local dir)

Leading/trailing silence is trimmed with the same energy VAD as tts_checks.audio_checks before embedding.
Per take it writes sim_prompt_<b> (vs references/qwen3-tts.wav) and sim_heldout_<b> (vs the centroid of the voice's
clips that are NOT in the prompt; absent when every clip is in the prompt, e.g. trump).

    python sim_eval.py --results results/<ts> --device cuda --backends base,large
    python sim_eval.py --calibrate --device cpu          # anchors on the real clips (what FINDINGS §6 reports)
"""
from __future__ import annotations

import argparse
import json
import os
import time
import wave
from pathlib import Path

import numpy as np
import torch

VOICES = Path(os.environ.get("VOICES_DIR", "/home/vector/tts-reference-voices/voices"))
MODELS = Path(os.environ.get("SIM_MODELS", Path(__file__).resolve().parents[1] / "models"))


def read_wav16(path: Path, trim: bool = True) -> np.ndarray:
    with wave.open(str(path)) as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        a = np.frombuffer(w.readframes(n), dtype={2: np.int16, 4: np.int32}[sw]).astype(np.float32)
    a = a.reshape(-1, ch).mean(axis=1) if ch > 1 else a
    a /= float(2 ** (8 * sw - 1))
    if trim:                                               # energy trim, 20 ms frames, p95 - 35 dB, floor -60 dBFS
        f = int(sr * 0.02)
        fr = a[: len(a) // f * f].reshape(-1, f)
        db = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-10)
        on = np.flatnonzero(db > max(-60.0, np.percentile(db, 95) - 35.0))
        if len(on):
            a = a[max(0, on[0] - 5) * f: min(len(fr), on[-1] + 6) * f]
    import torchaudio.functional as AF
    return AF.resample(torch.from_numpy(a), sr, 16000).numpy() if sr != 16000 else a


class Embedder:
    def __init__(self, backend: str, device: str) -> None:
        self.backend, self.device = backend, device
        if backend == "base":
            from transformers import Wav2Vec2FeatureExtractor, WavLMForXVector
            d = MODELS / "wavlm-base-plus-sv"
            self.fe = Wav2Vec2FeatureExtractor.from_pretrained(d)
            self.model = WavLMForXVector.from_pretrained(d).eval().to(device)
        elif backend == "large":
            import inspect
            from types import MethodType

            from transformers import AutoModel
            from transformers.models.wavlm.modeling_wavlm import WavLMAttention
            self.model = AutoModel.from_pretrained(MODELS / "beatrice", trust_remote_code=True).eval().to(device)
            # The port patches WavLMAttention.torch_multi_head_self_attention with the transformers-4.x signature
            # (..., output_attentions). transformers 5.x dropped that argument -> TypeError. Re-patch with an
            # adapter that merges the padding mask into the position bias exactly like the port does.
            if "output_attentions" not in inspect.signature(WavLMAttention.torch_multi_head_self_attention).parameters:
                orig = WavLMAttention.torch_multi_head_self_attention

                def adapter(att, hidden_states, attention_mask, gated_position_bias):
                    if attention_mask is not None:
                        keep = attention_mask.bool()
                        b, n = keep.shape
                        pad = hidden_states.new_zeros((b, 1, 1, n)).masked_fill_(~keep[:, None, None, :], -torch.inf)
                        gated_position_bias = (gated_position_bias.view(b, att.num_heads, n, n) + pad).view(b * att.num_heads, n, n)
                    return orig(att, hidden_states, None, gated_position_bias)

                for layer in self.model.wavlm.encoder.layers:
                    layer.attention.torch_multi_head_self_attention = MethodType(adapter, layer.attention)
        else:
            raise ValueError(backend)

    @torch.inference_mode()
    def __call__(self, wav16: np.ndarray) -> np.ndarray:
        if self.backend == "base":
            x = self.fe(wav16, sampling_rate=16000, return_tensors="pt").to(self.device)
            e = self.model(**x).embeddings[0]
        else:
            w = torch.from_numpy(wav16).float().to(self.device)
            e = self.model(w[None], sampling_rate=16000, input_lengths=torch.tensor([w.numel()], device=self.device)).embeddings[0]
        e = torch.nn.functional.normalize(e.float(), dim=-1)
        return e.cpu().numpy()


def voice_refs(voice: str) -> tuple[Path, list[Path]]:
    folder = VOICES / voice
    refs = json.loads((folder / "references" / "references.json").read_text(encoding="utf-8"))["qwen3-tts"]
    in_prompt = set(refs["clips"])
    clips = sorted(p for p in folder.glob("*.wav"))
    return folder / "references" / refs["file"], [p for p in clips if p.name not in in_prompt]


def cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def calibrate(backends: list[str], device: str) -> None:
    sh_prompt, sh_held = voice_refs("shehbaz")
    tr_prompt, _ = voice_refs("trump")
    tr = read_wav16(VOICES / "trump" / "trump_01.wav")
    for b in backends:
        t0 = time.perf_counter()
        emb = Embedder(b, device)
        load = time.perf_counter() - t0
        t0 = time.perf_counter()
        E = {p.name: emb(read_wav16(p)) for p in sorted((VOICES / "shehbaz").glob("*.wav"))}
        P = emb(read_wav16(sh_prompt))
        held = [E[p.name] for p in sh_held]
        cen = np.mean(held, axis=0)
        T = emb(tr)
        half = len(tr) // 2
        T1, T2 = emb(tr[:half]), emb(tr[half:])
        s02 = read_wav16(VOICES / "shehbaz" / "shehbaz_02.wav")
        crops = {f"{sec}s": cos(emb(s02[: sec * 16000]), P) for sec in (2, 3, 5)}
        audio_s = sum(len(read_wav16(p)) for p in sorted((VOICES / "shehbaz").glob("*.wav"))) / 16000 + 28 + 23 * 2 + 10
        took = time.perf_counter() - t0
        res = {
            "backend": b, "device": device, "load_s": round(load, 1), "embed_s": round(took, 1),
            "x_realtime": round(audio_s / took, 1),
            "shehbaz_heldout_clip_vs_prompt": {k: round(cos(E[k], P), 3) for k in (p.name for p in sh_held)},
            "shehbaz_inprompt_clip_vs_prompt": {k: round(cos(v, P), 3) for k, v in E.items() if k not in {p.name for p in sh_held}},
            "shehbaz_heldout_leave1out_vs_centroid": {p.name: round(cos(E[p.name], np.mean([E[q.name] for q in sh_held if q != p], axis=0)), 3) for p in sh_held},
            "shehbaz_prompt_vs_heldout_centroid": round(cos(P, cen), 3),
            "trump_half1_vs_half2": round(cos(T1, T2), 3),
            "trump_clip_vs_prompt(same audio)": round(cos(T, emb(read_wav16(tr_prompt))), 3),
            "cross_trump_vs_shehbaz_prompt": round(cos(T, P), 3),
            "cross_trump_vs_shehbaz_clips": {k: round(cos(T, v), 3) for k, v in E.items()},
            "short_crop_shehbaz02_vs_prompt": {k: round(v, 3) for k, v in crops.items()},
        }
        print(json.dumps(res, ensure_ascii=False, indent=1), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--backends", default="base,large")
    ap.add_argument("--threads", type=int, default=8)
    args = ap.parse_args()
    torch.set_num_threads(args.threads)
    backends = args.backends.split(",")
    if args.calibrate:
        return calibrate(backends, args.device)
    base = Path(args.results)
    rows = [json.loads(l) for l in open(base / "requests.jsonl", encoding="utf-8")]
    rows = [r for r in rows if r.get("file") and not r.get("error")]
    out = {id(r): {} for r in rows}
    for b in backends:
        emb = Embedder(b, args.device)
        anchors = {}
        for v in sorted({r["voice"] for r in rows}):
            prompt, held = voice_refs(v)
            anchors[v] = (emb(read_wav16(prompt)), np.mean([emb(read_wav16(p)) for p in held], axis=0) if held else None)
        for r in rows:
            wav = read_wav16(base / r["file"])
            if len(wav) < 2 * 16000:                        # < 2 s of speech: embedding too noisy to gate on
                continue
            e = emb(wav)
            p, c = anchors[r["voice"]]
            out[id(r)][f"sim_prompt_{b}"] = round(cos(e, p), 4)
            if c is not None:
                out[id(r)][f"sim_heldout_{b}"] = round(cos(e, c), 4)
    with open(base / "sim_eval.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"run": r["run"], "idx": r["idx"], "take": r.get("take", 0), "file": r["file"],
                                **out[id(r)]}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
