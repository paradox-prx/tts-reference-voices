#!/usr/bin/env python3
"""Restart a systemd user unit when its HTTP health endpoint keeps failing.

  health_watchdog.py [--unit qwen3-tts-engine.service] [--url http://127.0.0.1:$TTS_ENGINE_PORT/health]
                     [--interval 15] [--failures 4] [--timeout 5] [--grace 120]

Why: vLLM-Omni keeps its API server running when a stage process dies; GET /health then answers 503 (or hangs when
the event loop is wedged, vllm-omni #4855), so the unit never exits and Restart=on-failure never fires. This loop
checks the endpoint only while the unit is "active" (not while it starts: the engine unit stays "activating" until
engine/wait_ready.py got audio back), and after --failures consecutive failures (non-200, error or timeout) runs
`systemctl --user restart --no-block UNIT`, then waits --grace seconds before it looks again. It never starts a
stopped unit. Knobs also come from the environment: TTS_WATCHDOG_UNIT, TTS_WATCHDOG_URL, TTS_WATCHDOG_INTERVAL_S,
TTS_WATCHDOG_FAILURES. Stdlib only; logs one line per event to stdout (journald).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable


def unit_state(unit: str, systemctl: str = "systemctl") -> str:
    """ActiveState of a user unit ("active", "activating", "inactive", "failed", ...), or "unknown"."""
    try:
        r = subprocess.run([systemctl, "--user", "show", "--property=ActiveState", "--value", unit],
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    if r.returncode != 0:
        return "unknown"
    return r.stdout.strip() or "unknown"


def healthy(url: str, timeout: float) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout) as r:
            return r.status == 200, f"HTTP {r.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except (urllib.error.URLError, OSError) as exc:  # refused, reset, timeout
        return False, str(getattr(exc, "reason", exc))


class Watchdog:
    """One check per step(); returns the seconds to sleep before the next one. Side effects are injectable."""

    def __init__(self, unit: str, url: str, failures: int, interval: float, grace: float, timeout: float,
                 state: Callable[[str], str] = unit_state,
                 probe: Callable[[str, float], tuple[bool, str]] = healthy,
                 restart: Callable[[str], bool] | None = None,
                 log: Callable[[str], None] = lambda msg: print(msg, flush=True)) -> None:
        self.unit, self.url, self.failures, self.interval, self.grace = unit, url, failures, interval, grace
        self.timeout, self.state, self.probe, self.log = timeout, state, probe, log
        self.restart = restart or self._systemctl_restart
        self.failed = 0

    def _systemctl_restart(self, unit: str) -> bool:
        r = subprocess.run(["systemctl", "--user", "restart", "--no-block", unit], capture_output=True, text=True,
                           timeout=30)
        if r.returncode:
            self.log(f"watchdog: systemctl restart {unit} failed: {r.stderr.strip()}")
        return r.returncode == 0

    def step(self) -> float:
        state = self.state(self.unit)
        if state != "active":
            if self.failed:
                self.log(f"watchdog: {self.unit} is {state}; failure count reset")
            self.failed = 0
            return self.interval
        ok, detail = self.probe(self.url, self.timeout)
        if ok:
            if self.failed:
                self.log(f"watchdog: {self.url} healthy again after {self.failed} failure(s)")
            self.failed = 0
            return self.interval
        self.failed += 1
        self.log(f"watchdog: {self.url} failed ({detail}), {self.failed}/{self.failures}")
        if self.failed < self.failures:
            return self.interval
        self.log(f"watchdog: restarting {self.unit} after {self.failed} consecutive failures")
        self.failed = 0
        self.restart(self.unit)
        return self.grace


def main() -> int:
    env = os.environ.get
    port = env("TTS_ENGINE_PORT") or "8091"
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--unit", default=env("TTS_WATCHDOG_UNIT") or "qwen3-tts-engine.service")
    ap.add_argument("--url", default=env("TTS_WATCHDOG_URL") or f"http://127.0.0.1:{port}/health")
    ap.add_argument("--interval", type=float, default=float(env("TTS_WATCHDOG_INTERVAL_S") or 15),
                    help="seconds between checks (default %(default)s)")
    ap.add_argument("--failures", type=int, default=int(env("TTS_WATCHDOG_FAILURES") or 4),
                    help="consecutive failures before a restart (default %(default)s)")
    ap.add_argument("--timeout", type=float, default=5.0, help="per-check HTTP timeout (default %(default)s)")
    ap.add_argument("--grace", type=float, default=120.0,
                    help="seconds to wait after a restart before checking again (default %(default)s)")
    ap.add_argument("--once", action="store_true", help="one check, then exit (0 = healthy or not active)")
    a = ap.parse_args()
    if a.failures < 1 or a.interval <= 0:
        ap.error("--failures must be >= 1 and --interval > 0")
    dog = Watchdog(a.unit, a.url, a.failures, a.interval, a.grace, a.timeout)
    if a.once:
        dog.step()
        return 1 if dog.failed else 0
    dog.log(f"watchdog: watching {a.unit} via {a.url} every {a.interval:g} s, restart after {a.failures} failures")
    while True:
        time.sleep(dog.step())


if __name__ == "__main__":
    sys.exit(main())
