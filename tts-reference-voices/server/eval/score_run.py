#!/usr/bin/env python3
"""Score bench_tts.py result dirs (requests.jsonl + audio/) or a manifest of clips: per-take quality metrics, the
online `gate` verdict and the stricter offline `bad` label, written next to the run they score.

    eval/run.sh eval/score_run.py ../results/P5_urdu_rp_110 --device cuda --workers 4
    eval/run.sh eval/score_run.py ../results --device cuda                 # every requests.jsonl below, recursively
    CUDA_VISIBLE_DEVICES= eval/run.sh eval/score_run.py <dir> --device cpu --workers 1 --cpu-threads 8
    eval/run.sh eval/score_run.py <dir> --rejudge --thresholds t.json      # new thresholds, no models (fast)
    eval/run.sh eval/score_run.py --manifest eval/calibration/refs_manifest.jsonl --out eval/calibration/x.jsonl

Per run dir (the folder holding requests.jsonl):
  scores.jsonl          one row per take: the request's ids (run, voice, lang, idx, take, seed, prompt_id, file, ...),
                        every metric (tts_qc/scorer.py), gate_pass + gate_reasons, bad + bad_reasons, ms
  scores_summary.json   per bench run (and "ALL"): means / medians, corpus WER / CER / CER-nospace, gate-fail and bad
                        rates with 95 % Wilson CIs, bad rate of first takes (no guardrail) and of gate-passing takes,
                        gate recall / precision against `bad`, reason counts, per-prompt table; plus the thresholds,
                        model identities (sha256) and versions used
  scores_summary.md     the headline table
Resumable: rows already in scores.jsonl (matched by file) are skipped; --force rescores everything. Rows with an
error or no audio file are not scored. Grouping (takes.py): a setting is a bench run + the voice as the engine knows
it; a prompt is the repo voice + prompt id / text; takes are told apart by `take`, never by seed (vLLM-Omni 0.28 does
not reproduce seeds). Engine voice variants (trump-avg, shehbaz-prompt, <id>-<sha10>) are scored against voices/<id>.

ASR: faster-whisper large-v3 (stock), float16 on GPU / int8 on CPU, beam 5, language forced, no previous-text
conditioning, no VAD filter, word timestamps (tts_qc/asr.py). SIM: WavLM-Large+ECAPA (primary, `bad`) and
wavlm-base-plus-sv (secondary, the production gate's model), vs the prompt reference and vs the held-out centroid.
Definitions and thresholds: tts_qc/policy.py and eval/README.md.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "qc"))
sys.path.insert(0, str(HERE))

from stats import describe, rate  # noqa: E402
from takes import prompt_key, repo_voice, setting_key  # noqa: E402
from tts_qc import paths, policy  # noqa: E402
from tts_qc.policy import BAD, GATE  # noqa: E402

TZ = ZoneInfo(os.environ.get("TTS_QC_TZ", "Asia/Karachi"))
ID_FIELDS = ("run", "tag", "voice", "engine_voice", "lang", "size", "c", "idx", "text_idx", "take", "seed", "prompt_id",
             "voice_mode", "file", "text", "audio_s", "latency", "ttfa", "out_tokens", "params", "suspect_reason",
             "case", "expect")
MEAN_KEYS = ("wer", "cer", "cer_nospace", "char_ratio", "sim_prompt_large", "sim_heldout_large", "sim_prompt_base",
             "sim_heldout_base", "pace_ratio", "s_per_letter", "duration_s", "max_internal_sil_s", "trail_sil_s",
             "max_word_s", "unaligned_tail_s", "seg_max_cr")


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


# ------------------------------------------------------------------------------------------------ inputs

def find_run_dirs(targets: list[str]) -> list[Path]:
    dirs: list[Path] = []
    for t in targets:
        p = Path(t)
        if (p / "requests.jsonl").exists():
            dirs.append(p)
        elif p.is_dir():
            dirs += sorted(q.parent for q in p.rglob("requests.jsonl"))
        else:
            raise SystemExit(f"score_run: {t} has no requests.jsonl (and is not a folder to search)")
    if not dirs:
        raise SystemExit(f"score_run: no requests.jsonl under {targets}")
    return dirs


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def resolve(file: str, *bases: Path) -> Path:
    p = Path(file)
    if p.is_absolute():
        return p
    for b in bases:
        if (b / p).exists():
            return b / p
    return bases[0] / p


def take_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("file") and not r.get("error")]


# ------------------------------------------------------------------------------------------------ scoring

def verdicts(m: dict, lang: str, gate_t, bad_t, gate_sim: str, bad_sim: str) -> dict:
    g = policy.gate(m, lang, gate_t, gate_sim)
    b = policy.bad(m, lang, bad_t, bad_sim)
    return {"gate_pass": not g, "gate_reasons": g, "bad": bool(b), "bad_reasons": b}


def score_rows(scorer, rows: list[dict], base: Path, out_path: Path, args, gate_t, bad_t) -> int:
    from tts_qc.audio import read_wav, to_16k

    lock = threading.Lock()
    done = 0
    t_start = time.perf_counter()
    total = len(rows)

    def one(r: dict) -> dict:
        path = resolve(r["file"], base, paths.REPO_DIR)
        pcm, sr = read_wav(path)
        v = scorer.voice(r.get("voice")) or scorer.voice(r.get("engine_voice"))     # trump-avg -> voices/trump
        lang = r.get("lang") or (v.lang if v else "en")
        pace = False if args.no_pace else (r["expected_pace"] if "expected_pace" in r else True)
        m, ms = scorer.score(pcm, sr, r["text"], lang, v.id if v else None, policy.CHECKS, pace=pace)
        if args.lid and scorer.asr is not None:
            wav16 = to_16k(pcm, sr)
            _, _, probs = scorer.asr.model.detect_language(audio=wav16[: 30 * 16000])
            p = dict(probs or [])
            m.update({f"lid_{k}": round(p.get(k, 0.0), 3) for k in ("ur", "hi", "en")})
        out = {k: r[k] for k in ID_FIELDS if k in r}
        out.update({"lang": lang, "voice_ref": v.id if v else None, **m,
                    **verdicts(m, lang, gate_t, bad_t, args.gate_sim, args.bad_sim), "ms": ms, "scored_at": now()})
        return out

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex, open(out_path, "a", encoding="utf-8") as f:
        futures = {ex.submit(one, r): r for r in rows}
        for fut in as_completed(futures):
            r = futures[fut]
            try:
                res = fut.result()
            except Exception as exc:                                # keep going; the row is retried next time
                print(f"  ERROR {r.get('file')}: {type(exc).__name__}: {exc}", flush=True)
                continue
            with lock:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
                f.flush()
                done += 1
            if args.verbose or done % 20 == 0 or done == total:
                el = time.perf_counter() - t_start
                print(f"  {done}/{total} {el:.0f}s eta {el / done * (total - done):.0f}s | {res['file']}: "
                      f"wer={res.get('wer')} cer_ns={res.get('cer_nospace')} sim_L={res.get('sim_prompt_large')} "
                      f"gate={'pass' if res['gate_pass'] else ','.join(res['gate_reasons'])}"
                      f"{' BAD:' + ','.join(res['bad_reasons']) if res['bad'] else ''}", flush=True)
    return done


# ------------------------------------------------------------------------------------------------ summary

def corpus(rows: list[dict]) -> dict:
    import jiwer

    from tts_qc.textnorm import nospace
    pairs = [(r["ref_norm"], r.get("hyp_norm") or "") for r in rows if r.get("ref_norm")]
    if not pairs:
        return {}
    refs, hyps = [p[0] for p in pairs], [p[1] for p in pairs]
    return {"n": len(pairs), "wer": round(jiwer.wer(refs, hyps), 4), "cer": round(jiwer.cer(refs, hyps), 4),
            "cer_nospace": round(jiwer.cer([nospace(x) for x in refs], [nospace(x) for x in hyps]), 4)}


def summarize_group(rows: list[dict]) -> dict:
    n = len(rows)
    gate_fail = sum(not r["gate_pass"] for r in rows)
    nbad = sum(r["bad"] for r in rows)
    first = [r for r in rows if r.get("take", 0) == 0]
    passed = [r for r in rows if r["gate_pass"]]
    tp = sum(r["bad"] and not r["gate_pass"] for r in rows)
    fp = sum((not r["bad"]) and not r["gate_pass"] for r in rows)
    by_prompt: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_prompt[prompt_key(r)].append(r)
    per_prompt = []
    for key, rs in sorted(by_prompt.items()):
        entry = {"prompt": key, "takes": len(rs), "gate_fail": sum(not r["gate_pass"] for r in rs),
                 "bad": sum(r["bad"] for r in rs)}
        for k in ("wer", "cer_nospace", "sim_prompt_large", "sim_prompt_base", "pace_ratio", "duration_s"):
            d = describe([r.get(k) for r in rs])
            entry[k] = d["mean"] if d else None
        entry["reasons"] = dict(Counter(x for r in rs
                                        for x in r["gate_reasons"] + ["bad:" + b for b in r["bad_reasons"]]))
        per_prompt.append(entry)
    ks = Counter(len(rs) for rs in by_prompt.values())
    return {
        "voices": sorted({r.get("engine_voice") or r.get("voice") or "" for r in rows}),
        "repo_voices": sorted({repo_voice(r) for r in rows}), "langs": sorted({r.get("lang") or "" for r in rows}),
        "n_takes": n, "n_prompts": len(by_prompt), "takes_per_prompt": dict(sorted(ks.items())),
        "stats": {k: describe([r.get(k) for r in rows]) for k in MEAN_KEYS if any(r.get(k) is not None for r in rows)},
        "corpus": corpus(rows),
        "gate_fail": rate(gate_fail, n),
        "bad": rate(nbad, n),
        "bad_first_take": rate(sum(r["bad"] for r in first), len(first)),     # before guardrails (take 0 only)
        "bad_among_gate_pass": rate(sum(r["bad"] for r in passed), len(passed)),   # after, with unlimited retries
        "gate_vs_bad": {"recall": round(tp / nbad, 4) if nbad else None,
                        "precision": round(tp / gate_fail, 4) if gate_fail else None,
                        "false_reject_rate": round(fp / (n - nbad), 4) if n - nbad else None},
        "gate_reasons": dict(Counter(x for r in rows for x in r["gate_reasons"]).most_common()),
        "bad_reasons": dict(Counter(x for r in rows for x in r["bad_reasons"]).most_common()),
        "per_prompt": per_prompt,
    }


def fmt(x, nd=3) -> str:
    return "-" if x is None else f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def markdown(summary: dict) -> str:
    lines = [f"# Scores: {summary['dir']}", "",
             f"Scored {summary['scored_at']}; gate SIM model `{summary['thresholds']['gate_sim']}`, bad SIM model "
             f"`{summary['thresholds']['bad_sim']}`. Rates: k/n with 95 % Wilson CI. Means over takes; corpus = "
             "total edits / total reference length.", "",
             "| run | takes | prompts | WER mean | CER-ns mean | corpus WER | corpus CER-ns | SIM-L prompt | "
             "SIM-L heldout | SIM-B prompt | pace ratio | gate fail | bad | bad (take 0) | bad among gate-pass |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def r(d):
        return f"{d['k']}/{d['n']} {fmt(d['rate'])} [{fmt(d['ci95'][0])}, {fmt(d['ci95'][1])}]" if d["n"] else "-"

    for name, g in summary["runs"].items():
        st = g["stats"]

        def m(k, st=st):
            return fmt(st[k]["mean"]) if st.get(k) else "-"

        c = g["corpus"]
        lines.append(f"| {name} | {g['n_takes']} | {g['n_prompts']} | {m('wer')} | {m('cer_nospace')} | "
                     f"{fmt(c.get('wer'))} | {fmt(c.get('cer_nospace'))} | {m('sim_prompt_large')} | "
                     f"{m('sim_heldout_large')} | {m('sim_prompt_base')} | {m('pace_ratio')} | {r(g['gate_fail'])} | "
                     f"{r(g['bad'])} | {r(g['bad_first_take'])} | {r(g['bad_among_gate_pass'])} |")
    top = summary["runs"].get("ALL") or next(iter(summary["runs"].values()))
    lines.append("")
    for key in ("gate_reasons", "bad_reasons"):
        lines.append(f"{key.replace('_', ' ').capitalize()} (all runs): "
                     + (", ".join(f"{k} {v}" for k, v in top[key].items()) or "none") + "  ")
    lines.append("")
    return "\n".join(lines) + "\n"


def write_summary(rows: list[dict], out_json: Path, label: str, meta: dict, mode: str = "run") -> dict:
    """One summary per setting (takes.setting_key: bench run + voice as the engine knows it), plus ALL."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[setting_key(r, mode, default=label)].append(r)
    runs = {k: summarize_group(v) for k, v in sorted(groups.items())}
    if len(groups) > 1:
        runs["ALL"] = summarize_group(rows)
    summary = {"dir": label, "scored_at": now(), **meta, "runs": runs}
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    out_json.with_suffix(".md").write_text(markdown(summary), encoding="utf-8")
    return summary


