"""Tests for the engine and deploy scripts: run_engine.sh, install_engine.sh, wait_ready.py, deploy/install_units.sh
and deploy/health_watchdog.py. CPU only: every venv, vllm, uv, nvcc and systemctl here is a fake in tmp_path.

Run: venvs/gateway/bin/python -m pytest engine/tests
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
SERVER = ENGINE.parent
DEPLOY = SERVER / "deploy"
BASE_PATH = "/usr/local/bin:/usr/bin:/bin"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve string annotations through sys.modules
    spec.loader.exec_module(module)
    return module


def script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def bash(*args: str | Path, env: dict[str, str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", *map(str, args)], capture_output=True, text=True, env=env, cwd=cwd, timeout=60)


def clean_env(**extra: str) -> dict[str, str]:
    env = {"HOME": os.environ.get("HOME", "/tmp"), "PATH": BASE_PATH, "LANG": "C.UTF-8"}
    env.update(extra)
    return env


# ---------------------------------------------------------------- run_engine.sh

@pytest.fixture
def fake_engine(tmp_path: Path) -> dict[str, Path]:
    """A venv whose vllm prints its argv, cwd and the relevant environment; a complete-looking model directory."""
    venv = tmp_path / "venv"
    site = tmp_path / "site"
    script(venv / "bin" / "python", f'echo "{site}"\n')
    script(site / "nvidia" / "cu13" / "bin" / "nvcc", 'echo "Cuda compilation tools, release 13.4, V13.4.92"\n')
    script(venv / "bin" / "vllm", 'echo "ARGS $*"; echo "PWD $(pwd)"\n'
           'for v in CUDA_VISIBLE_DEVICES VLLM_USE_FLASHINFER_SAMPLER CUDA_HOME SPEAKER_SAMPLES_DIR VLLM_API_KEY; do\n'
           '  echo "ENV $v=${!v-<unset>}"; done\n')
    (venv / "cuda13-link").mkdir()
    (venv / "cuda13-link" / "libcudart.so").write_text("")
    model = tmp_path / "model"
    for rel in ("config.json", "model.safetensors", "speech_tokenizer/config.json",
                "speech_tokenizer/model.safetensors"):
        (model / rel).parent.mkdir(parents=True, exist_ok=True)
        (model / rel).write_text("x")
    yaml = tmp_path / "deploy.yaml"
    yaml.write_text("async_chunk: true\n")
    return {"venv": venv, "model": model, "yaml": yaml, "speakers": tmp_path / "speakers"}


def run_engine(fake: dict[str, Path], *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    e = clean_env(TTS_ENGINE_MODEL=str(fake["model"]), SPEAKER_SAMPLES_DIR=str(fake["speakers"]), **env)
    return bash(ENGINE / "run_engine.sh", fake["yaml"], "18091", fake["venv"], *args, env=e, cwd=fake["venv"].parent)


def parse(out: str) -> dict[str, str]:
    pairs = (line[4:].split("=", 1) for line in out.splitlines() if line.startswith("ENV "))
    return {key: value for key, value in pairs}


def test_run_engine_defaults_to_gpu0_and_the_pytorch_sampler(fake_engine: dict[str, Path]) -> None:
    r = run_engine(fake_engine, "--", "--no-async-chunk", TTS_ENGINE_API_KEY="k1")
    assert r.returncode == 0, r.stderr
    env = parse(r.stdout)
    assert env["CUDA_VISIBLE_DEVICES"] == "0" and env["VLLM_USE_FLASHINFER_SAMPLER"] == "0"
    assert env["VLLM_API_KEY"] == "k1" and env["CUDA_HOME"].endswith("nvidia/cu13")
    assert env["SPEAKER_SAMPLES_DIR"] == str(fake_engine["speakers"])
    args = next(line for line in r.stdout.splitlines() if line.startswith("ARGS "))
    for flag in ("--omni", "--deploy-config", "--port 18091", "--trust-remote-code", "--served-model-name model",
                 "--stage-init-timeout", "--init-timeout", "--disable-access-log-for-endpoints", "--no-async-chunk"):
        assert flag in args, (flag, args)
    assert "k1" not in args  # the key goes through the environment, never argv
    assert f"PWD {SERVER}" in r.stdout  # relative custom_voice_dir resolves against server/
    assert "flashinfer sampler 0" in r.stderr


def test_run_engine_gpu_selection(fake_engine: dict[str, Path]) -> None:
    assert parse(run_engine(fake_engine, TTS_ENGINE_GPU="3").stdout)["CUDA_VISIBLE_DEVICES"] == "3"
    env = parse(run_engine(fake_engine, TTS_ENGINE_GPU="3", CUDA_VISIBLE_DEVICES="5").stdout)
    assert env["CUDA_VISIBLE_DEVICES"] == "5"
    assert parse(run_engine(fake_engine, VLLM_USE_FLASHINFER_SAMPLER="1").stdout)["VLLM_USE_FLASHINFER_SAMPLER"] == "1"


def test_run_engine_requires_the_custom_voice_manifest(fake_engine: dict[str, Path], tmp_path: Path) -> None:
    voices = tmp_path / "voices"
    voices.mkdir()
    fake_engine["yaml"].write_text(f'async_chunk: true\ncustom_voice_dir: "{voices}"  # precomputed\n')
    r = run_engine(fake_engine)
    assert r.returncode == 1 and "custom_voice_manifest.json is missing" in r.stderr
    (voices / "custom_voice_manifest.json").write_text("{}")
    r = run_engine(fake_engine)
    assert r.returncode == 0 and f"voices {voices}" in r.stderr, r.stderr
    fake_engine["yaml"].write_text("custom_voice_dir: state/no-such-voices-dir\n")
    r = run_engine(fake_engine)
    assert r.returncode == 1 and f"{SERVER}/state/no-such-voices-dir/custom_voice_manifest.json" in r.stderr


# ---------------------------------------------------------------- install_engine.sh

@pytest.fixture
def fake_tools(tmp_path: Path) -> dict[str, Path]:
    """A fake uv, a fake venv python (reports 3.12, logs pip calls) and a fake python3.12 that creates such venvs."""
    log = tmp_path / "calls.log"
    uv = script(tmp_path / "bin" / "uv", f'echo "uv $*" >> "{log}"; exit ${{UV_EXIT:-0}}\n')
    venv_python = script(tmp_path / "templates" / "python",
                         f'if [[ $1 == -c ]]; then echo 3.12; exit 0; fi\n'
                         f'echo "venv-python $*" >> "{log}"; exit ${{UV_EXIT:-0}}\n')
    py312 = script(tmp_path / "py" / "python3.12",
                   'if [[ $1 == -c ]]; then exit 0; fi\n'
                   f'if [[ $1 == -m && $2 == venv ]]; then mkdir -p "$3/bin" && cp "{venv_python}" "$3/bin/python"; '
                   'exit 0; fi\nexit 1\n')
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    shutil.copy(venv_python, venv / "bin" / "python")
    return {"log": log, "uv": uv, "py312": py312, "venv": venv}


def install(tools: dict[str, Path], *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    return bash(ENGINE / "install_engine.sh", *args, env=clean_env(**env))


def test_install_engine_uv_dry_run_with_auto_constraints(fake_tools: dict[str, Path]) -> None:
    r = install(fake_tools, "--dry-run", str(fake_tools["venv"]), "-", "0.28.0", "0.28.0", UV=str(fake_tools["uv"]))
    assert r.returncode == 0, r.stderr
    call = fake_tools["log"].read_text().strip()
    assert call == (f"uv pip install -p {fake_tools['venv']}/bin/python -c {ENGINE}/constraints-omni28.txt "
                    "--dry-run vllm==0.28.0 vllm-omni==0.28.0")
    assert "post-install steps skipped" in r.stdout


def test_install_engine_offline_wheels_and_pip(fake_tools: dict[str, Path], tmp_path: Path) -> None:
    (tmp_path / "w1").mkdir()
    (tmp_path / "w2").mkdir()
    wheels = f"{tmp_path / 'w1'}:{tmp_path / 'w2'}"
    r = install(fake_tools, "--installer", "pip", "--constraints", "none", "--dry-run", str(fake_tools["venv"]),
                wheels, "0.30.0", "0.30.0rc1", UV=str(fake_tools["uv"]))
    assert r.returncode == 0, r.stderr
    call = fake_tools["log"].read_text().strip()
    assert call.startswith("venv-python -m pip install --disable-pip-version-check --no-input --no-index "
                           f"--find-links {tmp_path / 'w1'} --find-links {tmp_path / 'w2'} --dry-run")
    assert " -c " not in call and call.endswith("vllm==0.30.0 vllm-omni==0.30.0rc1")
    # auto: the 0.30 constraints file pins exactly vllm 0.30.0 + vllm-omni 0.30.0rc1
    fake_tools["log"].unlink()
    assert install(fake_tools, "--dry-run", str(fake_tools["venv"]), wheels, "0.30.0", "0.30.0rc1",
                   UV=str(fake_tools["uv"])).returncode == 0
    assert f"-c {ENGINE}/constraints-omni30.txt" in fake_tools["log"].read_text()
    # no file pins these versions: resolve without constraints, and say so
    fake_tools["log"].unlink()
    r = install(fake_tools, "--dry-run", str(fake_tools["venv"]), "-", "0.28.1", "0.28.1", UV=str(fake_tools["uv"]))
    assert r.returncode == 0 and "no constraints file pins" in r.stderr and " -c " not in fake_tools["log"].read_text()


def test_install_engine_finds_python312(fake_tools: dict[str, Path], tmp_path: Path) -> None:
    new = tmp_path / "new-venv"
    # $PY312 wins; the fake uv then fails, which stops the script right after the venv was created
    r = install(fake_tools, str(new), "-", "0.28.0", "0.28.0", UV=str(fake_tools["uv"]), UV_EXIT="3",
                PY312=str(fake_tools["py312"]))
    assert r.returncode == 3 and f"creating {new} with {fake_tools['py312']}" in r.stdout, r.stdout + r.stderr
    assert f"uv pip install -p {new}/bin/python" in fake_tools["log"].read_text()
    # no PY312 and no python3.12 on PATH: the newest pyenv 3.12.x
    pyenv = tmp_path / "pyenv"
    for version in ("3.12.1", "3.12.10"):
        (pyenv / "versions" / version / "bin").mkdir(parents=True)
        shutil.copy(fake_tools["py312"], pyenv / "versions" / version / "bin" / "python3.12")
    new2 = tmp_path / "new-venv-2"
    r = install(fake_tools, str(new2), "-", "0.28.0", "0.28.0", UV=str(fake_tools["uv"]), UV_EXIT="3",
                PYENV_ROOT=str(pyenv), PATH="/usr/bin:/bin")  # this box also has /usr/local/bin/python3.12
    assert f"with {pyenv}/versions/3.12.10/bin/python3.12" in r.stdout, r.stdout + r.stderr
    # a PY312 that does not run is an error, not a fallback
    r = install(fake_tools, str(tmp_path / "v3"), "-", "0.28.0", "0.28.0", UV=str(fake_tools["uv"]),
                PY312=str(tmp_path / "missing-python"))
    assert r.returncode == 1 and "not a working Python 3.12" in r.stderr


def test_install_engine_usage_errors(fake_tools: dict[str, Path]) -> None:
    assert install(fake_tools, "venv", "-", "0.28.0").returncode == 1
    assert install(fake_tools, "--installer", "conda", str(fake_tools["venv"]), "-", "1", "1").returncode == 1
    r = install(fake_tools, "--installer", "uv", str(fake_tools["venv"]), "-", "1", "1", UV="/nonexistent/uv")
    assert r.returncode == 1 and "uv not found" in r.stderr


# ---------------------------------------------------------------- wait_ready.py

def test_wait_ready_voices_dir_and_language() -> None:
    wr = load_module("wait_ready", ENGINE / "wait_ready.py")
    assert wr.VOICES_DIR == SERVER.parent / "voices" or os.environ.get("TTS_VOICES_DIR")
    voices = SERVER.parent / "voices"
    if not (voices / "trump" / "voice.json").is_file():
        pytest.skip("no repo voices")
    assert wr.voice_folder(voices, "trump-avg") == "trump"
    assert wr.voice_folder(voices, "shehbaz-0123456789") == "shehbaz"
    assert wr.language(voices, "trump-prompt") == "English"
    assert wr.language(voices, "shehbaz-avg") == "Auto"
    assert wr.language(voices, "nobody") == "Auto"


# ---------------------------------------------------------------- deploy/install_units.sh

@pytest.fixture
def units_env(tmp_path: Path) -> dict[str, str]:
    log = tmp_path / "systemctl.log"
    script(tmp_path / "bin" / "systemctl", f'echo "$*" >> "{log}"\n')
    script(tmp_path / "bin" / "loginctl", 'echo no\n')
    return clean_env(PATH=f"{tmp_path / 'bin'}:{BASE_PATH}", XDG_CONFIG_HOME=str(tmp_path / "cfg"),
                     XDG_RUNTIME_DIR=str(tmp_path / "run"), PYTHON3=shutil.which("python3", path=BASE_PATH) or
                     "/usr/bin/python3")


def test_install_units_renders_this_checkout(units_env: dict[str, str], tmp_path: Path) -> None:
    r = bash(DEPLOY / "install_units.sh", env=units_env)
    assert r.returncode == 0, r.stderr
    unit_dir = tmp_path / "cfg" / "systemd" / "user"
    env_file = tmp_path / "cfg" / "qwen3-tts" / "env"
    names = {"qwen3-tts-engine.service", "qwen3-tts-engine-watchdog.service", "qwen3-tts-gateway.service",
             "qwen3-tts-qc.service"}
    assert {p.name for p in unit_dir.iterdir()} == names
    for unit in unit_dir.iterdir():
        text = unit.read_text()
        assert not re.search(r"@[A-Z0-9_]+@", text) and "%h" not in text and "qwen3-tts-server" not in text
        assert "EnvironmentFile=" in text and str(env_file) in text
    engine = (unit_dir / "qwen3-tts-engine.service").read_text()
    assert f"ExecStart={SERVER}/engine/run_engine.sh" in engine and f"WorkingDirectory={SERVER}\n" in engine
    assert "VLLM_USE_FLASHINFER_SAMPLER=0" in engine and "Restart=on-failure" in engine
    gateway = (unit_dir / "qwen3-tts-gateway.service").read_text()
    assert f"ExecStart={SERVER}/venvs/gateway/bin/python -m tts_gateway" in gateway
    assert "After=qwen3-tts-engine.service qwen3-tts-qc.service" in gateway
    assert "Requires=" not in gateway and "Wants=qwen3-tts-engine.service\n" in gateway  # QC is ordering only
    assert f"{SERVER}/venvs/eval/bin/python -m tts_qc" in (unit_dir / "qwen3-tts-qc.service").read_text()
    assert "health_watchdog.py" in (unit_dir / "qwen3-tts-engine-watchdog.service").read_text()
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    env_text = env_file.read_text()
    assert "change-me" not in env_text and not re.search(r"^CUDA_VISIBLE_DEVICES=", env_text, re.M)
    assert "\nTTS_ENGINE_GPU=0\n" in env_text and "\nVLLM_USE_FLASHINFER_SAMPLER=0\n" in env_text
    assert (tmp_path / "systemctl.log").read_text().strip() == "--user daemon-reload"
    assert "enable-linger" in r.stdout

    # second run keeps the secrets file, and flags stale settings of an older install
    env_file.write_text(env_text + "CUDA_VISIBLE_DEVICES=1\n")
    env_file.chmod(0o644)
    r = bash(DEPLOY / "install_units.sh", env=units_env)
    assert r.returncode == 0 and "keeping existing" in r.stdout and "use TTS_ENGINE_GPU" in r.stderr
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600 and env_file.read_text().startswith(env_text)

    if shutil.which("systemd-analyze"):
        v = subprocess.run(["systemd-analyze", "--user", "verify", *sorted(map(str, unit_dir.iterdir()))],
                           capture_output=True, text=True, timeout=60)
        assert v.returncode == 0, v.stderr


def test_install_units_enable_flags(units_env: dict[str, str], tmp_path: Path) -> None:
    assert bash(DEPLOY / "install_units.sh", "--with-qc", env=units_env).returncode == 1
    r = bash(DEPLOY / "install_units.sh", "--enable", "--with-qc", env=units_env)
    assert r.returncode == 0, r.stderr
    calls = (tmp_path / "systemctl.log").read_text().splitlines()
    assert calls[-1] == ("--user enable --now qwen3-tts-engine.service qwen3-tts-engine-watchdog.service "
                         "qwen3-tts-gateway.service qwen3-tts-qc.service")


def test_env_example_has_no_machine_paths() -> None:
    text = (DEPLOY / "env.example").read_text()
    assert "/home/" not in text and "\nCUDA_VISIBLE_DEVICES=" not in text


# ---------------------------------------------------------------- deploy/health_watchdog.py

def test_health_watchdog_restarts_only_an_active_unhealthy_unit() -> None:
    wd = load_module("health_watchdog", DEPLOY / "health_watchdog.py")
    states = iter(["activating", "active", "active", "active", "active", "inactive", "active"])
    probes = iter([(False, "HTTP 503"), (False, "timed out"), (True, "HTTP 200"), (False, "HTTP 503"),
                   (False, "refused")])
    restarts: list[str] = []
    logs: list[str] = []
    dog = wd.Watchdog("engine.service", "http://x/health", failures=2, interval=15, grace=120, timeout=1,
                      state=lambda unit: next(states), probe=lambda url, t: next(probes),
                      restart=lambda unit: restarts.append(unit) or True, log=logs.append)
    sleeps = [dog.step() for _ in range(7)]
    # activating: not checked; 503 + timeout = 2 failures -> restart, then grace
    assert sleeps[:3] == [15, 15, 120] and restarts == ["engine.service"]
    # healthy resets; one failure; unit goes inactive (count reset, no restart); one failure again: still below 2
    assert sleeps[3:] == [15, 15, 15, 15] and restarts == ["engine.service"] and dog.failed == 1
    assert any("restarting engine.service" in line for line in logs)


def test_health_watchdog_once_against_a_closed_port() -> None:
    r = subprocess.run(["python3", str(DEPLOY / "health_watchdog.py"), "--once", "--unit", "no-such-unit.service",
                        "--url", "http://127.0.0.1:9/health"], capture_output=True, text=True, timeout=60,
                       env=clean_env())
    assert r.returncode == 0  # the unit is not active, so nothing is probed or restarted
