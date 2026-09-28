#!/usr/bin/env python3
"""Benchmark a Qwen3-TTS voice-clone server (vLLM-Omni's OpenAI-compatible /v1/audio/speech, or anything that
speaks the same request shape) under concurrency, across text lengths, with streaming latency.

    python bench/bench_tts.py --voice shehbaz --size short -n 32 -c 8
    python bench/bench_tts.py --voice trump --size medium --sweep 1,2,4,8,16,32
    python bench/bench_tts.py --voice shehbaz --stream --size long --sweep 1,4,8
    python bench/bench_tts.py --voice trump --matrix                  # every size x the default sweep
    python bench/bench_tts.py --voice shehbaz --param repetition_penalty=1.15 --size xlong -n 43 -c 8
    python bench/bench_tts.py --voice shehbaz --size xlong -n 43 --takes 4 --seed 1000 -c 16   # 4 seeded takes per text
    python bench/bench_tts.py --voice shehbaz --pools bench/pools/auralis_ur.json --size short medium long -n 20 -c 20

Per request: total latency, time to first audio (--stream), audio seconds (from the returned bytes), RTF,
seconds per word, token counts from x-vllm-omni-* headers, and a `suspect` flag when the audio is far too short
(skipped text) or too long (loop / padding) for the word count. Per run: latency and TTFA percentiles, wall time,
throughput (audio seconds per wall second), req/s, error and suspect counts, peak GPU memory and mean utilisation.

Texts come from bench/pools/<lang>.json. A run never repeats a string while the pool is large enough, and each
run continues where the previous one stopped, so numbers reflect real generation work rather than cache hits.
Voices come from voices/<id>/: the Qwen reference (references/qwen3-tts.wav) and its transcript (references.json).

Outputs go to results/<timestamp>/: requests.jsonl (every request), summary.csv and summary.md (one row per
run), and audio/<run>/*.wav unless --no-audio. Saved audio is rewritten as a clean RIFF file (streamed headers carry
bogus sizes) with a LIST/INFO comment marking it AI-generated; results/ is gitignored and must not be published.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import datetime as dt
import json
import os
import statistics
import struct
import subprocess
import threading
import time
from pathlib import Path

import httpx

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

REPO = Path(__file__).resolve().parents[1]
SIZES = ("short", "medium", "long", "xlong")
DEFAULT_SWEEP = (1, 2, 4, 8, 16, 32)
# seconds of audio per word outside this band = audio doesn't match the text (skipped words, or a loop / padding)
SPW_BAND = {"en": (0.18, 0.9), "ur": (0.18, 1.1)}
TIMEOUT = {"short": 120.0, "medium": 180.0, "long": 300.0, "xlong": 420.0}
AI_LABEL = "AI-generated speech (Qwen3-TTS voice clone benchmark). Not a real recording of the speaker. Do not publish."


def now_label() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


# ------------------------------------------------------------------------------------------------ audio length

def wav_header_len(data: bytes) -> int | None:
    """Offset of the first PCM byte (after the data chunk header), or None while the header is still incomplete."""
    i = data.find(b"data", 12)
    return i + 8 if i >= 0 and len(data) >= i + 8 else None


def wav_pcm(data: bytes) -> tuple[bytes, int, int, int]:
    """(pcm bytes, sample rate, channels, sample width) of a WAV payload, tolerant of streamed size fields."""
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("not a WAV payload")
    pos, sr, ch, width = 12, None, None, None
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        body = pos + 8
        if cid == b"fmt ":
            ch, sr = struct.unpack("<HI", data[body + 2:body + 8])
            width = struct.unpack("<H", data[body + 14:body + 16])[0] // 8
        elif cid == b"data":
            end = len(data) if size in (0, 0xFFFFFFFF) or body + size > len(data) else body + size
            if not (sr and ch and width):
                raise ValueError("WAV data chunk before fmt chunk")
            pcm = data[body:end]
            return pcm[:len(pcm) - len(pcm) % (ch * width)], sr, ch, width
        pos = body + size + (size & 1)
    raise ValueError("no data chunk in WAV payload")


def labelled_wav(pcm: bytes, sr: int, ch: int = 1, width: int = 2, comment: str = AI_LABEL) -> bytes:
    """A clean RIFF/WAVE file with a LIST/INFO chunk (ICMT comment, ISFT software) ahead of the data chunk."""
    def sub(cid: bytes, text: str) -> bytes:
        b = text.encode("utf-8") + b"\0"
        b += b"\0" * (len(b) & 1)
        return cid + struct.pack("<I", len(b)) + b
    info = b"INFO" + sub(b"ICMT", comment) + sub(b"ISFT", "tts-reference-voices/bench/bench_tts.py")
    fmt = struct.pack("<HHIIHH", 1, ch, sr, sr * ch * width, ch * width, width * 8)
    body = (b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"LIST" + struct.pack("<I", len(info)) + info
            + b"data" + struct.pack("<I", len(pcm)) + pcm + b"\0" * (len(pcm) & 1))
    return b"RIFF" + struct.pack("<I", len(body)) + body


# ------------------------------------------------------------------------------------------------ GPU sampling

class GpuMonitor:
    """nvidia-smi every 500 ms on the selected GPUs; per run: peak memory (MiB, summed over those GPUs, including any
    other tenant's memory on them) and mean utilisation."""

    def __init__(self, gpus: str | None = None) -> None:
        self.samples: list[tuple[float, float]] = []
        self.proc, self.pending = None, {}
        cmd = ["nvidia-smi", "--query-gpu=index,memory.used,utilization.gpu", "--format=csv,noheader,nounits", "-lms", "500"]
        if gpus:
            cmd.insert(1, f"--id={gpus}")
        self.n_gpus = len(gpus.split(",")) if gpus else None
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        except FileNotFoundError:
            return
        self.lock = threading.Lock()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        # one line per GPU per tick; a tick is complete when a GPU index repeats
        for line in self.proc.stdout:
            try:
                idx, mem, util = (float(x) for x in line.strip().split(","))
            except ValueError:
                continue
            if idx in self.pending or (self.n_gpus and len(self.pending) == self.n_gpus):
                tick, self.pending = self.pending, {}
                with self.lock:
                    self.samples.append((sum(m for m, _ in tick.values()), statistics.mean(u for _, u in tick.values())))
            self.pending[idx] = (mem, util)

    def mark(self) -> int:
        return len(self.samples) if self.proc else 0

    def since(self, mark: int) -> dict:
        if not self.proc:
            return {"gpu_mem_peak_mib": None, "gpu_util_mean": None}
        with self.lock:
            s = self.samples[mark:]
        if not s:
            return {"gpu_mem_peak_mib": None, "gpu_util_mean": None}
        return {"gpu_mem_peak_mib": round(max(m for m, _ in s)), "gpu_util_mean": round(statistics.mean(u for _, u in s), 1)}

    def stop(self) -> None:
        if self.proc:
            self.proc.terminate()


# ------------------------------------------------------------------------------------------------ requests

class Voice:
    def __init__(self, voice_id: str) -> None:
        folder = REPO / "voices" / voice_id
        refs = json.loads((folder / "references" / "references.json").read_text(encoding="utf-8"))["qwen3-tts"]
        meta = json.loads((folder / "voice.json").read_text(encoding="utf-8"))
        self.id, self.lang = voice_id, meta.get("language", "en")
        self.ref_path = folder / "references" / refs["file"]
        self.ref_text = refs["text"]
        self.ref_b64 = "data:audio/wav;base64," + base64.b64encode(self.ref_path.read_bytes()).decode()


def build_payload(args, voice: Voice, text: str, seed: int | None = None) -> dict:
    p = {"input": text, "task_type": "Base", "language": args.language or ("English" if voice.lang == "en" else "Auto"),
         "response_format": args.format}
    if args.voice_mode == "upload":
        p["voice"] = args.voice_name or f"bench-{voice.id}"
    else:
        p["ref_audio"], p["ref_text"] = voice.ref_b64, voice.ref_text
    if args.stream:
        p["stream"], p["stream_format"] = True, "audio"
    p.update(args.params)
    if seed is not None:
        p["seed"] = seed
    return p


async def one_request(client: httpx.AsyncClient, url: str, payload: dict, timeout: float, fmt: str = "wav",
                      headers: dict | None = None) -> dict:
    """ttfb = first response byte; ttfa = first byte of audio samples (past the WAV header, if any)."""
    t0 = time.perf_counter()
    ttfb, ttfa, chunks, status, rh, err, got = None, None, [], None, {}, None, 0
    try:
        async with client.stream("POST", url, json=payload, timeout=timeout, headers=headers) as r:
            status, rh = r.status_code, dict(r.headers)
            if status != 200:
                body = (await r.aread()).decode("utf-8", "replace")
                err = f"HTTP {status}: {body[:200]}"
            else:
                async for chunk in r.aiter_bytes():
                    if not chunk:
                        continue
                    now = time.perf_counter() - t0
                    chunks.append(chunk)
                    got += len(chunk)
                    if ttfb is None:
                        ttfb = now
                    if ttfa is None:
                        if fmt != "wav":
                            ttfa = now
                        else:
                            head = b"".join(chunks) if len(chunks) > 1 else chunk
                            hl = wav_header_len(head[:4096])
                            if hl is not None and got > hl:
                                ttfa = now
    except Exception as exc:                                  # noqa: BLE001 - every failure is a result
        err = f"{type(exc).__name__}: {exc}"
    return {"latency": time.perf_counter() - t0, "ttfb": ttfb, "ttfa": ttfa, "status": status, "error": err,
            "data": b"".join(chunks), "headers": rh}


async def register_voice(client: httpx.AsyncClient, args, voice: Voice) -> None:
    name = args.voice_name or f"bench-{voice.id}"
    files = {"audio_sample": (voice.ref_path.name, voice.ref_path.read_bytes(), "audio/wav")}
    data = {"name": name, "ref_text": voice.ref_text, "consent": args.consent}
    r = await client.post(args.url.rstrip("/") + "/v1/audio/voices", files=files, data=data, timeout=120.0,
                          headers=args.auth)
    print(f"voice upload {name!r}: HTTP {r.status_code} {r.text[:160]}")
    r.raise_for_status()


# ------------------------------------------------------------------------------------------------ runs

def pct(xs: list[float], p: float):
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))], 3)


