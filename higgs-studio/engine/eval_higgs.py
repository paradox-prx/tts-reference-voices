#!/usr/bin/env python3
"""Standalone Higgs TTS Benchmark & Evaluation Script.

Fires load test bursts against the Higgs TTS endpoint (Gateway on :8000 or vLLM-Omni on :8016),
saves all synthesized .wav audio files directly to the results folder, and outputs percentile latency tables.
"""

import argparse
import asyncio
import base64
import json
import random
import statistics as st
import time
from pathlib import Path
import httpx

# Default Target URL set directly to vLLM-Omni Engine on 8016
DEFAULT_URL = "http://127.0.0.1:8016"

# Default reference voice files for Higgs voice cloning on port 8016
DEFAULT_REF_AUDIO = "/home/vector/Documents/abdullah_workspace/qwen-server/tts-reference-voices/voices/shehbaz/references/higgs-v3-25s.wav"
DEFAULT_REF_TEXT = "آج موسم بہت خوشگوار ہے اور ہوا میں ہلکی ٹھنڈک محسوس ہو رہی ہے۔"

# Urdu prompts containing Higgs expression & inline control tags (<|sfx:...|>, <|emotion:...|>, <|prosody:pause|>)
FALLBACK_SENTENCES = [
    "<|emotion:excited|>آج موسم بہت خوشگوار ہے <|sfx:laughter|>ہیہی! اور ہوا میں ہلکی ٹھنڈک محسوس ہو رہی ہے۔",
    "ہمیں اپنے ملک کی ترقی کے لیے مل جل کر محنت کرنی ہوگی۔ <|prosody:pause|> یہ بات بہت اہم ہے۔",
    "<|emotion:sadness|>تعلیم ہر بچے کا بنیادی حق ہے اور اس پر کوئی سمجھوتہ نہیں ہونا چاہیے۔",
    "کسانوں کی مدد کے لیے نئی ٹیکنالوجی کا استعمال بہت ضروری ہو چکا ہے۔ <|sfx:sigh|>اہہ، لیکن اس میں کچھ وقت لگے گا۔",
    "بازار میں سبزیوں اور پھلوں کی قیمتیں پچھلے ہفتے کے مقابلے میں کچھ کم ہوئی ہیں۔",
    "براہِ کرم اپنی شکایت درج کروانے کے لیے نمبر دبائیں <|prosody:pause|> یا نمائندے سے بات کریں۔",
    "<|emotion:happy|>صحت مند زندگی کے لیے روزانہ ورزش اور متوازن خوراک بہت اہم ہے! <|sfx:laughter|>ہا ہا!",
    "پاکستان کے شمالی علاقوں میں سیاحت کے بے پناہ امکانات موجود ہیں۔",
    "جدید دور میں مصنوعی ذہانت نے بہت سے شعبوں کو بدل کر رکھ دیا ہے۔ <|sfx:sniff|>یہ ایک حیران کن تبدیلی ہے۔",
    "ہم آپ کے تعاون کا شکریہ ادا کرتے ہیں <|emotion:happy|>اور آپ کی رائے ہمارے لیے انتہائی قیمتی ہے۔",
]

PCTS = (50, 90, 95, 99)


def make_text(rng: random.Random, pool: list[str], n_words: int) -> str:
    """Generate sample text of specified word count while preserving inline expression tags."""
    words: list[str] = []
    while len(words) < n_words:
        words += rng.choice(pool).split()
    words = words[:n_words]
    text = " ".join(words)
    return text if text.endswith(("۔", ".", "?", "؟", "!")) else text + "۔"


def wav_seconds(b: bytes) -> float:
    """Parse RIFF WAV header to compute audio duration in seconds."""
    if len(b) < 44 or b[:4] != b"RIFF":
        return 0.0
    ch = int.from_bytes(b[22:24], "little")
    sr = int.from_bytes(b[24:28], "little")
    bits = int.from_bytes(b[34:36], "little")
    return max(0.0, (len(b) - 44) / (sr * ch * bits / 8)) if sr and ch and bits else 0.0


def pct(v: list[float], p: float) -> float | None:
    """Calculate percentile p from list of values."""
    if not v:
        return None
    v = sorted(v)
    return v[min(len(v) - 1, round(p / 100 * (len(v) - 1)))]


def bucket(x: int, width: int, lo: int) -> str:
    """Bucket integer x into ranges of specified width."""
    a = lo + (x - lo) // width * width
    return f"{a}-{a + width - 1}"


