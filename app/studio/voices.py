"""Preset voices: every folder under the voices dir is a voice (rescanned on each request, so a new folder appears
without code changes). A folder holds one or more audio clips, `transcripts.json` ({file: exact transcript}), optional
`persona.json` (card overrides), optional `reference.json` (an exact cut: {"clip", "start", "end", "text"} or a list
of those, used as-is instead of the automatic fit) and anything else (SOURCE.md...). A folder name like `Asad(pashto)` gives id `asad`
and a language hint. Clips are combined/cut into one reference under the engine's 30 s limit and cached."""
from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from . import audio
from .settings import settings
from .text import letters, split_sentences

AUDIO_EXT = {".wav", ".mp3", ".ogg", ".opus", ".flac", ".m4a"}
LANGUAGES = {  # the console languages; others are shown under "Other"
    "en": {"name": "English", "dir": "ltr"},
    "ur": {"name": "Urdu", "dir": "rtl"},
    "ps": {"name": "Pashto", "dir": "rtl"},
    "pa": {"name": "Punjabi (Shahmukhi)", "dir": "rtl"},
    "sd": {"name": "Sindhi", "dir": "rtl"},
}
HINTS = {"english": "en", "urdu": "ur", "pashto": "ps", "pushto": "ps", "punjabi": "pa", "panjabi": "pa",
         "shahmukhi": "pa", "gurmukhi": "pa_guru", "sindhi": "sd", "hindi": "hi"}
_PERSONAS = json.loads((Path(__file__).with_name("personas.json")).read_text(encoding="utf-8"))
DEFAULT_DELIVERY = {"speed": "normal", "expressiveness": "normal", "pitch": "normal", "emotion": "", "strength": "light"}
_PUNJABI_WORDS = {"اے", "دا", "دی", "دے", "تے", "وچ", "نال", "ساڈا", "ساڈے", "تہاڈا", "تہاڈے", "نئیں", "اوہ", "ایہہ", "کجھ",
                  "گل", "گلاں", "ویلا", "سانوں", "تسی", "تسیں", "واں", "ہویا", "جیہڑا"}


def voice_id(folder: str) -> tuple[str, str | None]:
    m = re.match(r"^\s*(.*?)\s*\(([^)]*)\)\s*$", folder)
    name, hint = (m.group(1), m.group(2)) if m else (folder, None)
    vid = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "voice"
    return vid, HINTS.get((hint or "").strip().lower()) if hint else None


