#!/usr/bin/env python3
"""Pick labelled AI-generated WAV samples from scored Higgs TTS 3 takes (scores.jsonl under a results dir): per voice
the best, typical and worst takes, written to samples/higgs-tts-3/{best,mid,worst}/ with samples.json and a README.

    python higgs/bench/pick_samples.py higgs/results/B0_baseline_flash_attn [--out samples/higgs-tts-3]
                                       [--best 6] [--mid 3] [--worst 4]

Quality score per take: speaker similarity (WavLM-Large vs the prompt clip) minus the recognition error (3 x WER for
English, CER-nospace for Urdu) minus half the pace deviation. best = clean takes (gate passed, not `bad`) with the
highest score, sizes spread, one text per clip; mid = takes closest to the voice's median score; worst = `bad` takes,
one per failure reason, the most extreme first. Texts that read as political or government speech are skipped (the
same keyword filter as server/eval/pick_samples.py: these are voice clones of real politicians). The WAVs already
carry the AI-generated label in their LIST/INFO comment (bench_tts.py); they are copied as they are.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "server" / "eval"))
from pick_samples import POLITICAL  # noqa: E402  (the shared keyword filter)

SIZES = ("short", "medium", "long", "xlong", "xxlong", "prompts")
SIZE_NAME = {"short": "short", "medium": "medium", "long": "long", "xlong": "30s", "prompts": "30s", "xxlong": "60s"}


def political(r: dict) -> bool:
    t = r.get("text") or ""
    return any(k in t for k in POLITICAL)


def score(r: dict) -> float:
    err = 3 * (r.get("wer") or 0) if r.get("lang") == "en" else (r.get("cer_nospace") or 0)
    pace = r.get("pace_ratio") or 1.0
    return (r.get("sim_prompt_large") or 0) - err - 0.5 * abs(pace - 1)


def load(results: Path) -> list[dict]:
    rows = []
    for f in sorted(results.rglob("scores.jsonl")):
        run_dir = f.parent
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            path = run_dir / r["file"] if not Path(r["file"]).is_absolute() else Path(r["file"])
            if not path.is_file() or not r.get("audio_s") or political(r):
                continue
            r["_path"], r["_score"], r["_run"] = path, score(r), run_dir.name
            rows.append(r)
    return rows


def spread(cands: list[dict], n: int, used: set[str]) -> list[dict]:
    """Round-robin over sizes so short and long clips both appear; one text per clip."""
    by_size: dict[str, list[dict]] = {}
    for r in cands:
        by_size.setdefault(r.get("size"), []).append(r)
    picks: list[dict] = []
    while len(picks) < n and any(by_size.values()):
        for size in [s for s in SIZES if s in by_size]:
            while by_size[size]:
                r = by_size[size].pop(0)
                if r["text"] not in used:
                    used.add(r["text"])
                    picks.append(r)
                    break
            if len(picks) >= n:
                break
    return picks


def pick(rows: list[dict], voice: str, best_n: int, mid_n: int, worst_n: int) -> dict[str, list[dict]]:
    mine = [r for r in rows if r.get("voice") == voice]
    used: set[str] = set()
    clean = sorted([r for r in mine if r.get("gate_pass") and not r.get("bad")], key=lambda r: -r["_score"])
    best = spread(clean, best_n, used)
    med = median(r["_score"] for r in mine) if mine else 0.0
    typical = sorted([r for r in mine if r["text"] not in used], key=lambda r: abs(r["_score"] - med))
    mid = spread(typical, mid_n, used)
    worst: list[dict] = []
    seen_reasons: set[str] = set()
    for r in sorted([r for r in mine if r.get("bad")], key=lambda r: r["_score"]):
        reason = (r.get("bad_reasons") or ["?"])[0].split(">")[0].split("<")[0].strip()
        if reason in seen_reasons or r["text"] in used:
            continue
        seen_reasons.add(reason)
        used.add(r["text"])
        worst.append(r)
        if len(worst) >= worst_n:
            break
    return {"best": best, "mid": mid, "worst": worst}


def write(category: str, picks: list[dict], out: Path) -> list[dict]:
    manifest = []
    (out / category).mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(picks, 1):
        name = f"{r['voice']}_{SIZE_NAME.get(r.get('size'), r.get('size'))}_{i:02d}.wav"
        shutil.copyfile(r["_path"], out / category / name)
        manifest.append({
            "file": f"{category}/{name}", "voice": r["voice"], "lang": r.get("lang"), "size": r.get("size"),
            "audio_s": r.get("audio_s"), "text": r.get("text"), "asr_text": r.get("asr_text"),
            "wer": r.get("wer"), "cer_nospace": r.get("cer_nospace"), "sim_large": r.get("sim_prompt_large"),
            "sim_base": r.get("sim_prompt_base"), "pace_ratio": r.get("pace_ratio"), "gate_pass": r.get("gate_pass"),
            "bad": r.get("bad"), "bad_reasons": r.get("bad_reasons"), "score": round(r["_score"], 3),
            "source": {"results": str(r["_path"].parents[2].name), "run": r["_run"], "file": r["file"]}})
    return manifest


README = """# Higgs TTS 3 voice-clone samples (AI-generated)

