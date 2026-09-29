#!/usr/bin/env bash
# One-shot environment for a fresh GPU box (Ubuntu, CUDA driver >= 12.x). Uses uv if present, else python -m venv.
#   bash setup.sh            # creates .venv, installs torch (cu128 by default) + requirements, downloads the models
#   TORCH_INDEX=https://download.pytorch.org/whl/cu130 bash setup.sh    # other CUDA builds
set -euo pipefail
cd "$(dirname "$0")"
TORCH_INDEX=${TORCH_INDEX:-https://download.pytorch.org/whl/cu128}
PY=${PYTHON:-python3.12}
if command -v uv >/dev/null; then
  uv venv -p "$PY" .venv
  uv pip install -p .venv/bin/python --index-url "$TORCH_INDEX" torch torchaudio
  uv pip install -p .venv/bin/python -r requirements.txt
else
  "$PY" -m venv .venv
  .venv/bin/pip install --index-url "$TORCH_INDEX" torch torchaudio
  .venv/bin/pip install -r requirements.txt
fi
.venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
for m in ("Qwen/Qwen3-TTS-12Hz-1.7B-Base", "Qwen/Qwen3-TTS-Tokenizer-12Hz"):
    print(snapshot_download(m, allow_patterns=["*.json", "*.safetensors", "*.txt"]))
PY
.venv/bin/python -c "import torch, qwen_tts; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
echo "ok: source .venv/bin/activate; python -m qwen_train.derive --help"
