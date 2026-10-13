#!/usr/bin/env python3
"""Rebuild the calibration inputs: synthetic failure clips spliced from the real reference clips, and the manifests
score_run.py --manifest reads.

    eval/run.sh eval/make_synth.py            # -> eval/lab/synth/*.wav (gitignored) + eval/calibration/*_manifest.jsonl

The splices reproduce the eval research's cases (eval-tooling.md findings 11, 12, 26; same durations) from real
recordings, so they are NOT Qwen output and may not look like real Qwen loops. They are made from a public broadcast
excerpt: keep them local (eval/lab/synth/ is gitignored), never publish them. Every splice point gets a 5 ms linear
crossfade so no click marks it. Deterministic (the noise tail uses a fixed seed).

Whisper does not always transcribe a loop. The research's English splice came back with the repeats written out
(insertion run 21, repeat excess 12); this one (3 s at 5.0 s) comes back as the clean text with a 9 s voiced hole
between two word timestamps, and the Urdu loops come back clean with one word stretched over the loop. Hence the
word-timing detectors (long_word, word_gap) next to the text ones.

  case                base        what                                              should trip
  ur_trail_silence6s  shehbaz_02  + 6 s digital silence                             trail_sil, unaligned_tail
  ur_trail_noise6s    shehbaz_02  + 6 s white noise at -50 dBFS RMS                 unaligned_tail
  ur_syllable_loop12  shehbaz_02  the 0.35 s at 3.00 s repeated 12 more times       long_word (ASR swallows it)
  ur_phrase_loop3     shehbaz_02  the 2.5 s at 2.00 s repeated 3 more times         long_word (ASR swallows it)
  ur_truncated60      shehbaz_02  first 60 %                                        cer_nospace, char_ratio, del_run
  ur_gap4s            shehbaz_02  4 s digital silence at the quietest point near 5 s  pause
  en_phrase_loop3     trump_01    the 3 s at 5.00 s repeated 3 more times           word_gap (ASR skips it)
  en_truncated70      trump_01    first 70 %                                        wer, char_ratio, del_run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "qc"))

from tts_qc import paths  # noqa: E402
from tts_qc.audio import read_wav  # noqa: E402

FADE_S = 0.005


def fade_join(parts: list[np.ndarray], sr: int) -> np.ndarray:
    """Concatenate with a short linear crossfade at every joint."""
    n = int(FADE_S * sr)
    out = parts[0].astype(np.float64)
    for p in parts[1:]:
        p = p.astype(np.float64)
        if len(out) >= n and len(p) >= n:
            ramp = np.linspace(0.0, 1.0, n)
            out[-n:] = out[-n:] * (1 - ramp) + p[:n] * ramp
            p = p[n:]
        out = np.concatenate([out, p])
    return np.clip(np.round(out), -32768, 32767).astype(np.int16)


def seg(x: np.ndarray, sr: int, a: float, b: float) -> np.ndarray:
    return x[int(a * sr): int(b * sr)]


def quietest(x: np.ndarray, sr: int, around: float, window: float = 1.0) -> float:
    f = int(0.02 * sr)
    a, b = int((around - window) * sr) // f, int((around + window) * sr) // f
    frames = x[a * f: b * f].astype(np.float64).reshape(-1, f)
    return (a + int(np.argmin((frames ** 2).mean(axis=1)))) * f / sr


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(HERE / "lab" / "synth"))
    ap.add_argument("--manifest-dir", default=str(HERE / "calibration"))
    args = ap.parse_args()
    out_dir, man_dir = Path(args.out_dir), Path(args.manifest_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    man_dir.mkdir(parents=True, exist_ok=True)
    import soundfile as sf

    voices = paths.voices_dir()
    rel = lambda p: str(Path(p).resolve().relative_to(paths.REPO_DIR))   # noqa: E731

    # real clips: the 8 shehbaz clips + trump_01 (texts from clips.json) and both prompt references
    refs = []
    for vid, lang in (("shehbaz", "ur"), ("trump", "en")):
        for c in json.loads((voices / vid / "clips.json").read_text(encoding="utf-8"))["clips"]:
            refs.append({"file": rel(voices / vid / c["file"]), "text": c["text"], "lang": lang, "voice": vid,
                         "case": Path(c["file"]).stem})
        r = json.loads((voices / vid / "references" / "references.json").read_text(encoding="utf-8"))["qwen3-tts"]
        refs.append({"file": rel(voices / vid / "references" / r["file"]), "text": r["text"], "lang": lang,
                     "voice": vid, "case": f"{vid}_prompt_qwen3-tts"})
    (man_dir / "refs_manifest.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in refs),
                                                 encoding="utf-8")

    clips = {c["file"]: c["text"] for v in ("shehbaz", "trump")
             for c in json.loads((voices / v / "clips.json").read_text(encoding="utf-8"))["clips"]}
    ur, ur_sr = read_wav(voices / "shehbaz" / "shehbaz_02.wav")
    en, en_sr = read_wav(voices / "trump" / "trump_01.wav")
    rng = np.random.default_rng(0)
    noise = rng.standard_normal(6 * ur_sr)
    noise = (noise / np.sqrt((noise ** 2).mean()) * 10 ** (-50 / 20) * 32767).astype(np.int16)
    gap_at = quietest(ur, ur_sr, 5.0)
    cases = {
        "ur_trail_silence6s": (ur_sr, [ur, np.zeros(6 * ur_sr, np.int16)], ["trail_sil", "unaligned_tail"]),
        "ur_trail_noise6s": (ur_sr, [ur, noise], ["unaligned_tail"]),
        "ur_syllable_loop12": (ur_sr, [seg(ur, ur_sr, 0, 3.35)] + [seg(ur, ur_sr, 3.0, 3.35)] * 12
                               + [seg(ur, ur_sr, 3.35, 99)], ["long_word"]),
        "ur_phrase_loop3": (ur_sr, [seg(ur, ur_sr, 0, 4.5)] + [seg(ur, ur_sr, 2.0, 4.5)] * 3
                            + [seg(ur, ur_sr, 4.5, 99)], ["long_word"]),
        "ur_truncated60": (ur_sr, [ur[: int(len(ur) * 0.6)]], ["cer_nospace", "char_ratio", "del_run"]),
        "ur_gap4s": (ur_sr, [seg(ur, ur_sr, 0, gap_at), np.zeros(4 * ur_sr, np.int16), seg(ur, ur_sr, gap_at, 99)],
                     ["pause"]),
        "en_phrase_loop3": (en_sr, [seg(en, en_sr, 0, 8.0)] + [seg(en, en_sr, 5.0, 8.0)] * 3
                            + [seg(en, en_sr, 8.0, 99)], ["word_gap"]),
        "en_truncated70": (en_sr, [en[: int(len(en) * 0.7)]], ["wer", "char_ratio", "del_run"]),
    }
    synth = []
    for name, (sr, parts, expect) in cases.items():
        wav = fade_join(parts, sr) if len(parts) > 1 else parts[0]
        path = out_dir / f"{name}.wav"
        sf.write(str(path), wav, sr, subtype="PCM_16")
        ur = name.startswith("ur")
        lang, voice, base = ("ur", "shehbaz", "shehbaz_02.wav") if ur else ("en", "trump", "trump_01.wav")
        synth.append({"file": rel(path), "text": clips[base], "lang": lang, "voice": voice, "case": name,
                      "expect": expect, "duration_s": round(len(wav) / sr, 3)})
        print(f"{name}: {len(wav) / sr:.2f} s -> {path}")
    (man_dir / "synth_manifest.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in synth),
                                                  encoding="utf-8")
    print(f"manifests: {man_dir / 'refs_manifest.jsonl'} ({len(refs)} clips), {man_dir / 'synth_manifest.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
