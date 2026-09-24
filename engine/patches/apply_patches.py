#!/usr/bin/env python3
"""Apply qwen3-tts-server's small, verified patches to an installed vllm_omni package.

  apply_patches.py --venv VENV          patch the vllm_omni installed in VENV
  apply_patches.py --package-dir DIR    patch a vllm_omni package directory (e.g. a copy of an unpacked wheel)
  add --check                           only report; exit 1 unless every patch is applied

Each patch swaps one exact upstream snippet for a marked replacement. Re-running is a no-op; when the snippet is not
found (upstream changed), the file is left untouched and the script exits 2. Stdlib only; nothing is imported from
vllm_omni, so CUDA is never touched.

Patches:
  rep_penalty  entrypoints/openai/serving_speech.py (0.28.0 L3089-3091, 0.30.0rc1 L2021-2023): per-request
               extra_params.repetition_penalty for the stage-0 talker. Upstream copies only temperature, top_p and
               top_k from extra_params onto the stage-0 SamplingParams, so repetition_penalty was server-side only.
               The value lands on the same per-request (deep-copied) SamplingParams; vLLM's sampler applies it to
               codebook 0 each step (gpu_input_batch.add_request -> Sampler.apply_penalties). Invalid values -> 400.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Patch:
    name: str
    path: str               # relative to the vllm_omni package directory
    original: str           # must occur exactly once
    replacement: str        # contains original's behaviour plus the marker
    marker: str
    requires: tuple[str, ...] = ()  # lines that must already exist in the file (e.g. imports the patch uses)


REP_PENALTY_MARKER = "# qwen3-tts-server patch: per-request repetition_penalty"
_LOOP = """\
            for name in ("temperature", "top_p", "top_k"):
                if (value := request.extra_params.get(name)) is not None:
                    setattr(sampling_params_list[0], name, value)
"""
PATCHES = (
    Patch(
        name="rep_penalty",
        path="entrypoints/openai/serving_speech.py",
        original=_LOOP,
        replacement=_LOOP + f"""\
            {REP_PENALTY_MARKER} (stage 0 = talker, codebook 0)
            if (penalty := request.extra_params.get("repetition_penalty")) is not None:
                if isinstance(penalty, bool) or not isinstance(penalty, (int, float)) or not 0 < penalty < math.inf:
                    raise ValueError("extra_params.repetition_penalty must be a finite number > 0")
                sampling_params_list[0].repetition_penalty = float(penalty)
""",
        marker=REP_PENALTY_MARKER,
        requires=("import math\n",),
    ),
)


class PatchError(Exception):
    pass


def find_package(venv: Path) -> Path:
    """Locate vllm_omni in a venv without importing it (find_spec does not run a top-level package's __init__)."""
    python = venv / "bin" / "python"
    if not python.exists():
        raise PatchError(f"{python} not found")
    code = "import importlib.util as u; s = u.find_spec('vllm_omni'); print(s.submodule_search_locations[0] if s else '')"
    r = subprocess.run([str(python), "-c", code], capture_output=True, text=True, timeout=60,
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if r.returncode != 0 or not r.stdout.strip():
        raise PatchError(f"vllm_omni is not installed in {venv}: {r.stderr.strip()[-500:]}")
    return Path(r.stdout.strip())


def state(text: str, patch: Patch) -> str:
    """'applied', 'pending' or 'unknown' (neither the original snippet nor the patched code is present)."""
    if patch.marker in text:
        if text.count(patch.marker) == 1 and patch.replacement in text:
            return "applied"
        return "unknown"
    return "pending" if text.count(patch.original) == 1 else "unknown"


def write_atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, path.stat().st_mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def apply(package: Path, patch: Patch, check_only: bool) -> str:
    path = package / patch.path
    if not path.is_file():
        raise PatchError(f"{patch.name}: {path} not found")
    text = path.read_text(encoding="utf-8")
    status = state(text, patch)
    if status == "unknown":
        raise PatchError(f"{patch.name}: the expected upstream snippet is not in {path} (vllm_omni changed?); "
                         "refusing to patch")
    if status == "applied" or check_only:
        return status
    if missing := [line.strip() for line in patch.requires if line not in text]:
        raise PatchError(f"{patch.name}: {path} lacks {missing}; refusing to patch")
    patched = text.replace(patch.original, patch.replacement, 1)
    compile(patched, str(path), "exec")
    write_atomic(path, patched)
    if state(path.read_text(encoding="utf-8"), patch) != "applied":
        raise PatchError(f"{patch.name}: verification failed after writing {path}")
    return "patched now"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    where = ap.add_mutually_exclusive_group(required=True)
    where.add_argument("--venv", type=Path, help="engine venv that has vllm_omni installed")
    where.add_argument("--package-dir", type=Path, help="a vllm_omni package directory")
    ap.add_argument("--check", action="store_true", help="report only; exit 1 unless every patch is applied")
    a = ap.parse_args()
    try:
        package = find_package(a.venv) if a.venv else a.package_dir.resolve()
        if not (package / "__init__.py").is_file():
            raise PatchError(f"{package} is not a python package")
        results = [(p.name, apply(package, p, a.check)) for p in PATCHES]
    except PatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for name, status in results:
        print(f"{name}: {status} ({package})")
    return 0 if all(status != "pending" for _, status in results) else 1


if __name__ == "__main__":
    sys.exit(main())
