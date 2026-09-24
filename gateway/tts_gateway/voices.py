"""Voice registry over VOICES_DIR/<id>/ (voice-server/v1 layout): voice.json plus references/references.json,
whose "qwen3-tts" entry names the in-context reference clip, its transcript and its sha256."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import soundfile as sf

from . import logs

REFERENCE_KEY = "qwen3-tts"
REF_SECONDS = (1.0, 30.0)  # the engine rejects reference clips outside this range
_VOICE_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_AUDIO_MIME = {".wav": "audio/wav", ".flac": "audio/flac", ".mp3": "audio/mpeg", ".ogg": "audio/ogg"}
_LANGUAGE_ALIASES = {"en": "English", "english": "English", "ur": "Auto", "urdu": "Auto", "auto": "Auto"}


def engine_language(lang: str) -> str:
    """Engine language for an ISO code: the codec has an English id; Urdu (and anything else) must use Auto."""
    return "English" if lang == "en" else "Auto"


def normalize_language(value: str) -> str:
    """A request's language field in the engine's spelling ("en" -> "English", "urdu" -> "Auto", "german" ->
    "German"); the engine validates the rest."""
    value = value.strip()
    return _LANGUAGE_ALIASES.get(value.lower(), value.title())


class VoiceError(ValueError):
    pass


@dataclass(frozen=True)
class Voice:
    id: str
    label: str
    lang: str  # ISO code from voice.json ("en", "ur")
    ref_path: Path
    ref_text: str
    ref_sha256: str
    ref_seconds: float
    ref_audio: bytes = field(repr=False)
    data_url: str = field(repr=False)  # data:audio/...;base64,... of ref_audio

    @property
    def language(self) -> str:
        return engine_language(self.lang)


def load_voice(folder: Path) -> Voice:
    """Read and validate one voice folder; raises VoiceError with the reason."""
    if not _VOICE_ID.fullmatch(folder.name):
        raise VoiceError("folder name must be a lowercase id: [a-z0-9][a-z0-9_-]{0,63}")
    try:
        meta = json.loads((folder / "voice.json").read_text(encoding="utf-8"))
        refs = json.loads((folder / "references" / "references.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VoiceError(f"unreadable metadata: {exc}") from None
    lang = meta.get("language")
    if not isinstance(lang, str) or not lang:
        raise VoiceError("voice.json has no language")
    ref = refs.get(REFERENCE_KEY)
    if not isinstance(ref, dict) or not all(isinstance(ref.get(k), str) and ref[k] for k in ("file", "text", "sha256")):
        raise VoiceError(f"references.json has no complete {REFERENCE_KEY!r} entry (file, text, sha256)")
    path = folder / "references" / ref["file"]
    mime = _AUDIO_MIME.get(path.suffix.lower())
    if mime is None or path.parent != folder / "references":
        raise VoiceError(f"reference {ref['file']!r} is not an audio file inside references/")
    try:
        audio = path.read_bytes()
    except OSError as exc:
        raise VoiceError(f"reference unreadable: {exc}") from None
    digest = hashlib.sha256(audio).hexdigest()
    if digest != ref["sha256"].lower():
        raise VoiceError(f"sha256 mismatch for {path.name}: file {digest}, references.json {ref['sha256']}")
    try:
        seconds = sf.info(io.BytesIO(audio)).duration
    except sf.LibsndfileError as exc:
        raise VoiceError(f"reference is not decodable audio: {exc}") from None
    if not REF_SECONDS[0] <= seconds <= REF_SECONDS[1]:
        raise VoiceError(f"reference lasts {seconds:.2f} s; the engine accepts {REF_SECONDS[0]:g}-{REF_SECONDS[1]:g} s")
    return Voice(id=folder.name, label=str(meta.get("label") or folder.name), lang=lang, ref_path=path,
                 ref_text=ref["text"].strip(), ref_sha256=digest, ref_seconds=round(seconds, 3), ref_audio=audio,
                 data_url=f"data:{mime};base64,{base64.b64encode(audio).decode()}")


class VoiceRegistry:
    def __init__(self, voices: list[Voice], errors: dict[str, str] | None = None) -> None:
        self._voices = {v.id: v for v in voices}
        self.errors = errors or {}

    @classmethod
    def load(cls, root: Path) -> VoiceRegistry:
        """Every valid voice folder under root; invalid ones are logged and skipped."""
        voices, errors = [], {}
        folders = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
        for folder in folders:
            try:
                voices.append(load_voice(folder))
            except VoiceError as exc:
                errors[folder.name] = str(exc)
                logs.event("voice_invalid", logging.ERROR, voice=folder.name, error=str(exc))
        return cls(voices, errors)

    def get(self, voice_id: str) -> Voice | None:
        return self._voices.get(voice_id.lower())

    def __iter__(self) -> Iterator[Voice]:
        return iter(self._voices.values())

    def __len__(self) -> int:
        return len(self._voices)
