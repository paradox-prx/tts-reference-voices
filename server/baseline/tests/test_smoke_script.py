"""smoke.py end to end against a real uvicorn server running the app with FakeTTS and the repo's voices."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import uvicorn

import qwen_tts_server as srv
from fake_qwen_tts import FakeTTS

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_smoke_script_against_fake_server(tmp_path):
    fake = FakeTTS(delay=0.05)
    port = free_port()
    args = srv.build_parser().parse_args(["--device", "cpu", "--no-warmup", "--port", str(port),
                                          "--batch-window-ms", "100"])
    app = srv.create_app(args, loader=lambda a: (fake, {"model_path": "fake"}))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None, access_log=False))
    app.state.st.server = server
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    try:
        for _ in range(200):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                    if r.status == 200:
                        break
            except Exception:  # noqa: BLE001
                time.sleep(0.05)
        out = tmp_path / "smoke"
        proc = subprocess.run([sys.executable, str(HERE.parent / "smoke.py"), "--url", f"http://127.0.0.1:{port}",
                               "--out", str(out)], capture_output=True, text=True, timeout=120)
    finally:
        server.should_exit = True
        th.join(10)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((out / "smoke.json").read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["steps"]["concurrent"]["batch_sizes"] == ["4"] * 4
    assert sorted(p.name for p in out.glob("*.wav")) == sorted(
        ["english_trump.wav", "urdu_shehbaz.wav", "inline_trump_ref.wav"]
        + [f"concurrent_{i}_{v}.wav" for i, v in enumerate(["trump", "shehbaz", "trump", "shehbaz"])])
    langs = [c["languages"] for c in fake.calls]
    assert langs[:3] == [["English"], ["Auto"], ["English"]] and sorted(langs[3]) == ["Auto", "Auto", "English",
                                                                                      "English"]
    assert "PASS" in proc.stdout
