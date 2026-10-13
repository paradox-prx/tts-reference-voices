#!/usr/bin/env bash
# Run a Python script or module with the eval venv (server/venvs/eval) and cuBLAS 12 on the loader path.
#
#   eval/run.sh eval/score_run.py <results-dir>... [--device cuda|cpu]     offline scoring of bench runs
#   eval/run.sh eval/gpu_check.py [--device cuda|cpu]                       ASR + WavLM in one process, on the GPU
#   cd qc && ../eval/run.sh -m tts_qc                                       the QC sidecar (127.0.0.1:8092)
#   cd qc && ../eval/run.sh -m pytest -q tests                              the sidecar tests
#
# Why this wrapper: the one eval venv holds torch 2.13 (CUDA 13; it finds its own libcublas.so.13 under
# site-packages/nvidia/cu13) and ctranslate2 4.8.2 (faster-whisper's backend), which dlopens libcublas.so.12 by
# soname and adds no search path on Linux. The .so.12 comes from the venv's nvidia-cublas-cu12 wheel; without it the
# loader falls back to the system one (Ubuntu's libcublas12, /usr/lib/x86_64-linux-gnu). The two sonames and their
# versioned symbols (@@libcublas.so.12 / .13) do not clash, so both load into one process (eval/gpu_check.py).
#
# Environment (all optional):
#   TTS_EVAL_VENV        venv to use (default server/venvs/eval)
#   TTS_CUBLAS12_DIR     directory holding libcublas.so.12 (default: the venv's nvidia/cublas/lib)
#   CUDA_VISIBLE_DEVICES passed through untouched; set it to "" to keep a run off the GPU
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
server=$(dirname "$here")
venv=${TTS_EVAL_VENV:-$server/venvs/eval}
python=$venv/bin/python
[[ -x $python ]] || { echo "run.sh: no python in $venv (see eval/README.md: create the eval venv)" >&2; exit 1; }
(($# > 0)) || { echo "usage: $0 <script.py | -m module> [args...]" >&2; exit 2; }

cublas=${TTS_CUBLAS12_DIR:-}
if [[ -z $cublas ]]; then
    for d in "$venv"/lib/python3*/site-packages/nvidia/cublas/lib; do [[ -e $d/libcublas.so.12 ]] && cublas=$d; done
fi
if [[ -n $cublas && -e $cublas/libcublas.so.12 ]]; then
    export LD_LIBRARY_PATH=$cublas${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
else
    echo "run.sh: no libcublas.so.12 in the venv; ctranslate2 will use the system one if any (ldconfig -p)" >&2
fi
# tts_qc (server/qc) is importable from anywhere: the eval scripts and the sidecar share it
export PYTHONPATH=$server/qc${PYTHONPATH:+:$PYTHONPATH}
export PYTHONUNBUFFERED=1
exec "$python" "$@"
