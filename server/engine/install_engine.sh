#!/usr/bin/env bash
# Build an engine venv (vLLM + vLLM-Omni), apply engine/patches and verify it without initialising CUDA.
#
#   install_engine.sh [options] <venv-dir> <wheels-dir[:dir...]|-> <vllm-version> <vllm-omni-version>
#   e.g. install_engine.sh venvs/engine   -                                 0.28.0 0.28.0
#        install_engine.sh venvs/engine   /data/bundle/wheels:wheels-extra  0.28.0 0.28.0
#        install_engine.sh venvs/engine30 /data/bundle/wheels               0.30.0 0.30.0rc1
#
# Options:
#   --constraints FILE|auto|none  pip/uv constraints file (-c). auto (default) picks engine/constraints-omni*.txt when
#                                 it pins exactly these vllm and vllm-omni versions (make_constraints.py writes them)
#   --installer auto|uv|pip       auto (default): uv when found ($UV or `uv` on PATH), else the venv's pip
#   --dry-run                     only resolve (`--dry-run` of uv/pip); no venv changes, no post-install steps
#
# The wheels argument is one or more ':'-separated --find-links directories used with --no-index (offline); '-'
# installs from PyPI instead (~4 GB). vllm-omni does not depend on vllm, so both are pinned in one resolve (vllm pins
# torch 2.13.0 cu130). Two dependencies are sdists (openai-whisper, antlr4-python3-runtime): offline they build only
# if setuptools and wheel are in the bundle too. Re-running is safe: an existing venv is reused, the installer only
# audits what is already installed, and the patches are idempotent.
#
# Python 3.12 for a new venv: $PY312, else `python3.12` on PATH if it actually runs (a pyenv shim may not), else the
# newest 3.12.x under `pyenv root`/versions (default ~/.pyenv).
#
# After the install: engine/patches/apply_patches.py, a cuda13-link/libcudart.so link for FlashInfer JIT, a check of
# the pip nvcc, and an import check with every GPU hidden.
#
# FlashInfer JIT note (see engine/run_engine.sh): vllm 0.28's humming-kernels[cu13] pulls an unpinned
# nvidia-cuda-nvcc (13.4.x) while torch pins the CUDA runtime headers to 13.0, which breaks FlashInfer's sampler JIT.
# run_engine.sh therefore defaults to VLLM_USE_FLASHINFER_SAMPLER=0. A consistent toolchain is nvidia-cuda-nvcc,
# nvidia-cuda-crt and nvidia-nvvm at 13.0.88 (uv resolves that set with only those three packages changed).
set -euo pipefail

die() { echo "install_engine: $*" >&2; exit 1; }
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
usage="usage: $0 [--constraints FILE|auto|none] [--installer auto|uv|pip] [--dry-run]"
usage+=" <venv-dir> <wheels-dir[:dir...]|-> <vllm-version> <vllm-omni-version>"

constraints=auto installer=auto dry_run=0
positional=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --constraints) [[ $# -ge 2 ]] || die "$usage"; constraints=$2; shift 2 ;;
        --constraints=*) constraints=${1#*=}; shift ;;
        --installer) [[ $# -ge 2 ]] || die "$usage"; installer=$2; shift 2 ;;
        --installer=*) installer=${1#*=}; shift ;;
        --dry-run) dry_run=1; shift ;;
        -h|--help) echo "$usage"; exit 0 ;;
        --) shift; positional+=("$@"); break ;;
        -?*) die "unknown option $1; $usage" ;;
        *) positional+=("$1"); shift ;;
    esac
done
[[ ${#positional[@]} -eq 4 ]] || die "$usage"
venv=$(realpath -m "${positional[0]}") wheels=${positional[1]}
vllm_version=${positional[2]} omni_version=${positional[3]}

# Python 3.12 that really runs (prints its path), or nothing.
find_py312() {
    local candidate root
    if [[ -n ${PY312:-} ]]; then
        "$PY312" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))' 2>/dev/null ||
            die "PY312=$PY312 is not a working Python 3.12"
        command -v "$PY312"
        return
    fi
    if candidate=$(command -v python3.12) &&
            "$candidate" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))' 2>/dev/null; then
        echo "$candidate"
        return
    fi
    root=$(pyenv root 2>/dev/null || echo "${PYENV_ROOT:-$HOME/.pyenv}")
    while read -r candidate; do
        [[ -n $candidate ]] || continue
        if "$candidate" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))' 2>/dev/null; then
            echo "$candidate"
            return
        fi
    done < <(compgen -G "$root/versions/3.12*/bin/python3.12" | sort -rV)
}

# The constraints file that pins exactly vllm==$1 and vllm-omni==$2, or nothing.
auto_constraints() {
    local file
    for file in "$here"/constraints-omni*.txt; do
        [[ -f $file ]] || continue
        if grep -qx "vllm==$1" "$file" && grep -qx "vllm-omni==$2" "$file"; then
            echo "$file"
            return
        fi
    done
}

