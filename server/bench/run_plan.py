#!/usr/bin/env python3
"""Run the benchmark plan (bench/plan.py) phase by phase: start the engine (and the gateway), run bench_tts.py,
snapshot nvidia-smi and /metrics around every bench command, stop everything and check that GPU 1 is back to its
baseline before the next phase.

    venvs/gateway/bin/python bench/run_plan.py --list
    venvs/gateway/bin/python bench/run_plan.py --dry-run --only 'P1_screen_*'
    venvs/gateway/bin/python bench/run_plan.py --only P0_smoke,P1_screen_default --stop-on-error

Resumable: a phase with results/<phase>/DONE is skipped unless --force. The directory of an unfinished (or forced)
phase is moved to results/_attic/ before the phase runs again, so runs never mix.
Keys: bench gets $TTS_API_KEY for the gateway (a throwaway key is generated when unset) and $TTS_ENGINE_API_KEY for
the engine, through its environment; keys never appear in argv, logs or phase.json.
Only GPU 1 is used or checked, and only processes this runner started are ever signalled.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import fnmatch
import hashlib
import importlib.util
import json
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
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = Path("/home/vector/tts-reference-voices/bench/bench_tts.py")
PYTHON = ROOT / "venvs" / "gateway" / "bin" / "python"          # runs the gateway and bench_tts.py
RUN_ENGINE = ROOT / "engine" / "run_engine.sh"
WAIT_READY = ROOT / "engine" / "wait_ready.py"
DEPLOY = ROOT / "engine" / "deploy"
GPU = "1"                                  # the only GPU this runner uses or inspects
VENVS = ("engine", "engine30")
ENGINE_PKGS = ("vllm", "vllm-omni", "torch", "torchaudio", "transformers", "flashinfer-python", "triton")
GATEWAY_PKGS = ("fastapi", "uvicorn", "starlette", "httpx", "pydantic", "numpy", "soundfile")
RUNNER_FLAGS = ("--url", "--out", "--gpus", "--tag", "--api-key")      # owned by the runner, not the plan
IGNORED_BY_ENGINE = ("temperature", "top_k", "top_p", "repetition_penalty")  # top-level: silently dropped
ENV_PREFIXES = ("TTS_", "VLLM_", "CUDA_", "HF_", "NCCL_", "PYTORCH_", "TORCH_", "FLASHINFER_", "OMP_", "SPEAKER_")
SECRET_WORDS = ("KEY", "TOKEN", "SECRET", "PASS")
GATEWAY_READY_S = 300.0
GPU_TOLERANCE_MIB = 256
GPU_RELEASE_S = 120.0
STOP_GRACE_S = ((signal.SIGINT, 30.0), (signal.SIGTERM, 15.0), (signal.SIGKILL, 10.0))


class PlanError(Exception):
    """The plan file is invalid."""


class PhaseError(Exception):
    """A phase failed; the run may continue with the next phase."""


class Abort(Exception):
    """Continuing would produce invalid measurements (GPU 1 not released)."""


def iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


# ------------------------------------------------------------------------------------------------ plan

@dataclass(frozen=True)
class Engine:
    kind: str                  # "vllm", "none" (reuse the engine already on the engine port) or "stub" (CPU tests)
    variant: str = ""
    venv: str = "engine"

    @property
    def yaml(self) -> Path | None:
        if self.kind != "vllm":
            return None
        if self.variant == "prod":
            return DEPLOY / "qwen3_tts_prod.yaml"
        return DEPLOY / "variants" / f"{self.variant}.yaml"

    @property
    def venv_path(self) -> Path:
        return ROOT / "venvs" / self.venv

    def describe(self) -> str:
        return {"vllm": f"{self.variant} ({self.venv})", "none": "reuse the running engine",
                "stub": "stub (gateway with TTS_BACKEND=stub)"}[self.kind]


@dataclass(frozen=True)
class Bench:
    args: tuple[str, ...]
    via: str                   # "engine" or "gateway"
    tag: str                   # <phase>[_<suffix>], prefixed to bench run names


@dataclass(frozen=True)
class Phase:
    name: str
    engine: Engine
    gateway: dict[str, str] | None     # TTS_* env overrides when the gateway is on
    bench: tuple[Bench, ...]
    note: str = ""
    ready_timeout_s: float = 1200.0


def _param_keys(args: tuple[str, ...]) -> list[str]:
    vals = [args[i + 1] for i, a in enumerate(args[:-1]) if a == "--param"]
    vals += [a.removeprefix("--param=") for a in args if a.startswith("--param=")]
    return [v.partition("=")[0] for v in vals]


def parse_phase(raw: dict) -> Phase:
    name = str(raw.get("name", ""))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
        raise PlanError(f"bad phase name {name!r}")
    if unknown := set(raw) - {"name", "engine", "gateway", "bench", "note", "ready_timeout_s"}:
        raise PlanError(f"{name}: unknown keys {sorted(unknown)}")
    eng = raw.get("engine", "none")
    if eng == "none":
        engine = Engine("none")
    elif isinstance(eng, dict) and not set(eng) - {"kind", "variant", "venv"}:
        engine = Engine(eng.get("kind", "vllm"), eng.get("variant", ""), eng.get("venv", "engine"))
        if engine.kind not in ("vllm", "stub") or (engine.kind == "vllm" and not engine.variant) \
                or engine.venv not in VENVS:
            raise PlanError(f"{name}: bad engine {eng!r} (variant required, venv one of {VENVS})")
    else:
        raise PlanError(f"{name}: engine must be 'none' or {{'variant': ..., 'venv': ...}}, got {eng!r}")
    gw = raw.get("gateway", False)
    gateway = None if gw in (False, None) else {} if gw is True else {str(k): str(v) for k, v in dict(gw).items()}
    bench = []
    for item in raw.get("bench", []):
        spec = item if isinstance(item, dict) else {"args": item}
        if set(spec) - {"args", "via", "tag"}:
            raise PlanError(f"{name}: unknown bench keys in {spec!r}")
        args = tuple(str(a) for a in spec["args"])
        via = spec.get("via") or ("gateway" if gateway is not None else "engine")
        if via not in ("engine", "gateway"):
            raise PlanError(f"{name}: bad via {via!r}")
        if via == "gateway" and gateway is None:
            raise PlanError(f"{name}: a bench command via the gateway needs the gateway on")
        if owned := [a for a in args if a.split("=")[0] in RUNNER_FLAGS]:
            raise PlanError(f"{name}: {owned} are set by run_plan.py")
        if via == "engine" and (dropped := set(_param_keys(args)) & set(IGNORED_BY_ENGINE)):
            raise PlanError(f"{name}: vLLM-Omni ignores top-level {sorted(dropped)}; use extra_params or a variant")
        bench.append(Bench(args, via, f"{name}_{spec['tag']}" if spec.get("tag") else name))
    return Phase(name, engine, gateway, tuple(bench), str(raw.get("note", "")),
                 float(raw.get("ready_timeout_s", 1200.0)))


def load_plan(path: Path) -> list[Phase]:
    spec = importlib.util.spec_from_file_location("bench_plan", path)
    if spec is None or spec.loader is None:
        raise PlanError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    phases = [parse_phase(p) for p in mod.PHASES]
    if dups := {p.name for p in phases if [q.name for q in phases].count(p.name) > 1}:
        raise PlanError(f"duplicate phase names {sorted(dups)}")
    return phases


def select(phases: list[Phase], only: str | None) -> list[Phase]:
    if not only:
        return phases
    pats = [p.strip() for p in only.split(",") if p.strip()]
    if missing := [p for p in pats if not any(fnmatch.fnmatchcase(ph.name, p) for ph in phases)]:
        raise PlanError(f"--only {missing} match no phase; see --list")
    return [ph for ph in phases if any(fnmatch.fnmatchcase(ph.name, p) for p in pats)]


# ------------------------------------------------------------------------------------------------ host helpers

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))    # localhost never goes through a proxy


def http_get(url: str, timeout: float = 5.0) -> tuple[int | None, str]:
    try:
        with _OPENER.open(url, timeout=timeout) as r:
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


def gpu_mem_mib() -> int | None:
    out = nvidia_smi(f"--id={GPU}", "--query-gpu=memory.used", "--format=csv,noheader,nounits").strip()
    return int(out) if out.isdigit() else None


def wait_gpu_released(baseline: int | None) -> tuple[bool | None, int | None]:
    """Poll GPU memory until it is within GPU_TOLERANCE_MIB of the pre-engine baseline."""
    deadline = time.monotonic() + GPU_RELEASE_S
    while True:
        used = gpu_mem_mib()
        if baseline is None or used is None:
            return None, used
        if used <= baseline + GPU_TOLERANCE_MIB:
            return True, used
        if time.monotonic() > deadline:
            return False, used
        time.sleep(2)


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


def visible_env(env: dict[str, str]) -> dict[str, str]:
    """The environment variables that matter for a run, with secrets redacted."""
    return {k: "<redacted>" if any(w in k for w in SECRET_WORDS) else v
            for k, v in sorted(env.items()) if k.startswith(ENV_PREFIXES)}


def env_prefix(env: dict[str, str]) -> str:
    return " ".join(f"{k}={shlex.quote(v)}" for k, v in visible_env(env).items())


def pkg_versions(python: Path, pkgs: tuple[str, ...]) -> dict:
    """Package versions of a venv, read from metadata (nothing is imported, so no CUDA initialisation)."""
    code = ("import importlib.metadata as m, json, sys\n"
            "def v(p):\n"
            "    try:\n        return m.version(p)\n"
            "    except m.PackageNotFoundError:\n        return None\n"
            "print(json.dumps({'python': sys.version.split()[0], **{p: v(p) for p in sys.argv[1:]}}))")
    if not python.exists():
        return {"error": f"{python} missing"}
    try:
        r = subprocess.run([str(python), "-c", code, *pkgs], capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"error": str(exc)}


def host_info() -> dict:
    def read(p: str) -> str | None:
        with contextlib.suppress(OSError):
            return Path(p).read_text().strip()
        return None
    cpu = next((line.split(":", 1)[1].strip() for line in (read("/proc/cpuinfo") or "").splitlines()
                if line.startswith("model name")), None)
    return {"hostname": platform.node(), "kernel": platform.release(), "cpu": cpu, "cpus": os.cpu_count(),
            "cpu_governor": read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
            "gpu": nvidia_smi(f"--id={GPU}", "--query-gpu=index,name,driver_version,vbios_version,power.limit,"
                              "clocks.max.sm,clocks.max.mem", "--format=csv,noheader").strip()}


# ------------------------------------------------------------------------------------------------ processes

class Child:
    """A long-running subprocess in its own session (process group), output appended to a log file."""

    def __init__(self, cmd: list[str], env: dict[str, str], cwd: Path, log: Path) -> None:
        self.cmd, self.log = cmd, log
        log.parent.mkdir(parents=True, exist_ok=True)
        self._log = open(log, "ab")
        self._log.write(f"\n=== {iso()} run_plan: {env_prefix(env)} {shlex.join(cmd)}\n".encode())
        self._log.flush()
        self.proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=self._log,
                                     stderr=subprocess.STDOUT, start_new_session=True)

    def alive(self) -> bool:
        return self.proc.poll() is None

    def _group_gone(self) -> bool:
        self.proc.poll()                                 # reap the leader so it no longer counts
        try:
            os.killpg(self.proc.pid, 0)
        except ProcessLookupError:
            return True
        return False

    def stop(self) -> str:
        """SIGINT, then SIGTERM, then SIGKILL to the process group; descendants that left the group are killed at the
        end. Returns how it ended."""
        tracked = descendants(self.proc.pid)
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
        for pid, start in tracked:                       # same pid and start time: still our process
            if (st := _proc_stat(pid)) and st[1] == start:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGKILL)
        self.proc.poll()
        self._log.close()
        return how


def tee(cmd: list[str], env: dict[str, str], log: Path) -> int:
    """Run cmd to completion; its output goes to log and, indented, to our stdout."""
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"=== {iso()} {shlex.join(cmd)}\n")
        proc = subprocess.Popen(cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, errors="replace")
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                f.write(line)
                f.flush()
                print("    " + line, end="", flush=True)
            return proc.wait()
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()


# ------------------------------------------------------------------------------------------------ runner

@dataclass
class LiveEngine:
    """An engine this runner started; kept across phases while the next phase says engine 'none'."""
    spec: Engine
    child: Child
    owner: str
    record: dict
    baseline_mib: int | None


class Runner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.results: Path = args.results
        self.logs: Path = args.logs
        self.engine_url = f"http://127.0.0.1:{args.engine_port}"
        self.gateway_url = f"http://127.0.0.1:{args.gateway_port}"
        self.gateway_key = os.environ.get("TTS_API_KEY") or secrets.token_urlsafe(24)
        self.engine_key = os.environ.get("TTS_ENGINE_API_KEY")
        self.live: LiveEngine | None = None
        self._versions: dict[str, dict] = {}

    # --- commands (shared by --dry-run and the real run)

    def engine_launch(self, spec: Engine) -> tuple[list[str], dict[str, str], Path, str]:
        """argv, env overrides, cwd and readiness path of an engine."""
        port = str(self.args.engine_port)
        if spec.kind == "stub":
            return ([str(PYTHON), "-m", "tts_gateway"],
                    {"TTS_BACKEND": "stub", "TTS_HOST": "127.0.0.1", "TTS_PORT": port, "TTS_AUTH_DISABLED": "1",
                     "TTS_ALLOW_INLINE_REF": "1"}, ROOT / "gateway", "/ready")
        return (["bash", str(RUN_ENGINE), str(spec.yaml), port, str(spec.venv_path)], {"CUDA_VISIBLE_DEVICES": GPU},
                ROOT, "/health")

    def gateway_launch(self, ph: Phase) -> tuple[list[str], dict[str, str]]:
        stub = ph.engine.kind == "stub" or (ph.engine.kind == "none" and self.live and self.live.spec.kind == "stub")
        env = {"TTS_HOST": "127.0.0.1", "TTS_PORT": str(self.args.gateway_port), "TTS_ENGINE_URL": self.engine_url,
               "TTS_API_KEY": self.gateway_key, **({"TTS_BACKEND": "stub"} if stub else {}), **(ph.gateway or {})}
        return [str(PYTHON), "-m", "tts_gateway"], env

    def bench_launch(self, b: Bench, out: Path) -> tuple[list[str], dict[str, str]]:
        url = self.gateway_url if b.via == "gateway" else self.engine_url
        cmd = [str(PYTHON), str(BENCH), *b.args, "--url", url, "--out", str(out), "--gpus", GPU, "--tag", b.tag]
        key = self.gateway_key if b.via == "gateway" else self.engine_key
        env = {k: v for k, v in os.environ.items() if k != "TTS_API_KEY"} | {"PYTHONUNBUFFERED": "1"}
        return cmd, env | ({"TTS_API_KEY": key} if key else {})

    # --- dry run

    def show(self, ph: Phase, status: str) -> None:
        out = self.results / ph.name
        print(f"\n== {ph.name}  [{status}]" + (f"  {ph.note}" if ph.note else ""))
        if ph.engine.kind == "none":
            print(f"  engine: reuse the engine running at {self.engine_url}")
        else:
            cmd, env, cwd, ready = self.engine_launch(ph.engine)
            yaml = ph.engine.yaml
            needed = (yaml, RUN_ENGINE, ph.engine.venv_path / "bin" / "vllm") if yaml else ()
            missing = [str(p) for p in needed if not p.exists()]
            print(f"  engine: {ph.engine.describe()}" + (f"  yaml {yaml}" if yaml else "")
                  + (f"  MISSING: {', '.join(missing)}" if missing else ""))
            print(f"    $ cd {cwd} && {env_prefix(env)} {shlex.join(cmd)} >> {self.logs / f'engine_{ph.name}.log'}")
            print(f"    ready: GET {self.engine_url}{ready} within {ph.ready_timeout_s:.0f} s")
        if ph.gateway is None:
            print("  gateway: off")
        else:
            cmd, env = self.gateway_launch(ph)
            print(f"  gateway: $ cd {ROOT / 'gateway'} && {env_prefix(env)} {shlex.join(cmd)}"
                  f" >> {self.logs / f'gateway_{ph.name}.log'}")
            print(f"    ready: GET {self.gateway_url}/ready within {GATEWAY_READY_S:.0f} s")
        for i, b in enumerate(ph.bench, 1):
            cmd, _ = self.bench_launch(b, out)
            print(f"  [{i}] via {b.via}: {shlex.join(cmd)} > {out / f'bench_{i:02d}_{b.via}.log'}")
        print("  then: stop gateway + engine (SIGINT, SIGTERM, SIGKILL), GPU 1 back to baseline, phase.json, DONE")

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
        rec: dict = {"phase": ph.name, "note": ph.note, "status": "running", "started": iso(),
                     "argv": sys.argv, "plan": str(self.args.plan), "host": host_info(),
                     "sources": {"bench_tts.py": sha256(BENCH), "plan": sha256(self.args.plan),
                                 "run_plan.py": sha256(Path(__file__)),
                                 "gateway": tree_sha256(ROOT / "gateway" / "tts_gateway"),
                                 "engine_patches": tree_sha256(ROOT / "engine" / "patches")},
                     "gpu": {"index": GPU}, "bench": []}
        gateway: Child | None = None
        ok = False
        try:
            rec["engine"] = self.ensure_engine(ph, out)
            rec["versions"] = self.versions(rec["engine"].get("venv"))
            if ph.gateway is not None:
                gateway, rec["gateway"] = self.start_gateway(ph)
            else:
                rec["gateway"] = {"enabled": False}
            for i, b in enumerate(ph.bench, 1):
                self.run_bench(ph, i, b, out, gateway, rec["bench"])
            ok = True
        except PhaseError as exc:
            rec["error"] = str(exc)
            print(f"  FAILED: {exc}", flush=True)
        except KeyboardInterrupt:
            rec["error"] = "interrupted"
            raise
        finally:
            if gateway:
                rec["gateway"]["stopped_with"] = gateway.stop()
                print(f"  gateway stopped ({rec['gateway']['stopped_with']})")
            if self.live and not (ok and keep_engine):
                rec["gpu"].update(self.stop_engine())
            rec.update(status="done" if ok else "interrupted" if rec.get("error") == "interrupted" else "failed",
                       finished=iso(), duration_s=round(time.monotonic() - t0, 1))
            (out / "phase.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            if ok:
                (out / "DONE").write_text(iso() + "\n", encoding="utf-8")
            print(f"  {ph.name}: {rec['status']} in {rec['duration_s']:.0f} s -> {out}", flush=True)
        if rec["gpu"].get("released") is False:
            raise Abort(f"GPU {GPU} still uses {rec['gpu']['after_stop_mib']} MiB after stopping the engine "
                        f"(baseline {rec['gpu']['baseline_mib']} MiB); later phases would be measured on a busy GPU")
        return ok

    def ensure_engine(self, ph: Phase, out: Path) -> dict:
        spec = ph.engine
        if spec.kind == "none":
            if self.live:
                return {"reused_from": self.live.owner, **self.live.record}
            if http_get(self.engine_url + "/health")[0] != 200:
                raise PhaseError(f"engine 'none' but nothing healthy at {self.engine_url}")
            return {"reused_from": "external", "url": self.engine_url}
        if spec.kind == "vllm" and (missing := [str(p) for p in (spec.yaml, RUN_ENGINE, spec.venv_path / "bin" / "vllm")
                                                 if p and not p.exists()]):
            raise PhaseError(f"missing {', '.join(missing)}")
        if port_in_use(self.args.engine_port):
            raise PhaseError(f"port {self.args.engine_port} is already in use; stop that server first "
                             "(run_plan never touches processes it did not start)")
        cmd, overrides, cwd, ready = self.engine_launch(spec)
        env = {**os.environ, **overrides}
        log = self.logs / f"engine_{ph.name}.log"
        rec: dict = {"kind": spec.kind, "variant": spec.variant, "venv": spec.venv if spec.kind == "vllm" else None,
                     "cmd": cmd, "cwd": str(cwd), "url": self.engine_url, "log": str(log), "env": visible_env(env)}
        if spec.yaml:
            rec.update(yaml_path=str(spec.yaml), yaml_sha256=sha256(spec.yaml), yaml=spec.yaml.read_text())
            shutil.copy(spec.yaml, out / "deploy.yaml")
        baseline = gpu_mem_mib()
        rec["gpu_baseline_mib"] = baseline
        print(f"  engine {spec.describe()}: {shlex.join(cmd)}  (log {log}; GPU {GPU} baseline {baseline} MiB)",
              flush=True)
        try:
            child = Child(cmd, env, cwd, log)
        except OSError as exc:
            raise PhaseError(f"cannot start the engine: {exc}") from exc
        self.live = LiveEngine(spec, child, ph.name, rec, baseline)
        rec["ready_s"] = self.wait_ready("engine", self.engine_url + ready, self.live.child, ph.ready_timeout_s)
        if spec.kind == "vllm" and WAIT_READY.exists():
            rec["wait_ready"] = self.run_wait_ready(ph.ready_timeout_s - rec["ready_s"])
        print(f"  engine ready in {rec['ready_s']:.0f} s", flush=True)
        return rec

    def run_wait_ready(self, budget_s: float) -> dict:
        """engine/wait_ready.py after /health is green: one short synthesis must return real audio."""
        budget_s = max(budget_s, 120.0)
        cmd = [str(PYTHON), str(WAIT_READY), self.engine_url, "--timeout", f"{budget_s:.0f}"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=budget_s + 60)
        except subprocess.TimeoutExpired as exc:
            raise PhaseError(f"{WAIT_READY.name} timed out after {exc.timeout:.0f} s") from exc
        if r.returncode != 0:
            raise PhaseError(f"{WAIT_READY.name} failed ({r.returncode}): {(r.stdout + r.stderr).strip()[-400:]}")
        return {"cmd": cmd, "output": (r.stdout + r.stderr).strip()[-2000:]}

    def start_gateway(self, ph: Phase) -> tuple[Child, dict]:
        if port_in_use(self.args.gateway_port):
            raise PhaseError(f"port {self.args.gateway_port} is already in use; stop that server first")
        cmd, overrides = self.gateway_launch(ph)
        env = {**os.environ, **overrides}
        log = self.logs / f"gateway_{ph.name}.log"
        print(f"  gateway: {env_prefix(overrides)} {shlex.join(cmd)}  (log {log})", flush=True)
        try:
            child = Child(cmd, env, ROOT / "gateway", log)
        except OSError as exc:
            raise PhaseError(f"cannot start the gateway: {exc}") from exc
        rec = {"enabled": True, "cmd": cmd, "url": self.gateway_url, "log": str(log), "overrides": ph.gateway,
               "env": visible_env(env)}
        try:
            rec["ready_s"] = self.wait_ready("gateway", self.gateway_url + "/ready", child, GATEWAY_READY_S)
        except PhaseError:
            child.stop()
            raise
        print(f"  gateway ready in {rec['ready_s']:.0f} s", flush=True)
        return child, rec

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

    def run_bench(self, ph: Phase, i: int, b: Bench, out: Path, gateway: Child | None, records: list) -> None:
        cmd, env = self.bench_launch(b, out)
        log = out / f"bench_{i:02d}_{b.via}.log"
        self.snapshot(out, f"bench{i:02d}_before", gateway is not None)
        print(f"  [{i}/{len(ph.bench)}] via {b.via}: {shlex.join(cmd[2:])}", flush=True)
        t0 = time.monotonic()
        code = tee(cmd, env, log)
        self.snapshot(out, f"bench{i:02d}_after", gateway is not None)
        records.append({"i": i, "via": b.via, "tag": b.tag, "cmd": cmd, "log": str(log), "exit_code": code,
                        "duration_s": round(time.monotonic() - t0, 1)})
        if code != 0:
            raise PhaseError(f"bench command {i} exited with {code}; see {log}")
        if self.live and not self.live.child.alive():
            raise PhaseError(f"engine exited during bench command {i}; see {self.live.child.log}")
        if gateway and not gateway.alive():
            raise PhaseError(f"gateway exited during bench command {i}; see {gateway.log}")

    def snapshot(self, out: Path, label: str, gateway_on: bool) -> None:
        snap = out / "snapshots"
        snap.mkdir(exist_ok=True)
        (snap / f"{label}_nvidia-smi.txt").write_text(
            f"# {iso()}\n" + nvidia_smi("-i", GPU) + "\n"
            + nvidia_smi(f"--id={GPU}", "--query-gpu=timestamp,memory.used,memory.total,utilization.gpu,"
                         "temperature.gpu,power.draw,clocks.sm,clocks.mem,pstate", "--format=csv") + "\n"
            + nvidia_smi(f"--id={GPU}", "--query-compute-apps=pid,process_name,used_memory", "--format=csv"),
            encoding="utf-8")
        for name, base in (("engine", self.engine_url), *((("gateway", self.gateway_url),) if gateway_on else ())):
            status, body = http_get(base + "/metrics")
            (snap / f"{label}_{name}_metrics.txt").write_text(
                body if status == 200 else f"# GET {base}/metrics failed: {status} {body[:300]}\n", encoding="utf-8")

    def stop_engine(self) -> dict:
        live, self.live = self.live, None
        assert live is not None
        how = live.child.stop()
        released, used = wait_gpu_released(live.baseline_mib)
        print(f"  engine stopped ({how}); GPU {GPU} {used} MiB (baseline {live.baseline_mib} MiB)", flush=True)
        return {"engine_stopped_with": how, "baseline_mib": live.baseline_mib, "after_stop_mib": used,
                "released": released}

    def versions(self, venv: str | None) -> dict:
        keys = {"gateway": (PYTHON, GATEWAY_PKGS)}
        if venv:
            keys[venv] = (ROOT / "venvs" / venv / "bin" / "python", ENGINE_PKGS)
        for key, (python, pkgs) in keys.items():
            if key not in self._versions:
                self._versions[key] = pkg_versions(python, pkgs)
        return {"runner_python": sys.version.split()[0], **{k: self._versions[k] for k in keys}}

    def shutdown(self) -> None:
        if self.live:
            self.stop_engine()


# ------------------------------------------------------------------------------------------------ main

def phase_status(results: Path, name: str) -> str:
    d = results / name
    if (d / "DONE").exists():
        return "DONE"
    if (d / "phase.json").exists():
        with contextlib.suppress(OSError, json.JSONDecodeError):
            return json.loads((d / "phase.json").read_text())["status"]
    return "partial" if d.exists() else "pending"


def _on_sigterm(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", type=Path, default=Path(__file__).with_name("plan.py"))
    ap.add_argument("--only", metavar="NAME[,NAME]", help="phases to run; globs allowed, e.g. 'P1_screen_*'")
    ap.add_argument("--list", action="store_true", help="list phases and their status, then exit")
    ap.add_argument("--dry-run", action="store_true", help="print every command; start nothing, write nothing")
    ap.add_argument("--force", action="store_true", help="rerun phases that are DONE")
    ap.add_argument("--stop-on-error", action="store_true", help="stop at the first failed phase")
    ap.add_argument("--engine-port", type=int, default=8091)
    ap.add_argument("--gateway-port", type=int, default=8090)
    ap.add_argument("--results", type=Path, default=ROOT / "results")
    ap.add_argument("--logs", type=Path, default=ROOT / "logs")
    ap.add_argument("--stub", action="store_true", help=argparse.SUPPRESS)   # self-test: every engine is a stub
    args = ap.parse_args()
    args.plan, args.results, args.logs = args.plan.resolve(), args.results.resolve(), args.logs.resolve()
    try:
        phases = select(load_plan(args.plan), args.only)
    except PlanError as exc:
        print(f"plan error: {exc}", file=sys.stderr)
        return 2
    if args.stub:
        phases = [replace(p, engine=Engine("stub")) if p.engine.kind == "vllm" else p for p in phases]
    runner = Runner(args)

    if args.list:
        for p in phases:
            print(f"{p.name:28} {phase_status(args.results, p.name):11} engine={p.engine.describe():36} "
                  f"gateway={'on' if p.gateway is not None else 'off':3} bench={len(p.bench):<3} {p.note}")
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
    lock = open(args.results / ".run_plan.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"another run_plan.py is using {args.results}", file=sys.stderr)
        return 2
    signal.signal(signal.SIGTERM, _on_sigterm)
    done: list[str] = []
    failed: list[str] = []
    try:
        for i, ph in enumerate(todo):
            keep = i + 1 < len(todo) and todo[i + 1].engine.kind == "none"
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
    print(f"\n{len(done)}/{len(todo)} phases done" + (f"; failed: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
