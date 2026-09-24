#!/usr/bin/env bash
# Build an engine venv (vLLM + vLLM-Omni), apply engine/patches and verify it without initialising CUDA.
#
#   install_engine.sh <venv-dir> <bundle-wheels-dir[:dir...]|-> <vllm-version> <vllm-omni-version>
#   e.g. install_engine.sh venvs/engine   /data/bundle/wheels:wheels-extra 0.28.0 0.28.0
#        install_engine.sh venvs/engine30 /data/bundle/wheels 0.30.0 0.30.0rc1
#
# The wheels argument is one or more ':'-separated --find-links directories used with --no-index; '-' installs from
# PyPI instead (~4 GB, slow on this link). vllm-omni does not depend on vllm, so both are pinned in one resolve
# (vllm pins torch 2.13.0 cu130). Two dependencies are sdists (openai-whisper, antlr4-python3-runtime): offline they
# build only if setuptools and wheel are in the bundle too. Re-running is safe: pip skips what is installed and the
# patches are idempotent.
set -euo pipefail

die() { echo "install_engine: $*" >&2; exit 1; }
[[ $# -eq 4 ]] || die "usage: $0 <venv-dir> <bundle-wheels-dir[:dir...]|-> <vllm-version> <vllm-omni-version>"
venv=$(realpath -m "$1") wheels=$2 vllm_version=$3 omni_version=$4
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

command -v python3.12 >/dev/null || die "python3.12 not found"
[[ -x $venv/bin/python ]] || python3.12 -m venv "$venv"
py=$venv/bin/python
[[ $("$py" -c 'import sys; print("%d.%d" % sys.version_info[:2])') == 3.12 ]] || die "$venv is not a Python 3.12 venv"

pip_args=(install --disable-pip-version-check --no-input)
if [[ $wheels == - ]]; then
    echo "install_engine: installing from PyPI"
else
    pip_args+=(--no-index)
    IFS=: read -ra dirs <<<"$wheels"
    setuptools=0
    for dir in "${dirs[@]}"; do
        [[ -d $dir ]] || die "wheel directory $dir not found"
        pip_args+=(--find-links "$(realpath "$dir")")
        compgen -G "$dir/setuptools-*.whl" >/dev/null && setuptools=1
    done
    ((setuptools)) || echo "install_engine: note: no setuptools wheel in the bundle; sdists cannot build offline" >&2
fi
"$py" -m pip "${pip_args[@]}" "vllm==$vllm_version" "vllm-omni==$omni_version"

"$py" "$here/patches/apply_patches.py" --venv "$venv"

# FlashInfer JIT toolchain: the pip CUDA 13 wheels install a toolkit tree at site-packages/nvidia/cu13
# (bin/nvcc, include/, lib/, nvvm/). Its runtime ships only libcudart.so.13, but FlashInfer links JIT modules with
# -lcudart, which would otherwise resolve to the system's CUDA 12.0 /usr/lib/x86_64-linux-gnu/libcudart.so.
site=$("$py" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
cu13=$site/nvidia/cu13
[[ -x $cu13/bin/nvcc && -e $cu13/lib/libcudart.so.13 ]] || die "no pip CUDA 13 toolchain in $cu13 (nvidia-cuda-nvcc)"
mkdir -p "$venv/cuda13-link"
ln -sfn "$cu13/lib/libcudart.so.13" "$venv/cuda13-link/libcudart.so"
nvcc_release=$("$cu13/bin/nvcc" --version | sed -n 's/.*release \([0-9.]*\),.*/\1/p')
[[ $nvcc_release == 13.* ]] || die "unexpected nvcc release '$nvcc_release' in $cu13"

# Import check with every GPU hidden and torch's NVML-based availability check: proves the packages (and the patched
# serving_speech module) import, and fails if anything initialised CUDA on the way.
CUDA_VISIBLE_DEVICES="" PYTORCH_NVML_BASED_CUDA_CHECK=1 VLLM_LOGGING_LEVEL=WARNING PYTHONDONTWRITEBYTECODE=1 \
    "$py" - "$vllm_version" "$omni_version" <<'EOF'
import importlib.metadata as md
import sys

import torch
import vllm
import vllm_omni
import vllm_omni.entrypoints.openai.serving_speech  # noqa: F401  (the patched module)

want_vllm, want_omni = sys.argv[1:3]
got = {name: md.version(name) for name in ("vllm", "vllm-omni", "torch", "flashinfer-python", "transformers")}
assert got["vllm"] == want_vllm and got["vllm-omni"] == want_omni, f"version mismatch: {got}"
assert not torch.cuda.is_initialized(), "importing vllm / vllm_omni initialised CUDA"
print("install_engine: imports ok, CUDA not initialised;", ", ".join(f"{k} {v}" for k, v in got.items()),
      f"(torch CUDA {torch.version.cuda})")
EOF
[[ -x $venv/bin/vllm ]] || die "$venv/bin/vllm missing"
echo "install_engine: ready: $venv (nvcc $nvcc_release at $cu13/bin/nvcc)"
