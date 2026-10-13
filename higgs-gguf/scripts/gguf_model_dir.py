#!/usr/bin/env python3
"""Make a vLLM model directory from a lone Higgs GGUF: writes the config.json / tokenizer files embedded in its
metadata next to it (or into --out, with a symlink to the GGUF).

    python scripts/gguf_model_dir.py path/to/model.gguf [--out dir] [--overwrite]
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from higgs_gguf.reader import write_side_files  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("gguf")
ap.add_argument("--out")
ap.add_argument("--overwrite", action="store_true")
a = ap.parse_args()
gguf = Path(a.gguf).resolve()
out = Path(a.out).resolve() if a.out else gguf.parent
for p in write_side_files(gguf, out, a.overwrite):
    print(f"wrote {p}")
if out != gguf.parent and not (out / gguf.name).exists():
    os.symlink(gguf, out / gguf.name)
    print(f"linked {out / gguf.name} -> {gguf}")
