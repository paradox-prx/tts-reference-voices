#!/usr/bin/env python3
"""Re-tag speakers by voice when the labels cannot be trusted (same label = different people inside a folder, the same
person under different labels across batches).

    python -m qwen_train.speakers embed   --manifest data/x/manifest.jsonl --out data/x/spk [--device cuda]
    python -m qwen_train.speakers cluster --out data/x/spk [--threshold 0.10] [--min-cluster-hours 0.3]
    python -m qwen_train.derive ... --speaker-map data/x/spk/assignments.jsonl

embed: a speaker-verification embedding per clip (WavLM-base-plus-sv, 512-d, on the middle 10 s), plus one per
3 s window (up to 6) to flag clips that contain more than one voice. Resumable (embeddings.npz).

cluster: spherical k-means over-clustering (~1 centroid per 150 clips), then average-linkage agglomerative clustering
of the centroids across ALL folders with a cosine-distance threshold, then every clip is assigned to the nearest
merged speaker. Writes
    assignments.jsonl   id, speaker (spk_NNN), cos to its speaker, margin to the second-best, multi_voice flag,
                        original label/folder
    clusters.md         per new speaker: clips, hours, cohesion, and which original labels/folders it came from
    merges.tsv          the centroid merge distances (a gap shows the natural speaker count)
    listen/spk_NNN/     symlinks to 5 clips per speaker, to check by ear

Clips with low confidence (cos < --min-conf) or several voices are kept for training with their own voice but marked
ref_ok=false, so they are never used as the "same speaker" reference of another clip.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

DEFAULT_MODEL = os.environ.get("SPK_MODEL", "microsoft/wavlm-base-plus-sv")
SR = 16000


def load_16k(path: str, max_s: float = 60.0) -> np.ndarray:
    x, sr = sf.read(path, dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != SR:
        import soxr
        x = soxr.resample(x, sr, SR, quality="HQ")
    return x[: int(max_s * SR)].astype(np.float32)


def bounded_map(ex, fn, items, ahead: int):
    """Like ex.map(fn, items) in order, but with at most `ahead` items loaded and waiting (Executor.map submits every
    item at once, which kept 35k decoded clips, ~25 GB, in RAM)."""
    import collections as _c
    it = iter(items)
    q = _c.deque()
    for x in it:
        q.append(ex.submit(fn, x))
        if len(q) >= ahead:
            break
    while q:
        yield q.popleft().result()
        nxt = next(it, None)
        if nxt is not None:
            q.append(ex.submit(fn, nxt))


def middle(x: np.ndarray, seconds: float) -> np.ndarray:
    n = int(seconds * SR)
    if len(x) <= n:
        return x
    s = (len(x) - n) // 2
    return x[s:s + n]


def windows(x: np.ndarray, win_s: float = 3.0, max_n: int = 6) -> list[np.ndarray]:
    n = int(win_s * SR)
    if len(x) < 2 * n:
        return []
    starts = np.linspace(0, len(x) - n, num=min(max_n, len(x) // n)).astype(int)
    return [x[s:s + n] for s in starts]


class Embedder:
    def __init__(self, model: str, device: str):
        from transformers import AutoFeatureExtractor, WavLMForXVector
        self.fe = AutoFeatureExtractor.from_pretrained(model)
        self.m = WavLMForXVector.from_pretrained(model).to(device).eval()
        self.device = device

    @torch.inference_mode()
    def __call__(self, wavs: list[np.ndarray]) -> np.ndarray:
        inp = self.fe(wavs, sampling_rate=SR, return_tensors="pt", padding=True, return_attention_mask=True).to(self.device)
        e = self.m(**inp).embeddings
        return torch.nn.functional.normalize(e.float(), dim=-1).cpu().numpy()


def cmd_embed_large(a) -> int:
    """Clip embeddings from the seed-tts-eval SIM model (UniSpeech WavLM-Large + ECAPA-TDNN, via tts_qc.sim). Much sharper
    on same-gender, same-accent voices than WavLM-base-sv. Batched WITHOUT padding (the model was calibrated on unpadded
    single clips): every clip is cut to the middle min(clip_s, whole seconds of its length) and batched with clips of the
    same cut length, so each batch is a plain [B, T] tensor. Needs the eval venv: PYTHONPATH=.:<server>/qc <server>/eval/run.sh"""
    from tts_qc.sim import Embedder as SimEmbedder
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in open(a.manifest, encoding="utf-8")]
    store = out / "embeddings_large.npz"
    ids, E = [], []
    if store.exists():
        z = np.load(store, allow_pickle=True)
        ids, E = list(z["ids"]), list(z["emb"])
    done = set(ids)
    todo = [r for r in rows if r["id"] not in done]
    print(f"{len(rows)} clips, {len(done)} embedded (large), {len(todo)} to do, batch {a.batch}", flush=True)
    if todo:
        emb = SimEmbedder("large", a.models_dir, device=a.device)
        torch = emb._torch
        if a.tf32:  # 1.28x on a 3090; embeddings agree with fp32 to cos >= 0.9999
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        cut_s = lambda r: int(min(a.clip_s, max(1.0, float(r.get("duration") or a.clip_s))))  # noqa: E731
        todo.sort(key=cut_s)  # equal cut lengths are adjacent: batches need no padding
        t0 = time.time()
        buckets: dict[int, list] = {}

        def run(batch):
            x = torch.from_numpy(np.stack([w for _, w in batch])).to(emb.device)
            with torch.inference_mode():
                e = emb.model(x, sampling_rate=16000,
                              input_lengths=torch.full((len(batch),), x.shape[1], device=emb.device)).embeddings
            e = torch.nn.functional.normalize(e.float(), dim=-1).cpu().numpy()
            for (r, _), v in zip(batch, e):
                ids.append(r["id"]); E.append(v.astype(np.float16))

        def load(r):
            x = load_16k(r["audio"])
            n = cut_s(r) * SR
            if len(x) < n:  # header duration a little longer than the samples: pad by repeating the start
                x = np.concatenate([x, x[:n - len(x)]]) if len(x) else np.zeros(n, np.float32)
            return r, middle(x, cut_s(r))[:n]

        n_done = 0
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            for r, w in bounded_map(ex, load, todo, 4 * a.batch):
                b = buckets.setdefault(len(w), [])
                b.append((r, w))
                if len(b) >= a.batch:
                    run(b); n_done += len(b); buckets[len(w)] = []
                    if n_done % (a.batch * 30) < a.batch:
                        np.savez(store, ids=np.array(ids), emb=np.stack(E))
                        el = time.time() - t0
                        print(f"  {n_done}/{len(todo)} {el:.0f}s ({n_done / el:.1f} clips/s)", flush=True)
            for b in buckets.values():
                if b:
                    run(b); n_done += len(b)
        np.savez(store, ids=np.array(ids), emb=np.stack(E))
        el = time.time() - t0
        print(f"  {n_done}/{len(todo)} {el:.0f}s ({n_done / el:.1f} clips/s)", flush=True)
    meta = {r["id"]: {k: r.get(k) for k in ("speaker", "source", "audio", "duration")} for r in rows}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    return 0


def cmd_embed(a) -> int:
    if a.backend == "large":
        return cmd_embed_large(a)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in open(a.manifest, encoding="utf-8")]
    store = out / "embeddings.npz"
    done_ids, E, W, WN = [], [], [], []
    if store.exists():
        z = np.load(store, allow_pickle=True)
        done_ids, E, W, WN = list(z["ids"]), list(z["emb"]), list(z["win"]), list(z["win_n"])
    done = set(done_ids)
    todo = [r for r in rows if r["id"] not in done]
    print(f"{len(rows)} clips, {len(done)} embedded, {len(todo)} to do", flush=True)
    if todo:
        emb = Embedder(a.model, a.device)
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            batch = []
            def flush():
                clips = [middle(x, a.clip_s) for _, x in batch]
                wins = [windows(x) for _, x in batch]
                ce = emb(clips)
                flat = [w for ws in wins for w in ws]
                we = emb(flat) if flat else np.zeros((0, ce.shape[1]), np.float32)
                k = 0
                for (r, _), c, ws in zip(batch, ce, wins):
                    wv = np.zeros((6, ce.shape[1]), np.float16)
                    wv[:len(ws)] = we[k:k + len(ws)]
                    k += len(ws)
                    done_ids.append(r["id"]); E.append(c.astype(np.float16)); W.append(wv); WN.append(len(ws))
                batch.clear()
            for i, (r, x) in enumerate(zip(todo, bounded_map(ex, lambda r: load_16k(r["audio"]), todo, 4 * a.batch)), 1):
                batch.append((r, x))
                if len(batch) >= a.batch:
                    flush()
                if i % 2000 == 0 or i == len(todo):
                    if batch:
                        flush()
                    np.savez(store, ids=np.array(done_ids), emb=np.stack(E), win=np.stack(W), win_n=np.array(WN))
                    el = time.time() - t0
                    print(f"  {i}/{len(todo)} {el:.0f}s ({i / el:.1f} clips/s)", flush=True)
    meta = {r["id"]: {k: r.get(k) for k in ("speaker", "source", "audio", "duration")} for r in rows}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    return 0


def spherical_kmeans(X: np.ndarray, k: int, iters: int = 25, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    C = X[rng.choice(len(X), size=k, replace=False)].copy()
    for _ in range(iters):
        lab = (X @ C.T).argmax(1)
        for j in range(k):
            m = X[lab == j]
            if len(m):
                c = m.mean(0)
                C[j] = c / (np.linalg.norm(c) + 1e-9)
            else:
                C[j] = X[rng.integers(len(X))]
    return C, (X @ C.T).argmax(1)


def cmd_cluster(a) -> int:
    from scipy.cluster.hierarchy import fcluster, linkage
    out = Path(a.out)
    z = np.load(out / "embeddings.npz", allow_pickle=True)
    meta = json.loads((out / "meta.json").read_text())
    ids = [str(i) for i in z["ids"]]
    X = z["emb"].astype(np.float32)
    W, WN = z["win"].astype(np.float32), z["win_n"]
    Xb = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)  # base embeddings: for the multi-voice windows
    if a.embeddings == "large":
        zl = np.load(out / "embeddings_large.npz", allow_pickle=True)
        pos = {str(k): i for i, k in enumerate(zl["ids"])}
        missing = [i for i in ids if i not in pos]
        if missing:
            raise SystemExit(f"{len(missing)} clips have no large embedding yet: run embed --backend large")
        X = zl["emb"].astype(np.float32)[[pos[i] for i in ids]]
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    if a.threshold is None:
        a.threshold = 0.35 if a.embeddings == "large" else 0.10
    dur = np.array([meta[i]["duration"] or 0.0 for i in ids])
    # multi-voice clips: some window far from the clip's own embedding
    win_min = np.ones(len(ids))
    for i in range(len(ids)):
        if WN[i] >= 2:
            w = W[i, :WN[i]].copy()
            w /= np.linalg.norm(w, axis=1, keepdims=True) + 1e-9
            win_min[i] = float((w @ Xb[i]).min())
    multi = win_min < a.multi_cos
    within = []  # same-speaker reference: 3 s windows of the same clip
    for i in range(len(ids)):
        if WN[i] >= 2 and not multi[i]:
            w = W[i, :WN[i]] / (np.linalg.norm(W[i, :WN[i]], axis=1, keepdims=True) + 1e-9)
            sw = w @ w.T
            within.extend(sw[np.triu_indices(len(w), 1)].tolist())
    within = np.array(within) if within else np.array([1.0])
    # stage 1: over-cluster the single-voice clips
    base = np.where(~multi)[0]
    k = max(8, min(2000, len(base) // a.clips_per_centroid))
    C, lab1 = spherical_kmeans(X[base], k, seed=a.seed)
    sizes = np.bincount(lab1, minlength=k)
    keep = sizes >= 3
    C = C[keep]
    # stage 2: agglomerative merge of centroids (cosine distance, average linkage)
    Z = linkage(C, method="average", metric="cosine")
    heights = Z[:, 2]
    lab2 = fcluster(Z, t=a.threshold, criterion="distance") - 1
    n_spk = lab2.max() + 1
    S = np.stack([C[lab2 == s].mean(0) for s in range(n_spk)])
    S /= np.linalg.norm(S, axis=1, keepdims=True)
    # stage 3: assign every clip; recompute speaker centroids from their clips once
    sims = X @ S.T
    lab = sims.argmax(1)
    for _ in range(2):
        S = np.stack([X[lab == s].mean(0) if (lab == s).any() else S[s] for s in range(n_spk)])
        S /= np.linalg.norm(S, axis=1, keepdims=True)
        sims = X @ S.T
        lab = sims.argmax(1)
    top2 = np.sort(sims, axis=1)[:, -2:] if n_spk > 1 else np.stack([np.zeros(len(X)), sims[:, 0]], 1)
    conf, margin = top2[:, 1], top2[:, 1] - top2[:, 0]
    # tiny speakers (under --min-cluster-hours) are kept but not used as references
    hours = np.array([dur[lab == s].sum() / 3600 for s in range(n_spk)])
    order = np.argsort(-hours)  # spk_000 = the largest
    rename = {int(s): f"spk_{r:03d}" for r, s in enumerate(order)}
    ref_ok = (~multi) & (conf >= a.min_conf) & (hours[lab] >= a.min_cluster_hours)

    with open(out / "assignments.jsonl", "w", encoding="utf-8") as f:
        for i, uid in enumerate(ids):
            m = meta[uid]
            f.write(json.dumps({"id": uid, "speaker": rename[int(lab[i])], "conf": round(float(conf[i]), 4),
                                "margin": round(float(margin[i]), 4), "multi_voice": bool(multi[i]),
                                "win_min_cos": round(float(win_min[i]), 4), "ref_ok": bool(ref_ok[i]),
                                "orig_speaker": m["speaker"], "source": m["source"], "audio": m["audio"]},
                               ensure_ascii=False) + "\n")
    with open(out / "merges.tsv", "w") as f:
        f.write("n_clusters_after\tmerge_distance\n")
        for j, h in enumerate(heights):
            f.write(f"{len(C) - j - 1}\t{h:.4f}\n")
    # report
    lines = [f"# speaker re-tagging: {len(ids)} clips, {dur.sum() / 3600:.1f} h", "",
             f"threshold {a.threshold} (cosine distance between centroid groups), {k} fine centroids -> **{n_spk} speakers**; "
             f"multi-voice clips {int(multi.sum())} ({multi.mean():.1%}); low-confidence clips (cos < {a.min_conf}) "
             f"{int((conf < a.min_conf).sum())}; usable as references {int(ref_ok.sum())} ({ref_ok.mean():.1%})", "",
             f"same-speaker reference (3 s windows of one clip): cos p5 {np.percentile(within, 5):.3f}, "
             f"p50 {np.median(within):.3f}", "",
             "speaker count at other thresholds: " + ", ".join(
                 f"{t}: {int(fcluster(Z, t=t, criterion='distance').max())}"
                 for t in ((0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6) if a.embeddings == "large"
                           else (0.03, 0.05, 0.07, 0.1, 0.12, 0.15, 0.2))), "",
             "largest centroid merge distances (a jump = the natural speaker count): "
             + ", ".join(f"{h:.3f}" for h in sorted(heights)[-15:]), "",
             "| new speaker | clips | hours | cohesion (mean cos) | nearest other speaker (cos) | came from (folder / original label: clips) |",
             "|---|---|---|---|---|---|"]
    SS = S @ S.T
    np.fill_diagonal(SS, -1)
    for s in order:
        mask = lab == s
        src = collections.Counter(f"{meta[ids[i]]['source'].split('/')[0]} / {meta[ids[i]]['speaker']}" for i in np.where(mask)[0])
        near = int(SS[s].argmax()) if n_spk > 1 else s
        lines.append(f"| {rename[int(s)]} | {int(mask.sum())} | {hours[s]:.2f} | {float(conf[mask].mean()):.3f} | "
                     f"{rename[near]} ({SS[s, near]:.2f}) | " + "; ".join(f"{k}: {v}" for k, v in src.most_common(6)) + " |")
    # the pairs most likely to be the same person: listen to these first
    pairs = sorted(((float(SS[i, j]), i, j) for i in range(n_spk) for j in range(i + 1, n_spk)), reverse=True)[:12]
    lines += ["", "Closest pairs of new speakers (check by ear: listen/<a>/ vs listen/<b>/; merge if same person):", "",
              "| a | b | cos | a hours | b hours |", "|---|---|---|---|---|"]
    for c_, i, j in pairs:
        lines.append(f"| {rename[i]} | {rename[j]} | {c_:.3f} | {hours[i]:.2f} | {hours[j]:.2f} |")
    # reverse view: how each original label splits
    lines += ["", "| folder / subfolder / original label | clips | split into new speakers |", "|---|---|---|"]
    orig = collections.defaultdict(collections.Counter)
    for i, uid in enumerate(ids):
        orig[f"{meta[uid]['source'].split('/')[0]} / {Path(meta[uid]['audio']).parent.name} / {meta[uid]['speaker']}"][rename[int(lab[i])]] += 1
    for k_, c in sorted(orig.items()):
        lines.append(f"| {k_} | {sum(c.values())} | " + ", ".join(f"{s}: {v}" for s, v in c.most_common(6)) + " |")
    (out / "clusters.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:5]))
    # listening samples: 5 most typical clips per speaker
    listen = out / "listen"
    if listen.exists():
        for p in listen.rglob("*"):
            if p.is_symlink():
                p.unlink()
    for s in order:
        idx = np.where(lab == s)[0]
        best = idx[np.argsort(-conf[idx])][:5]
        d = listen / rename[int(s)]
        d.mkdir(parents=True, exist_ok=True)
        for i in best:
            src = meta[ids[i]]["audio"]
            dst = d / f"{Path(src).parent.name}_{Path(src).name}"
            if not dst.exists():
                os.symlink(src, dst)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("embed")
    e.add_argument("--manifest", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--model", default=DEFAULT_MODEL)
    e.add_argument("--device", default="cuda")
    e.add_argument("--batch", type=int, default=16)
    e.add_argument("--workers", type=int, default=8)
    e.add_argument("--clip-s", type=float, default=10.0)
    e.add_argument("--backend", choices=("base", "large"), default="base",
                   help="base: WavLM-base-plus-sv, batched, + 3 s windows for multi-voice detection; large: the SIM-L "
                        "model (sharper speaker separation, one clip at a time, no windows)")
    e.add_argument("--models-dir", default=os.environ.get("TTS_EVAL_MODELS", ""), help="dir holding beatrice/ (large)")
    e.add_argument("--no-tf32", dest="tf32", action="store_false", help="full fp32 matmuls (default: TF32, cos >= 0.9999)")
    c = sub.add_parser("cluster")
    c.add_argument("--out", required=True)
    c.add_argument("--embeddings", choices=("base", "large"), default="large")
    c.add_argument("--threshold", type=float, default=None,
                   help="cosine distance for merging centroid groups (default: 0.35 for large embeddings, where one "
                        "speaker's clips score ~0.6-0.9 and different speakers ~0.1-0.5; 0.10 for base, where they "
                        "score 0.85-0.95 vs 0.75-0.93)")
    c.add_argument("--clips-per-centroid", type=int, default=150)
    c.add_argument("--multi-cos", type=float, default=0.55, help="a window below this cos to its clip => multi-voice")
    c.add_argument("--min-conf", type=float, default=0.6)
    c.add_argument("--min-cluster-hours", type=float, default=0.3)
    c.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    return cmd_embed(a) if a.cmd == "embed" else cmd_cluster(a)


if __name__ == "__main__":
    sys.exit(main())
