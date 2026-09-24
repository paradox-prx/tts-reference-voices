"""Tests for engine/make_variant.py and engine/patches/apply_patches.py (CPU only; uses copies, never ops/upstream).

Run: venvs/gateway/bin/python -m pytest engine/tests
"""

from __future__ import annotations

import copy
import math
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ENGINE = Path(__file__).resolve().parents[1]
UPSTREAM = ENGINE.parent / "ops" / "upstream"
SERVING = "entrypoints/openai/serving_speech.py"
VERSIONS = ["0.28.0", "0.30.0rc1"]


def run(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, timeout=120)


# ---------------------------------------------------------------- apply_patches.py

@pytest.fixture(params=VERSIONS)
def package(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    src = UPSTREAM / f"vllm_omni-{request.param}" / "vllm_omni"
    if not src.is_dir():
        pytest.skip(f"{src} not unpacked")
    dst = tmp_path / "vllm_omni"
    (dst / SERVING).parent.mkdir(parents=True)
    shutil.copy(src / "__init__.py", dst / "__init__.py")
    shutil.copy(src / SERVING, dst / SERVING)
    return dst


def patched_block(path: Path):
    """The patched extra_params block of serving_speech.py as a function (request, sampling_params_list) -> list."""
    src = path.read_text()
    start = src.index("        if request.extra_params is not None and sampling_params_list:")
    end = src.index("\n", src.index('logger.info("Applied extra_params', start)) + 1
    body = textwrap.indent(textwrap.dedent(src[start:end]), "    ")
    ns = {"math": math, "HTTPException": Exception, "logger": SimpleNamespace(info=lambda *a: None),
          "HTTPStatus": SimpleNamespace(BAD_REQUEST=SimpleNamespace(value=400))}
    exec(f"def block(request, sampling_params_list):\n{body}    return sampling_params_list\n", ns)
    return ns["block"]


def test_patch_is_idempotent_and_applies_per_request(package: Path) -> None:
    tool = ENGINE / "patches" / "apply_patches.py"
    assert run(tool, "--package-dir", package, "--check").returncode == 1
    assert run(tool, "--package-dir", package).returncode == 0
    patched = (package / SERVING).read_text()
    second = run(tool, "--package-dir", package)
    assert second.returncode == 0 and "rep_penalty: applied" in second.stdout
    assert (package / SERVING).read_text() == patched
    assert run(tool, "--package-dir", package, "--check").returncode == 0

    block = patched_block(package / SERVING)
    defaults = [SimpleNamespace(temperature=0.9, top_p=1.0, top_k=50, repetition_penalty=1.05, extra_args=None),
                SimpleNamespace(temperature=0.0, top_p=1.0, top_k=-1, repetition_penalty=1.0, extra_args=None)]
    out = block(SimpleNamespace(extra_params={"repetition_penalty": 1.2, "top_k": 30}), defaults)
    assert (out[0].repetition_penalty, out[0].top_k, out[1].repetition_penalty) == (1.2, 30, 1.0)
    assert defaults[0].repetition_penalty == 1.05  # the shared server defaults stay untouched
    assert block(SimpleNamespace(extra_params={"top_k": 20}), defaults)[0].repetition_penalty == 1.05
    for bad in (0, -1, math.nan, math.inf, "1.1", True):
        with pytest.raises(ValueError):
            block(SimpleNamespace(extra_params={"repetition_penalty": bad}), defaults)


def test_patch_refuses_unknown_upstream(package: Path) -> None:
    path = package / SERVING
    path.write_text(path.read_text().replace('("temperature", "top_p", "top_k")', '("temperature", "top_p")'))
    before = path.read_text()
    result = run(ENGINE / "patches" / "apply_patches.py", "--package-dir", package)
    assert result.returncode == 2 and "refusing" in result.stderr
    assert path.read_text() == before


# ---------------------------------------------------------------- make_variant.py

@pytest.fixture(scope="module")
def mv():
    sys.path.insert(0, str(ENGINE))
    try:
        import make_variant
    finally:
        sys.path.remove(str(ENGINE))
    return make_variant


def test_standard_variants(tmp_path: Path, mv) -> None:
    result = run(ENGINE / "make_variant.py", "--standard", "--out-dir", tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert {p.stem for p in tmp_path.glob("*.yaml")} == set(mv.STANDARD)
    load = lambda name: yaml.safe_load((tmp_path / f"{name}.yaml").read_text())  # noqa: E731
    base = yaml.safe_load(mv.BASE.read_text())
    assert load("default") == base
    assert load("no_async_chunk")["async_chunk"] is False
    assert [s["enforce_eager"] for s in load("eager")["stages"]] == [True, True]
    assert load("rp120")["stages"][0]["default_sampling_params"]["repetition_penalty"] == 1.2
    fp32 = load("fp32_talker")["stages"][0]
    assert (fp32["dtype"], fp32["gpu_memory_utilization"], fp32["max_num_batched_tokens"]) == ("float32", 0.55, 8192)
    assert [s["max_num_seqs"] for s in load("seqs128")["stages"]] == [128, 128]
    extra = load("decode8")["connectors"][mv.CONNECTOR]["extra"]
    assert (extra["decode_batch_max_size"], extra["decode_cudagraph_batch_sizes"]) == (8, [1, 2, 4, 8])


def test_validate_catches_what_the_loader_would_drop(mv) -> None:
    doc = copy.deepcopy(yaml.safe_load(mv.BASE.read_text()))
    assert mv.validate(doc) == ([], [])
    doc["async_chunks"] = False
    doc["stages"][0]["gpu_memory_utilisation"] = 0.5
    doc["stages"][1]["devices"] = 0
    doc["stages"][1]["gpu_memory_utilization"] = 0.7
    doc["stages"][0]["default_sampling_params"]["repetition_penalty"] = 0
    errors, _ = mv.validate(doc)
    assert len(errors) == 5, errors
