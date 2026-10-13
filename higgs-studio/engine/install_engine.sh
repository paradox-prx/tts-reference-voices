#!/usr/bin/env bash
# Build the engine venv: vLLM 0.28.0 + vLLM-Omni 0.28.0 (CUDA 13 wheels, ~4 GB from PyPI), the PR #7065 patch, a
# libcudart link for FlashInfer, and an import check with every GPU hidden.
#
#   engine/install_engine.sh [<venv>]      default $HIGGS_ENGINE_VENV (engine/.venv)
#
# Re-running is safe: an existing venv is reused and the installer only checks what is already there. Needs uv (or a
# Python 3.12 with pip; set PY312 to pick one).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/common.sh"

venv=$(realpath -m "${1:-$HIGGS_ENGINE_VENV}")
constraints=$ROOT/engine/constraints-omni28.txt
uv=${UV:-$(command -v uv || true)}

if [[ ! -x $venv/bin/python ]]; then
    if [[ -n $uv ]]; then
        say "creating $venv (uv, Python 3.12)"
        "$uv" venv --seed -p 3.12 "$venv"
    else
        py=${PY312:-$(command -v python3.12 || true)}
        [[ -n $py ]] && "$py" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))' 2>/dev/null ||
            die "need uv or a working Python 3.12 (set PY312)"
        say "creating $venv ($py)"
        "$py" -m venv "$venv"
    fi
fi
py=$venv/bin/python
[[ $("$py" -c 'import sys; print("%d.%d" % sys.version_info[:2])') == 3.12 ]] || die "$venv is not a Python 3.12 venv"

reqs=("vllm==$VLLM_VERSION" "vllm-omni==$VLLM_OMNI_VERSION" "huggingface_hub[cli]")
if [[ -n $uv ]]; then
    "$uv" pip install -p "$py" -c "$constraints" "${reqs[@]}"
else
    "$py" -m pip install --disable-pip-version-check -c "$constraints" "${reqs[@]}"
fi

"$ROOT/engine/apply_pr7065.sh" "$venv"

# FlashInfer links JIT modules with -lcudart; the pip CUDA 13 runtime only ships libcudart.so.13, so point a
# libcudart.so at it (otherwise a system CUDA 12 library could be linked).
site=$("$py" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
cu13=$site/nvidia/cu13
[[ -x $cu13/bin/nvcc && -e $cu13/lib/libcudart.so.13 ]] || die "no pip CUDA 13 toolchain in $cu13 (nvidia-cuda-nvcc)"
mkdir -p "$venv/cuda13-link"
ln -sfn "$cu13/lib/libcudart.so.13" "$venv/cuda13-link/libcudart.so"

CUDA_VISIBLE_DEVICES="" PYTORCH_NVML_BASED_CUDA_CHECK=1 VLLM_LOGGING_LEVEL=WARNING PYTHONDONTWRITEBYTECODE=1 \
    "$py" - "$VLLM_VERSION" "$VLLM_OMNI_VERSION" <<'EOF'
import importlib.metadata as md
import sys

import torch
import vllm  # noqa: F401
import vllm_omni  # noqa: F401
import vllm_omni.entrypoints.openai.serving_speech  # noqa: F401  (the patched module)

got = {n: md.version(n) for n in ("vllm", "vllm-omni", "torch", "transformers")}
assert (got["vllm"], got["vllm-omni"]) == tuple(sys.argv[1:3]), f"version mismatch: {got}"
assert not torch.cuda.is_initialized(), "importing vllm / vllm_omni initialised CUDA"
print("install_engine: imports ok;", ", ".join(f"{k} {v}" for k, v in got.items()), f"(torch CUDA {torch.version.cuda})")
EOF
say "engine venv ready: $venv"
