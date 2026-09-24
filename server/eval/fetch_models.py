#!/usr/bin/env python3
"""Download the evaluation / QC models into server/models/eval/ at pinned Hugging Face revisions and verify every
LFS file against its sha256 (the HF LFS oid, re-read from the Hub API and compared with the value pinned here).

    venvs/tools/bin/python eval/fetch_models.py                 # all required models
    venvs/tools/bin/python eval/fetch_models.py --verify-only   # re-hash what is on disk
    venvs/tools/bin/python eval/fetch_models.py --with-ecapa    # + the optional SpeechBrain ECAPA checkpoint

Writes models/eval/SHA256SUMS (sha256sum -c compatible) and models/eval/MANIFEST.json. Needs huggingface_hub (+ hf_xet)
only; server/venvs/tools has both. Models (see docs/research/eval-tooling.md, findings 1, 18-23, 30):
  faster-whisper-large-v3  stock openai/whisper-large-v3 converted to CTranslate2 (Systran), ASR for WER/CER
  wavlm-base-plus-sv       microsoft/wavlm-base-plus-sv (WavLMForXVector), secondary SIM, Kaggle scale (0.974 / <0.88)
  beatrice                 seed-tts-eval SIM model (UniSpeech WavLM-Large + ECAPA-TDNN), torch-native port, primary SIM
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
DEFAULT_DEST = Path(os.environ.get("EVAL_MODELS_DIR", SERVER / "models" / "eval"))

# local dir -> (repo, pinned revision, files, {lfs file: sha256})
MODELS: dict[str, dict] = {
    "faster-whisper-large-v3": {
        "repo": "Systran/faster-whisper-large-v3",
        "revision": "edaa852ec7e145841d8ffdb056a99866b5f0a478",
        "files": ["config.json", "model.bin", "preprocessor_config.json", "tokenizer.json", "vocabulary.json",
                  "README.md"],
        "sha256": {"model.bin": "69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1"},
    },
    "wavlm-base-plus-sv": {
        "repo": "microsoft/wavlm-base-plus-sv",
        "revision": "feb593a6c23c1cc3d9510425c29b0a14d2b07b1e",
        "files": ["config.json", "preprocessor_config.json", "pytorch_model.bin", "README.md"],
        "sha256": {"pytorch_model.bin": "e906bce2fa42fb497a1d1a9ecf81548adb7e03b12a5644e32d2f42f0d6500fad"},
    },
    "beatrice": {
        "repo": "prj-beatrice/unispeech-wavlm-large-ecapa-tdnn-torch-native",
        "revision": "13ad4fcc740cbd47992bcc2aaa59186d4072b7c9",
        "files": ["config.json", "model.safetensors", "modeling_wavlm_speaker_verification.py", "LICENSE",
                  "README.md"],
        "sha256": {"model.safetensors": "559b87088828b5f1bc5762d9746c08ef00ba4e5141b6897bebce1b77a58ae2b7"},
    },
}
OPTIONAL = {
    "speechbrain-spkrec-ecapa-voxceleb": {
        "repo": "speechbrain/spkrec-ecapa-voxceleb",
        "revision": "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286",
        "files": ["embedding_model.ckpt", "hyperparams.yaml", "mean_var_norm_emb.ckpt", "README.md"],
        "sha256": {"embedding_model.ckpt": "0575cb64845e6b9a10db9bcb74d5ac32b326b8dc90352671d345e2ee3d0126a2"},
    },
}


def sha256(path: Path, bufsize: int = 1 << 24) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(bufsize):
            h.update(chunk)
    return h.hexdigest()


def hub_oids(repo: str, revision: str) -> dict[str, str]:
    """LFS sha256 of every LFS file at that revision, straight from the Hub API."""
    from huggingface_hub import HfApi
    info = HfApi().model_info(repo, revision=revision, files_metadata=True)
    return {s.rfilename: s.lfs.sha256 for s in info.siblings if s.lfs}


def fetch(name: str, spec: dict, dest: Path, verify_only: bool) -> dict:
    from huggingface_hub import hf_hub_download
    local = dest / name
    local.mkdir(parents=True, exist_ok=True)
    if not verify_only:
        oids = hub_oids(spec["repo"], spec["revision"])
        for f, want in spec["sha256"].items():
            if oids.get(f) != want:
                raise SystemExit(f"{spec['repo']}@{spec['revision'][:8]} {f}: Hub oid {oids.get(f)} != pinned {want}")
        for f in spec["files"]:
            t0 = time.time()
            hf_hub_download(spec["repo"], f, revision=spec["revision"], local_dir=local)
            print(f"  {name}/{f}: {(local / f).stat().st_size / 1e6:.1f} MB in {time.time() - t0:.1f}s", flush=True)
    result = {"repo": spec["repo"], "revision": spec["revision"], "files": {}}
    for f in spec["files"]:
        p = local / f
        if not p.is_file():
            raise SystemExit(f"missing {p}")
        entry = {"bytes": p.stat().st_size}
        if f in spec["sha256"]:
            got = sha256(p)
            entry |= {"sha256": got, "expected": spec["sha256"][f], "ok": got == spec["sha256"][f]}
            print(f"  {name}/{f}: sha256 {got[:16]}... {'OK' if entry['ok'] else 'MISMATCH'}", flush=True)
        result["files"][f] = entry
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    ap.add_argument("--only", nargs="*", help="subset of local model dirs")
    ap.add_argument("--with-ecapa", action="store_true", help="also fetch the optional SpeechBrain ECAPA checkpoint")
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_XET_CHUNK_CACHE_SIZE_BYTES", "0")   # no second copy in ~/.cache/huggingface/xet
    models = dict(MODELS) | (OPTIONAL if args.with_ecapa else {})
    if args.only:
        models = {k: v for k, v in models.items() if k in args.only}
    args.dest.mkdir(parents=True, exist_ok=True)
    manifest_path = args.dest / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    for name, spec in models.items():
        print(f"{name} <- {spec['repo']}@{spec['revision'][:8]}", flush=True)
        manifest[name] = fetch(name, spec, args.dest, args.verify_only)
    manifest_path.write_text(json.dumps(manifest, indent=1) + "\n")
    sums = [f"{e['sha256']}  {name}/{f}" for name, m in sorted(manifest.items()) for f, e in m["files"].items()
            if "sha256" in e]
    (args.dest / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    bad = [f"{n}/{f}" for n, m in manifest.items() for f, e in m["files"].items() if e.get("ok") is False]
    total = sum(e["bytes"] for m in manifest.values() for e in m["files"].values())
    verdict = "MISMATCH: " + ", ".join(bad) if bad else "all OK"
    print(f"{len(manifest)} models, {total / 1e9:.2f} GB in {args.dest}; sha256 {verdict}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