async def run_one(client, args, voice, pool, cursor, size, n, c, gpu, out_dir) -> tuple[dict, int]:
    """n distinct texts from the pool (continuing at cursor), each sent --takes times; c requests in flight."""
    texts = [pool[(cursor + i) % len(pool)] for i in range(n)]
    if n > len(pool):
        print(f"  note: {n} requests > {len(pool)} {size} texts, so some repeat within this run")
    jobs = [(i, k) for i in range(n) for k in range(args.takes)]
    url = args.url.rstrip("/") + "/v1/audio/speech"
    run = (f"{args.tag + '_' if args.tag else ''}{voice.id}_{size}_c{c}_n{n}"
           f"{f'_k{args.takes}' if args.takes > 1 else ''}{'_stream' if args.stream else ''}")
    audio_dir = None if args.no_audio else out_dir / "audio" / run
    if audio_dir:
        audio_dir.mkdir(parents=True, exist_ok=True)
    lo, hi = SPW_BAND.get(voice.lang, SPW_BAND["en"])
    timeout = args.timeout or TIMEOUT[size] * max(1.0, c / 16)
    sem, rows = asyncio.Semaphore(c), []

    async def guarded(i: int, k: int) -> None:
        seed = None if args.seed is None else args.seed + (cursor + i) * 100 + k
        async with sem:
            res = await one_request(client, url, build_payload(args, voice, texts[i], seed), timeout, args.format,
                                    args.auth)
        words = len(texts[i].split())
        row = {"run": run, "tag": args.tag, "voice": voice.id, "lang": voice.lang, "size": size, "c": c, "idx": i,
               "take": k, "seed": seed, "words": words, "chars": len(texts[i]),
               "latency": round(res["latency"], 3),
               "ttfb": round(res["ttfb"], 3) if res["ttfb"] is not None and args.stream else None,
               "ttfa": round(res["ttfa"], 3) if res["ttfa"] is not None and args.stream else None,
               "status": res["status"], "error": res["error"], "bytes": len(res["data"]),
               "out_tokens": res["headers"].get("x-vllm-omni-output-tokens"),
               "resp_headers": {h: v for h, v in res["headers"].items() if h.startswith("x-")},
               "params": args.params, "text": texts[i]}
        if not res["error"]:
            try:
                if args.format == "wav":
                    pcm, sr, ch, width = wav_pcm(res["data"])
                elif args.format == "pcm":
                    pcm, sr, ch, width = res["data"], args.pcm_rate, 1, 2
                else:
                    pcm = None
                secs = len(pcm) / (sr * ch * width) if pcm is not None else float("nan")
            except ValueError as exc:
                row["error"], secs, pcm = f"bad audio: {exc}", 0.0, None
            row["audio_s"] = round(secs, 3)
            row["rtf"] = round(res["latency"] / secs, 3) if secs else None
            row["s_per_word"] = round(secs / words, 3) if secs else None
            row["suspect"] = bool(secs) and not (lo <= secs / words <= hi)
            if audio_dir and pcm is not None:
                name = f"{i:03d}{f'_t{k}' if args.takes > 1 else ''}.wav"
                (audio_dir / name).write_bytes(labelled_wav(pcm, sr, ch, width))
                row["file"] = str((audio_dir / name).relative_to(out_dir))
        rows.append(row)

    mark = gpu.mark()
    t0 = time.perf_counter()
    await asyncio.gather(*[guarded(i, k) for i, k in jobs])
    wall = time.perf_counter() - t0

    ok = [r for r in rows if not r["error"]]
    lat = [r["latency"] for r in ok]
    ttfa = [r["ttfa"] for r in ok if r["ttfa"] is not None]
    audio = sum(r.get("audio_s") or 0 for r in ok)
    retries = [int(r["resp_headers"].get("x-tts-retries", 0) or 0) for r in ok]
    summary = {"run": run, "tag": args.tag, "voice": voice.id, "size": size, "c": c, "n": len(jobs),
               "stream": args.stream, "ok": len(ok), "errors": len(jobs) - len(ok),
               "suspect": sum(bool(r.get("suspect")) for r in ok),
               "retried": sum(1 for x in retries if x), "wall_s": round(wall, 2),
               "lat_mean": round(statistics.mean(lat), 3) if lat else None, "lat_p50": pct(lat, 50),
               "lat_p90": pct(lat, 90), "lat_p95": pct(lat, 95), "lat_p99": pct(lat, 99),
               "lat_max": round(max(lat), 3) if lat else None,
               "ttfa_p50": pct(ttfa, 50), "ttfa_p90": pct(ttfa, 90), "ttfa_p99": pct(ttfa, 99),
               "audio_s": round(audio, 1), "throughput_x_realtime": round(audio / wall, 2) if wall else None,
               "req_per_s": round(len(ok) / wall, 2) if wall else None,
               "rtf_p50": pct([r["rtf"] for r in ok if r.get("rtf")], 50),
               "rtf_p90": pct([r["rtf"] for r in ok if r.get("rtf")], 90),
               "mean_words": round(statistics.mean(r["words"] for r in rows), 1), **gpu.since(mark)}
    with open(out_dir / "requests.jsonl", "a", encoding="utf-8") as f:
        for r in sorted(rows, key=lambda r: (r["idx"], r["take"])):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    t = f" ttfa p50={summary['ttfa_p50']}s p90={summary['ttfa_p90']}s |" if args.stream else ""
    print(f"  {run}: ok {summary['ok']}/{len(jobs)} err {summary['errors']} suspect {summary['suspect']} | "
          f"lat p50={summary['lat_p50']}s p90={summary['lat_p90']}s p99={summary['lat_p99']}s |{t} "
          f"{summary['throughput_x_realtime']}x realtime, {summary['req_per_s']} req/s | "
          f"gpu {summary['gpu_mem_peak_mib']} MiB {summary['gpu_util_mean']}%", flush=True)
    for r in [r for r in rows if r["error"]][:3]:
        print(f"    ERR[{r['idx']}] {r['error']}")
    return summary, cursor + n


