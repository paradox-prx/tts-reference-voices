#!/usr/bin/env python3
"""Pick labelled AI-generated sample clips from the scored benchmark takes: the best, typical and worst takes per voice.

    venvs/gateway/bin/python eval/pick_samples.py [--results results] [--out ../samples/qwen3-tts]
        [--best 10] [--mid 5] [--worst 5]

Pool: every scored vLLM-Omni take with audio (`results/<phase>/takes_all.jsonl` from eval/failure_classes.py; the
qwen-tts baseline P9 and the exploratory 00-06 runs are left out). Quality score per take: speaker similarity
(WavLM-Large, vs the voice's prompt clip) minus the recognition error (3 x WER English, 1 x CER-nospace Urdu, whose
error is mostly accent) minus half the pace deviation.
  best   clean takes (no failure detector fired) with the highest score; one text per clip, sizes spread
         (short, medium, long, ~30 s, ~60 s), the recommended configuration first
  mid    takes whose score is closest to the voice's median, any tier (what a typical request sounds like)
  worst  the most extreme failure of each kind: for Urdu a garbled take, a skipped passage at a normal duration, a
         loop Whisper swallowed, a long voiced gap and a pace outlier; for English wrong-voice takes (speaker
         similarity at cross-speaker level) and pace outliers
Texts that read as political or government speech are skipped (the benchmark prompts are fictional and meant to be
apolitical, but these are voice clones of real politicians). Each clip is written as FLAC with an AI-generated label
in its COMMENT and TITLE tags; samples.json lists every clip's text, metrics, failure reasons and source take."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
LABEL = ("AI-generated speech: a Qwen3-TTS voice clone. Not a real recording of the speaker; the words are fictional "
         "benchmark text.")
SIZES = ("short", "medium", "long", "xlong", "xxlong")
SIZE_NAME = {"short": "short", "medium": "medium", "long": "long", "xlong": "30s", "prompts": "30s", "xxlong": "60s"}
POLITICAL = ("حکومت", "قوم", "پاکستان", "وزیر", "ووٹ", "انتخاب", "بہنو اور بھائیو", "فوج", "افواج", "دشمن", "جنگ",
             "سیاست", "اپوزیشن", "عوام", "اسمبلی", "پارلیمنٹ", "vote", "election", "president", "america", "country",
             "military", "war ", "enemy", "border", "china", "tariff", "government", "democrat", "republican",
             "nation", "congress", "senate",
             # official events narrated as if real (announcements, promises, visits, inaugurations, press): the most
             # misusable texts in a real head of government's voice
             "سرکاری", "اعلامیہ", "ہم وطن", "وعدہ", "افتتاح", "صحافی", "آگ لگی", "announcement", "press",
             # claims about public projects or policy ("the bridge is finished", "equal opportunity for every child")
             "پل مکمل", "برابر موقع", "کام شروع", "منصوب", "پلانٹ", "کسانوں")
# the recommended configuration's runs are preferred for best / mid (Urdu with non_streaming_mode, splitting)
PREFERRED = ("P5_urdu_nsm", "X8_split_nsm", "X6_nsm_long_urdu", "X7_split_60", "P2_matrix", "P3_stream")


def voice_of(r: dict) -> str:
    return (r.get("voice") or "").split("-")[0]


def score(r: dict) -> float:
    ur = voice_of(r) == "shehbaz"
    err = (r.get("cer_nospace") if ur else r.get("wer")) or 0.0
    return (r.get("sim_prompt_large") or 0.0) - (1.0 if ur else 3.0) * err - 0.5 * abs((r.get("pace_ratio") or 1) - 1)


def size_of(r: dict) -> str:
    return "xlong" if r.get("size") == "prompts" else (r.get("size") or "")


def text_key(r: dict) -> str:
    return (r.get("text") or "").strip()[:80]


def political(r: dict) -> bool:
    t = (r.get("text") or "").lower()
    return any(k in t for k in POLITICAL)


def load(results: Path) -> list[dict]:
    rows = []
    for f in sorted(results.glob("*/takes_all.jsonl")):
        phase = f.parent.name
        if phase.startswith(("P9", "_", "0")):
            continue
        for line in f.open():
            r = json.loads(line)
            if not r.get("file") or r.get("sim_prompt_large") is None or political(r):
                continue
            r["_phase"], r["_score"] = phase, score(r)
            rows.append(r)
    return rows


def pick_best(rows: list[dict], voice: str, n: int, used: set[str]) -> list[dict]:
    pool = [r for r in rows if voice_of(r) == voice and r.get("tier") == "clean"]
    pool.sort(key=lambda r: (r["_phase"] not in PREFERRED, -r["_score"]))
    out: list[dict] = []
    while len(out) < n:
        before = len(out)
        for size in SIZES:  # one per size per round
            for r in pool:
                if size_of(r) == size and text_key(r) not in used and r not in out:
                    out.append(r)
                    used.add(text_key(r))
                    break
            if len(out) == n:
                break
        if len(out) == before:
            break
    return out


def pick_mid(rows: list[dict], voice: str, n: int, used: set[str]) -> list[dict]:
    pool = [r for r in rows if voice_of(r) == voice]
    median = statistics.median(r["_score"] for r in pool)
    out = []
    for size in SIZES:
        cands = sorted((r for r in pool if size_of(r) == size and text_key(r) not in used),
                       key=lambda r: (r["_phase"] not in PREFERRED, abs(r["_score"] - median)))
        if cands:
            out.append(cands[0])
            used.add(text_key(cands[0]))
        if len(out) == n:
            break
    for r in out:
        r["_median"] = median
    return out


def pick_worst(rows: list[dict], voice: str, n: int, used: set[str]) -> list[dict]:
    dur = lambda r: r.get("audio_s") or r.get("duration_s") or 0  # noqa: E731
    pool = [r for r in rows if voice_of(r) == voice and 2.0 <= dur(r) <= 90]  # long enough to hear, short to publish
    g = lambda r, k, d=0.0: r.get(k) if isinstance(r.get(k), (int, float)) else d  # noqa: E731
    if voice == "shehbaz":
        kinds = [
            ("garbled speech", lambda r: g(r, "cer_nospace")),
            ("skipped passage at a normal duration", lambda r: g(r, "del_run")
             if 0.85 <= g(r, "pace_ratio", 1) <= 1.15 and g(r, "cer_nospace") < 0.6 else -1),  # not total garble
            ("loop Whisper hears as one long word", lambda r: g(r, "max_word_s") if g(r, "max_word_voiced") > 0.8 else -1),
            ("long voiced gap (filler / babble)", lambda r: g(r, "max_gap_s") if g(r, "max_gap_voiced") > 0.5 else -1),
            ("pace far off (cut short or padded)", lambda r: abs(g(r, "pace_ratio", 1) - 1)),
        ]
    else:
        kinds = [
            ("wrong voice (another speaker)", lambda r: 1 - g(r, "sim_prompt_base", 1) if g(r, "sim_speech_s") >= 3 else -1),
            ("wrong voice (another speaker)", lambda r: 1 - g(r, "sim_prompt_base", 1) if g(r, "sim_speech_s") >= 3 else -1),
            ("wrong voice (another speaker)", lambda r: 1 - g(r, "sim_prompt_base", 1) if g(r, "sim_speech_s") >= 3 else -1),
            ("far too long for its text (padding / drawn out)", lambda r: g(r, "pace_ratio", 1)),
            ("phrase skipped", lambda r: g(r, "del_run") + g(r, "wer")),  # longest run of words Whisper did not hear
        ]
    out, texts = [], set()  # distinct from best/mid texts; worst clips only need distinct full texts among themselves
    for kind, severity in kinds[:n]:
        cands = sorted((r for r in pool if text_key(r) not in used and r["text"] not in texts), key=severity, reverse=True)
        if cands and severity(cands[0]) > 0:
            cands[0]["_kind"] = kind
            out.append(cands[0])
            texts.add(cands[0]["text"])
    return out


def write(category: str, picks: list[dict], results: Path, out_dir: Path) -> list[dict]:
    (out_dir / category).mkdir(parents=True, exist_ok=True)
    manifest, counts = [], {}
    for r in picks:
        voice = voice_of(r)
        size = SIZE_NAME.get(r.get("size"), r.get("size"))
        counts[(voice, size)] = counts.get((voice, size), 0) + 1
        name = f"{voice}_{size}_{counts[(voice, size)]}.flac"
        src = Path(r["file"]) if Path(r["file"]).is_absolute() else results / r["_phase"] / r["file"]
        if not src.exists():  # takes_all.jsonl stores paths relative to the run dir or absolute
            src = next(results.glob(f"{r['_phase']}/**/{Path(r['file']).name}"))
        x, sr = sf.read(src, dtype="int16")
        with sf.SoundFile(out_dir / category / name, "w", samplerate=sr, channels=1, format="FLAC",
                          subtype="PCM_16") as f:
            f.comment = LABEL
            f.title = f"AI-generated {voice} voice clone ({category}, {size})"
            f.write(x)
        manifest.append({
            "category": category, "file": f"{category}/{name}", "voice": voice,
            "language": "ur" if voice == "shehbaz" else "en", "size": size, "seconds": round(len(x) / sr, 2),
            "text": r.get("text"), "failure": r.get("_kind"), "tier": r.get("tier"),
            "tier_reasons": r.get("tier_reasons"), "quality_score": round(r["_score"], 3),
            "sim_wavlm_large": round(r.get("sim_prompt_large") or 0, 3),
            "sim_wavlm_base_plus_sv": round(r.get("sim_prompt_base") or 0, 3),
            "wer": round(r.get("wer") or 0, 3), "cer_nospace": round(r.get("cer_nospace") or 0, 3),
            "char_ratio": round(r.get("char_ratio") or 0, 3), "longest_deletion_run_words": r.get("del_run"),
            "pace_ratio": round(r.get("pace_ratio") or 0, 2), "asr_transcript": r.get("asr_text"),
            "source_run": f"{r['_phase']}/{r.get('run')}", "source_file": str(r["file"]).split("results/")[-1]})
    return manifest


README_HEAD = """# Qwen3-TTS voice-clone samples (AI-generated)

