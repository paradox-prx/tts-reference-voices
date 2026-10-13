#!/usr/bin/env python3
"""ASR half of the TTS quality evaluation: Whisper large-v3 (faster-whisper) -> normalized WER / CER / CER-nospace,
loop/skip text checks, energy-VAD audio checks, Whisper decode diagnostics, optional language-ID probabilities.

Input: a bench_tts.py results dir (reads requests.jsonl rows that have "file") or a manifest JSONL of
{"file", "text", "lang": "en"|"ur", ...}. Output: <out>.jsonl, one row per take (input row + metrics).

    # GPU (later): float16, 4 CTranslate2 workers sharing one copy of the weights
    LD_LIBRARY_PATH=$(python -c 'import os,nvidia.cublas.lib as l;print(os.path.dirname(l.__file__))') \
      python asr_eval.py --results results/<ts> --device cuda --device-index 1 --compute float16 --workers 4
    # CPU (what was used for the calibration in FINDINGS.md)
    python asr_eval.py --manifest refs.jsonl --device cpu --compute int8 --workers 1 --cpu-threads 8
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import jiwer
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from tts_checks import audio_checks, text_checks, word_timing_checks                      # noqa: E402
from tts_textnorm import UrduNormalizer, nospace, script_fractions     # noqa: E402
from whisper_normalizers import EnglishTextNormalizer                  # noqa: E402  (vendored from openai-whisper)

NORM = {"en": EnglishTextNormalizer(), "ur": UrduNormalizer()}
WHISPER_LANG = {"en": "en", "ur": "ur"}


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path)) as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        a = np.frombuffer(w.readframes(n), dtype={2: np.int16, 4: np.int32}[sw])
    return (a.reshape(-1, ch).mean(axis=1).astype(a.dtype) if ch > 1 else a), sr


def load_rows(args) -> tuple[list[dict], Path]:
    if args.results:
        base = Path(args.results)
        rows = [json.loads(l) for l in open(base / "requests.jsonl", encoding="utf-8")]
        rows = [r for r in rows if r.get("file") and not r.get("error")]
    else:
        base = Path(args.manifest).parent
        rows = [json.loads(l) for l in open(args.manifest, encoding="utf-8")]
    return rows[: args.limit] if args.limit else rows, base


def main() -> None:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--results")
    src.add_argument("--manifest")
    ap.add_argument("--out", default=None)
    ap.add_argument("--model", default="large-v3", help="faster-whisper size or local CT2 dir")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--device-index", type=int, default=0)
    ap.add_argument("--compute", default="float16", help="float16 (GPU default) | int8_float16 | int8 (CPU)")
    ap.add_argument("--workers", type=int, default=4, help="CTranslate2 inter_threads; weights are shared")
    ap.add_argument("--cpu-threads", type=int, default=0)
    ap.add_argument("--beam", type=int, default=5)
    ap.add_argument("--lid", action="store_true", help="also run language ID (first 30 s) and store p(ur), p(hi), p(en)")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    from faster_whisper import WhisperModel
    rows, base = load_rows(args)
    model = WhisperModel(args.model, device=args.device, device_index=args.device_index, compute_type=args.compute,
                         num_workers=args.workers, cpu_threads=args.cpu_threads)

    def one(r: dict) -> dict:
        lang = r.get("lang") or ("ur" if r.get("voice") == "shehbaz" else "en")
        path = base / r["file"] if not Path(r["file"]).is_absolute() else Path(r["file"])
        wav, sr = read_wav(path)
        t0 = time.perf_counter()
        segs, info = model.transcribe(
            str(path), language=WHISPER_LANG[lang], task="transcribe", beam_size=args.beam,
            condition_on_previous_text=False,     # stops one bad window's repetition from seeding the next
            vad_filter=False,                     # score everything; silence is measured by audio_checks instead
            word_timestamps=True)
        segs = list(segs)
        hyp = " ".join(s.text.strip() for s in segs)
        out = {**{k: v for k, v in r.items() if k not in ("resp_headers",)}, "hyp": hyp, "asr_s": 0.0}
        if args.lid:
            from faster_whisper import decode_audio
            audio16 = decode_audio(str(path), sampling_rate=16000)
            _, _, probs = model.detect_language(audio=audio16[: 30 * 16000])
            p = dict(probs or [])
            out.update({"lid_ur": round(p.get("ur", 0), 3), "lid_hi": round(p.get("hi", 0), 3), "lid_en": round(p.get("en", 0), 3)})
        out["asr_s"] = round(time.perf_counter() - t0, 2)
        norm = NORM[lang]
        rn, hn = norm(r["text"]), norm(hyp)
        out.update({
            "ref_norm": rn, "hyp_norm": hn,
            "wer": round(jiwer.wer(rn, hn), 4) if rn else None,
            "cer": round(jiwer.cer(rn, hn), 4) if rn else None,
            "cer_nospace": round(jiwer.cer(nospace(rn), nospace(hn)), 4) if rn else None,
            **{f"t_{k}": v for k, v in text_checks(rn, hn).items() if k not in ("wer",)},
            **{f"a_{k}": v for k, v in audio_checks(wav, sr).items()},
            "hyp_scripts": script_fractions(hyp),
            **{f"w_{k}": v for k, v in word_timing_checks([w for s in segs for w in (s.words or [])], wav, sr).items()},
            "seg_max_cr": round(max((s.compression_ratio for s in segs), default=0.0), 2),
            "seg_fallback": sum(1 for s in segs if (s.temperature or 0) > 0),
            "seg_min_logprob": round(min((s.avg_logprob for s in segs), default=0.0), 3),
            "seg_max_nospeech": round(max((s.no_speech_prob for s in segs), default=0.0), 3),
            # audio after the last recognized word = babble / filler / loop the ASR ignored, or trailing silence
            "unaligned_tail_s": round(len(wav) / sr - max((w.end for s in segs for w in (s.words or [])), default=0.0), 2),
        })
        return out

    out_path = Path(args.out or (base / "asr_eval.jsonl"))
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex, open(out_path, "w", encoding="utf-8") as f:
        for res in ex.map(one, rows):
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
            print(f"{res.get('file')}: wer={res['wer']} cer={res['cer']} cer_ns={res['cer_nospace']} "
                  f"asr={res['asr_s']}s | {res['hyp'][:80]}", flush=True)
    print(f"done {len(rows)} in {time.perf_counter() - t0:.1f}s -> {out_path}")


if __name__ == "__main__":
    main()
