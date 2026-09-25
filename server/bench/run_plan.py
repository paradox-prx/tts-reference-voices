#!/usr/bin/env python3
"""Run the benchmark plan (bench/plan.py) phase by phase: start the engine (vLLM-Omni variant, the qwen-tts baseline,
or a CPU stand-in), optionally the gateway and the QC sidecar, verify the phase's knobs, run bench_tts.py, snapshot
nvidia-smi and /metrics around every bench command, then stop what it started and check that the GPU is released
before the next phase.

    venvs/gateway/bin/python bench/run_plan.py --list                        # phases, status, audio h, GPU min
    venvs/gateway/bin/python bench/run_plan.py --dry-run --only 'P1_screen_*'
    venvs/gateway/bin/python bench/run_plan.py --only P0_smoke,P1_screen_default --stop-on-error
    venvs/gateway/bin/python bench/run_plan.py                               # every pending non-optional phase
    venvs/gateway/bin/python bench/run_plan.py --stub --only P0_smoke --results /tmp/x --logs /tmp/x/logs  # CPU test

Results (default server/results/), one folder per phase:
  <phase>/<run>/audio/*.wav, requests.jsonl, summary.json     one folder per bench run (see bench_tts.py)
  <phase>/requests.jsonl, summary.{csv,md,json}               every run of the phase
  <phase>/phase.json      config, estimate, versions, host, git, engine YAML, GPU baseline/release, commands, exit codes
  <phase>/commands.sh     the exact commands (keys come from the environment), for reproduction
  <phase>/versions/*.txt  every installed package of each venv used
  <phase>/logs/*.log      the engine / gateway / QC log lines of this phase; bench_NN_*.log per bench command
  <phase>/snapshots/      nvidia-smi, compute apps and /metrics before and after every bench command
  <phase>/knobs/<check>/  knob verification takes (AI-labelled WAVs) and verdicts
  <phase>/deploy.yaml     the engine deploy YAML used;   <phase>/DONE when it finished
Then bench/collect.py writes results/INDEX.md, results/ALL_summary.{csv,json} and results/REPORT_tables.md.

Resumable: a phase with <phase>/DONE is skipped unless --force; an unfinished (or forced) phase's folder is moved to
results/_attic/ first, so runs never mix. One runner per results folder (lock file). Keys: bench gets $TTS_API_KEY
(the gateway key; a throwaway one is generated when unset) or $TTS_ENGINE_API_KEY through its environment; keys never
appear in argv, logs or phase.json. GPU: --gpu (default $TTS_BENCH_GPU or 0) is the only GPU used or inspected. Before
a GPU engine starts, the GPU must have no compute process (the desktop's graphics memory is not one); after it
stops, no compute process may remain that this runner started (its process tree, tracked while it ran) or that
appeared during the phase. Only processes this runner started are ever signalled.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import fnmatch
import hashlib
import http.server
import importlib.util
import io
import json
import math
import os
import platform
import re
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]                      # server/
REPO = ROOT.parent                                               # the tts-reference-voices checkout
BENCH = REPO / "bench" / "bench_tts.py"
PYTHON = ROOT / "venvs" / "gateway" / "bin" / "python"          # runs the gateway, bench_tts.py and the checks
RUN_ENGINE = ROOT / "engine" / "run_engine.sh"
WAIT_READY = ROOT / "engine" / "wait_ready.py"
APPLY_PATCHES = ROOT / "engine" / "patches" / "apply_patches.py"
DEPLOY = ROOT / "engine" / "deploy"
BASELINE = ROOT / "baseline" / "qwen_tts_server.py"
FAKE_ENGINE = ROOT / "gateway" / "tests" / "fake_vllm_omni.py"
VERIFY_KNOBS = Path(__file__).with_name("verify_knobs.py")
QC_DIR = ROOT / "qc"
QC_LAUNCHER = ROOT / "eval" / "run.sh"                          # eval venv + cuBLAS 12: cd qc && ../eval/run.sh -m tts_qc
VOICES_DIR = REPO / "voices"
ENGINE_VENVS = ("engine", "engine30")
ENGINE_ENV = {"VLLM_USE_FLASHINFER_SAMPLER": "0"}               # FlashInfer's JIT sampler fails on this box
PKGS = {"engine": ("vllm", "vllm-omni", "torch", "torchaudio", "transformers", "flashinfer-python", "triton",
                   "nvidia-cudnn-cu13", "nvidia-nccl-cu13", "safetensors", "numpy"),
        "engine30": ("vllm", "vllm-omni", "torch", "torchaudio", "transformers", "flashinfer-python", "triton"),
        "gateway": ("fastapi", "uvicorn", "starlette", "httpx", "pydantic", "pydantic-settings", "numpy", "soundfile"),
        "qwentts": ("qwen-tts", "torch", "torchaudio", "transformers", "accelerate", "numpy"),
        "eval": ("torch", "transformers", "faster-whisper", "ctranslate2", "jiwer", "soundfile")}
RUNNER_FLAGS = ("--url", "--out", "--gpus", "--tag", "--api-key", "--meta")    # owned by the runner, not the plan
IGNORED_BY_ENGINE = ("temperature", "top_k", "top_p", "repetition_penalty")    # top-level: silently dropped
ENV_PREFIXES = ("TTS_", "VLLM_", "CUDA_", "HF_", "NCCL_", "PYTORCH_", "TORCH_", "FLASHINFER_", "OMP_", "SPEAKER_",
                "TRANSFORMERS_")
SECRET_WORDS = ("KEY", "TOKEN", "SECRET", "PASS", "CREDENTIAL")
GATEWAY_READY_S = 600.0
QC_READY_S = 600.0
GPU_RELEASE_S = 120.0
GPU_MEM_WARN_MIB = 1024          # after stop, memory this far above the baseline is reported (the desktop fluctuates)
STOP_GRACE_S = ((signal.SIGINT, 30.0), (signal.SIGTERM, 15.0), (signal.SIGKILL, 10.0))
WAV_BYTES_PER_S = 48000          # 24 kHz mono PCM16
DISK_MARGIN = 1.3                # audio estimate x this (suspect takes run long) when checking free disk

# Aggregate x-realtime of vLLM-Omni 0.28 on this 3090, engine direct, long pool (docs/EXPERIMENTS.md E01: c1 5.5,
# c4 15.6, c8 19.3, c16 26.3-27.6, c32 35, c64 38.5; c2 and c48 interpolated). Used only for --list GPU-minute
# estimates and the default bench timeouts; update after P2.
X_OMNI = {1: 5.5, 2: 9.5, 4: 15.6, 8: 19.3, 16: 27.0, 32: 35.0, 48: 36.5, 64: 38.5}
X_VARIANT = {"eager": 0.55, "fp32_talker": 0.7}
X_QWENTTS_C1 = 0.9               # qwen-tts 0.1.1 batch 1 on a 3090 (~RTF 1); a batch of b scales by b ** 0.6
START_MIN = {"vllm": 5.0, "qwentts": 2.0, "fake": 0.1, "stub": 0.1, "none": 0.0}


class PlanError(Exception):
    """The plan file is invalid."""


class PhaseError(Exception):
    """A phase failed; the run may continue with the next phase."""


class Abort(Exception):
    """Continuing would produce invalid measurements (GPU not released, disk full)."""


def iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


# ------------------------------------------------------------------------------------------------ plan

@dataclass(frozen=True)
class Engine:
    kind: str                  # vllm | qwentts | fake | stub | none (reuse whatever runs on the engine port)
    variant: str = ""          # vllm: engine/deploy/variants/<variant>.yaml; "prod" = engine/deploy/qwen3_tts_prod.yaml
    venv: str = "engine"       # vllm: venvs/<venv>
    args: tuple[str, ...] = ()  # vllm: extra `vllm serve` args; qwentts / fake: server args

    @property
    def yaml(self) -> Path | None:
        if self.kind != "vllm":
            return None
        return DEPLOY / "qwen3_tts_prod.yaml" if self.variant == "prod" else DEPLOY / "variants" / f"{self.variant}.yaml"

    @property
    def venv_path(self) -> Path:
        return ROOT / "venvs" / (self.venv if self.kind == "vllm" else "qwentts")

    @property
    def uses_gpu(self) -> bool:
        return self.kind in ("vllm", "qwentts")

    def describe(self) -> str:
        extra = f" {' '.join(self.args)}" if self.args else ""
        return {"vllm": f"vllm-omni {self.variant} ({self.venv}){extra}", "qwentts": f"qwen-tts baseline{extra}",
                "fake": f"fake vLLM-Omni (CPU){extra}", "stub": "stub gateway (CPU)",
                "none": "external engine"}[self.kind]


@dataclass(frozen=True)
class Bench:
    args: tuple[str, ...]
    via: str                   # "engine" or "gateway"
    tag: str                   # run-name prefix inside the phase folder
    timeout_s: float | None = None


@dataclass(frozen=True)
class Phase:
    name: str
    engine: Engine
    gateway: dict[str, str] | None     # TTS_* env overrides when the gateway is on
    qc: bool                           # start the QC sidecar (and point the gateway at it)
    bench: tuple[Bench, ...]
    checks: tuple[dict, ...] = ()      # verify_knobs.py specs, run after startup
    note: str = ""
    kind: str = "perf"                 # perf | quality (a label; no phase may send --seed)
    optional: bool = False             # only with --optional or when --only names it
    fresh_engine: bool = False         # never reuse the previous phase's engine
    ready_timeout_s: float = 1800.0
    requires: tuple[str, ...] = ()     # paths (relative to server/) that must exist, e.g. precomputed voices
    qc_env: tuple[tuple[str, str], ...] = ()  # TTS_QC_* overrides of this phase's QC sidecar (on top of plan QC_ENV)


PHASE_KEYS = {"name", "engine", "gateway", "qc", "bench", "checks", "note", "kind", "optional", "fresh_engine",
              "ready_timeout_s", "requires"}


def _flag_values(args: tuple[str, ...], flag: str) -> list[str]:
    vals = [args[i + 1] for i, a in enumerate(args[:-1]) if a == flag]
    return vals + [a.split("=", 1)[1] for a in args if a.startswith(flag + "=")]


def parse_engine(name: str, eng) -> Engine:
    if eng in ("none", None):
        return Engine("none")
    if not isinstance(eng, dict) or set(eng) - {"kind", "variant", "venv", "args"}:
        raise PlanError(f"{name}: engine must be 'none' or {{kind, variant, venv, args}}, got {eng!r}")
    e = Engine(eng.get("kind", "vllm"), eng.get("variant", ""), eng.get("venv", "engine"),
               tuple(str(a) for a in eng.get("args", ())))
    if e.kind not in ("vllm", "qwentts", "fake", "stub"):
        raise PlanError(f"{name}: unknown engine kind {e.kind!r}")
    if e.kind == "vllm" and (not e.variant or e.venv not in ENGINE_VENVS):
        raise PlanError(f"{name}: a vllm engine needs a variant and a venv in {ENGINE_VENVS}, got {eng!r}")
    return e


def parse_phase(raw: dict) -> Phase:
    name = str(raw.get("name", ""))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
        raise PlanError(f"bad phase name {name!r}")
    if unknown := set(raw) - PHASE_KEYS:
        raise PlanError(f"{name}: unknown keys {sorted(unknown)}")
    engine = parse_engine(name, raw.get("engine", "none"))
    gw = raw.get("gateway", False)
    gateway = None if gw in (False, None) else {} if gw is True else {str(k): str(v) for k, v in dict(gw).items()}
    qc_raw = raw.get("qc", False)
    qc = bool(qc_raw)
    qc_env = tuple((str(k), str(v)) for k, v in qc_raw.items()) if isinstance(qc_raw, dict) else ()
    if qc and gateway is None:
        raise PlanError(f"{name}: qc needs the gateway on")
    kind = raw.get("kind", "perf")
    if kind not in ("perf", "quality"):
        raise PlanError(f"{name}: kind must be perf or quality")
    bench = []
    for item in raw.get("bench", []):
        spec = item if isinstance(item, dict) else {"args": item}
        if set(spec) - {"args", "via", "tag", "timeout_s"}:
            raise PlanError(f"{name}: unknown bench keys in {spec!r}")
        args = tuple(str(a) for a in spec["args"])
        via = spec.get("via") or ("gateway" if gateway is not None else "engine")
        if via not in ("engine", "gateway"):
            raise PlanError(f"{name}: bad via {via!r}")
        if via == "gateway" and gateway is None:
            raise PlanError(f"{name}: a bench command via the gateway needs the gateway on")
        if owned := [a for a in args if a.split("=")[0] in RUNNER_FLAGS]:
            raise PlanError(f"{name}: {owned} are set by run_plan.py")
        if "--no-audio" in args:
            raise PlanError(f"{name}: --no-audio is not allowed (every output is kept)")
        if any(a.split("=")[0] == "--seed" for a in args):
            raise PlanError(f"{name}: no --seed in any phase: on vLLM-Omni 0.28 a seed does not reproduce even at c=1 "
                            "(docs/EXPERIMENTS.md E04), serialises the code predictor of the batch and disables the "
                            "engine's retry; repeat takes unseeded (--takes) and compare by prompt")
        params = {v.partition("=")[0] for v in _flag_values(args, "--param")}
        if via == "engine" and (dropped := params & set(IGNORED_BY_ENGINE)):
            raise PlanError(f"{name}: vLLM-Omni ignores top-level {sorted(dropped)}; use --extra-param")
        modes = _flag_values(args, "--voice-mode")
        if via == "gateway" and (modes or ["inline"])[-1] in ("inline", "nocache", "upload") \
                and (gateway or {}).get("TTS_ALLOW_INLINE_REF") != "1":
            raise PlanError(f"{name}: via the gateway use --voice-mode server (inline references need "
                            "TTS_ALLOW_INLINE_REF=1; the gateway has no upload route)")
        tag = str(spec.get("tag", ""))
        if tag and not re.fullmatch(r"[A-Za-z0-9._+=-]+", tag):
            raise PlanError(f"{name}: bad tag {tag!r}")
        bench.append(Bench(args, via, tag, float(spec["timeout_s"]) if spec.get("timeout_s") else None))
    checks = []
    for chk in raw.get("checks", []):
        if not isinstance(chk, dict) or not chk.get("name") or chk.get("via", "engine") not in ("engine", "gateway"):
            raise PlanError(f"{name}: a check needs a name and via engine|gateway: {chk!r}")
        if chk.get("via") == "gateway" and gateway is None:
            raise PlanError(f"{name}: check {chk['name']} via the gateway needs the gateway on")
        checks.append(chk)
    return Phase(name, engine, gateway, qc, tuple(bench), tuple(checks), str(raw.get("note", "")), kind,
                 bool(raw.get("optional", False)), bool(raw.get("fresh_engine", False)),
                 float(raw.get("ready_timeout_s", 1800.0)), tuple(str(r) for r in raw.get("requires", ())), qc_env)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise PlanError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod                      # dataclasses resolve string annotations through sys.modules
    spec.loader.exec_module(mod)
    return mod


def load_plan(path: Path) -> tuple[list[Phase], object]:
    mod = load_module(path, "bench_plan")
    phases = [parse_phase(p) for p in mod.PHASES]
    if dups := {p.name for p in phases if [q.name for q in phases].count(p.name) > 1}:
        raise PlanError(f"duplicate phase names {sorted(dups)}")
    return phases, mod


def select(phases: list[Phase], only: str | None, optional: bool) -> list[Phase]:
    """--only picks phases by name or glob (an exact name also picks an optional phase; a glob only with
    --optional); otherwise every non-optional phase (and the optional ones with --optional)."""
    if not only:
        return [p for p in phases if optional or not p.optional]
    pats = [p.strip() for p in only.split(",") if p.strip()]
    if missing := [p for p in pats if not any(fnmatch.fnmatchcase(ph.name, p) for ph in phases)]:
        raise PlanError(f"--only {missing} match no phase; see --list")
    return [ph for ph in phases if any(ph.name == p or (fnmatch.fnmatchcase(ph.name, p) and (optional or not ph.optional))
                                       for p in pats)]


# ------------------------------------------------------------------------------------------------ estimates

_bench_mod = None


def bench_module():
    global _bench_mod
    if _bench_mod is None:
        _bench_mod = load_module(BENCH, "bench_tts")
    return _bench_mod


def x_realtime(engine: Engine, c: int, seeded: bool, stream: bool) -> float:
    if engine.kind == "qwentts":
        batch = int(_flag_values(engine.args, "--max-batch")[-1]) if _flag_values(engine.args, "--max-batch") else 8
        return X_QWENTTS_C1 * min(c, batch) ** 0.6
    keys = sorted(X_OMNI)
    lo = max([k for k in keys if k <= c], default=keys[0])
    hi = min([k for k in keys if k >= c], default=keys[-1])
    x = X_OMNI[lo] if lo == hi else X_OMNI[lo] + (X_OMNI[hi] - X_OMNI[lo]) * (c - lo) / (hi - lo)
    if seeded and c > 1:                     # 0.28: a seeded row runs the code predictor row by row
        x = min(x, X_OMNI[1] * 1.5)
    x *= X_VARIANT.get(engine.variant, 1.0) * (0.9 if stream else 1.0)
    return x


def estimate_bench(b: Bench, engine: Engine) -> dict:
    """{audio_s, requests, gpu_s, runs} of one bench command (bench_tts.py --estimate, in process)."""
    try:
        est = bench_module().estimate([*b.args, "--estimate"])
    except SystemExit as exc:                # argparse error inside the plan's args
        raise PlanError(f"bench args {list(b.args)} rejected by bench_tts.py (exit {exc.code})") from None
    except (OSError, ValueError, KeyError) as exc:    # unknown voice, missing pools / prompts file
        raise PlanError(f"bench args {list(b.args)}: {type(exc).__name__}: {exc}") from None
    gpu_s = 0.0
    for r in est["runs"]:
        if "audio_s" in r:
            gpu_s += r["audio_s"] / x_realtime(engine, r["c"], r["seeded"], r["stream"]) + 0.02 * r["requests"]
    gpu_s += est["warmup_audio_s"] / 3.0
    return {"audio_s": est["audio_s"] + est["warmup_audio_s"], "requests": est["requests"] + est["warmup_requests"],
            "gpu_s": gpu_s, "runs": len(est["runs"])}


def estimate_phase(ph: Phase) -> dict:
    parts = [estimate_bench(b, ph.engine) for b in ph.bench]
    gpu_min = sum(p["gpu_s"] for p in parts) / 60 + START_MIN.get(ph.engine.kind, 0.0) \
        + (1.0 if ph.gateway is not None else 0.0) + (2.0 if ph.qc else 0.0) + 0.5 * len(ph.checks)
    return {"audio_h": round(sum(p["audio_s"] for p in parts) / 3600, 2),
            "audio_gb": round(sum(p["audio_s"] for p in parts) * WAV_BYTES_PER_S / 1e9, 2),
            "requests": sum(p["requests"] for p in parts), "runs": sum(p["runs"] for p in parts),
            "gpu_min": round(gpu_min, 1), "per_command": parts}


# ------------------------------------------------------------------------------------------------ host helpers

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))    # localhost never goes through a proxy


def http_get(url: str, timeout: float = 5.0, key: str | None = None) -> tuple[int | None, str]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"} if key else {})
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except OSError as exc:
        return None, str(exc)


def port_in_use(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def nvidia_smi(*args: str) -> str:
    try:
        r = subprocess.run(["nvidia-smi", *args], capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else f"nvidia-smi {' '.join(args)}: exit {r.returncode} {r.stderr}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"nvidia-smi unavailable: {exc}"


def gpu_mem_mib(gpu: str) -> int | None:
    out = nvidia_smi(f"--id={gpu}", "--query-gpu=memory.used", "--format=csv,noheader,nounits").strip()
    return int(out) if out.isdigit() else None


def compute_apps(gpu: str) -> list[dict] | None:
    """Compute processes on the GPU (graphics clients such as the desktop are not listed); None = nvidia-smi failed."""
    out = nvidia_smi(f"--id={gpu}", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader,nounits")
    if out.startswith("nvidia-smi"):
        return None
    apps = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3 and parts[0].isdigit():
            apps.append({"pid": int(parts[0]), "name": ",".join(parts[1:-1]),
                         "mib": int(parts[-1]) if parts[-1].isdigit() else None})
    return apps


def _proc_stat(pid: int) -> tuple[int, int] | None:
    """(ppid, start time) of a live pid."""
    try:
        s = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    f = s[s.rindex(")") + 2:].split()
    return int(f[1]), int(f[19])


def descendants(root: int) -> list[tuple[int, int]]:
    """(pid, start time) of every live descendant of root."""
    children: dict[int, list[tuple[int, int]]] = {}
    for d in Path("/proc").iterdir():
        if d.name.isdigit() and (st := _proc_stat(int(d.name))):
            children.setdefault(st[0], []).append((int(d.name), st[1]))
    out, todo = [], [root]
    while todo:
        for pid, start in children.get(todo.pop(), []):
            out.append((pid, start))
            todo.append(pid)
    return out


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def tree_sha256(root: Path) -> str | None:
    """One hash over every file under root (names and contents), ignoring caches."""
    if not root.is_dir():
        return None
    h = hashlib.sha256()
    for p in sorted(q for q in root.rglob("*") if q.is_file() and "__pycache__" not in q.parts):
        h.update(str(p.relative_to(root)).encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def is_secret(name: str) -> bool:
    return any(w in name.upper() for w in SECRET_WORDS)


def redact(env: dict[str, str]) -> dict[str, str]:
    return {k: "<redacted>" if is_secret(k) else v for k, v in env.items()}


def visible_env(env: dict[str, str]) -> dict[str, str]:
    """The environment variables that matter for a run, with secrets redacted."""
    return redact({k: v for k, v in sorted(env.items()) if k.startswith(ENV_PREFIXES)})


def env_prefix(env: dict[str, str]) -> str:
    return " ".join(f"{k}={shlex.quote(v)}" for k, v in visible_env(env).items())


def pkg_versions(python: Path, pkgs: tuple[str, ...]) -> dict:
    """Package versions of a venv, read from metadata (nothing is imported, so no CUDA initialisation), plus the full
    list of installed distributions."""
    code = ("import importlib.metadata as m, json, sys\n"
            "def v(p):\n"
            "    try:\n        return m.version(p)\n"
            "    except m.PackageNotFoundError:\n        return None\n"
            "allv = sorted({f\"{d.metadata['Name']}=={d.version}\" for d in m.distributions() if d.metadata['Name']},"
            " key=str.lower)\n"
            "print(json.dumps({'python': sys.version.split()[0], 'packages': {p: v(p) for p in sys.argv[1:]},"
            " 'all': allv}))")
    if not python.exists():
        return {"error": f"{python} missing"}
    try:
        r = subprocess.run([str(python), "-c", code, *pkgs], capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"error": str(exc)}


def git_info() -> dict:
    def git(*a: str) -> str | None:
        try:
            r = subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True, timeout=30)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    status = git("status", "--porcelain") or ""
    return {"head": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty_files": [line[3:] for line in status.splitlines()][:200]}


def host_info(gpu: str) -> dict:
    def read(p: str) -> str | None:
        with contextlib.suppress(OSError):
            return Path(p).read_text().strip()
        return None
    cpu = next((line.split(":", 1)[1].strip() for line in (read("/proc/cpuinfo") or "").splitlines()
                if line.startswith("model name")), None)
    mem = next((line.split(":", 1)[1].strip() for line in (read("/proc/meminfo") or "").splitlines()
                if line.startswith("MemTotal")), None)
    osname = next((line.split("=", 1)[1].strip('"') for line in (read("/etc/os-release") or "").splitlines()
                   if line.startswith("PRETTY_NAME=")), None)
    return {"hostname": platform.node(), "os": osname, "kernel": platform.release(), "cpu": cpu, "cpus": os.cpu_count(),
            "mem_total": mem, "cpu_governor": read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
            "cpu_epp": read("/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference"),
            "no_turbo": read("/sys/devices/system/cpu/intel_pstate/no_turbo"), "tz": time.strftime("%Z %z"),
            "gpu": nvidia_smi(f"--id={gpu}", "--query-gpu=index,name,uuid,driver_version,vbios_version,power.limit,"
                              "clocks.max.sm,clocks.max.mem,pcie.link.gen.max,pcie.link.width.max,memory.total",
                              "--format=csv").strip()}


def disk_free_gb(path: Path) -> float:
    p = path
    while not p.exists():
        p = p.parent
    return round(shutil.disk_usage(p).free / 1e9, 2)


def dir_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else 0


# ------------------------------------------------------------------------------------------------ processes

class Child:
    """A long-running subprocess in its own session (process group), output appended to a log file. `mark()` and
    `copy_since()` cut the log per phase."""

    def __init__(self, what: str, cmd: list[str], env: dict[str, str], cwd: Path, log: Path) -> None:
        self.what, self.log, self.cmd, self.cwd = what, log, cmd, cwd
        log.parent.mkdir(parents=True, exist_ok=True)
        self.start_offset = log.stat().st_size if log.exists() else 0
        self._log = open(log, "ab")
        self._log.write(f"\n=== {iso()} run_plan: cd {cwd} && {env_prefix(env)} {shlex.join(cmd)}\n".encode())
        self._log.flush()
        self.proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=self._log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
        self.tracked: set[tuple[int, int]] = set()
        self.track()

    def alive(self) -> bool:
        return self.proc.poll() is None

    def track(self) -> set[int]:
        """Remember the process tree (pid, start time) as it is now; returns every pid seen so far."""
        if self.alive() and (st := _proc_stat(self.proc.pid)):
            self.tracked.add((self.proc.pid, st[1]))
        self.tracked.update(descendants(self.proc.pid))
        return {pid for pid, _ in self.tracked}

    def mark(self) -> int:
        if not self._log.closed:
            self._log.flush()
        return self.log.stat().st_size if self.log.exists() else 0

    def copy_since(self, offset: int, dest: Path) -> None:
        """Append the log from `offset` to dest (the phase's own slice of a log that may span phases)."""
        if not self._log.closed:
            self._log.flush()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log, "rb") as src, open(dest, "ab") as dst:
            src.seek(offset)
            shutil.copyfileobj(src, dst)

    def _group_gone(self) -> bool:
        self.proc.poll()                                 # reap the leader so it no longer counts
        try:
            os.killpg(self.proc.pid, 0)
        except ProcessLookupError:
            return True
        return False

    def stop(self) -> str:
        """SIGINT, then SIGTERM, then SIGKILL to the process group; tracked descendants that left the group are
        killed at the end (same pid and start time only). Returns how it ended."""
        self.track()
        how = f"exited ({self.proc.returncode})" if not self.alive() else "exited"
        for sig, grace in STOP_GRACE_S:
            if self._group_gone():
                break
            how = sig.name
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self.proc.pid, sig)
            deadline = time.monotonic() + grace
            while time.monotonic() < deadline and not self._group_gone():
                time.sleep(0.2)
        for pid, start in self.tracked:
            if (st := _proc_stat(pid)) and st[1] == start:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGKILL)
        self.proc.poll()
        with contextlib.suppress(OSError):
            self._log.close()
        return how