> **Every file in this folder is AI-generated speech.** It imitates the voices of real people (`trump`: Donald Trump,
> `shehbaz`: Shehbaz Sharif) with Boson AI's Higgs TTS 3 (`bosonai/higgs-tts-3-4b`) voice cloning. **None of it is a
> real recording, and the speakers never said these words:** the texts are the fictional benchmark prompts of this
> repository. Each WAV carries the label in its metadata (LIST/INFO comment). Do not present, cut or redistribute
> these clips as anything other than labelled AI-generated benchmark samples. This audio was created with Boson AI's
> Higgs Audio (https://www.boson.ai/higgs-audio), under its research and non-commercial licence.

Takes from the benchmark in [`higgs/REPORT.md`](../../higgs/REPORT.md) (vLLM-Omni 0.28.0 on one RTX 3090, bf16,
sampling temperature 0.8 / top_k 50), chosen by `higgs/bench/pick_samples.py` from the scored takes of
`{results}`:

- **[best/](best/)**: clean on every automatic check, the highest speaker similarity and lowest recognition error
  for their length (sizes spread from one sentence to ~30 s).
- **[mid/](mid/)**: the takes closest to each voice's median quality: what a typical request sounds like.
- **[worst/](worst/)**: the most extreme failure of each kind the evaluation found (mostly text dropped from ~30 s
  and ~60 s inputs; see the report).

Texts that read as political statements or official announcements were left out. SIM = cosine speaker similarity
to the voice's reference clip (WavLM-Large / WavLM base-plus-sv; real same-speaker recordings score 0.90-0.94 /
>= 0.975, different speakers 0.10-0.18 / 0.75-0.80). Errors are from stock Whisper large-v3 (WER for English,
CER-nospace for Urdu). Pace = seconds per letter / the voice's calibrated pace (1.0 = typical). Every clip's text,
transcript, metrics and source take are in [`samples.json`](samples.json).

"""


def write_readme(manifest: list[dict], out: Path, results: Path) -> None:
    lines = [README.format(results=results)]
    for category in ("best", "mid", "worst"):
        rows = [m for m in manifest if m["file"].startswith(category + "/")]
        if not rows:
            continue
        lines += [f"## {category}", "", "| file | voice | length | SIM Large / base | error | pace | notes | text |",
                  "|---|---|---|---|---|---|---|---|"]
        for m in rows:
            err = f"WER {m['wer']:.3f}" if m["lang"] == "en" else f"CER-ns {m['cer_nospace']:.3f}"
            notes = ", ".join(m["bad_reasons"] or []) if m["bad"] else "clean" if m["gate_pass"] else "gate fail"
            text = (m["text"] or "").replace("|", "/")
            text = text[:110] + ("…" if len(text) > 110 else "")
            lines.append(f"| [{m['file']}]({m['file']}) | {m['voice']} | {m['audio_s']:.1f} s | "
                         f"{m['sim_large']:.2f} / {m['sim_base']:.3f} | {err} | {m['pace_ratio']:.2f} | {notes} | {text} |")
        lines.append("")
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "samples" / "higgs-tts-3")
    ap.add_argument("--best", type=int, default=6)
    ap.add_argument("--mid", type=int, default=3)
    ap.add_argument("--worst", type=int, default=4)
    args = ap.parse_args()
    rows = load(args.results)
    voices = sorted({r["voice"] for r in rows})
    print(f"{len(rows)} scored, non-political takes with audio; voices {voices}")
    if args.out.exists():
        shutil.rmtree(args.out)
    manifest: list[dict] = []
    for category in ("best", "mid", "worst"):
        for voice in voices:
            picks = pick(rows, voice, args.best, args.mid, args.worst)[category]
            manifest += write(category, picks, args.out)
    (args.out / "samples.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    write_readme(manifest, args.out, args.results)
    total = sum((args.out / m["file"]).stat().st_size for m in manifest)
    print(f"{len(manifest)} clips, {total / 1e6:.1f} MB -> {args.out}; ", Counter(m["file"].split("/")[0] for m in manifest))


if __name__ == "__main__":
    main()