# ------------------------------------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*", help="bench results dirs (with requests.jsonl) or folders to search")
    ap.add_argument("--manifest", help="JSONL of {file, text, lang, voice?, case?} instead of results dirs")
    ap.add_argument("--out", help="manifest mode: output JSONL (default <manifest>.scores.jsonl)")
    ap.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    ap.add_argument("--device-index", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4, help="parallel takes = CTranslate2 workers (default 4)")
    ap.add_argument("--cpu-threads", type=int, default=8)
    ap.add_argument("--asr-compute", default=None, help="float16 (cuda default) | int8_float16 | int8 (cpu default)")
    ap.add_argument("--beam", type=int, default=5)
    ap.add_argument("--no-asr", action="store_true")
    ap.add_argument("--sim", default="large,base", help="SIM models to compute (large,base | base | large | none)")
    ap.add_argument("--gate-sim", default=policy.GATE_SIM_MODEL, help="SIM model of the gate verdict (production)")
    ap.add_argument("--bad-sim", default=policy.BAD_SIM_MODEL, help="SIM model of the bad label")
    ap.add_argument("--thresholds", help='JSON {"gate": {...}, "bad": {...}} overriding policy.GATE / policy.BAD')
    ap.add_argument("--no-pace", action="store_true", help="no pace check (e.g. human reference clips)")
    ap.add_argument("--lid", action="store_true", help="also store Whisper language-ID p(ur), p(hi), p(en)")
    ap.add_argument("--limit", type=int, default=0, help="score at most N new takes per dir")
    ap.add_argument("--force", action="store_true", help="rescore every take (overwrites scores.jsonl)")
    ap.add_argument("--rejudge", action="store_true", help="recompute verdicts + summary from stored metrics only")
    ap.add_argument("--setting", choices=("run", "tag", "params", "dir"), default="run",
                    help="summary groups: bench run (default), tag, params, or the results dir; always split by voice")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    if bool(args.manifest) == bool(args.targets):
        ap.error("give results dirs or --manifest (one of them)")

    over = json.loads(Path(args.thresholds).read_text()) if args.thresholds else {}
    gate_t, bad_t = GATE.updated(over.get("gate")), BAD.updated(over.get("bad"))
    sims = tuple(s for s in args.sim.split(",") if s and s != "none")
    meta_t = {"gate": gate_t.as_dict(), "bad": bad_t.as_dict(), "gate_sim": args.gate_sim, "bad_sim": args.bad_sim}

    # (rows to score, base dir for relative files, scores.jsonl, summary json, label)
    jobs = []
    if args.manifest:
        man = Path(args.manifest)
        out = Path(args.out) if args.out else man.with_suffix(".scores.jsonl")
        jobs.append((read_jsonl(man), man.parent, out, out.with_name(out.stem + "_summary.json"), str(man)))
    else:
        for d in find_run_dirs(args.targets):
            jobs.append((take_rows(read_jsonl(d / "requests.jsonl")), d, d / "scores.jsonl",
                         d / "scores_summary.json", str(d)))

    scorer = None
    for rows, base, out, summ, label in jobs:
        if args.rejudge:
            scored = read_jsonl(out)
            if not scored:
                print(f"{label}: nothing scored yet ({out} missing or empty)")
                continue
            for r in scored:
                r.update(verdicts(r, r["lang"], gate_t, bad_t, args.gate_sim, args.bad_sim))
            tmp = out.with_suffix(".tmp")
            tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in scored), encoding="utf-8")
            tmp.replace(out)
            meta_path = summ if summ.exists() else None
            old = json.loads(meta_path.read_text()) if meta_path else {}
            s = write_summary(scored, summ, label, {"scorer": old.get("scorer"), "thresholds": meta_t,
                                                    "rejudged": True}, args.setting)
            print(f"{label}: rejudged {len(scored)} takes -> {summ}")
            continue
        if args.force and out.exists():
            out.unlink()
        have = {r["file"] for r in read_jsonl(out)}
        todo = [r for r in rows if r["file"] not in have]
        if args.limit:
            todo = todo[: args.limit]
        print(f"{label}: {len(rows)} takes, {len(have)} already scored, {len(todo)} to score -> {out}", flush=True)
        if todo:
            if scorer is None:
                from tts_qc.scorer import Scorer, ScorerConfig
                need = tuple(dict.fromkeys(sims + tuple(x for x in (args.gate_sim, args.bad_sim) if x in sims)))
                cfg = ScorerConfig(device=args.device, device_index=args.device_index, asr=not args.no_asr,
                                   asr_compute=args.asr_compute, beam=args.beam, workers=args.workers,
                                   cpu_threads=args.cpu_threads, sim_models=need)
                t0 = time.perf_counter()
                scorer = Scorer(cfg).load()
                print(f"models loaded in {time.perf_counter() - t0:.1f}s: {scorer.load_s}", flush=True)
            t0 = time.perf_counter()
            n = score_rows(scorer, todo, base, out, args, gate_t, bad_t)
            print(f"{label}: scored {n} in {time.perf_counter() - t0:.1f}s", flush=True)
        scored = read_jsonl(out)
        if scored:
            s = write_summary(scored, summ, label, {"scorer": scorer.describe() if scorer else None,
                                                    "thresholds": meta_t, "args": vars(args)}, args.setting)
            a = s["runs"].get("ALL") or next(iter(s["runs"].values()))
            print(f"{label}: gate fail {a['gate_fail']['k']}/{a['gate_fail']['n']}, bad {a['bad']['k']}/{a['bad']['n']}"
                  f", corpus {a['corpus']} -> {summ}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