def tee(cmd: list[str], env: dict[str, str], log: Path, timeout_s: float) -> int | str:
    """Run cmd in its own process group to completion (or until timeout_s: then the group is killed and 'timeout'
    returned); its output goes to log and, indented, to our stdout."""
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"=== {iso()} {shlex.join(cmd)}\n")
        proc = subprocess.Popen(cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, errors="replace", start_new_session=True)
        timed_out = threading.Event()

        def kill_group(sig: int = signal.SIGKILL) -> None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, sig)

        def watchdog() -> None:
            timed_out.set()
            kill_group(signal.SIGTERM)
            time.sleep(10)
            kill_group()
        timer = threading.Timer(timeout_s, watchdog)
        timer.daemon = True
        timer.start()
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                f.write(line)
                f.flush()
                print("    " + line, end="", flush=True)
            code = proc.wait()
            return "timeout" if timed_out.is_set() else code
        finally:
            timer.cancel()
            if proc.poll() is None:
                kill_group(signal.SIGTERM)
                with contextlib.suppress(subprocess.TimeoutExpired):
                    proc.wait(10)
            kill_group()                                 # nvidia-smi and anything else left in bench's group
            proc.wait()


# ------------------------------------------------------------------------------------------------ fake QC sidecar

def serve_fake_qc(port: int) -> None:
    """--fake-qc PORT: a stand-in for server/qc (CPU tests only): /health 200, every take passes."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def _json(self, obj: dict) -> None:
            body = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:                        # noqa: N802
            self._json({"ok": True, "fake": True})

        def do_POST(self) -> None:                       # noqa: N802
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            self._json({"pass": True, "reasons": [], "metrics": {"fake": True}, "ms": 1.0})

        def log_message(self, *a) -> None:
            pass
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


# ------------------------------------------------------------------------------------------------ runner

@dataclass
class LiveEngine:
    """An engine this runner started; kept across phases while the next phase wants the same engine."""
    spec: Engine
    child: Child
    owner: str
    record: dict
    baseline_mib: int | None
    baseline_apps: list[dict] | None


@dataclass
class PhaseCtx:
    ph: Phase
    out: Path
    rec: dict
    children: list[tuple[str, Child, int]] = field(default_factory=list)    # (name, child, log offset)
    commands: list[str] = field(default_factory=list)


class Runner:
    def __init__(self, args: argparse.Namespace, plan_mod) -> None:
        self.args = args
        self.gpu = str(args.gpu)
        self.results: Path = args.results
        self.logs: Path = args.logs
        self.engine_url = f"http://127.0.0.1:{args.engine_port}"
        self.gateway_url = f"http://127.0.0.1:{args.gateway_port}"
        self.qc_url = f"http://127.0.0.1:{args.qc_port}"
        self.gateway_key = os.environ.get("TTS_API_KEY") or secrets.token_urlsafe(24)
        self.engine_key = os.environ.get("TTS_ENGINE_API_KEY")
        self.qc_cmd = getattr(plan_mod, "QC_CMD", None)
        self.qc_env = {str(k): str(v) for k, v in (getattr(plan_mod, "QC_ENV", None) or {}).items()}
        self.live: LiveEngine | None = None
        self._versions: dict[str, dict] = {}

    # --- commands (shared by --dry-run and the real run)

    def engine_launch(self, spec: Engine) -> tuple[list[str], dict[str, str], Path, str]:
        """argv, env overrides, cwd and readiness path of an engine."""
        port = str(self.args.engine_port)
        gpu_env = {"CUDA_VISIBLE_DEVICES": self.gpu, "TTS_ENGINE_GPU": self.gpu}
        if spec.kind == "stub":
            return ([str(PYTHON), "-m", "tts_gateway"],
                    {"TTS_BACKEND": "stub", "TTS_HOST": "127.0.0.1", "TTS_PORT": port, "TTS_AUTH_DISABLED": "1",
                     "TTS_ALLOW_INLINE_REF": "1"}, ROOT / "gateway", "/ready")
        if spec.kind == "fake":
            return [str(PYTHON), str(FAKE_ENGINE), "--port", port, "--patched", *spec.args], {}, ROOT / "gateway", "/health"
        if spec.kind == "qwentts":
            return ([str(spec.venv_path / "bin" / "python"), str(BASELINE), "--host", "127.0.0.1", "--port", port,
                     *spec.args], {**gpu_env, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}, ROOT, "/health")
        cmd = ["bash", str(RUN_ENGINE), str(spec.yaml), port, str(spec.venv_path)]
        return cmd + (["--", *spec.args] if spec.args else []), {**gpu_env, **ENGINE_ENV}, ROOT, "/health"

    def gateway_launch(self, ph: Phase, engine: Engine) -> tuple[list[str], dict[str, str]]:
        stub = engine.kind == "stub"
        env = {"TTS_HOST": "127.0.0.1", "TTS_PORT": str(self.args.gateway_port), "TTS_ENGINE_URL": self.engine_url,
               "TTS_API_KEY": self.gateway_key, "TTS_VOICES_DIR": str(VOICES_DIR),
               **({"TTS_ENGINE_API_KEY": self.engine_key} if self.engine_key else {}),
               **({"TTS_BACKEND": "stub"} if stub else {}), **({"TTS_QC_URL": self.qc_url} if ph.qc else {}),
               **(ph.gateway or {})}
        return [str(PYTHON), "-m", "tts_gateway"], env

    def qc_launch(self, ph: Phase | None = None) -> tuple[list[str], dict[str, str], Path]:
        env = {"TTS_QC_HOST": "127.0.0.1", "TTS_QC_PORT": str(self.args.qc_port), "CUDA_VISIBLE_DEVICES": self.gpu,
               **self.qc_env, **dict(ph.qc_env if ph else ())}
        if self.args.stub:
            return [str(PYTHON), str(Path(__file__).resolve()), "--fake-qc", str(self.args.qc_port)], {}, ROOT
        if self.qc_cmd:
            return [str(a).format(root=ROOT, port=self.args.qc_port) for a in self.qc_cmd], env, QC_DIR
        if QC_LAUNCHER.exists():
            return ["bash", str(QC_LAUNCHER), "-m", "tts_qc"], env, QC_DIR
        return [str(ROOT / "venvs" / "eval" / "bin" / "python"), "-m", "tts_qc"], env, QC_DIR

    def meta_args(self, ph: Phase, b: Bench) -> list[str]:
        eng = self.effective_engine(ph)
        gw = {k: v for k, v in (ph.gateway or {}).items() if not is_secret(k)}
        meta = {"phase": ph.name, "via": b.via, "engine": eng.describe(), "engine_kind": eng.kind,
                "variant": eng.variant, "venv": eng.venv if eng.kind == "vllm" else "",
                "gateway": json.dumps(gw, sort_keys=True) if b.via == "gateway" else "", "qc": str(ph.qc).lower()}
        return [a for k, v in meta.items() for a in ("--meta", f"{k}={v}")]

    def bench_launch(self, ph: Phase, b: Bench, out: Path) -> tuple[list[str], dict[str, str]]:
        url = self.gateway_url if b.via == "gateway" else self.engine_url
        cmd = [str(PYTHON), str(BENCH), *b.args, "--url", url, "--out", str(out), "--gpus", self.gpu,
               *(["--tag", b.tag] if b.tag else []), *self.meta_args(ph, b)]
        key = self.gateway_key if b.via == "gateway" else self.engine_key
        env = {k: v for k, v in os.environ.items() if k != "TTS_API_KEY"} | {"PYTHONUNBUFFERED": "1"}
        return cmd, env | ({"TTS_API_KEY": key} if key else {})

    def check_launch(self, chk: dict, out: Path) -> tuple[list[str], dict[str, str]]:
        via = chk.get("via", "engine")
        url = self.gateway_url if via == "gateway" else self.engine_url
        cmd = [str(PYTHON), str(VERIFY_KNOBS), "--url", url, "--out", str(out / "knobs"), "--voices-dir",
               str(VOICES_DIR), "--spec", json.dumps(chk, ensure_ascii=False)] + (["--lenient"] if self.args.stub else [])
        key = self.gateway_key if via == "gateway" else self.engine_key
        env = {k: v for k, v in os.environ.items() if k != "TTS_API_KEY"} | {"PYTHONUNBUFFERED": "1"}
        return cmd, env | ({"TTS_API_KEY": key} if key else {})

    def effective_engine(self, ph: Phase) -> Engine:
        if ph.engine.kind == "none" and self.live:
            return self.live.spec
        return ph.engine

    def bench_timeout(self, ph: Phase, b: Bench) -> float:
        if b.timeout_s:
            return b.timeout_s
        return max(1800.0, 4 * estimate_bench(b, ph.engine)["gpu_s"] + 900)

    # --- listing and dry run

    def show(self, ph: Phase, status: str) -> None:
        out = self.results / ph.name
        est = estimate_phase(ph)
        print(f"\n== {ph.name}  [{status}]{'  (optional)' if ph.optional else ''}  {ph.kind}; "
              f"~{est['audio_h']} h audio ({est['audio_gb']} GB), ~{est['gpu_min']} GPU min, {est['requests']} requests"
              + (f"\n   {ph.note}" if ph.note else ""))
        if ph.engine.kind == "none":
            print(f"  engine: reuse the engine running at {self.engine_url}")
        else:
            cmd, env, cwd, ready = self.engine_launch(ph.engine)
            print(f"  engine: {ph.engine.describe()}" + (f"  yaml {ph.engine.yaml}" if ph.engine.yaml else "")
                  + ("" if not (missing := self.missing(ph.engine, ph.requires)) else f"  MISSING: {', '.join(missing)}")
                  + ("  (fresh)" if ph.fresh_engine else ""))
            print(f"    $ cd {cwd} && {env_prefix(env)} {shlex.join(cmd)} >> {self.logs / f'engine_{ph.name}.log'}")
            print(f"    ready: GET {self.engine_url}{ready} within {ph.ready_timeout_s:.0f} s"
                  + (f", then {WAIT_READY.name}" if ph.engine.kind == "vllm" else ""))
        if ph.qc:
            cmd, env, cwd = self.qc_launch(ph)
            print(f"  qc: $ cd {cwd} && {env_prefix(env)} {shlex.join(cmd)}; ready: GET {self.qc_url}/health")
        if ph.gateway is None:
            print("  gateway: off")
        else:
            cmd, env = self.gateway_launch(ph, self.effective_engine(ph))
            print(f"  gateway: $ cd {ROOT / 'gateway'} && {env_prefix(env)} {shlex.join(cmd)}"
                  f" >> {self.logs / f'gateway_{ph.name}.log'}")
            print(f"    ready: GET {self.gateway_url}/ready within {GATEWAY_READY_S:.0f} s")
        for chk in ph.checks:
            cmd, _ = self.check_launch(chk, out)
            print(f"  check {chk['name']} via {chk.get('via', 'engine')}: {shlex.join(cmd)}")
        for i, (b, e) in enumerate(zip(ph.bench, est["per_command"]), 1):
            cmd, _ = self.bench_launch(ph, b, out)
            print(f"  [{i}] via {b.via} (~{e['audio_s'] / 3600:.2f} h audio, ~{e['gpu_s'] / 60:.1f} min, "
                  f"timeout {self.bench_timeout(ph, b):.0f} s): {shlex.join(cmd)} > {out / f'bench_{i:02d}_{b.via}.log'}")
        print(f"  then: stop what the phase started (SIGINT, SIGTERM, SIGKILL), GPU {self.gpu} released, phase.json, DONE")

    def missing(self, spec: Engine, requires: tuple[str, ...] = ()) -> list[str]:
        extra = [str(ROOT / r) for r in requires if not (ROOT / r).exists()]
        if spec.kind == "vllm":
            need = (spec.yaml, RUN_ENGINE, spec.venv_path / "bin" / "vllm")
        elif spec.kind == "qwentts":
            need = (BASELINE, spec.venv_path / "bin" / "python")
        elif spec.kind == "fake":
            need = (FAKE_ENGINE,)
        else:
            need = ()
        return [str(p) for p in need if p and not p.exists()] + extra

    # --- real run

    def run_phase(self, ph: Phase, keep_engine: bool) -> bool:
        out = self.results / ph.name
        print(f"\n=== {ph.name}" + (f": {ph.note}" if ph.note else ""), flush=True)
        if out.exists():
            attic = self.results / "_attic" / f"{ph.name}_{dt.datetime.now():%Y%m%d_%H%M%S}"
            attic.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(out, attic)
            print(f"  previous results moved to {attic}")
        out.mkdir(parents=True)
        t0 = time.monotonic()
        est = estimate_phase(ph)
        spec = {"engine": ph.engine.__dict__ | {"args": list(ph.engine.args)}, "gateway": redact(ph.gateway)
                if ph.gateway is not None else None, "qc": ph.qc, "kind": ph.kind, "optional": ph.optional,
                "fresh_engine": ph.fresh_engine, "checks": list(ph.checks),
                "bench": [{"args": list(b.args), "via": b.via, "tag": b.tag, "timeout_s": b.timeout_s} for b in ph.bench]}
        rec: dict = {"phase": ph.name, "note": ph.note, "status": "running", "started": iso(), "stub": self.args.stub,
                     "argv": sys.argv, "plan": str(self.args.plan), "plan_sha256": sha256(self.args.plan), "spec": spec,
                     "estimate": {k: v for k, v in est.items() if k != "per_command"}, "host": host_info(self.gpu),
                     "git": git_info(),
                     "sources": {"bench_tts.py": sha256(BENCH), "run_plan.py": sha256(Path(__file__)),
                                 "verify_knobs.py": sha256(VERIFY_KNOBS),
                                 "gateway": tree_sha256(ROOT / "gateway" / "tts_gateway"),
                                 "engine_patches": tree_sha256(ROOT / "engine" / "patches"),
                                 "run_engine.sh": sha256(RUN_ENGINE), "baseline": sha256(BASELINE),
                                 "qc": tree_sha256(QC_DIR / "tts_qc"), "pace.json": sha256(ROOT / "calibration" / "pace.json")},
                     "gpu": {"index": self.gpu, "phase_start_mib": gpu_mem_mib(self.gpu),
                             "phase_start_apps": compute_apps(self.gpu)},
                     "disk": {"free_gb_before": disk_free_gb(self.results)},
                     "knob_checks": [], "bench": []}
        ctx = PhaseCtx(ph, out, rec)
        (out / "snapshots").mkdir()
        (out / "snapshots" / "phase_start_nvidia-smi.txt").write_text(f"# {iso()}\n" + nvidia_smi("-i", self.gpu)
                                                                      + nvidia_smi("-q", "-i", self.gpu),
                                                                      encoding="utf-8")
        ok = False
        try:
            self.check_disk(est["audio_gb"], f"phase {ph.name}")
            rec["engine"] = self.ensure_engine(ctx)
            rec["versions"] = self.versions(ctx)
            if ph.qc:
                rec["qc"] = self.start_child(ctx, "qc", *self.qc_launch(ph), f"{self.qc_url}/health", QC_READY_S)
            if ph.gateway is not None:
                cmd, env = self.gateway_launch(ph, self.effective_engine(ph))
                rec["gateway"] = self.start_child(ctx, "gateway", cmd, env, ROOT / "gateway",
                                                  f"{self.gateway_url}/ready", GATEWAY_READY_S)
                rec["gateway"]["overrides"] = redact(ph.gateway)
                rec["gateway"]["ready_body"] = self.json_get(self.gateway_url + "/ready")
                rec["gateway"]["voices"] = self.json_get(self.gateway_url + "/v1/voices", self.gateway_key)
            else:
                rec["gateway"] = {"enabled": False}
            for chk in ph.checks:
                self.run_check(ctx, chk)
            for i, b in enumerate(ph.bench, 1):
                self.run_bench(ctx, i, b)
            ok = True
        except PhaseError as exc:
            rec["error"] = str(exc)
            print(f"  FAILED: {exc}", flush=True)
        except Abort as exc:
            rec["error"] = f"abort: {exc}"
            raise
        except KeyboardInterrupt:
            rec["error"] = "interrupted"
            raise
        finally:
            self.finish_phase(ctx, ok, keep_engine, t0)
        if rec["gpu"].get("released") is False:
            raise Abort(f"GPU {self.gpu} still has compute processes after the phase: "
                        f"{rec['gpu'].get('remaining_apps')}; later phases would be measured on a busy GPU")
        return ok

    def finish_phase(self, ctx: PhaseCtx, ok: bool, keep_engine: bool, t0: float) -> None:
        rec, out = ctx.rec, ctx.out
        for name, child, offset in reversed(ctx.children):          # gateway before QC; the engine separately
            try:
                rec.setdefault(name, {})["stopped_with"] = child.stop()
                print(f"  {name} stopped ({rec[name]['stopped_with']})", flush=True)
                child.copy_since(offset, out / "logs" / f"{name}.log")
            except Exception as exc:                                 # noqa: BLE001 - keep cleaning up
                rec.setdefault("cleanup_errors", []).append(f"{name}: {type(exc).__name__}: {exc}")
        child_pids: set[int] = {pid for _, c, _ in ctx.children for pid, _ in c.tracked}
        if self.live:
            live = self.live
            try:
                live.child.copy_since(rec.get("engine", {}).get("log_offset", live.child.start_offset),
                                      out / "logs" / "engine.log")
                rec.setdefault("engine", {})["log_findings"] = self.log_findings(out / "logs" / "engine.log")
            except Exception as exc:                                 # noqa: BLE001
                rec.setdefault("cleanup_errors", []).append(f"engine log: {type(exc).__name__}: {exc}")
            if not (ok and keep_engine):
                rec["gpu"].update(self.stop_engine(child_pids))
            else:
                rec["gpu"]["engine_kept_for_next_phase"] = True
                if child_pids:
                    rec["gpu"].update(self.wait_pids_gone(child_pids))
        elif child_pids:                                             # QC next to an external engine
            rec["gpu"].update(self.wait_pids_gone(child_pids))
        rec.update(status="done" if ok else "interrupted" if rec.get("error") == "interrupted" else "failed",
                   finished=iso(), duration_s=round(time.monotonic() - t0, 1))
        rec["disk"].update(free_gb_after=disk_free_gb(self.results), phase_bytes=dir_bytes(out))
        rec["audio"] = self.audio_totals(out)
        rec["commands"] = ctx.commands
        (out / "commands.sh").write_text(
            "# Commands run_plan.py ran for this phase, in order (keys come from the environment:\n"
            "# TTS_API_KEY for the gateway, TTS_ENGINE_API_KEY for the engine). For reference and reproduction.\n"
            + "\n".join(ctx.commands) + "\n", encoding="utf-8")
        tmp = out / "phase.json.tmp"
        tmp.write_text(json.dumps(rec, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        tmp.replace(out / "phase.json")
        if ok:
            (out / "DONE").write_text(iso() + "\n", encoding="utf-8")
        print(f"  {ctx.ph.name}: {rec['status']} in {rec['duration_s']:.0f} s -> {out}", flush=True)

    @staticmethod
    def audio_totals(out: Path) -> dict:
        files, seconds = 0, 0.0
        try:
            runs = json.loads((out / "summary.json").read_text(encoding="utf-8")).get("runs") or []
            seconds = sum(float(r.get("audio_s") or 0) for r in runs)
        except (OSError, json.JSONDecodeError):
            runs = []
        files = sum(1 for _ in out.rglob("*.wav"))
        return {"runs": len(runs), "wav_files": files, "seconds": round(seconds, 1), "hours": round(seconds / 3600, 3)}

    @staticmethod
    def log_findings(log: Path) -> dict:
        """Lines worth a look in the engine log of the phase: KV-cache size / max concurrency, preemption, errors."""
        found = {"kv_cache": [], "preemption": 0, "builtin_retries": 0, "errors": 0, "error_samples": []}
        with contextlib.suppress(OSError):
            for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
                if "Maximum concurrency" in line or "GPU KV cache size" in line:
                    found["kv_cache"].append(re.sub(r"\x1b\[[0-9;]*m", "", line)[-200:])
                if "failed generation validation; retrying once" in line:      # the engine's own runaway retry
                    found["builtin_retries"] += 1
                if re.search(r"preempt", line, re.I):
                    found["preemption"] += 1
                if re.search(r"\bERROR\b|Traceback", line):
                    found["errors"] += 1
                    if len(found["error_samples"]) < 10:
                        found["error_samples"].append(re.sub(r"\x1b\[[0-9;]*m", "", line)[-300:])
        return found

    def json_get(self, url: str, key: str | None = None):
        status, body = http_get(url, 10.0, key)
        try:
            return {"status": status, "body": json.loads(body)}
        except json.JSONDecodeError:
            return {"status": status, "body": body[:2000]}

    def check_disk(self, need_gb: float, what: str) -> None:
        free = disk_free_gb(self.results)
        need = need_gb * DISK_MARGIN + self.args.min_free_gb
        if free < need:
            raise Abort(f"{what}: {free} GB free on the results disk, need ~{need:.1f} GB "
                        f"({need_gb} GB of audio x {DISK_MARGIN} + --min-free-gb {self.args.min_free_gb})")

    def gpu_busy(self) -> list[dict] | None:
        apps = compute_apps(self.gpu)
        return apps if apps else None

    def ensure_engine(self, ctx: PhaseCtx) -> dict:
        ph, spec = ctx.ph, ctx.ph.engine
        if spec.kind in ("none", "fake", "stub") and (missing := [r for r in ph.requires if not (ROOT / r).exists()]):
            raise PhaseError(f"missing {', '.join(missing)}")
        if self.live and (spec.kind == "none" or (spec == self.live.spec and not ph.fresh_engine)):
            live = self.live
            live.child.track()
            ctx.commands.append(f"# engine: reused, started in phase {live.owner}")
            ctx.rec["gpu"].update(baseline_mib=live.baseline_mib, baseline_apps=live.baseline_apps,
                                  engine_ready_mib=live.record.get("ready_mib"), engine_started_in=live.owner)
            return {**live.record, "reused_from": live.owner, "log_offset": live.child.mark(),
                    "voices": self.json_get(self.engine_url + "/v1/audio/voices", self.engine_key)}
        if self.live:                                    # a different engine is up: stop it first
            ctx.rec["gpu"]["previous_engine"] = self.stop_engine(set())
            if ctx.rec["gpu"]["previous_engine"].get("released") is False:
                raise Abort(f"the previous engine did not release GPU {self.gpu}")
        if spec.kind == "none":
            if http_get(self.engine_url + "/health")[0] != 200:
                raise PhaseError(f"engine 'none' but nothing healthy at {self.engine_url}")
            ctx.commands.append(f"# engine: external, already running at {self.engine_url}")
            return {"kind": "none", "reused_from": "external", "url": self.engine_url,
                    "voices": self.json_get(self.engine_url + "/v1/audio/voices", self.engine_key)}
        if missing := self.missing(spec, ph.requires):
            raise PhaseError(f"missing {', '.join(missing)}")
        if port_in_use(self.args.engine_port):
            raise PhaseError(f"port {self.args.engine_port} is already in use; stop that server first "
                             "(run_plan never touches processes it did not start)")
        apps = compute_apps(self.gpu)
        if spec.uses_gpu and apps and not self.args.allow_busy_gpu:
            raise PhaseError(f"GPU {self.gpu} already runs compute processes {apps}; free it first "
                             "(or --allow-busy-gpu to measure next to them)")
        cmd, overrides, cwd, ready = self.engine_launch(spec)
        env = {k: v for k, v in os.environ.items() if k != "TTS_API_KEY"} | overrides    # the gateway's key
        log = self.logs / f"engine_{ctx.ph.name}.log"
        rec: dict = {"kind": spec.kind, "variant": spec.variant, "venv": spec.venv if spec.kind == "vllm" else None,
                     "args": list(spec.args), "describe": spec.describe(), "cmd": cmd, "cwd": str(cwd),
                     "url": self.engine_url, "log": str(log), "env": visible_env(env)}
        ctx.rec["engine"] = rec                          # recorded even if the start fails
        if spec.yaml:
            rec.update(yaml_path=str(spec.yaml), yaml_sha256=sha256(spec.yaml), yaml=spec.yaml.read_text())
            shutil.copy(spec.yaml, ctx.out / "deploy.yaml")
        if spec.kind == "vllm" and APPLY_PATCHES.exists():
            r = subprocess.run([str(PYTHON), str(APPLY_PATCHES), "--check", "--venv", str(spec.venv_path)],
                               capture_output=True, text=True, timeout=60)
            rec["patches"] = {"all_applied": r.returncode == 0, "exit_code": r.returncode,
                              "output": (r.stdout + r.stderr).strip()[-1500:]}
        baseline = gpu_mem_mib(self.gpu)
        rec.update(gpu_baseline_mib=baseline, gpu_baseline_apps=apps)
        ctx.rec["gpu"].update(baseline_mib=baseline, baseline_apps=apps)
        ctx.commands.append(f"cd {cwd} && {env_prefix(overrides)} {shlex.join(cmd)} >> {log} 2>&1 &")
        print(f"  engine {spec.describe()}: {shlex.join(cmd)}  (log {log}; GPU {self.gpu} baseline {baseline} MiB)",
              flush=True)
        try:
            child = Child("engine", cmd, env, cwd, log)
        except OSError as exc:
            raise PhaseError(f"cannot start the engine: {exc}") from exc
        rec["log_offset"] = child.start_offset
        self.live = LiveEngine(spec, child, ctx.ph.name, rec, baseline, apps)
        rec["ready_s"] = self.wait_ready("engine", self.engine_url + ready, child, ctx.ph.ready_timeout_s)
        if spec.kind == "vllm" and WAIT_READY.exists():
            rec["wait_ready"] = self.run_wait_ready(ctx, ctx.ph.ready_timeout_s - rec["ready_s"])
        child.track()
        rec.update(ready_mib=gpu_mem_mib(self.gpu), ready_apps=compute_apps(self.gpu),
                   voices=self.json_get(self.engine_url + "/v1/audio/voices", self.engine_key))
        ctx.rec["gpu"].update(engine_ready_mib=rec["ready_mib"], engine_ready_apps=rec["ready_apps"])
        print(f"  engine ready in {rec['ready_s']:.0f} s; GPU {self.gpu} {rec['ready_mib']} MiB", flush=True)
        return rec

    def run_wait_ready(self, ctx: PhaseCtx, budget_s: float) -> dict:
        """engine/wait_ready.py after /health is green: one short synthesis must return real audio."""
        budget_s = max(budget_s, 120.0)
        cmd = [str(PYTHON), str(WAIT_READY), self.engine_url, "--timeout", f"{budget_s:.0f}", "--voices-dir",
               str(VOICES_DIR)]
        ctx.commands.append(shlex.join(cmd))
        env = {**os.environ, **({"TTS_ENGINE_API_KEY": self.engine_key} if self.engine_key else {})}
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=budget_s + 60, env=env)
        except subprocess.TimeoutExpired as exc:
            raise PhaseError(f"{WAIT_READY.name} timed out after {exc.timeout:.0f} s") from exc
        if r.returncode != 0:
            raise PhaseError(f"{WAIT_READY.name} failed ({r.returncode}): {(r.stdout + r.stderr).strip()[-400:]}")
        return {"cmd": cmd, "output": (r.stdout + r.stderr).strip()[-2000:]}

    def start_child(self, ctx: PhaseCtx, name: str, cmd: list[str], overrides: dict[str, str], cwd: Path,
                    ready_url: str, timeout: float) -> dict:
        port = int(ready_url.split(":")[2].split("/")[0])
        if port_in_use(port):
            raise PhaseError(f"{name}: port {port} is already in use; stop that server first")
        env = {**os.environ, **overrides}
        log = self.logs / f"{name}_{ctx.ph.name}.log"
        ctx.commands.append(f"cd {cwd} && {env_prefix(overrides)} {shlex.join(cmd)} >> {log} 2>&1 &")
        print(f"  {name}: {env_prefix(overrides)} {shlex.join(cmd)}  (log {log})", flush=True)
        try:
            child = Child(name, cmd, env, cwd, log)
        except OSError as exc:
            raise PhaseError(f"cannot start the {name}: {exc}") from exc
        ctx.children.append((name, child, child.start_offset))
        rec = {"enabled": True, "cmd": cmd, "cwd": str(cwd), "url": ready_url.rsplit("/", 1)[0], "log": str(log),
               "env": visible_env(env)}
        ctx.rec[name] = rec                              # recorded even if it never gets ready
        rec["ready_s"] = self.wait_ready(name, ready_url, child, timeout)
        child.track()
        print(f"  {name} ready in {rec['ready_s']:.0f} s", flush=True)
        return rec

    def wait_ready(self, what: str, url: str, child: Child, timeout: float) -> float:
        t0 = time.monotonic()
        while True:
            if not child.alive():
                raise PhaseError(f"{what} exited ({child.proc.returncode}) before it was ready; see {child.log}")
            if http_get(url)[0] == 200:
                return round(time.monotonic() - t0, 1)
            if time.monotonic() - t0 > timeout:
                raise PhaseError(f"{what} not ready after {timeout:.0f} s ({url}); see {child.log}")
            time.sleep(1)

    def run_check(self, ctx: PhaseCtx, chk: dict) -> None:
        cmd, env = self.check_launch(chk, ctx.out)
        log = ctx.out / "logs" / "knobs.log"
        log.parent.mkdir(exist_ok=True)
        ctx.commands.append(shlex.join(cmd))
        print(f"  check {chk['name']} via {chk.get('via', 'engine')}", flush=True)
        code = tee(cmd, env, log, 900.0)
        report = {}
        with contextlib.suppress(OSError, json.JSONDecodeError):
            report = json.loads((ctx.out / "knobs" / chk["name"] / "knobs.json").read_text(encoding="utf-8"))
        ctx.rec["knob_checks"].append({"name": chk["name"], "via": chk.get("via", "engine"), "exit_code": code,
                                       "ok": report.get("ok"), "problems": report.get("problems"),
                                       "deterministic_base": report.get("deterministic_base"),
                                       "verdicts": {t["label"]: t.get("verdict") for t in report.get("takes", [])},
                                       "enforced": not self.args.stub})
        if code != 0:
            raise PhaseError(f"knob check {chk['name']} failed ({code}): {report.get('problems')}")
        self.check_alive(ctx, f"knob check {chk['name']}")

    def run_bench(self, ctx: PhaseCtx, i: int, b: Bench) -> None:
        ph, out = ctx.ph, ctx.out
        cmd, env = self.bench_launch(ph, b, out)
        est = estimate_bench(b, ph.engine)
        self.check_disk(round(est["audio_s"] * WAV_BYTES_PER_S / 1e9, 2), f"bench command {i}")
        log = out / f"bench_{i:02d}_{b.via}.log"
        timeout = self.bench_timeout(ph, b)
        self.snapshot(ctx, f"bench{i:02d}_before")
        ctx.commands.append(shlex.join(cmd))
        print(f"  [{i}/{len(ph.bench)}] via {b.via} (~{est['audio_s'] / 3600:.2f} h audio, timeout {timeout:.0f} s): "
              f"{shlex.join(cmd[2:])}", flush=True)
        before = self.run_names(out)
        t0 = time.monotonic()
        code = tee(cmd, env, log, timeout)
        self.snapshot(ctx, f"bench{i:02d}_after")
        ctx.rec["bench"].append({"i": i, "via": b.via, "tag": b.tag, "cmd": cmd, "log": str(log.relative_to(out)),
                                 "exit_code": code, "timeout_s": timeout, "duration_s": round(time.monotonic() - t0, 1),
                                 "estimate_audio_s": round(est["audio_s"], 1),
                                 "runs": [r for r in self.run_names(out) if r not in before]})
        if code != 0:
            raise PhaseError(f"bench command {i} exited with {code}; see {log}")
        self.check_alive(ctx, f"bench command {i}")

    @staticmethod
    def run_names(out: Path) -> list[str]:
        with contextlib.suppress(OSError, json.JSONDecodeError):
            return [r["run"] for r in json.loads((out / "summary.json").read_text(encoding="utf-8"))["runs"]]
        return []

    def check_alive(self, ctx: PhaseCtx, after: str) -> None:
        if self.live and not self.live.child.alive():
            raise PhaseError(f"engine exited during {after}; see {self.live.child.log}")
        for name, child, _ in ctx.children:
            if not child.alive():
                raise PhaseError(f"{name} exited during {after}; see {child.log}")

    def snapshot(self, ctx: PhaseCtx, label: str) -> None:
        snap = ctx.out / "snapshots"
        if self.live:
            self.live.child.track()
        for _, child, _ in ctx.children:
            child.track()
        (snap / f"{label}_nvidia-smi.txt").write_text(
            f"# {iso()}\n" + nvidia_smi("-i", self.gpu) + "\n"
            + nvidia_smi(f"--id={self.gpu}", "--query-gpu=timestamp,memory.used,memory.total,utilization.gpu,"
                         "temperature.gpu,power.draw,clocks.sm,clocks.mem,pstate", "--format=csv") + "\n"
            + nvidia_smi(f"--id={self.gpu}", "--query-compute-apps=pid,process_name,used_memory", "--format=csv"),
            encoding="utf-8")
        urls = {"gateway": self.gateway_url, "qc": self.qc_url}
        targets = [("engine", self.engine_url)] + [(n, urls[n]) for n, _, _ in ctx.children if n in urls]
        for name, base in targets:
            status, body = http_get(base + "/metrics")
            (snap / f"{label}_{name}_metrics.txt").write_text(
                body if status == 200 else f"# GET {base}/metrics failed: {status} {body[:300]}\n", encoding="utf-8")

    def release_check(self, ours: set[int], baseline_apps: list[dict] | None, baseline_mib: int | None) -> dict:
        """Poll until no compute process on the GPU is one we started or one that was not there at the baseline."""
        known = {a["pid"] for a in baseline_apps or []}
        deadline = time.monotonic() + GPU_RELEASE_S
        while True:
            apps = compute_apps(self.gpu)
            used = gpu_mem_mib(self.gpu)
            if apps is None:
                return {"released": None, "after_stop_mib": used, "note": "nvidia-smi unavailable"}
            remaining = [a | {"ours": a["pid"] in ours} for a in apps if a["pid"] in ours or a["pid"] not in known]
            if not remaining:
                res = {"released": True, "after_stop_mib": used, "after_stop_apps": apps}
                if baseline_mib is not None and used is not None and used > baseline_mib + GPU_MEM_WARN_MIB:
                    res["warning"] = (f"{used} MiB used vs {baseline_mib} MiB baseline with no compute process of "
                                      "ours left (graphics / another tenant?)")
                return res
            if time.monotonic() > deadline:
                return {"released": False, "after_stop_mib": used, "remaining_apps": remaining}
            time.sleep(2)

    def wait_pids_gone(self, ours: set[int]) -> dict:
        """Wait until no compute process on the GPU is one of ours (QC sidecar next to a kept or external engine)."""
        deadline = time.monotonic() + GPU_RELEASE_S
        while True:
            apps = compute_apps(self.gpu)
            if apps is None:
                return {"released": None, "note": "nvidia-smi unavailable"}
            remaining = [a for a in apps if a["pid"] in ours]
            if not remaining:
                return {"released": True, "sidecars_gone": True}
            if time.monotonic() > deadline:
                return {"released": False, "remaining_apps": remaining}
            time.sleep(2)

    def stop_engine(self, extra_pids: set[int]) -> dict:
        live, self.live = self.live, None
        assert live is not None
        how = live.child.stop()
        ours = {pid for pid, _ in live.child.tracked} | extra_pids
        res = self.release_check(ours, live.baseline_apps, live.baseline_mib) if live.spec.uses_gpu else \
            {"released": True, "note": f"{live.spec.kind} engine uses no GPU"}
        print(f"  engine stopped ({how}); GPU {self.gpu} released={res.get('released')} "
              f"{res.get('after_stop_mib')} MiB (baseline {live.baseline_mib} MiB)", flush=True)
        return {"engine_stopped_with": how, "baseline_mib": live.baseline_mib, "engine_started_in": live.owner, **res}

    def versions(self, ctx: PhaseCtx) -> dict:
        eng = self.effective_engine(ctx.ph)
        venvs = {"gateway": PYTHON}
        if eng.kind == "vllm":
            venvs[eng.venv] = ROOT / "venvs" / eng.venv / "bin" / "python"
        elif eng.kind == "qwentts":
            venvs["qwentts"] = ROOT / "venvs" / "qwentts" / "bin" / "python"
        if ctx.ph.qc and not self.args.stub:
            venvs["eval"] = ROOT / "venvs" / "eval" / "bin" / "python"
        folder = ctx.out / "versions"
        folder.mkdir(exist_ok=True)
        out = {"runner_python": sys.version.split()[0]}
        for key, python in venvs.items():
            if key not in self._versions:
                self._versions[key] = pkg_versions(python, PKGS.get(key, ()))
            v = self._versions[key]
            (folder / f"{key}.txt").write_text("\n".join(v.get("all") or [f"# {v.get('error')}"]) + "\n",
                                               encoding="utf-8")
            out[key] = {k: v[k] for k in ("python", "packages", "error") if k in v}
        out["nvidia_driver"] = nvidia_smi(f"--id={self.gpu}", "--query-gpu=driver_version", "--format=csv,noheader").strip()
        return out

    def shutdown(self) -> None:
        if self.live:
            self.stop_engine(set())


# ------------------------------------------------------------------------------------------------ main

def phase_status(results: Path, name: str) -> str:
    d = results / name
    if (d / "DONE").exists():
        return "DONE"
    if (d / "phase.json").exists():
        with contextlib.suppress(OSError, json.JSONDecodeError, KeyError):
            return json.loads((d / "phase.json").read_text())["status"]
    return "partial" if d.exists() else "pending"


def _on_sigterm(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def list_phases(runner: Runner, phases: list[Phase], results: Path) -> None:
    rows, totals = [], {"default": [0.0, 0.0, 0.0], "optional": [0.0, 0.0, 0.0]}
    for p in phases:
        est = estimate_phase(p)
        bucket = totals["optional" if p.optional else "default"]
        bucket[0] += est["audio_h"]
        bucket[1] += est["gpu_min"]
        bucket[2] += est["audio_gb"]
        gw = "off" if p.gateway is None else ("on+qc" if p.qc else "on")
        missing = runner.missing(p.engine, p.requires)
        rows.append(f"{p.name:27} {phase_status(results, p.name):9} {'opt' if p.optional else '   '} {p.kind:7} "
                    f"{est['audio_h']:6.2f} h {est['gpu_min']:7.1f} min {est['requests']:6d} req  gw={gw:5} "
                    f"engine={p.engine.describe()}{'  MISSING ' + ', '.join(Path(m).name for m in missing) if missing else ''}")
    print(f"{'phase':27} {'status':9} {'':3} {'kind':7} {'audio':>8} {'GPU time':>11} {'requests':>10}")
    print("\n".join(rows))
    for key, (h, m, gb) in totals.items():
        print(f"total {key:8}: ~{h:.1f} h audio (~{gb:.1f} GB WAV), ~{m / 60:.1f} h GPU"
              + ("  (run with --optional or --only NAME)" if key == "optional" else ""))
    attic = results / "_attic"
    if attic.exists():
        print(f"_attic: {dir_bytes(attic) / 1e9:.2f} GB of earlier partial phases (delete when no longer needed)")
    print(f"disk free on {results}: {disk_free_gb(results)} GB. GPU minutes are rough: measured engine-direct "
          "throughput (X_OMNI in run_plan.py, E01), plus engine starts; update after P2.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", type=Path, default=Path(__file__).with_name("plan.py"))
    ap.add_argument("--only", metavar="NAME[,NAME]", help="phases to run; globs allowed, e.g. 'P1_screen_*'")
    ap.add_argument("--optional", action="store_true", help="include optional phases (see --list)")
    ap.add_argument("--list", action="store_true", help="list phases, status, estimated audio hours and GPU minutes")
    ap.add_argument("--dry-run", action="store_true", help="print every command; start nothing, write nothing")
    ap.add_argument("--force", action="store_true", help="rerun phases that are DONE")
    ap.add_argument("--stop-on-error", action="store_true", help="stop at the first failed phase")
    ap.add_argument("--gpu", default=os.environ.get("TTS_BENCH_GPU", "0"),
                    help="the GPU to use and inspect (engine CUDA_VISIBLE_DEVICES, bench --gpus); default "
                         "$TTS_BENCH_GPU or 0")
    ap.add_argument("--allow-busy-gpu", action="store_true",
                    help="start a GPU engine even when other compute processes use the GPU (numbers are then shared)")
    ap.add_argument("--engine-port", type=int, default=8091)
    ap.add_argument("--gateway-port", type=int, default=8090)
    ap.add_argument("--qc-port", type=int, default=8092)
    ap.add_argument("--min-free-gb", type=float, default=3.0,
                    help="free disk to keep on the results filesystem beyond the phase's estimated audio (default 3)")
    ap.add_argument("--results", type=Path, default=ROOT / "results")
    ap.add_argument("--logs", type=Path, default=ROOT / "logs")
    ap.add_argument("--stub", action="store_true",
                    help="CPU self-test: vllm and qwentts engines become the fake vLLM-Omni "
                         "(gateway/tests/fake_vllm_omni.py --patched), the QC sidecar a built-in fake, knob checks "
                         "are not enforced. Use it with --results/--logs outside server/results")
    ap.add_argument("--fake-qc", type=int, default=None, metavar="PORT", help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.fake_qc:
        serve_fake_qc(args.fake_qc)
        return 0
    args.plan, args.results, args.logs = args.plan.resolve(), args.results.resolve(), args.logs.resolve()
    try:
        all_phases, plan_mod = load_plan(args.plan)
        phases = select(all_phases, args.only, args.optional or args.list)
        if args.stub:
            phases = [replace(p, engine=Engine("fake")) if p.engine.uses_gpu else p for p in phases]
        runner = Runner(args, plan_mod)
        if args.list or args.dry_run:
            for p in phases:
                estimate_phase(p)                        # validates every bench command's arguments
    except PlanError as exc:
        print(f"plan error: {exc}", file=sys.stderr)
        return 2

    if args.list:
        list_phases(runner, phases, args.results)
        return 0
    todo = [p for p in phases if args.force or phase_status(args.results, p.name) != "DONE"]
    if args.dry_run:
        for p in phases:
            runner.show(p, "run" if p in todo else "DONE, skipped (--force reruns)")
        return 0
    for p in phases:
        if p not in todo:
            print(f"skip {p.name}: DONE (--force reruns)")

    args.results.mkdir(parents=True, exist_ok=True)
    lock = open(args.results / ".run_plan.lock", "a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"another run_plan.py is using {args.results}", file=sys.stderr)
        return 2
    lock.seek(0)
    lock.truncate()
    lock.write(f"{os.getpid()} {iso()} {shlex.join(sys.argv)}\n")
    lock.flush()
    signal.signal(signal.SIGTERM, _on_sigterm)
    done: list[str] = []
    failed: list[str] = []
    try:
        for i, ph in enumerate(todo):
            nxt = todo[i + 1] if i + 1 < len(todo) else None
            keep = bool(nxt) and (nxt.engine.kind == "none" or (nxt.engine == ph.engine and not nxt.fresh_engine))
            (done if runner.run_phase(ph, keep_engine=keep) else failed).append(ph.name)
            if failed and args.stop_on_error:
                break
    except Abort as exc:
        print(f"\nABORT: {exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    finally:
        runner.shutdown()
    print(f"\n{len(done)}/{len(todo)} phases done" + (f"; failed: {', '.join(failed)}" if failed else "")
          + f"\nnext: {PYTHON} {Path(__file__).with_name('collect.py')} --results {args.results}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
