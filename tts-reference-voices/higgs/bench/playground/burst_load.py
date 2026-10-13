#!/usr/bin/env python3
"""Burst load test for the Higgs gateway (higgs_server.py).

Each burst fires N concurrent requests (N random in [5, 35]); the next burst starts when the whole
burst has finished. Every request gets a text of a random word count in [10, 80].

    python burst_load.py --url http://127.0.0.1:8000 --bursts 100 --seed 0 [--stream] [--prompts-file x.json]

--prompts-file: JSON list of strings (or objects with a "text" field) used as the sentence pool.
Writes <out>/requests.jsonl, <out>/bursts.jsonl, <out>/summary.json.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics as st
import time
from pathlib import Path

import httpx

FALLBACK_SENTENCES = [
    "آج موسم بہت خوشگوار ہے اور ہوا میں ہلکی ٹھنڈک محسوس ہو رہی ہے۔",
    "ہمیں اپنے ملک کی ترقی کے لیے مل جل کر محنت کرنی ہوگی۔",
    "تعلیم ہر بچے کا بنیادی حق ہے اور اس پر کوئی سمجھوتہ نہیں ہونا چاہیے۔",
    "کسانوں کی مدد کے لیے نئی ٹیکنالوجی کا استعمال بہت ضروری ہو چکا ہے۔",
    "بازار میں سبزیوں اور پھلوں کی قیمتیں پچھلے ہفتے کے مقابلے میں کچھ کم ہوئی ہیں۔",
    "براہِ کرم اپنی شکایت درج کروانے کے لیے نمبر دبائیں یا نمائندے سے بات کریں۔",
    "صحت مند زندگی کے لیے روزانہ ورزش اور متوازن خوراک بہت اہم ہے۔",
    "پاکستان کے شمالی علاقوں میں سیاحت کے بے پناہ امکانات موجود ہیں۔",
    "جدید دور میں مصنوعی ذہانت نے بہت سے شعبوں کو بدل کر رکھ دیا ہے۔",
    "ہم آپ کے تعاون کا شکریہ ادا کرتے ہیں اور آپ کی رائے ہمارے لیے قیمتی ہے۔",
    "بارش کی وجہ سے کئی علاقوں میں سڑکیں بند ہیں اور شہریوں کو احتیاط کی ہدایت کی گئی ہے۔",
    "اس منصوبے کا مقصد دیہی علاقوں میں رہنے والے لوگوں تک سہولیات پہنچانا ہے۔",
]


def load_pool(path: Path | None) -> list[str]:
    if not path:
        return FALLBACK_SENTENCES
    items = json.loads(path.read_text(encoding="utf-8"))
    pool = [(i["text"] if isinstance(i, dict) else i).strip() for i in items]
    return [s for s in pool if s]


def make_text(rng: random.Random, pool: list[str], n_words: int) -> str:
    words: list[str] = []
    while len(words) < n_words:
        words += rng.choice(pool).split()
    words = words[:n_words]
    text = " ".join(words)
    return text if text.endswith(("۔", ".", "?", "؟", "!")) else text + "۔"


def wav_seconds(b: bytes) -> float:
    if len(b) < 44 or b[:4] != b"RIFF":
        return 0.0
    ch = int.from_bytes(b[22:24], "little")
    sr = int.from_bytes(b[24:28], "little")
    bits = int.from_bytes(b[34:36], "little")
    return max(0.0, (len(b) - 44) / (sr * ch * bits / 8)) if sr and ch and bits else 0.0


async def one(client: httpx.AsyncClient, url: str, text: str, stream: bool, extra: dict) -> dict:
    t0 = time.perf_counter()
    rec = {"words": len(text.split()), "ok": False, "ttfa": None, "lat": None, "audio_s": 0.0, "err": None}
    try:
        async with client.stream("POST", f"{url}/tts", json={"text": text, "stream": stream, **extra}) as r:
            if r.status_code != 200:
                rec["err"] = f"{r.status_code} {(await r.aread()).decode()[:200]}"
                return rec
            buf = bytearray()
            async for chunk in r.aiter_bytes():
                if rec["ttfa"] is None and chunk:
                    rec["ttfa"] = time.perf_counter() - t0
                buf += chunk
        rec["audio_s"] = wav_seconds(bytes(buf))
        rec["ok"] = rec["audio_s"] > 0
        if not rec["ok"]:
            rec["err"] = "empty audio"
    except Exception as e:  # noqa: BLE001
        rec["err"] = f"{type(e).__name__}: {e}"
    rec["lat"] = time.perf_counter() - t0
    return rec


def pct(v: list[float], p: float) -> float | None:
    if not v:
        return None
    v = sorted(v)
    return v[min(len(v) - 1, round(p / 100 * (len(v) - 1)))]


async def main_async(a: argparse.Namespace) -> None:
    rng = random.Random(a.seed)
    pool = load_pool(a.prompts_file)
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    extra = {k: v for k, v in (("temperature", a.temperature), ("top_p", a.top_p), ("top_k", a.top_k)) if v is not None}
    limits = httpx.Limits(max_connections=a.max_burst + 8)
    all_recs, burst_recs = [], []
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0), limits=limits) as client:
        if a.warmup:
            await asyncio.gather(*[one(client, a.url, make_text(rng, pool, 15), a.stream, extra) for _ in range(a.warmup)])
        t_all = time.perf_counter()
        with open(out / "requests.jsonl", "w", encoding="utf-8") as fr, open(out / "bursts.jsonl", "w") as fb:
            for b in range(a.bursts):
                size = rng.randint(a.min_burst, a.max_burst)
                texts = [make_text(rng, pool, rng.randint(a.min_words, a.max_words)) for _ in range(size)]
                t0 = time.perf_counter()
                recs = await asyncio.gather(*[one(client, a.url, t, a.stream, extra) for t in texts])
                wall = time.perf_counter() - t0
                for i, r in enumerate(recs):
                    r.update(burst=b, idx=i, burst_size=size)
                    fr.write(json.dumps(r, ensure_ascii=False) + "\n")
                ok = [r for r in recs if r["ok"]]
                lat = [r["lat"] for r in ok]
                br = {"burst": b, "size": size, "wall_s": wall, "ok": len(ok), "errors": size - len(ok),
                      "lat_p50": pct(lat, 50), "lat_p90": pct(lat, 90), "audio_s": sum(r["audio_s"] for r in ok),
                      "xrt": sum(r["audio_s"] for r in ok) / wall}
                fb.write(json.dumps(br) + "\n")
                fr.flush(); fb.flush()
                all_recs += recs
                burst_recs.append(br)
                print(f"burst {b + 1:3d}/{a.bursts} size={size:2d} wall={wall:6.1f}s ok={len(ok):2d}/{size} "
                      f"p50={br['lat_p50'] or 0:5.1f}s p90={br['lat_p90'] or 0:5.1f}s xRT={br['xrt']:5.1f}", flush=True)
        total_wall = time.perf_counter() - t_all
    ok = [r for r in all_recs if r["ok"]]
    lat = [r["lat"] for r in ok]
    ttfa = [r["ttfa"] for r in ok if r["ttfa"] is not None]
    summary = {
        "bursts": a.bursts, "requests": len(all_recs), "ok": len(ok), "errors": len(all_recs) - len(ok),
        "stream": a.stream, "seed": a.seed, "words": [a.min_words, a.max_words], "burst_size": [a.min_burst, a.max_burst],
        "total_wall_s": total_wall, "audio_s_total": sum(r["audio_s"] for r in ok),
        "xrt_overall": sum(r["audio_s"] for r in ok) / total_wall,
        "lat_p50": pct(lat, 50), "lat_p90": pct(lat, 90), "lat_p99": pct(lat, 99),
        "ttfa_p50": pct(ttfa, 50), "ttfa_p90": pct(ttfa, 90),
        "burst_wall_mean_s": st.mean(b["wall_s"] for b in burst_recs),
        "error_samples": sorted({r["err"] for r in all_recs if r["err"]})[:5],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--bursts", type=int, default=100)
    ap.add_argument("--min-burst", type=int, default=5)
    ap.add_argument("--max-burst", type=int, default=35)
    ap.add_argument("--min-words", type=int, default=10)
    ap.add_argument("--max-words", type=int, default=80)
    ap.add_argument("--stream", action="store_true")
    ap.add_argument("--seed", type=int, default=None, help="seed for burst sizes and texts (reproducible load)")
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--prompts-file", type=Path, default=None)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--top-p", type=float, default=None)
    ap.add_argument("--top-k", type=int, default=None)
    ap.add_argument("--out", type=Path, default=Path(f"burst_{time.strftime('%Y-%m-%d_%H%M%S')}"))
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()