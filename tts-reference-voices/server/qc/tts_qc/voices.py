"""The repo's voices (voices/<id>/): language, the Qwen prompt reference, held-out clips and expected pace.

SIM references per voice (eval-tooling.md finding 22):
  prompt   references/qwen3-tts.wav, the audio the model is conditioned on (seed-tts SIM-o convention).
  heldout  centroid of the voice's clips that are NOT in the prompt (references.json "qwen3-tts".clips): shehbaz
           02-06; none for trump, whose single clip is the prompt.
Pace (seconds per letter, letters = str.isalnum count) comes from server/calibration/pace.json; a voice missing there
falls back to its reference clip's pace, as in the gateway. Do not use the clip pace for shehbaz: that clip is a slow,
pause-heavy address (0.183 s/letter) while good Qwen Urdu runs ~0.088.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .textnorm import count_letters

PROMPT_KEY = "qwen3-tts"
# engine / gateway names of one repo voice: "<id>-avg" (averaged speaker embedding), "<id>-prompt" (the prompt clip),
# content-addressed "<id>-<sha10>" (an uploaded reference), in any combination
_VARIANT = re.compile(r"-(?:avg|prompt|[0-9a-f]{10})$")


def resolve_voice(name: str | None, known: Iterable[str]) -> str | None:
    """The repo voice (voices/<id>) behind a row's or request's voice name, or None. Exact ids win; otherwise the
    -avg / -prompt / -<sha10> suffixes are stripped one at a time: 'trump-avg' -> 'trump', 'shehbaz-3f9a0c1b2d' ->
    'shehbaz'. All of them are scored against the repo voice's references."""
    known = set(known)
    while name:
        if name in known:
            return name
        stripped = _VARIANT.sub("", name)
        if stripped == name:
            return None
        name = stripped
    return None


@dataclass(frozen=True)
class VoiceInfo:
    id: str
    lang: str                       # "en" or "ur" (voice.json "language")
    prompt: Path                    # references/qwen3-tts.wav
    prompt_text: str
    prompt_clips: tuple[str, ...]   # clip file names inside the prompt
    heldout: tuple[Path, ...]       # clips not in the prompt
    pace: float                     # expected s/letter
    pace_source: str


def load_pace(pace_file: Path | None) -> dict[str, float]:
    if not pace_file or not Path(pace_file).exists():
        return {}
    data = json.loads(Path(pace_file).read_text(encoding="utf-8"))
    return {k: float(v["s_per_letter"]) for k, v in data.items() if isinstance(v, dict) and "s_per_letter" in v}


def load_voices(voices_dir: Path, pace_file: Path | None = None) -> dict[str, VoiceInfo]:
    """Every voices/<id>/ with references/references.json holding a 'qwen3-tts' entry."""
    import soundfile as sf

    paces = load_pace(pace_file)
    out: dict[str, VoiceInfo] = {}
    for folder in sorted(p for p in Path(voices_dir).iterdir() if p.is_dir()):
        ref_json = folder / "references" / "references.json"
        if not ref_json.exists():
            continue
        refs = json.loads(ref_json.read_text(encoding="utf-8")).get(PROMPT_KEY)
        if not refs:
            continue
        vj = folder / "voice.json"
        meta = json.loads(vj.read_text(encoding="utf-8")) if vj.exists() else {}
        prompt = folder / "references" / refs["file"]
        in_prompt = tuple(refs.get("clips", []))
        heldout = tuple(sorted(p for p in folder.glob("*.wav") if p.name not in set(in_prompt)))
        if folder.name in paces:
            pace, source = paces[folder.name], "pace_file"
        else:
            letters = max(1, count_letters(refs.get("text", "")))
            pace, source = sf.info(str(prompt)).duration / letters, "reference_clip"
        out[folder.name] = VoiceInfo(folder.name, meta.get("language", "en"), prompt, refs.get("text", ""),
                                     in_prompt, heldout, pace, source)
    return out