async def send_request(
    client: httpx.AsyncClient,
    url: str,
    text: str,
    model_name: str,
    audio_dir: Path,
    req_id: str,
    ref_audio_b64: str | None = None,
    ref_text: str | None = None
) -> dict:
    """Send a single TTS request, measure performance, and write WAV file to disk."""
    t0 = time.perf_counter()
    rec = {"words": len(text.split()), "ok": False, "ttfa": None, "lat": None, "audio_s": 0.0, "err": None}
    
    clean_url = url.rstrip('/')
    if clean_url.endswith(":8000"):
        endpoint = f"{clean_url}/tts"
        payload = {
            "text": text,
            "voice": "default"
        }
    else:
        endpoint = f"{clean_url}/v1/audio/speech"
        payload = {
            "model": model_name,
            "input": text,
            "voice": "default",
            "response_format": "wav"
        }
        if ref_audio_b64 and ref_text:
            payload["ref_audio"] = f"data:audio/wav;base64,{ref_audio_b64}"
            payload["ref_text"] = ref_text

    try:
        async with client.stream("POST", endpoint, json=payload) as r:
            if r.status_code != 200:
                err_text = (await r.aread()).decode()[:200]
                rec["err"] = f"HTTP {r.status_code}: {err_text}"
                rec["lat"] = time.perf_counter() - t0
                print(f"\n[REQUEST ERROR] {rec['err']}")  # Print error immediately to console
                return rec
            
            buf = bytearray()
            async for chunk in r.aiter_bytes():
                if rec["ttfa"] is None and chunk:
                    rec["ttfa"] = time.perf_counter() - t0
                buf += chunk
                
        rec["audio_s"] = wav_seconds(bytes(buf))
        rec["ok"] = rec["audio_s"] > 0
        
        # Write binary WAV file to results directory
        if rec["ok"]:
            wav_path = audio_dir / f"{req_id}.wav"
            wav_path.write_bytes(bytes(buf))
        else:
            rec["err"] = "empty audio or invalid WAV header"

    except Exception as e:
        rec["err"] = f"{type(e).__name__}: {e}"
        print(f"\n[EXCEPTION ERROR] {rec['err']}")
        
    rec["lat"] = time.perf_counter() - t0
    return rec


def compute_stats(rows: list[dict]) -> dict:
    """Compute summary statistics for latency and TTFA metrics."""
    ok = [r for r in rows if r["ok"]]
    out = {
        "requests": len(rows),
        "ok": len(ok),
        "errors": len(rows) - len(ok),
        "audio_s_mean": st.mean(r["audio_s"] for r in ok) if ok else 0.0,
    }
    for metric_key, metric_name in (("lat", "latency"), ("ttfa", "ttfa")):
        vals = [r[metric_key] for r in ok if r.get(metric_key) is not None]
        for p in PCTS:
            out[f"{metric_name}_p{p}"] = pct(vals, p)
    return out


def print_md_table(title: str, label_header: str, groups: dict[str, list[dict]]) -> None:
    """Print formatted Markdown percentile tables."""
    print(f"\n### {title}")
    cols = [label_header, "requests", "errors", "audio_s_mean", "lat_p50", "lat_p90", "lat_p95", "lat_p99", "ttfa_p50", "ttfa_p90"]
    print(" | ".join(cols))
    print(" | ".join("---" for _ in cols))

    sorted_keys = sorted(groups.keys(), key=lambda k: int(k.split("-")[0]) if "-" in k else 0)
    for k in sorted_keys:
        st_data = compute_stats(groups[k])
        row = [
            k,
            str(st_data["requests"]),
            str(st_data["errors"]),
            f"{st_data['audio_s_mean']:.2f}s",
            f"{st_data['latency_p50'] or 0:.3f}s",
            f"{st_data['latency_p90'] or 0:.3f}s",
            f"{st_data['latency_p95'] or 0:.3f}s",
            f"{st_data['latency_p99'] or 0:.3f}s",
            f"{st_data['ttfa_p50'] or 0:.3f}s",
            f"{st_data['ttfa_p90'] or 0:.3f}s",
        ]
        print(" | ".join(row))