SUMMARY_COLS = ["run", "tag", "voice", "size", "c", "n", "stream", "ok", "errors", "suspect", "retried", "wall_s",
                "lat_mean", "lat_p50", "lat_p90", "lat_p95", "lat_p99", "lat_max", "ttfa_p50", "ttfa_p90", "ttfa_p99",
                "audio_s", "throughput_x_realtime", "req_per_s", "rtf_p50", "rtf_p90", "mean_words",
                "gpu_mem_peak_mib", "gpu_util_mean"]


def write_tables(out_dir: Path, summaries: list[dict]) -> None:
    with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_COLS)
        w.writeheader()
        w.writerows(summaries)
    md = ["| tag | voice | size | c | n | ok | err | suspect | lat p50 | lat p90 | lat p99 | TTFA p50 | TTFA p90 | x realtime | req/s | GPU MiB | GPU % |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        md.append("| " + " | ".join(str(s[k]) if s[k] not in (None, "") else "–" for k in (
            "tag", "voice", "size", "c", "n", "ok", "errors", "suspect", "lat_p50", "lat_p90", "lat_p99", "ttfa_p50",
            "ttfa_p90", "throughput_x_realtime", "req_per_s", "gpu_mem_peak_mib", "gpu_util_mean")) + " |")
    (out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def parse_param(s: str):
    k, _, v = s.partition("=")
    try:
        return k, json.loads(v)
    except json.JSONDecodeError:
        return k, v


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8091", help="server base URL")
    ap.add_argument("--voice", nargs="+", default=["shehbaz"], help="voice id(s) from voices/")
    ap.add_argument("--size", nargs="+", choices=SIZES, default=["short"])
    ap.add_argument("-n", type=int, default=None, help="requests per run (default: max(8, 2 x concurrency))")
    ap.add_argument("-c", type=int, default=8, help="concurrency (ignored with --sweep)")
    ap.add_argument("--sweep", default=None, help="comma-separated concurrencies, e.g. 1,2,4,8,16,32")
    ap.add_argument("--matrix", action="store_true", help=f"every size x sweep {','.join(map(str, DEFAULT_SWEEP))}")
    ap.add_argument("--stream", action="store_true", help="stream=true, stream_format=audio; measures time to first audio")
    ap.add_argument("--format", choices=["wav", "pcm", "flac", "mp3", "opus"], default="wav")
    ap.add_argument("--pcm-rate", type=int, default=24000, help="sample rate of --format pcm (s16 mono)")
    ap.add_argument("--language", default=None, help="override (default: English for en voices, Auto for ur)")
    ap.add_argument("--voice-mode", choices=["inline", "upload"], default="inline",
                    help="inline: ref_audio + ref_text in every request; upload: POST /v1/audio/voices once, then voice=<name>")
    ap.add_argument("--voice-name", default=None)
    ap.add_argument("--consent", default="benchmark", help="consent id for POST /v1/audio/voices")
    ap.add_argument("--param", action="append", default=[], metavar="K=V",
                    help="extra request field, JSON value (e.g. temperature=0.9 top_k=50 repetition_penalty=1.05)")
    ap.add_argument("--pools", type=Path, default=None,
                    help="custom pools JSON {short|medium|long|xlong: [texts]} instead of bench/pools/<lang>.json "
                         "(e.g. an existing benchmark's sentence lists, for an apples-to-apples comparison)")
    ap.add_argument("--takes", type=int, default=1, help="requests per distinct text (independent takes), for failure rates")
    ap.add_argument("--seed", type=int, default=None, help="base seed; each request gets seed + 100*text_index + take")
    ap.add_argument("--api-key", default=os.environ.get("TTS_API_KEY"), help="Bearer token (default: $TTS_API_KEY)")
    ap.add_argument("--gpus", default=os.environ.get("BENCH_GPUS"), help="nvidia-smi GPU ids to sample, e.g. 1 (default: all)")
    ap.add_argument("--tag", default="", help="label prefixed to run names, e.g. bf16_graphs")
    ap.add_argument("--timeout", type=float, default=None, help="per-request timeout (default: by size, scaled by c/16)")
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--out", type=Path, default=None, help="results dir (default results/<timestamp>)")
    ap.add_argument("--no-audio", action="store_true", help="don't save the generated audio")
    args = ap.parse_args()
    args.params = dict(parse_param(p) for p in args.param)
    args.auth = {"Authorization": f"Bearer {args.api_key}"} if args.api_key else None

    sweep = DEFAULT_SWEEP if args.matrix and not args.sweep else \
        tuple(int(x) for x in args.sweep.split(",")) if args.sweep else (args.c,)
    sizes = SIZES if args.matrix else tuple(args.size)
    out_dir = args.out or REPO / "results" / now_label()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(json.dumps({k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()
                                                     if k not in ("api_key", "auth")}, indent=1), encoding="utf-8")
    if not args.no_audio:
        (out_dir / "AI_GENERATED_AUDIO.txt").write_text(AI_LABEL + "\n", encoding="utf-8")
    gpu = GpuMonitor(args.gpus)
    summaries: list[dict] = []
    limits = httpx.Limits(max_connections=max(sweep) + 8, max_keepalive_connections=max(sweep) + 8)
    summaries_path = out_dir / "summary.csv"
    if summaries_path.exists():                                # --out reused: keep earlier runs in the tables
        with open(summaries_path, encoding="utf-8") as f:
            summaries = list(csv.DictReader(f))
    try:
        async with httpx.AsyncClient(limits=limits) as client:
            for vid in args.voice:
                voice = Voice(vid)
                pool_file = args.pools or REPO / "bench" / "pools" / f"{voice.lang}.json"
                pools = json.loads(pool_file.read_text(encoding="utf-8"))
                print(f"voice {vid} ({voice.lang}): ref {voice.ref_path.name}, pools {pool_file.name}: "
                      + ", ".join(f"{s}={len(pools[s])}" for s in SIZES if pools.get(s)))
                if args.voice_mode == "upload":
                    await register_voice(client, args, voice)
                for w in range(args.warmup):
                    warm = pools.get("short") or next(pools[s] for s in SIZES if pools.get(s))
                    res = await one_request(client, args.url.rstrip("/") + "/v1/audio/speech",
                                            build_payload(args, voice, warm[-1 - w]), TIMEOUT["short"], args.format,
                                            args.auth)
                    print(f"warmup {w + 1}: {res['latency']:.2f}s {res['error'] or 'ok'}")
                for size in sizes:
                    if not pools.get(size):
                        print(f"  skip {size}: not in {pool_file.name}")
                        continue
                    cursor = 0
                    for c in sweep:
                        n = args.n or max(8, 2 * c)
                        s, cursor = await run_one(client, args, voice, pools[size], cursor, size, n, c, gpu, out_dir)
                        summaries.append(s)
                        write_tables(out_dir, summaries)
    finally:
        gpu.stop()
    print(f"\nresults: {out_dir}\n" + (out_dir / "summary.md").read_text(encoding="utf-8") if summaries else "")


if __name__ == "__main__":
    asyncio.run(main())
