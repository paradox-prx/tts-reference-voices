"""Tests for engine/make_variant.py, engine/patches/apply_patches.py and the deploy YAMLs (CPU only; patches work on
copies, never on ops/upstream or the engine venv).

Run: venvs/gateway/bin/python -m pytest engine/tests
The patch tests use ops/upstream/vllm_omni-<version> when unpacked, and always the vllm_omni installed in venvs/engine
(its serving_speech.py is copied and, if already patched, reverted to the upstream text first). The real-loader test
needs venvs/engine.
"""

from __future__ import annotations

import copy
import importlib.util
import json
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
SERVER = ENGINE.parent
UPSTREAM = SERVER / "ops" / "upstream"
ENGINE_VENV = SERVER / "venvs" / "engine"
SERVING = "entrypoints/openai/serving_speech.py"
VERSIONS = ["0.28.0", "0.30.0rc1", "installed"]


def installed_package() -> Path | None:
    found = sorted(ENGINE_VENV.glob("lib/python3*/site-packages/vllm_omni"))
    return found[0] if found else None


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve string annotations through sys.modules
    spec.loader.exec_module(module)
    return module


def run(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, timeout=120)


# ---------------------------------------------------------------- apply_patches.py

@pytest.fixture(params=VERSIONS)
def package(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    src = installed_package() if request.param == "installed" else UPSTREAM / f"vllm_omni-{request.param}" / "vllm_omni"
    if src is None or not src.is_dir():
        pytest.skip(f"vllm_omni {request.param} not available ({src})")
    dst = tmp_path / "vllm_omni"
    (dst / SERVING).parent.mkdir(parents=True)
    shutil.copy(src / "__init__.py", dst / "__init__.py")
    text = (src / SERVING).read_text()
    for patch in load_module("apply_patches", ENGINE / "patches" / "apply_patches.py").PATCHES:
        text = text.replace(patch.replacement, patch.original)  # back to upstream when the venv is patched
    (dst / SERVING).write_text(text)
    return dst


def test_installed_engine_is_patched() -> None:
    """engine/install_engine.sh applied rep_penalty to venvs/engine (the running engine picks it up on restart)."""
    if installed_package() is None:
        pytest.skip("no venvs/engine")
    result = run(ENGINE / "patches" / "apply_patches.py", "--venv", ENGINE_VENV, "--check")
    assert result.returncode == 0 and "rep_penalty: applied" in result.stdout, result.stdout + result.stderr


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
    assert (fp32["dtype"], fp32["gpu_memory_utilization"], fp32["max_num_batched_tokens"], fp32["max_num_seqs"]) \
        == ("float32", 0.70, 8192, 32)
    assert [s["max_num_seqs"] for s in load("seqs128")["stages"]] == [128, 128]
    extra = load("decode8")["connectors"][mv.CONNECTOR]["extra"]
    assert (extra["decode_batch_max_size"], extra["decode_cudagraph_batch_sizes"]) == (8, [1, 2, 4, 8])
    voices = load("custom_voices")
    assert voices.pop("custom_voice_dir") == "state/custom_voices" and voices == base


def test_committed_variants_match_the_production_file(tmp_path: Path, mv) -> None:
    """engine/deploy/variants/*.yaml are regenerated from the current prod YAML (same base sha, same bodies)."""
    assert run(ENGINE / "make_variant.py", "--standard", "--out-dir", tmp_path).returncode == 0
    for fresh in sorted(tmp_path.glob("*.yaml")):
        committed = mv.OUT_DIR / fresh.name
        assert committed.is_file(), f"{committed} missing: run engine/make_variant.py --standard"
        assert committed.read_text() == fresh.read_text(), \
            f"{committed} is stale: run engine/make_variant.py --standard"
    assert {p.name for p in mv.OUT_DIR.glob("*.yaml")} == {p.name for p in tmp_path.glob("*.yaml")}


# Measured on the 3090 (logs/engine_smoke_prod.log at 0.45): cudaMemGetInfo total, the stage-0 process memory outside
# the KV cache (10.60 GiB request - 6.2 GiB KV), the activation peak and graphs that come on top, KV bytes per token.
TOTAL_GIB, STAGE0_NON_KV_GIB, STAGE0_EXTRA_GIB, KV_KIB_PER_TOKEN = 23.56, 4.40, 1.5 + 0.17, 112
TAKE_TOKENS = 1248  # ICL prompt <= ~362 positions + 875 codec frames (70 s), in 16-token blocks


def test_production_memory_split_fits_without_preemption(mv) -> None:
    doc = yaml.safe_load(mv.BASE.read_text())
    talker, code2wav = mv.stage(doc, 0), mv.stage(doc, 1)
    kv_gib = talker["gpu_memory_utilization"] * TOTAL_GIB - STAGE0_NON_KV_GIB
    kv_tokens = kv_gib * 1024 * 1024 / KV_KIB_PER_TOKEN
    assert kv_tokens >= talker["max_num_seqs"] * TAKE_TOKENS, (kv_tokens, talker["max_num_seqs"])
    # the arithmetic reproduces both measurements: 58,032 tokens logged at 0.45, 91,120 at 0.60 (logs/engine_e03_*)
    for util, logged in ((0.45, 58032), (0.60, 91120)):
        assert abs((util * TOTAL_GIB - STAGE0_NON_KV_GIB) * 1024 * 1024 / KV_KIB_PER_TOKEN - logged) < 1000
    assert talker["gpu_memory_utilization"] != 0.60 or 91120 >= talker["max_num_seqs"] * TAKE_TOKENS
    # desktop headroom: stage-0 peak + stage 1 (~4.5 GiB under load, unmeasured) + desktop (0.6) leaves >= 1.5 GiB
    peak = talker["gpu_memory_utilization"] * TOTAL_GIB + STAGE0_EXTRA_GIB + 4.5 + 0.6
    assert TOTAL_GIB - peak >= 1.5, peak
    assert code2wav["max_num_seqs"] >= talker["max_num_seqs"]
    assert mv.validate(doc) == ([], [])


def test_custom_voice_dir_validation(mv) -> None:
    doc = copy.deepcopy(yaml.safe_load(mv.BASE.read_text()))
    doc["custom_voice_dir"] = "state/custom_voices"
    errors, warnings = mv.validate(doc)
    assert errors == [] and any("relative" in w for w in warnings)
    doc["custom_voice_dir"] = "/abs/voices"
    assert mv.validate(doc) == ([], [])
    doc["custom_voice_dir"] = ""
    assert any("custom_voice_dir" in e for e in mv.validate(doc)[0])


def test_compare_resolved_reports_dropped_keys(mv) -> None:
    doc = yaml.safe_load(mv.BASE.read_text())
    doc["custom_voice_dir"] = "state/custom_voices"
    stages = {}
    for s in doc["stages"]:
        args = {k: v for k, v in s.items() if k not in mv.RESERVED_STAGE_KEYS}
        args.update(async_chunk=True, custom_voice_dir="state/custom_voices")
        stages[str(s["stage_id"])] = {"engine_args": args, "runtime": {"devices": s["devices"]},
                                      "default_sampling_params": dict(s["default_sampling_params"])}
    resolved = {"connectors": doc["connectors"], "stages": stages, "model_runner_supported": False}
    assert mv.compare_resolved(doc, resolved) == []
    del stages["0"]["engine_args"]["silence_ban_frames"]
    stages["1"]["engine_args"]["custom_voice_dir"] = None
    stages["0"]["default_sampling_params"]["repetition_penalty"] = 1.0
    problems = mv.compare_resolved(doc, resolved)
    assert len(problems) == 3 and any("silence_ban_frames" in p for p in problems), problems


def test_real_loader_accepts_prod_and_variants() -> None:
    """Every key of the prod YAML and the variants reaches the stage configs of the installed vllm_omni loader."""
    if not (ENGINE_VENV / "bin" / "python").exists():
        pytest.skip("no venvs/engine")
    files = [ENGINE / "deploy" / "qwen3_tts_prod.yaml", *sorted((ENGINE / "deploy" / "variants").glob("*.yaml"))]
    result = run(ENGINE / "make_variant.py", "--validate", *files, "--check", ENGINE_VENV)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    assert result.stdout.count("upstream loader ok") == len(files)


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


# ---------------------------------------------------------------- make_constraints.py

def test_make_constraints(tmp_path: Path) -> None:
    mc = load_module("make_constraints", ENGINE / "make_constraints.py")
    report = {"install": [{"metadata": {"name": n, "version": v}}
                          for n, v in (("vllm", "0.28.0"), ("Jinja2", "3.1"), ("nvidia_cuda_nvcc", "13.4.92"))]}
    assert mc.constraints(report) == ["Jinja2==3.1", "nvidia_cuda_nvcc==13.4.92", "vllm==0.28.0"]
    report["install"].append({"metadata": {"name": "nvidia-cuda-nvcc", "version": "13.0.88"}})
    with pytest.raises(ValueError, match="twice"):
        mc.constraints(report)
    with pytest.raises(ValueError):
        mc.constraints({})
    # the committed files pin exactly the versions install_engine.sh --constraints auto matches on
    for name, pins in (("constraints-omni28.txt", ("vllm==0.28.0", "vllm-omni==0.28.0")),
                       ("constraints-omni30.txt", ("vllm==0.30.0", "vllm-omni==0.30.0rc1"))):
        lines = (ENGINE / name).read_text().splitlines()
        assert all(pin in lines for pin in pins) and lines == sorted(lines, key=str.lower)


def test_constraints_match_the_installed_engine_venv() -> None:
    """venvs/engine was installed with constraints-omni28.txt: every pin is what is installed."""
    python = ENGINE_VENV / "bin" / "python"
    if not python.exists():
        pytest.skip("no venvs/engine")
    code = ("import importlib.metadata as md, json; print(json.dumps({d.metadata['Name'].lower().replace('_', '-')"
            ".replace('.', '-'): d.version for d in md.distributions()}))")
    installed = json.loads(subprocess.run([str(python), "-c", code], capture_output=True, text=True,
                                          timeout=120).stdout)
    pins = dict(line.split("==") for line in (ENGINE / "constraints-omni28.txt").read_text().split())
    wrong = {k: (v, installed.get(k.lower().replace("_", "-").replace(".", "-"))) for k, v in pins.items()
             if installed.get(k.lower().replace("_", "-").replace(".", "-")) != v}
    assert wrong == {}


def test_no_machine_specific_paths_in_engine_and_deploy() -> None:
    files = [*ENGINE.glob("*.sh"), *ENGINE.glob("*.py"), *(ENGINE / "deploy").rglob("*.yaml"),
             *(SERVER / "deploy").glob("*.py"), *(SERVER / "deploy" / "systemd").glob("*.service"),
             SERVER / "deploy" / "env.example"]
    for path in files:
        text = path.read_text()
        assert "/home/vector" not in text and "%h/qwen3-tts-server" not in text, path