> **Every file in this folder is AI-generated speech.** It imitates the voices of real people (`trump`: Donald Trump,
> `shehbaz`: Shehbaz Sharif) using Qwen/Qwen3-TTS-12Hz-1.7B-Base voice cloning. **None of it is a real recording, and
> the speakers never said these words:** the texts are fictional benchmark prompts of this repository. Each FLAC carries
> the label in its metadata (Vorbis `COMMENT` and `TITLE`). Do not present, cut or redistribute these clips as anything
> other than labelled AI-generated benchmark samples.

Forty takes from the benchmark in [`server/REPORT.md`](../../server/REPORT.md) (vLLM-Omni 0.28.0 on one RTX 3090, bf16,
sampling 0.9 / 50 / repetition_penalty 1.05), chosen by `server/eval/pick_samples.py` from ~4,300 scored takes:

- **[best/](best/)** (10 per voice): clean on every automatic check, the highest speaker similarity and lowest
  recognition error for their length; the recommended configuration's runs first (Urdu with `non_streaming_mode`,
  the ~60 s texts through the gateway's 60-word splitting).
- **[mid/](mid/)** (5 per voice): the takes closest to each voice's median quality: what a typical request sounds like.
- **[worst/](worst/)** (5 per voice): the most extreme failure of each kind the evaluation found. They come from all
  benchmark settings, including ones the recommended configuration avoids (see "run"); with that configuration Urdu
  still fails like this in ~6-8% of takes and English in ~1% (mostly the wrong-voice case).