def detect_language(text: str) -> str:
    chars = [c for c in text if c.isalpha()]
    if not chars:
        return "ur"
    n = len(chars)
    if sum("਀" <= c <= "੿" for c in chars) / n > 0.3:
        return "pa_guru"
    if sum("ऀ" <= c <= "ॿ" for c in chars) / n > 0.3:
        return "hi"
    if sum(c.isascii() for c in chars) / n > 0.6:
        return "en"
    if sum(c in "ڪڏڄٻڀٽٺڊڌڍڦڱڳڻڃڇ" for c in chars) >= 3:
        return "sd"
    if sum(c in "ټډړږښګڼۍې" for c in chars) >= 3:
        return "ps"
    words = re.findall(r"\w+", text)
    if sum(w in _PUNJABI_WORDS for w in words) >= max(3, len(words) // 25):
        return "pa"
    return "ur"


@dataclass
class Reference:
    wav: bytes               # 24 kHz mono 16-bit, <= max_ref_s
    text: str                # its exact transcript
    seconds: float
    s_per_letter: float      # the voice's pace: Higgs copies it
    clips: list[str] = field(default_factory=list)
    note: str = ""


def build_reference(clips: list[tuple[np.ndarray, str, str]], max_s: float) -> Reference:
    """clips: (audio 24 kHz, transcript, name). Whole clips are joined (0.3 s gaps) while they fit; if even the first
    clip is too long it is cut at a matching sentence/word boundary (audio.fit_reference)."""
    gap = 0.3
    chosen, total = [], 0.0
    for x, t, name in clips:
        x = audio.trim_silence(x)
        d = len(x) / audio.SR
        if total + d + (gap if chosen else 0) <= max_s:
            chosen.append((x, t, name))
            total += d + (gap if len(chosen) > 1 else 0)
    note = ""
    if not chosen:
        x, t, name = clips[0]
        fit = audio.fit_reference(x, t, max_s)
        chosen, note = [(fit.audio, fit.text, name)], fit.note
    y = audio.join([c[0] for c in chosen], gap)
    text = " ".join(c[1].strip() for c in chosen)
    secs = len(y) / audio.SR
    n_sent = max(1, len(split_sentences(text)))
    spl = max(0.03, (secs - 0.25 * (n_sent - 1)) / max(1, letters(text)))
    return Reference(audio.wav_bytes(y), text, round(secs, 2), round(spl, 4), [c[2] for c in chosen], note)


@dataclass
class Voice:
    id: str
    folder: str
    name: str
    role: str
    language: str
    gender: str
    description: str
    delivery: dict
    hidden: bool
    public_figure: bool
    clips: list[str]
    source_seconds: float
    transcript_ok: bool
    warnings: list[str]

    def card(self) -> dict:
        d = asdict(self)
        d["language_name"] = LANGUAGES.get(self.language, {"name": self.language})["name"]
        d["preview_url"] = f"/api/voices/{self.id}/reference.wav"
        return d


class VoiceRegistry:
    def __init__(self, root: Path | None = None, cache_dir: Path | None = None):
        self.root = Path(root or settings.voices_dir)
        self.cache = Path(cache_dir or settings.data_dir / "refcache")
        self.cache.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def scan(self) -> dict[str, Voice]:
        out: dict[str, Voice] = {}
        if not self.root.is_dir():
            return out
        for d in sorted(p for p in self.root.iterdir() if p.is_dir() and not p.name.startswith(".")):
            clips = sorted(p.name for p in d.iterdir() if p.suffix.lower() in AUDIO_EXT)
            # prefer WAV when the same clip exists in several formats
            stems = {}
            for c in clips:
                s = Path(c).stem
                if s not in stems or c.lower().endswith(".wav"):
                    stems[s] = c
            clips = sorted(stems.values())
            if not clips:
                continue
            vid, hint = voice_id(d.name)
            tr = self._transcripts(d)
            persona = dict(_PERSONAS.get(vid, {}))
            if (d / "persona.json").exists():
                try:
                    persona |= json.loads((d / "persona.json").read_text(encoding="utf-8"))
                except ValueError:
                    pass
            text_all = " ".join(tr.get(c, "") for c in clips)
            warnings = []
            missing = [c for c in clips if not tr.get(c)]
            if missing:
                warnings.append(f"no transcript for {', '.join(missing)} (transcripts.json)")
            lang = persona.get("language") or hint or detect_language(text_all)
            delivery = DEFAULT_DELIVERY | persona.get("delivery", {})
            src_s = 0.0
            for c in clips:
                try:
                    import soundfile as sf
                    src_s += sf.info(str(d / c)).duration
                except Exception:  # noqa: BLE001 - non-WAV: duration unknown until decoded
                    pass
            if vid in out:
                vid = f"{vid}_{len(out)}"
            out[vid] = Voice(vid, d.name, persona.get("name", d.name.split("(")[0].strip().title()),
                             persona.get("role", LANGUAGES.get(lang, {"name": lang})["name"] + " voice"), lang,
                             persona.get("gender", ""), persona.get("description", ""), delivery,
                             bool(persona.get("hidden", False)), bool(persona.get("public_figure", False)), clips,
                             round(src_s, 1), not missing, warnings)
        return out

    @staticmethod
    def _override(d: Path) -> list[dict] | None:
        f = d / "reference.json"
        if not f.exists():
            return None
        data = json.loads(f.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else [data]

    @staticmethod
    def _transcripts(d: Path) -> dict[str, str]:
        f = d / "transcripts.json"
        if not f.exists():
            return {}
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            return {}
        out = {}
        for k, v in data.items():  # keys may be given with another extension (asad_saab.ogg -> .wav)
            out[k] = v
            out[Path(k).stem + ".wav"] = out.get(Path(k).stem + ".wav", v)
        return out

    def reference(self, vid: str, max_s: float | None = None) -> Reference:
        max_s = min(max_s or settings.max_ref_s, settings.max_ref_s)
        voices = self.scan()
        if vid not in voices:
            raise KeyError(f"unknown voice {vid!r}")
        v = voices[vid]
        d = self.root / v.folder
        tr = self._transcripts(d)
        ov = d / "reference.json"
        key = hashlib.sha1(json.dumps([max_s, ov.read_text(encoding="utf-8") if ov.exists() else "", [(c, (d / c).stat().st_mtime_ns, (d / c).stat().st_size, tr.get(c))
                                                for c in v.clips]], ensure_ascii=False).encode()).hexdigest()[:16]
        wav_p, meta_p = self.cache / f"{vid}_{key}.wav", self.cache / f"{vid}_{key}.json"
        with self._lock:
            if wav_p.exists() and meta_p.exists():
                m = json.loads(meta_p.read_text(encoding="utf-8"))
                return Reference(wav_p.read_bytes(), m["text"], m["seconds"], m["s_per_letter"], m["clips"], m["note"])
            override = self._override(d)
            if override:
                segs = [(audio.trim_silence(audio.decode(str(d / o["clip"]))[int(float(o.get("start", 0)) * audio.SR):
                                                                         int(float(o["end"]) * audio.SR)]),
                         o["text"], o["clip"]) for o in override]
                y = audio.join([sg[0] for sg in segs], 0.3)
                if len(y) / audio.SR > max_s:
                    raise ValueError(f"{d.name}/reference.json selects {len(y) / audio.SR:.1f}s, over {max_s}s")
                text = " ".join(sg[1].strip() for sg in segs)
                n_sent = max(1, len(split_sentences(text)))
                spl = max(0.03, (len(y) / audio.SR - 0.25 * (n_sent - 1)) / max(1, letters(text)))
                ref = Reference(audio.wav_bytes(y), text, round(len(y) / audio.SR, 2), round(spl, 4),
                                [sg[2] for sg in segs], "exact cut from reference.json")
            else:
                clips = [(audio.decode(str(d / c)), tr.get(c, ""), c) for c in v.clips if tr.get(c)]
                if not clips:
                    raise ValueError(f"voice {vid} has no clip with a transcript")
                ref = build_reference(clips, max_s)
            wav_p.write_bytes(ref.wav)
            meta_p.write_text(json.dumps({k: getattr(ref, k) for k in ("text", "seconds", "s_per_letter", "clips", "note")},
                                         ensure_ascii=False), encoding="utf-8")
            return ref