case $constraints in
    none) constraints="" ;;
    auto)
        constraints=$(auto_constraints "$vllm_version" "$omni_version")
        [[ -n $constraints ]] || echo "install_engine: note: no constraints file pins vllm $vllm_version +" \
                                      "vllm-omni $omni_version; resolving freely" >&2 ;;
    *) [[ -f $constraints ]] || die "constraints file $constraints not found"; constraints=$(realpath "$constraints") ;;
esac

uv=""
case $installer in
    auto|uv)
        uv=${UV:-$(command -v uv || true)}
        if [[ -z $uv || ! -x $uv ]]; then
            [[ $installer == auto ]] || die "--installer uv: uv not found (set UV or put uv on PATH)"
            uv=""
        fi ;;
    pip) ;;
    *) die "--installer must be auto, uv or pip" ;;
esac

if [[ ! -x $venv/bin/python ]]; then
    ((dry_run == 0)) || die "--dry-run needs an existing venv ($venv)"
    py312=$(find_py312) || true
    [[ -n $py312 ]] || die "no working Python 3.12 (set PY312, or install one with pyenv)"
    echo "install_engine: creating $venv with $py312"
    "$py312" -m venv "$venv"
fi
py=$venv/bin/python
[[ $("$py" -c 'import sys; print("%d.%d" % sys.version_info[:2])') == 3.12 ]] || die "$venv is not a Python 3.12 venv"

source_args=()
if [[ $wheels == - ]]; then
    echo "install_engine: installing from PyPI"
else
    source_args+=(--no-index)
    IFS=: read -ra dirs <<<"$wheels"
    setuptools=0
    for dir in "${dirs[@]}"; do
        [[ -d $dir ]] || die "wheel directory $dir not found"
        source_args+=(--find-links "$(realpath "$dir")")
        compgen -G "$dir/setuptools-*.whl" >/dev/null && setuptools=1
    done
    ((setuptools)) || echo "install_engine: note: no setuptools wheel in the bundle; sdists cannot build offline" >&2
fi
[[ -z $constraints ]] || source_args+=(-c "$constraints")
((dry_run == 0)) || source_args+=(--dry-run)
requirements=("vllm==$vllm_version" "vllm-omni==$omni_version")

if [[ -n $uv ]]; then
    echo "install_engine: $uv pip install -p $py ${source_args[*]} ${requirements[*]}"
    "$uv" pip install -p "$py" "${source_args[@]}" "${requirements[@]}"
else
    echo "install_engine: $py -m pip install ${source_args[*]} ${requirements[*]}"
    "$py" -m pip install --disable-pip-version-check --no-input "${source_args[@]}" "${requirements[@]}"
fi
if ((dry_run)); then
    echo "install_engine: dry run only; post-install steps skipped"
    exit 0
fi

"$py" "$here/patches/apply_patches.py" --venv "$venv"

# FlashInfer JIT toolchain: the pip CUDA 13 wheels install a toolkit tree at site-packages/nvidia/cu13
# (bin/nvcc, include/, lib/, nvvm/). Its runtime ships only libcudart.so.13, but FlashInfer links JIT modules with
# -lcudart, which would otherwise resolve to a system CUDA 12 libcudart.so (or fail to link).
site=$("$py" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
cu13=$site/nvidia/cu13
[[ -x $cu13/bin/nvcc && -e $cu13/lib/libcudart.so.13 ]] || die "no pip CUDA 13 toolchain in $cu13 (nvidia-cuda-nvcc)"
mkdir -p "$venv/cuda13-link"
ln -sfn "$cu13/lib/libcudart.so.13" "$venv/cuda13-link/libcudart.so"
nvcc_release=$("$cu13/bin/nvcc" --version | sed -n 's/.*release \([0-9.]*\),.*/\1/p')
[[ $nvcc_release == 13.* ]] || die "unexpected nvcc release '$nvcc_release' in $cu13"
cudart=$(sed -n 's/^#define CUDART_VERSION[[:space:]]*\([0-9]*\).*/\1/p' "$cu13/include/cuda_runtime_api.h")
cudart=${cudart:+$((cudart / 1000)).$(((cudart % 1000) / 10))}
if [[ -n $cudart && $nvcc_release != "$cudart" ]]; then
    echo "install_engine: note: nvcc $nvcc_release but CUDA runtime headers $cudart: FlashInfer's JIT sampler" \
         "will not compile; run_engine.sh keeps VLLM_USE_FLASHINFER_SAMPLER=0" >&2
fi

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
echo "install_engine: ready: $venv (nvcc $nvcc_release at $cu13/bin/nvcc${constraints:+, constraints $constraints})"
