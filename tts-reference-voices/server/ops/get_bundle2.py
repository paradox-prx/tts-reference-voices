#!/usr/bin/env python3
"""Fetch everything the Qwen3-TTS server still needs into ONE folder, on a machine with fast internet.

    python -m pip install -U pip huggingface_hub
    python get_bundle2.py                                  # -> ./qwen_tts_bundle2   (~5-6 GB)
    python get_bundle2.py --have qwen_tts_bundle/wheels    # drop wheels you already copied (smaller transfer)
    python get_bundle2.py --all-models                     # also re-fetch Qwen3-TTS, Whisper, WavLM (+~8 GB)

Runs on any OS with Python >= 3.10 and pip >= 23. Wheels are fetched for the SERVER: Linux x86_64, CPython 3.12,
glibc 2.39. Copy the resulting folder to the server with rsync -a or tar. It contains no symlinks.

Why a second bundle: `pip download vllm-omni` does not fetch vllm (vllm-omni declares no dependency on it) and
resolves torch 2.14, but vllm 0.28/0.30 pin torch 2.13. Two dependencies (antlr4-python3-runtime 4.9.3,
openai-whisper 20250625) exist only as source packages, which --only-binary rejects. Some wheels are tagged
manylinux_2_31/2_34, and the first script's platform list excluded them.
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PY = "3.12"
# every manylinux tag a glibc 2.39 x86_64 server accepts (pip does not always expand these itself)
PLATFORMS = [f"manylinux_2_{m}_x86_64" for m in range(39, 4, -1)] + \
            ["manylinux2014_x86_64", "manylinux2010_x86_64", "manylinux1_x86_64"]
SDIST_ONLY = ["antlr4-python3-runtime==4.9.3", "openai-whisper==20250625", "sox==1.5.0"]
BUILD_TOOLS = ["pip", "setuptools", "wheel"]
SETS = {  # name: (pip args, required)
    "omni28":  (["vllm==0.28.0", "vllm-omni==0.28.0"], True),                   # the engine (stable pair)
    "omni30":  (["--pre", "vllm==0.30.0", "vllm-omni==0.30.0rc1"], False),       # newer pair, head-to-head
    "qwentts": (["qwen-tts==0.1.1", "torch==2.13.0", "torchaudio==2.11.0"], False),  # official backend baseline
    "eval":    (["torch==2.13.0", "torchaudio==2.11.0", "transformers>=5.10.1,<5.15", "jiwer", "soundfile",
                 "librosa", "scipy", "matplotlib", "speechbrain"], False),       # WER / speaker similarity
}
MODELS_SMALL = {"speechbrain/spkrec-ecapa-voxceleb": None}                        # second speaker-similarity model
MODELS_BIG = {
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base": None,
    "openai/whisper-large-v3": ["model.safetensors", "*.json", "*.txt"],
    "microsoft/wavlm-base-plus-sv": ["*.json", "*.bin", "*.md"],
}


def pip(*args: str, check: bool = True) -> int:
    cmd = [sys.executable, "-m", "pip", *args]
    print("\n$ " + " ".join(cmd), flush=True)
    code = subprocess.call(cmd)
    if check and code:
        raise SystemExit(f"pip failed ({code}): {' '.join(args[:3])} ...")
    return code


def target_args() -> list[str]:
    return ["--only-binary=:all:", "--python-version", PY, "--implementation", "cp",
            *[a for p in PLATFORMS for a in ("--platform", p)]]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=Path("qwen_tts_bundle2"))
    ap.add_argument("--have", type=Path, action="append", default=[],
                    help="a wheels dir already copied to the server; identical files are dropped from this bundle")
    ap.add_argument("--sets", default=",".join(SETS), help=f"package sets to fetch (default: {','.join(SETS)})")
    ap.add_argument("--all-models", action="store_true", help="also fetch the big models from the first bundle")
    ap.add_argument("--skip-models", action="store_true")
    args = ap.parse_args()
    wheels, sdists, models = args.out / "wheels", args.out / "sdist", args.out / "models"
    for d in (wheels, sdists, models):
        d.mkdir(parents=True, exist_ok=True)
    report: list[str] = []

    # 1. source-only packages: keep the sdists and build pure-python wheels from them, so --only-binary resolves
    pip("download", "--no-deps", "--no-binary=:all:", "-d", str(sdists), *SDIST_ONLY)
    for sd in sorted(sdists.iterdir()):
        if pip("wheel", "--no-deps", "-w", str(wheels), str(sd), check=False):
            report.append(f"WARN could not build a wheel from {sd.name}; the server will build it from sdist/")
    pip("download", "-d", str(wheels), *target_args(), *BUILD_TOOLS)

    # 2. each package set, resolved for the server, then verified to install offline from this folder alone
    for name in [s for s in args.sets.split(",") if s]:
        pkgs, required = SETS[name]
        code = pip("download", "-d", str(wheels), "--find-links", str(wheels), *target_args(), *pkgs,
                   check=required)
        with tempfile.TemporaryDirectory() as tmp:
            ok = code == 0 and pip("install", "--dry-run", "--ignore-installed", "--no-index", "--find-links",
                                   str(wheels), "--target", tmp, *target_args(), *pkgs, check=False) == 0
        report.append(f"{'OK  ' if ok else 'FAIL'} set {name}: {' '.join(pkgs)}")
        if required and not ok:
            raise SystemExit(f"required set {name} does not resolve offline; see the pip output above")

    # 3. models as plain folders (local_dir: real files, no cache symlinks)
    if not args.skip_models:
        from huggingface_hub import snapshot_download
        for repo, allow in {**MODELS_SMALL, **(MODELS_BIG if args.all_models else {})}.items():
            dest = models / repo.replace("/", "--")
            snapshot_download(repo, local_dir=dest, allow_patterns=allow, max_workers=8)
            size = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
            report.append(f"OK   model {repo}: {size / 1e9:.2f} GB -> models/{dest.name}")

    # 4. drop wheels the server already has (same name and size)
    for have in args.have:
        for w in list(wheels.iterdir()):
            twin = have / w.name
            if twin.is_file() and twin.stat().st_size == w.stat().st_size:
                w.unlink()
        report.append(f"note: dropped wheels already present in {have}")

    files = sorted(f for f in args.out.rglob("*") if f.is_file() and f.name not in ("MANIFEST.txt", "README.txt"))
    (args.out / "MANIFEST.txt").write_text(
        "".join(f"{sha256(f)}  {f.stat().st_size:>12}  {f.relative_to(args.out)}\n" for f in files), encoding="utf-8")
    total = sum(f.stat().st_size for f in files)
    (args.out / "README.txt").write_text(f"""Second offline bundle for the Qwen3-TTS server (Linux x86_64, CPython {PY}).

wheels/  vllm 0.28.0 + vllm-omni 0.28.0 (+ torch 2.13.0 and CUDA 13 wheels), vllm 0.30.0 + vllm-omni 0.30.0rc1,
         qwen-tts 0.1.1, eval tools; wheels built from the source-only packages; pip/setuptools/wheel.
sdist/   the source-only packages, in case a wheel could not be built here.
models/  plain-folder model snapshots (no symlinks): {', '.join(p.name for p in models.iterdir()) or 'none'}
Install (on the server): pip install --no-index --find-links wheels [--find-links <first bundle>/wheels] <pkgs>
Integrity: sha256sum -c <(awk '{{print $1"  "$3}}' MANIFEST.txt)

Results:
""" + "\n".join(report) + "\n", encoding="utf-8")
    print("\n" + "\n".join(report))
    print(f"\ndone: {args.out} ({total / 1e9:.1f} GB in {len(files)} files). Copy the whole folder to the server.")


if __name__ == "__main__":
    main()
