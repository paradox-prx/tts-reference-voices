#!/usr/bin/env python3
"""Extract the 12.5 Hz codec codes (16 codebooks) and the speaker embedding (x-vector) of every utterance.

    python -m qwen_train.prepare --manifest data/x/manifest.jsonl --out data/x/codes --device cuda

Writes shards shard_NNNN.npz (2,000 utterances each, resumable: existing shards are skipped) with
    ids        [n]            utterance ids
    offsets    [n+1]          frame offsets into codes
    codes      [frames, 16]   int16
    xvec       [n, 2048]      float16 speaker embeddings from the model's frozen speaker encoder (24 kHz, 128 mels)
    seconds    [n]            audio length
and index.json with the totals. data.py loads every shard.

Audio is read with soundfile, mixed to mono and resampled to 24 kHz in worker threads, then encoded in batches of
similar length. The x-vector uses exactly extract_speaker_embedding() of the model, so training conditions match
inference (the same function computes the reference clip's embedding when serving).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

TARGET_SR = 24000
SHARD = 2000


def load_24k(path: str) -> np.ndarray:
    import librosa
    x, sr = sf.read(path, dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != TARGET_SR:
        x = librosa.resample(x, orig_sr=sr, target_sr=TARGET_SR, res_type="soxr_hq")
    return np.ascontiguousarray(np.clip(x, -1.0, 1.0), dtype=np.float32)  # resampling can overshoot by ~0.02


def load_speaker_encoder(model_path: str, device: str, dtype):
    """Only the speaker encoder of the Base model (76 small tensors), not the 1.7B talker."""
    from qwen_tts.core.models.configuration_qwen3_tts import Qwen3TTSConfig
    from qwen_tts.core.models.modeling_qwen3_tts import Qwen3TTSSpeakerEncoder
    from safetensors import safe_open
    from huggingface_hub import snapshot_download
    local = model_path if os.path.isdir(model_path) else snapshot_download(model_path, allow_patterns=["*.json", "*.safetensors", "*.txt"])
    config = Qwen3TTSConfig.from_pretrained(local)
    enc = Qwen3TTSSpeakerEncoder(config.speaker_encoder_config)
    state = {}
    for f in glob.glob(os.path.join(local, "*.safetensors")):
        with safe_open(f, "pt") as st:
            for k in st.keys():
                if k.startswith("speaker_encoder."):
                    state[k[len("speaker_encoder."):]] = st.get_tensor(k)
    missing, unexpected = enc.load_state_dict(state, strict=False)
    assert not missing and not unexpected, (missing, unexpected)
    return enc.to(device=device, dtype=dtype).eval(), config


@torch.inference_mode()
def xvector(enc, wav: np.ndarray, device: str, dtype) -> torch.Tensor:
    from qwen_tts.core.models.modeling_qwen3_tts import mel_spectrogram
    mels = mel_spectrogram(torch.from_numpy(wav).unsqueeze(0), n_fft=1024, num_mels=128, sampling_rate=TARGET_SR,
                           hop_size=256, win_size=1024, fmin=0, fmax=12000).transpose(1, 2)
    return enc(mels.to(device).to(dtype))[0].float().cpu()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tokenizer", default="Qwen/Qwen3-TTS-Tokenizer-12Hz")
    ap.add_argument("--model", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base", help="for the speaker encoder")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-xvec", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)

    from qwen_tts import Qwen3TTSTokenizer
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in open(a.manifest, encoding="utf-8")]
    if a.limit:
        rows = rows[:a.limit]
    rows.sort(key=lambda r: r["duration"])  # similar lengths per batch: less padding
    shards = [rows[i:i + SHARD] for i in range(0, len(rows), SHARD)]
    todo = [(i, s) for i, s in enumerate(shards) if not (out / f"shard_{i:04d}.npz").exists()]
    print(f"{len(rows)} utterances, {len(shards)} shards, {len(todo)} to do", flush=True)
    if not todo:
        return write_index(out)

    tok = Qwen3TTSTokenizer.from_pretrained(a.tokenizer, device_map=a.device)
    dtype = torch.bfloat16 if a.device.startswith("cuda") else torch.float32
    enc = None if a.no_xvec else load_speaker_encoder(a.model, a.device, dtype)[0]
    t0 = time.time()
    done_utts = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for si, shard in todo:
            ids, offsets, codes, xvecs, seconds = [], [0], [], [], []
            wavs = ex.map(lambda r: load_24k(r["audio"]), shard)  # decoded ahead of the GPU by the threads
            batch_rows, batch_wavs = [], []

            def flush():
                enc_res = tok.encode(batch_wavs, sr=TARGET_SR)
                for r, w, c in zip(batch_rows, batch_wavs, enc_res.audio_codes):
                    c = c.cpu().numpy().astype(np.int16)  # [T, 16]
                    assert c.ndim == 2 and c.shape[1] == 16, c.shape
                    ids.append(r["id"]); codes.append(c); offsets.append(offsets[-1] + len(c)); seconds.append(len(w) / TARGET_SR)
                    if enc is not None:
                        xvecs.append(xvector(enc, w, a.device, dtype).numpy().astype(np.float16))
                batch_rows.clear(); batch_wavs.clear()

            for r, w in zip(shard, wavs):
                batch_rows.append(r); batch_wavs.append(w)
                if len(batch_rows) >= a.batch:
                    flush()
            if batch_rows:
                flush()
            np.savez(out / f"shard_{si:04d}.npz", ids=np.array(ids), offsets=np.array(offsets, dtype=np.int64),
                     codes=np.concatenate(codes, axis=0), xvec=np.stack(xvecs) if xvecs else np.zeros((0, 0), np.float16),
                     seconds=np.array(seconds, dtype=np.float32))
            done_utts += len(shard)
            el = time.time() - t0
            fps = sum(len(c) for c in codes) / sum(seconds)
            print(f"  shard {si} done: {done_utts}/{len(rows)} utts, {el:.0f}s, {done_utts / el:.1f} utt/s, "
                  f"{fps:.2f} frames/s of audio", flush=True)
    return write_index(out)


def write_index(out: Path) -> int:
    n_utt = n_frames = 0
    secs = 0.0
    for f in sorted(out.glob("shard_*.npz")):
        z = np.load(f)
        n_utt += len(z["ids"]); n_frames += int(z["offsets"][-1]); secs += float(z["seconds"].sum())
    info = {"utterances": n_utt, "frames": n_frames, "hours": round(secs / 3600, 3),
            "frames_per_second": round(n_frames / secs, 3) if secs else None}
    (out / "index.json").write_text(json.dumps(info, indent=1))
    print(info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
