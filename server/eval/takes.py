"""How score_run.py and retry_sim.py group bench rows into settings, prompts and takes. Seeds are never used: on
vLLM-Omni 0.28 a seed does not reproduce a take (same seed, different audio), so the K takes of a prompt are K
unseeded requests told apart by `take` (0..K-1), and settings (e.g. repetition_penalty values) pair by prompt only.

  setting  one bench run and one voice as the engine knows it: "<run> [<voice>]" (the run name carries the tag, size,
           concurrency and K; the voice may be an engine variant such as trump-avg, which is a different setting
           from trump-prompt). --setting tag / params / dir group by those instead of the run name.
  prompt   "<repo voice>/<prompt>": the repo voice behind the row's voice (tts_qc.voices.resolve_voice strips
           -avg / -prompt / -<sha10>), and the prompt id (benchmarks/*.json, --size prompts), else the pool text
           index, else a hash of the text. So the same text under two settings or two voice variants pairs up.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qc"))

from tts_qc.voices import resolve_voice  # noqa: E402

REPO_VOICES = ("trump", "shehbaz")   # fallback when voices/ cannot be listed


def _known() -> list[str]:
    try:
        from tts_qc import paths
        return [p.name for p in paths.voices_dir().iterdir() if (p / "references").is_dir()] or list(REPO_VOICES)
    except OSError:
        return list(REPO_VOICES)


KNOWN = _known()


def raw_voice(r: dict) -> str:
    """The voice as requested: the engine's name when bench used one (engine_voice), else the row's voice."""
    return str(r.get("engine_voice") or r.get("voice") or "")


def repo_voice(r: dict) -> str:
    v = r.get("voice") or r.get("engine_voice") or ""
    return resolve_voice(v, KNOWN) or resolve_voice(r.get("engine_voice"), KNOWN) or v


def prompt_id(r: dict) -> str:
    if r.get("prompt_id"):
        return str(r["prompt_id"])
    if r.get("text_idx") is not None:
        return f"text{r['text_idx']}"
    if r.get("text"):
        return "sha1:" + hashlib.sha1(r["text"].encode("utf-8")).hexdigest()[:10]
    return r.get("case") or Path(r.get("file", "")).stem


def prompt_key(r: dict) -> str:
    return f"{repo_voice(r)}/{prompt_id(r)}"


def setting_key(r: dict, mode: str = "run", default: str = "") -> str:
    if mode == "tag":
        base = r.get("tag") or default
    elif mode == "params":
        base = json.dumps(r.get("params") or {}, sort_keys=True, ensure_ascii=False)
    elif mode == "dir":
        base = default
    else:
        base = r.get("run") or default
    v = raw_voice(r)
    return f"{base} [{v}]" if v else str(base)