async def run_benchmark(a: argparse.Namespace) -> None:
    rng = random.Random(a.seed)
    out_dir = Path(a.out)
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    ref_audio_b64 = None
    if a.ref_audio and Path(a.ref_audio).exists():
        ref_audio_b64 = base64.b64encode(Path(a.ref_audio).read_bytes()).decode("utf-8")
        print(f"Loaded Reference Audio: {a.ref_audio}")
    else:
        print("Warning: No valid reference audio file found/provided.")

    limits = httpx.Limits(max_connections=a.max_burst + 20)
    all_recs = []

    print(f"Target Endpoint: {a.url}")
    print(f"Audio Output Folder: {audio_dir.resolve()}")
    print(f"Benchmark Config: {a.bursts} bursts | burst size {a.min_burst}-{a.max_burst} | text words {a.min_words}-{a.max_words}\n")

    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0), limits=limits) as client:
        t_start = time.perf_counter()

        for b in range(a.bursts):
            size = rng.randint(a.min_burst, a.max_burst)
            texts = [make_text(rng, FALLBACK_SENTENCES, rng.randint(a.min_words, a.max_words)) for _ in range(size)]

            t0 = time.perf_counter()
            tasks = [
                send_request(
                    client,
                    a.url,
                    t,
                    a.model,
                    audio_dir,
                    req_id=f"sample_b{b:03d}_i{i:02d}",
                    ref_audio_b64=ref_audio_b64,
                    ref_text=a.ref_text
                )
                for i, t in enumerate(texts)
            ]
            recs = await asyncio.gather(*tasks)
            wall = time.perf_counter() - t0

            for i, r in enumerate(recs):
                r.update({"burst": b, "idx": i, "burst_size": size})
                all_recs.append(r)

            ok_count = sum(1 for r in recs if r["ok"])
            lats = [r["lat"] for r in recs if r["ok"]]
            p50 = pct(lats, 50) or 0.0
            p90 = pct(lats, 90) or 0.0
            audio_total = sum(r["audio_s"] for r in recs if r["ok"])
            xrt = audio_total / wall if wall > 0 else 0.0

            print(f"burst {b + 1:3d}/{a.bursts} | size={size:2d} | wall={wall:5.1f}s | ok={ok_count:2d}/{size:2d} | p50={p50:5.2f}s | p90={p90:5.2f}s | xRT={xrt:4.1f}x")

        total_wall = time.perf_counter() - t_start

    # Groupings for analysis
    by_words: dict[str, list] = {}
    by_burst: dict[str, list] = {}
    for r in all_recs:
        by_words.setdefault(bucket(r["words"], 10, 10), []).append(r)
        by_burst.setdefault(bucket(r["burst_size"], 5, 5), []).append(r)

    print("\n" + "=" * 80)
    print(f"EVALUATION COMPLETED IN {total_wall:.1f}s")
    print(f"Total Requests: {len(all_recs)} | Successful: {sum(1 for r in all_recs if r['ok'])} | Failed: {sum(1 for r in all_recs if not r['ok'])}")
    print("=" * 80)

    # Print Percentile Tables
    print_md_table("Latency & TTFA by Word Count Buckets", "Words Bucket", by_words)
    print_md_table("Latency & TTFA by Burst Size Buckets", "Burst Size Bucket", by_burst)

    # Save summary metadata
    overall_stats = compute_stats(all_recs)
    overall_stats["total_wall_s"] = total_wall
    overall_stats["audio_dir"] = str(audio_dir.resolve())
    (out_dir / "summary.json").write_text(json.dumps(overall_stats, indent=2), encoding="utf-8")
    
    print(f"\nSaved summary JSON to: {out_dir / 'summary.json'}")
    print(f"Saved {sum(1 for r in all_recs if r['ok'])} `.wav` audio files to: {audio_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone Higgs TTS Benchmark Script with Audio Saving")
    parser.add_argument("--url", default=DEFAULT_URL, help="Target URL (default: http://127.0.0.1:8016)")
    parser.add_argument("--model", default="higgs-tts-3-4b", help="Engine model identifier")
    parser.add_argument("--ref-audio", default=DEFAULT_REF_AUDIO, help="Path to reference audio file (.wav)")
    parser.add_argument("--ref-text", default=DEFAULT_REF_TEXT, help="Reference transcript for voice cloning")
    parser.add_argument("--bursts", type=int, default=100, help="Number of bursts")
    parser.add_argument("--min-burst", type=int, default=5, help="Minimum burst size")
    parser.add_argument("--max-burst", type=int, default=35, help="Maximum burst size")
    parser.add_argument("--min-words", type=int, default=10, help="Minimum words per prompt")
    parser.add_argument("--max-words", type=int, default=80, help="Maximum words per prompt")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--out", default=f"results/eval_{time.strftime('%Y%m%d_%H%M%S')}", help="Output directory")

    args = parser.parse_args()
    asyncio.run(run_benchmark(args))


if __name__ == "__main__":
    main()