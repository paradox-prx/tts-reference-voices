#!/usr/bin/env python3
"""End-to-end check against a running studio (engine + app), through the public API only.

  .venv/bin/python scripts/e2e_check.py [--url http://127.0.0.1:8100] [--out results/<date>_e2e] [--skip-dev]

Dev console: a job with 3 speakers (preset voices' references uploaded as speaker WAVs) and 20 rows (2 pinned, tags,
one fixed seed). It waits for the job, checks the stratified samples, regenerates one row, then downloads the zip
(with the pipe_csv extra) and checks:
  - the layout;
  - metadata.csv paths and counts against metadata.jsonl, rejected.csv, the per-speaker distribution and the WAV
    headers.
Customer console: one sample per language (en, ur, ps, pa, sd). One has tags and one uses an uploaded reference; one
is streamed and its live PCM is checked. WAVs plus one MP3 are saved.

Writes <out>/summary.json and the audio; exits 1 when a check fails.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
import wave
import zipfile
from datetime import date
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
FAILS: list[str] = []


def check(cond: bool, msg: str) -> bool:
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)
    return cond


def wav_info(b: bytes) -> tuple[int, float]:
    with wave.open(io.BytesIO(b)) as w:
        return w.getframerate(), w.getnframes() / w.getframerate()


ROWS = [  # id, text, speaker (pin), tags, seed
    ("r01", "السلام علیکم، آپ کا بل اس مہینے کی پندرہ تاریخ تک جمع کروا دیں۔", "", "", ""),
    ("r02", "ہماری نئی سروس اب آپ کے شہر میں بھی دستیاب ہے۔", "", "emotion:enthusiasm", ""),
    ("r03", "Your order has been shipped and will arrive within three working days.", "", "", ""),
    ("r04", "آج موسم بہت اچھا ہے، چلیں باہر چائے پیتے ہیں۔", "", "", "4242"),
    ("r05", "براہ کرم اپنا شناختی کارڈ نمبر بتائیں تاکہ میں آپ کا اکاؤنٹ چیک کر سکوں۔", "callagent", "", ""),
    ("r06", "Thank you for your patience. A specialist will call you back shortly.", "", "prosody:speed_slow", ""),
    ("r07", "میچ کے آخری اوور میں سات رنز درکار ہیں، اور سٹیڈیم میں سناٹا ہے۔", "", "emotion:surprise", ""),
    ("r08", "یہ پیکج تیس دن کے لیے کارآمد ہوگا۔", "", "", ""),
    ("r09", "We are sorry for the inconvenience caused by the outage this morning.", "", "", ""),
    ("r10", "<|emotion:sadness|>مجھے افسوس ہے کہ آپ کو یہ مسئلہ پیش آیا۔ ہم اسے جلد حل کریں گے۔", "", "", ""),
    ("r11", "کیا آپ مزید کسی چیز کے بارے میں جاننا چاہیں گے؟", "", "", ""),
    ("r12", "Please hold the line while I transfer your call.", "trump", "", ""),
    ("r13", "شہر میں آج رات بارش کا امکان ہے، اس لیے احتیاط کریں۔", "", "", ""),
    ("r14", "آپ کی شکایت درج کر لی گئی ہے اور اس کا نمبر آپ کو ایس ایم ایس کر دیا جائے گا۔", "", "", ""),
    ("r15", "Our offices will remain closed on Friday for the public holiday.", "", "", ""),
    ("r16", "بہت شکریہ، آپ کا دن اچھا گزرے۔", "", "emotion:contentment", ""),
    ("r17", "نئے صارفین کے لیے پہلا مہینہ بالکل مفت ہے۔", "", "", ""),
    ("r18", "The meeting has been moved to Thursday at four in the afternoon.", "", "", ""),
    ("r19", "اپنا پاس ورڈ کسی کے ساتھ شیئر نہ کریں۔", "", "", ""),
    ("r20", "اگلی قسط کی تاریخ آپ کے موبائل ایپ میں دیکھی جا سکتی ہے۔", "", "", ""),
]
SPEAKERS = ["callagent", "trump", "hammad"]

SAMPLES = [  # label, language, voice, text, extra body
    ("en", "en", {"preset": "trump"},
     "Thanks for calling. Your new plan is active, and you'll see the change on your next bill.", {"stream": True}),
    ("ur_tags", "ur", {"preset": "callagent"},
     "<|emotion:enthusiasm|>السلام علیکم! آپ کے نمبر کے لیے ایک خاص پیکج دستیاب ہے۔ <|prosody:speed_slow|>"
     "اس میں ہر روز دو جی بی انٹرنیٹ شامل ہے۔", {}),
    ("ps", "ps", {"preset": "asad"}, "سلام ورور، ستاسو لپاره نن یو ځانګړی پیکج شته چې ډېر ارزانه انټرنیټ لري.", {}),
    ("pa", "pa", {"preset": "hammad"}, "سلام جی، اج تہاڈے لئی اک نواں پیکج آیا اے، جیہدے وچ بہت سستا انٹرنیٹ اے۔", {}),
    ("sd", "sd", {"preset": "chandiyo"}, "سلام سائين، اڄ توهان لاءِ هڪ نئون پيڪيج آهي جنهن ۾ سستو انٽرنيٽ آهي.", {}),
    ("ur_upload", "ur", "upload:shehzad",
     "آج کی اہم خبروں میں، شہر میں بارش کے بعد موسم خوشگوار ہو گیا ہے۔", {"delivery": {"emotion": "contentment"}}),
]


def dev(c: httpx.Client, out: Path) -> dict:
    print("dev console")
    res: dict = {}
    spk = []
    for v in SPEAKERS:
        d = c.get(f"/api/voices/{v}").raise_for_status().json()
        wav = c.get(f"/api/voices/{v}/reference.wav").raise_for_status().content
        m = c.post("/api/dev/speakers", files={"file": (f"{v}.wav", wav, "audio/wav")}).raise_for_status().json()
        check(m["tag"] == v, f"speaker tag from file stem: {m['tag']}")
        spk.append({"upload": m["id"], "tag": m["tag"], "transcript": d["reference_text"], "seconds": m["seconds"]})
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "text", "speaker", "tags", "seed"])
    w.writerows(ROWS)
    rows = c.post("/api/dev/rows", files={"file": ("rows.csv", buf.getvalue().encode(), "text/csv")}).raise_for_status().json()
    check(rows["count"] == 20 and rows["tag_error_count"] == 0, f"rows parsed: {rows['count']}, tag errors {rows['tag_error_count']}")
    check(rows["pinned"] == {"callagent": 1, "trump": 1}, f"pinned {rows['pinned']}")
    dist_cfg = {"mode": "balanced", "seed": 7}
    dist = c.post("/api/dev/distribution", json={"rows": rows["id"], "speakers": SPEAKERS,
                                                  "distribution": dist_cfg}).raise_for_status().json()["counts"]
    check(sum(dist.values()) == 20 and max(dist.values()) - min(dist.values()) <= 1, f"balanced preview {dist}")
    cfg = {"distribution": dist_cfg, "takes": 1, "tags": {"mode": "keep", "export_text": "keep"},
           "seeds": {"mode": "base", "base": 1000}, "qc": {"retries": 1}}
    t0 = time.time()
    job = c.post("/api/dev/jobs", json={"name": "e2e", "config": cfg, "rows": rows["id"], "speakers": [
        {k: s[k] for k in ("upload", "tag", "transcript")} for s in spk]}).raise_for_status().json()
    jid = job["id"]
    while True:
        s = c.get(f"/api/dev/jobs/{jid}").raise_for_status().json()
        if s["status"] not in ("running", "queued"):
            break
        time.sleep(3)
    res["job"] = {k: s[k] for k in ("id", "status", "counts", "per_speaker", "audio_s", "rtf_x", "errors")} | {
        "wall_s": round(time.time() - t0, 1), "distribution_preview": dist}
    good = s["counts"].get("done", 0) + s["counts"].get("flagged", 0)
    check(s["status"] == "done" and good == 20, f"job {s['status']}, {good}/20 rows with audio, counts {s['counts']}")
    check({k: v["total"] for k, v in s["per_speaker"].items()} == dist, f"per-speaker totals match the preview {s['per_speaker']}")
    samples = c.get(f"/api/dev/jobs/{jid}/samples?n=50&seed=1").raise_for_status().json()
    check(len(samples) == s["counts"].get("done", 0) + s["counts"].get("flagged", 0), f"samples: {len(samples)}")
    one = c.get(f"/api/dev/jobs/{jid}/samples?n=50&seed=1&speaker=trump").raise_for_status().json()
    check(all(x["speaker"] == "trump" for x in one), "sample filter by speaker")
    r4 = next(x for x in samples if x["id"] == "r04")
    check(r4["seed"] == 4242, f"row seed column used: r04 seed {r4['seed']}")
    r1 = next(x for x in samples if x["id"] == "r01")
    check(r1["seed"] == 1000, f"base seed + row index: r01 seed {r1['seed']}")
    regen = c.post(f"/api/dev/jobs/{jid}/rows/{r1['idx']}/regenerate", timeout=300).raise_for_status().json()
    check(regen["status"] in ("done", "flagged"), f"regenerate row r01: {regen['status']} seed {regen['seed']}")
    z = c.get(f"/api/dev/jobs/{jid}/download.zip?extra_format=pipe_csv", timeout=300).raise_for_status().content
    (out / "dev_e2e.zip").write_bytes(z)
    zf = zipfile.ZipFile(io.BytesIO(z))
    names = set(zf.namelist())
    for n in ("metadata.csv", "metadata.jsonl", "rejected.csv", "speakers.csv", "job_config.json", "README.md",
              "metadata_pipe.csv", *[f"speakers/{t}.wav" for t in SPEAKERS]):
        check(n in names, f"zip has {n}")
    meta = list(csv.DictReader(io.StringIO(zf.read("metadata.csv").decode("utf-8"))))
    jl = [json.loads(x) for x in zf.read("metadata.jsonl").decode("utf-8").splitlines() if x.strip()]
    rej = list(csv.DictReader(io.StringIO(zf.read("rejected.csv").decode("utf-8"))))
    check(list(meta[0].keys()) == ["audio_path", "text", "speaker", "tags", "seed", "duration_s", "sample_rate",
                                   "qc_status", "wer"], f"metadata.csv columns {list(meta[0].keys())}")
    check(len(meta) == len(jl) and len(meta) + len(rej) == 20, f"metadata {len(meta)} + rejected {len(rej)} = 20, jsonl {len(jl)}")
    wavs = {n for n in names if n.startswith("wavs/")}
    check(wavs == {m["audio_path"] for m in meta}, "every metadata audio_path is in the zip and vice versa")
    bad = []
    for m in meta:
        sp, idd = m["audio_path"].split("/")[1:]
        sr, dur = wav_info(zf.read(m["audio_path"]))
        if sp != m["speaker"] or idd[:-4] not in {r[0] for r in ROWS} or sr != int(m["sample_rate"]) or \
                abs(dur - float(m["duration_s"])) > 0.05:
            bad.append(m["audio_path"])
    check(not bad, f"paths wavs/<speaker>/<id>.wav, sample rate and duration match the WAVs {bad or ''}")
    check(all(m["qc_status"] == "pass" for m in meta), "flagged rows excluded by default (qc_status all pass)")
    by = {}
    for m in meta:
        by[m["speaker"]] = by.get(m["speaker"], 0) + 1
    for r in rej:
        by[r["speaker"]] = by.get(r["speaker"], 0) + 1
    check(by == dist, f"zip per-speaker counts (incl. rejected) match the distribution {by}")
    pinned = {m["audio_path"] for m in meta} | {f"wavs/{r['speaker']}/{r['id']}.wav" for r in rej}
    check("wavs/callagent/r05.wav" in pinned and "wavs/trump/r12.wav" in pinned, "pinned rows kept their speaker")
    tagged = next(m for m in meta if m["audio_path"].endswith("/r02.wav")) if any(
        m["audio_path"].endswith("/r02.wav") for m in meta) else None
    if tagged:
        check("<|emotion:enthusiasm|>" in tagged["text"] and tagged["tags"] == "emotion:enthusiasm",
              f"tags column applied and kept in text: {tagged['tags']}")
    cfg_back = json.loads(zf.read("job_config.json"))
    check(cfg_back["distribution"]["seed"] == 7 and len(cfg_back["speakers"]) == 3, "job_config.json round-trips")
    pipe = zf.read("metadata_pipe.csv").decode("utf-8").splitlines()
    check(len(pipe) == len(meta) + 1 and pipe[0] == "audio_file|text|speaker_name", f"pipe_csv: {pipe[0]}")
    res["zip"] = {"bytes": len(z), "files": len(names), "metadata_rows": len(meta), "rejected": len(rej),
                  "per_speaker": by, "rejected_reasons": [r.get("reason") for r in rej]}
    return res


def customer(c: httpx.Client, out: Path) -> list:
    print("customer console")
    res = []
    for label, lang, voice, text, extra in SAMPLES:
        if voice == "upload:shehzad":  # an uploaded reference: a preset's clip re-uploaded as the user's file
            d = c.get("/api/voices/shehzad").raise_for_status().json()
            wav = c.get("/api/voices/shehzad/reference.wav").raise_for_status().content
            up = c.post("/api/studio/upload", files={"file": ("my_voice.wav", wav, "audio/wav")}).raise_for_status().json()
            voice = {"upload": up["id"], "start": 0, "end": min(up["seconds"], 29.5), "transcript": d["reference_text"]}
        body = {"text": text, "voice": voice, "takes": 1, "stream": False} | extra
        t0 = time.time()
        g = c.post("/api/studio/generate", json=body).raise_for_status().json()
        tk = g["takes"][0]
        live = b""
        if tk["stream"]:
            with c.stream("GET", f"/api/studio/takes/{tk['id']}/live.pcm", timeout=300) as r:
                first = None
                for chunk in r.iter_bytes():
                    if first is None:
                        first = time.time() - t0
                    live += chunk
        while (info := c.get(f"/api/studio/takes/{tk['id']}").raise_for_status().json())["state"] not in ("done", "error"):
            time.sleep(0.5)
        wall = time.time() - t0
        ok = check(info["state"] == "done", f"{label}: {info['state']} {info.get('error') or ''}")
        row = {"label": label, "language": lang, "voice": body["voice"].get("preset") or "upload", "text": text,
               "text_sent": g["text_sent"], "seed": tk["seed"], "parts": g["parts"], "est_s": g["est_s"],
               "wall_s": round(wall, 2), "state": info["state"], "error": info.get("error")}
        if ok:
            b = c.get(f"/api/studio/takes/{tk['id']}.wav").raise_for_status().content
            (out / f"customer_{label}.wav").write_bytes(b)
            sr, dur = wav_info(b)
            r = info["result"]
            row |= {"seconds": round(dur, 2), "sample_rate": sr, "qc_ok": r["ok"], "qc_reasons": r["reasons"],
                    "pace_ratio": [p.get("qc", {}).get("pace_ratio") for p in r["parts"]]}
            if live:
                row |= {"live_pcm_s": round(len(live) / 2 / 24000, 2), "first_audio_s": round(first, 2)}
                check(len(live) > 24000, f"{label}: live PCM streamed {row['live_pcm_s']} s, first audio {row['first_audio_s']} s")
            if label == "en":
                mp3 = c.get(f"/api/studio/takes/{tk['id']}.mp3").raise_for_status().content
                (out / "customer_en.mp3").write_bytes(mp3)
                check(mp3[:3] == b"ID3" or mp3[:2] == b"\xff\xfb", f"en: MP3 download {len(mp3)} bytes")
        res.append(row)
        print(f"       {label}: {row.get('seconds')} s audio, QC {row.get('qc_ok')} {row.get('qc_reasons', '')}, {row['wall_s']} s")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8100")
    ap.add_argument("--out", type=Path, default=ROOT / "results" / f"{date.today()}_e2e")
    ap.add_argument("--skip-dev", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=a.url, timeout=120) as c:
        st = c.get("/api/status").raise_for_status().json()
        if not check(st["engine"], "engine healthy"):
            sys.exit(1)
        summary = {"url": a.url, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
        summary["customer"] = customer(c, a.out)
        if not a.skip_dev:
            summary |= dev(c, a.out)
    summary["fails"] = FAILS
    (a.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"\n{'ALL CHECKS PASSED' if not FAILS else f'{len(FAILS)} FAILED'}; results in {a.out}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
