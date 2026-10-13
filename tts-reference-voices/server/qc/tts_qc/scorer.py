"""One code path for scoring a take: the sidecar (app.py) and the offline scorer (server/eval/score_run.py) both call
Scorer.score() and then policy.gate() / policy.bad() on the metrics it returns.

Per take (all keys optional; a check that did not run leaves its keys out):
  audio   duration_s, speech_ratio, lead_sil_s, trail_sil_s, max_internal_sil_s, n_internal_sil_gt1s, speech_span_s,
          clip_frac, thr_db (checks.audio_checks); letters, s_per_letter, pace (the voice's expected s/letter),
          pace_ratio (s_per_letter / pace)
  asr     asr_text, ref_norm, hyp_norm, wer, cer, cer_nospace, sub, del, ins, del_run, ins_run, char_ratio,
          repeat_excess, repeat_what, token_run(_ref), char_runs(_ref) (checks.text_checks); max_word_s, max_word,
          max_word_voiced, max_gap_s, max_gap_voiced, max_gap_at_s, aligned_chars_per_s, n_words_asr
          (checks.word_timing_checks); words ([start, end, word, probability] per ASR word); unaligned_tail_s
          (audio after the last ASR word); seg_max_cr, seg_fallback, seg_min_logprob, seg_max_nospeech, n_segments
          (Whisper decode diagnostics); script_arabic / script_latin / script_devanagari (+ _ref for the input text)
  sim     sim_speech_s (seconds embedded, after trimming leading/trailing silence), sim_prompt_<model>,
          sim_heldout_<model> (model = base | large; heldout only for voices with clips outside the prompt)
"""
from __future__ import annotations

import importlib.metadata as md
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import jiwer
import numpy as np

from . import paths
from .audio import ASR_RATE, read_wav, to_16k, trim_16k
from .checks import Vad, audio_checks, text_checks, word_timing_checks
from .policy import CHECKS
from .textnorm import count_letters, normalizer, nospace, script_fractions
from .voices import VoiceInfo, load_voices, resolve_voice


@dataclass
class ScorerConfig:
    device: str = "cuda"                   # cuda | cpu (both models)
    device_index: int = 0
    asr: bool = True
    asr_compute: str | None = None         # float16 (cuda default) | int8_float16 | int8 (cpu default)
    beam: int = 5
    workers: int = 2                       # CTranslate2 replicas (share weights on one GPU)
    cpu_threads: int = 8                   # per CT2 worker on CPU; torch intra-op threads for SIM on CPU
    sim_models: tuple[str, ...] = ("base",)
    models_dir: Path = field(default_factory=paths.models_dir)
    voices_dir: Path = field(default_factory=paths.voices_dir)
    pace_file: Path | None = field(default_factory=paths.pace_file)


@dataclass
class VoiceRefs:
    prompt: np.ndarray
    heldout: np.ndarray | None
    prompt_speech_s: float
    heldout_files: list[str]


def _r(x: float | None, nd: int = 4) -> float | None:
    return None if x is None else round(float(x), nd)


