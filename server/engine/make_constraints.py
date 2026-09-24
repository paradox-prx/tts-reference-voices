#!/usr/bin/env python3
"""Write a pip/uv constraints file (one `name==version` per line) from a `pip install --dry-run --report` JSON.

  make_constraints.py REPORT.json OUT.txt

The engine constraints files pin the whole resolved engine stack, so an install reproduces exactly the set the
research resolved (docs/research/artifacts/local-env/report-*.json; Python 3.12, x86_64):

  make_constraints.py docs/research/artifacts/local-env/report-omni-0.28.0+vllm.json engine/constraints-omni28.txt
  make_constraints.py docs/research/artifacts/local-env/report-omni-0.30.0rc1+vllm-0.30.0.json \\
      engine/constraints-omni30.txt

Lines are sorted case-insensitively with no header, the format engine/constraints-omni28.txt was first written in, so
regenerating it is byte-identical. Use the file with engine/install_engine.sh --constraints. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def constraints(report: dict) -> list[str]:
    """`name==version` for every package the report installs, sorted case-insensitively."""
    install = report.get("install")
    if not isinstance(install, list) or not install:
        raise ValueError("not a pip --report JSON (no 'install' list)")
    pins: dict[str, str] = {}
    for item in install:
        name, version = item["metadata"]["name"], item["metadata"]["version"]
        key = name.lower().replace("_", "-").replace(".", "-")
        if pins.setdefault(key, f"{name}=={version}") != f"{name}=={version}":
            raise ValueError(f"{name} appears twice with different versions")
    return sorted(pins.values(), key=str.lower)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", type=Path, help="pip --report JSON")
    ap.add_argument("out", type=Path, help="constraints file to write")
    a = ap.parse_args()
    try:
        lines = constraints(json.loads(a.report.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {a.report}: {exc}", file=sys.stderr)
        return 2
    a.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{a.out}: {len(lines)} pins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