Texts that read as political statements, official announcements or claims about public projects were left out.
SIM = cosine speaker similarity to the voice's reference clip (WavLM-Large / WavLM base-plus-sv; real same-speaker
recordings score 0.90-0.94 / >= 0.975, different speakers 0.10-0.18 / 0.75-0.80). Errors are from stock Whisper
large-v3; Urdu error is mostly accent (the same Whisper scores this speaker's real recordings at CER-nospace 0.04).
Pace = seconds per letter / the voice's calibrated pace (1.0 = typical). Every clip's text, transcript, metrics and
source take are in [`samples.json`](samples.json).
"""


def write_readme(manifest: list[dict], out_dir: Path) -> None:
    parts = [README_HEAD]
    for cat in ("best", "mid", "worst"):
        rows = [m for m in manifest if m["category"] == cat]
        head = "| file | lang | length | SIM Large / base | error | pace |" + (" what went wrong |" if cat == "worst" else "")
        head += " run |"
        lines = [f"\n## {cat}\n", head, "|" + "---|" * (head.count("|") - 1)]
        for m in rows:
            err = f'WER {m["wer"]:.2f}' if m["language"] == "en" else f'CER-nospace {m["cer_nospace"]:.2f}'
            line = (f'| [{m["file"].split("/")[1]}]({m["file"]}) | {m["language"]} | {m["seconds"]:.1f} s | '
                    f'{m["sim_wavlm_large"]:.2f} / {m["sim_wavlm_base_plus_sv"]:.2f} | {err} | {m["pace_ratio"]:.2f} |')
            if cat == "worst":
                line += f' {m["failure"]} |'
            lines.append(line + f' `{m["source_run"].split("/")[0]}` |')
        parts.append("\n".join(lines))
    parts.append("\n## Texts\n")
    parts += [f'- **{m["file"]}**: {m["text"]}' for m in manifest]
    (out_dir / "README.md").write_text("\n".join(parts) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--out", default=str(ROOT.parent / "samples" / "qwen3-tts"))
    ap.add_argument("--best", type=int, default=10, help="per voice")
    ap.add_argument("--mid", type=int, default=5, help="per voice")
    ap.add_argument("--worst", type=int, default=5, help="per voice")
    a = ap.parse_args()
    results, out_dir = Path(a.results), Path(a.out)
    rows = load(results)
    manifest = []
    for voice in ("trump", "shehbaz"):
        used: set[str] = set()
        manifest += write("best", pick_best(rows, voice, a.best, used), results, out_dir)
        manifest += write("mid", pick_mid(rows, voice, a.mid, used), results, out_dir)
        manifest += write("worst", pick_worst(rows, voice, a.worst, used), results, out_dir)
    (out_dir / "samples.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    write_readme(manifest, out_dir)
    for m in manifest:
        print(f'{m["file"]:28s} {m["seconds"]:6.1f}s q={m["quality_score"]:+.3f} simL={m["sim_wavlm_large"]:.2f} '
              f'simB={m["sim_wavlm_base_plus_sv"]:.2f} wer={m["wer"]:.2f} cer={m["cer_nospace"]:.2f} '
              f'pace={m["pace_ratio"]:.2f} {m["failure"] or ""} [{m["source_run"][:40]}]')


if __name__ == "__main__":
    main()