class Scorer:
    def __init__(self, cfg: ScorerConfig) -> None:
        self.cfg = cfg
        self.asr = None
        self.embedders: dict = {}
        self.voices: dict[str, VoiceInfo] = {}
        self.refs: dict[tuple[str, str], VoiceRefs] = {}
        self.load_s: dict[str, float] = {}
        self._ready = threading.Event()

    # ------------------------------------------------------------------------------------------------ loading

    @property
    def ready(self) -> bool:
        return self._ready.is_set()

    def load(self) -> "Scorer":
        cfg = self.cfg
        self.voices = load_voices(cfg.voices_dir, cfg.pace_file)
        if cfg.device == "cpu" and cfg.sim_models:
            import torch
            torch.set_num_threads(max(1, cfg.cpu_threads))
        if cfg.asr:
            from .asr import Asr
            self.asr = Asr(cfg.models_dir / "faster-whisper-large-v3", cfg.device, cfg.asr_compute, cfg.workers,
                           cfg.cpu_threads, cfg.beam, cfg.device_index)
            self.load_s["asr"] = round(self.asr.load_s, 2)
        from .sim import Embedder
        for name in cfg.sim_models:
            emb = Embedder(name, cfg.models_dir, cfg.device, cfg.device_index)
            self.embedders[name] = emb
            self.load_s[f"sim_{name}"] = round(emb.load_s, 2)
            t0 = time.perf_counter()
            for vid, v in self.voices.items():
                self.refs[(vid, name)] = self._voice_refs(emb, v)
            self.load_s[f"refs_{name}"] = round(time.perf_counter() - t0, 2)
        self._ready.set()
        return self

    def _embed_file(self, emb, path: Path) -> tuple[np.ndarray, float]:
        pcm, sr = read_wav(path)
        a = audio_checks(pcm, sr)
        wav = trim_16k(to_16k(pcm, sr), a["lead_sil_s"], a["trail_sil_s"])
        return emb(wav), len(wav) / ASR_RATE

    def _voice_refs(self, emb, v: VoiceInfo) -> VoiceRefs:
        from .sim import centroid
        prompt, secs = self._embed_file(emb, v.prompt)
        held = [self._embed_file(emb, p)[0] for p in v.heldout]
        return VoiceRefs(prompt, centroid(held), round(secs, 2), [p.name for p in v.heldout])

    def voice(self, name: str | None) -> VoiceInfo | None:
        """The repo voice behind `name` (engine variants like 'trump-avg' map to 'trump'), or None."""
        vid = resolve_voice(name, self.voices)
        return self.voices[vid] if vid else None

    def describe(self) -> dict:
        """Provenance for score files: versions, model identities (sha256 from models/eval/MANIFEST.json)."""
        manifest = {}
        mf = self.cfg.models_dir / "MANIFEST.json"
        if mf.exists():
            for name, entry in json.loads(mf.read_text()).items():
                shas = {f: v.get("sha256") for f, v in entry.get("files", {}).items() if v.get("sha256")}
                manifest[name] = {"repo": entry.get("repo"), "revision": entry.get("revision"), "sha256": shas}
        versions = {}
        for pkg in ("faster-whisper", "ctranslate2", "torch", "transformers", "jiwer", "numpy", "av"):
            try:
                versions[pkg] = md.version(pkg)
            except md.PackageNotFoundError:
                pass
        from . import __version__
        return {"tts_qc": __version__, "device": self.cfg.device,
                "asr": self.asr.describe() if self.asr else None, "sim_models": list(self.embedders),
                "models": manifest, "versions": versions, "load_s": self.load_s,
                "voices": {k: {"lang": v.lang, "pace": v.pace, "pace_source": v.pace_source,
                               "prompt": v.prompt.name, "heldout": [p.name for p in v.heldout]}
                           for k, v in self.voices.items()}}

    # ------------------------------------------------------------------------------------------------ scoring

    def score(self, pcm: np.ndarray, sr: int, text: str, lang: str, voice: str | None,
              checks: Iterable[str] = CHECKS, pace: float | None | bool = True) -> tuple[dict, dict]:
        """One take: mono int16 PCM at `sr`, the input text, its language ('en', 'ur' or 'und'), the repo voice id
        (None/'' for an inline reference: no SIM, no pace; engine variants such as 'trump-avg' or 'trump-<sha10>' use
        the repo voice's references). `pace`: True = the voice's expected pace, a float = that s/letter, False/None =
        no pace check. Returns (metrics, ms) with ms = {audio, asr, sim, total}."""
        checks = set(checks)
        t_start = time.perf_counter()
        v = self.voice(voice)
        m: dict = {}
        ms = {"audio": 0.0, "asr": 0.0, "sim": 0.0, "total": 0.0}

        t0 = time.perf_counter()
        vad = Vad.compute(pcm, sr)
        m.update(audio_checks(pcm, sr, vad=vad))
        letters = count_letters(text)
        m["letters"] = letters
        expected = (v.pace if v else None) if pace is True else (pace or None)
        if letters and m["duration_s"]:
            m["s_per_letter"] = round(m["duration_s"] / letters, 4)
            if expected:
                m["pace"] = round(expected, 4)
                m["pace_ratio"] = round(m["s_per_letter"] / expected, 3)
        need16 = ("asr" in checks and self.asr is not None) or ("sim" in checks and v is not None and self.embedders)
        wav16 = to_16k(pcm, sr) if need16 else None
        ms["audio"] = (time.perf_counter() - t0) * 1000

        if "asr" in checks and self.asr is not None and lang in ("en", "ur"):
            t0 = time.perf_counter()
            m.update(self._asr_metrics(wav16, text, lang, vad, m["duration_s"]))
            ms["asr"] = (time.perf_counter() - t0) * 1000

        if "sim" in checks and v is not None and self.embedders:
            t0 = time.perf_counter()
            from .sim import MIN_SECONDS, cosine
            trimmed = trim_16k(wav16, m["lead_sil_s"], m["trail_sil_s"])
            m["sim_speech_s"] = round(len(trimmed) / ASR_RATE, 2)
            if m["speech_ratio"] and len(trimmed) >= MIN_SECONDS * ASR_RATE:
                for name, emb in self.embedders.items():
                    e = emb(trimmed)
                    ref = self.refs[(v.id, name)]
                    m[f"sim_prompt_{name}"] = _r(cosine(e, ref.prompt))
                    if ref.heldout is not None:
                        m[f"sim_heldout_{name}"] = _r(cosine(e, ref.heldout))
            ms["sim"] = (time.perf_counter() - t0) * 1000

        ms["total"] = (time.perf_counter() - t_start) * 1000
        return m, {k: round(x, 1) for k, x in ms.items()}

    def _asr_metrics(self, wav16: np.ndarray, text: str, lang: str, vad: Vad, duration_s: float) -> dict:
        res = self.asr.transcribe(wav16, lang)
        norm = normalizer(lang)
        rn, hn = norm(text), norm(res.text)
        out: dict = {"asr_text": res.text, "ref_norm": rn, "hyp_norm": hn, "asr_s": round(res.seconds, 3)}
        if rn:
            out["wer"] = _r(jiwer.wer(rn, hn))
            out["cer"] = _r(jiwer.cer(rn, hn))
            rs, hs = nospace(rn), nospace(hn)
            out["cer_nospace"] = _r(jiwer.cer(rs, hs)) if rs else None
            out.update(text_checks(rn, hn))
        out.update(word_timing_checks(res.words, vad))
        out["words"] = [[round(w.start, 2), round(w.end, 2), w.word.strip(), round(w.probability, 2)]
                        for w in res.words]
        last = max((w.end for w in res.words), default=0.0)
        out["unaligned_tail_s"] = round(max(0.0, duration_s - last), 2)
        out.update(res.diag)
        hyp_s, ref_s = script_fractions(res.text), script_fractions(text)
        for k in ("arabic", "latin", "devanagari"):
            out[f"script_{k}"] = hyp_s[k]
            out[f"script_{k}_ref"] = ref_s[k]
        return out
