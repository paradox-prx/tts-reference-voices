"""The benchmark plan run by run_plan.py: an ordered list of phases. Edit freely, then check with
`run_plan.py --list` and `run_plan.py --dry-run --only NAME`.

Phase keys:
  name      results/<name>/ and logs/{engine,gateway}_<name>.log
  engine    {"variant": V, "venv": "engine" | "engine30"}: engine/deploy/variants/V.yaml ("prod" means
            engine/deploy/qwen3_tts_prod.yaml), started fresh for the phase and stopped after it;
            or "none": reuse the engine already running on :8091 (e.g. kept from the previous phase)
  gateway   False: off. True or {TTS_* env overrides}: the gateway runs in front of the engine for this phase
  bench     bench_tts.py argument lists. A dict {"args": [...], "via": "engine" | "gateway", "tag": "x"} picks the
            target (default: the gateway when it is on, else the engine on :8091) and names the runs <name>_x.
            run_plan.py appends --url, --out results/<name>/, --gpus 1, --tag and the API key (via env).
  note      shown by --list and stored in phase.json
  ready_timeout_s  engine start budget (default 1200 s: first start compiles CUDA graphs / FlashInfer)

Rules the plan must keep: vLLM-Omni silently ignores top-level temperature/top_k/top_p/repetition_penalty, so
engine-direct runs send sampling as extra_params and change repetition_penalty only through variants; no seeds on
throughput phases (a seed serialises the code predictor in 0.28, docs/research/omni-source.md).
"""

# ---- choices made after the P1 screen: edit these, then run P2..P7 -------------------------------------------
CHOSEN = "default"             # engine variant for P2..P7
CHOSEN_VENV = "engine"         # "engine" (vllm-omni 0.28.0) or "engine30" (0.30.0rc1)
CHOSEN_STREAM = CHOSEN         # the streaming matrix may want a different variant (async_chunk on)

VOICES = ["trump", "shehbaz"]
FULL_SWEEP = "1,2,4,8,16,32,48,64"
SAMPLING = ["--param", 'extra_params={"temperature":0.9,"top_k":50}']   # engine-direct sampling (codebook 0)
AURALIS_POOLS = "/home/vector/tts-reference-voices/bench/pools/auralis_ur.json"

# P1 screen: (variant, venv) from engine/make_variant.py; streaming is screened only where it can change the answer
SCREEN = [("default", "engine"), ("no_async_chunk", "engine"), ("eager", "engine"), ("fp16_talker", "engine"),
          ("fp32_talker", "engine"), ("seqs32", "engine"), ("seqs128", "engine"), ("decode8", "engine"),
          ("default", "engine30"), ("mrv2", "engine30")]   # 0.30 with our settings, and with its own defaults
SCREEN_STREAM = {("default", "engine"), ("no_async_chunk", "engine")}

# P5: repetition_penalty is server-side only, one variant per value
RP_VARIANTS = {"1.05": "default", "1.10": "rp110", "1.15": "rp115", "1.20": "rp120"}


def engine(variant: str, venv: str = "engine") -> dict:
    return {"variant": variant, "venv": venv}


def direct(*args: str, tag: str = "") -> dict:
    """A bench command against the engine itself, with sampling in extra_params."""
    return {"args": [*args, *SAMPLING], "via": "engine", "tag": tag}


def via_gateway(voices: list[str], *args: str, tag: str = "") -> list[dict]:
    """Bench commands through the gateway, one per voice. The gateway serves voices by id (registered with the
    engine at startup) and rejects inline references unless TTS_ALLOW_INLINE_REF=1, so bench's inline
    ref_audio/ref_text are replaced by voice=<id>. Sampling and retries follow the gateway's settings."""
    return [{"args": ["--voice", v, *args, "--param", f"voice={v}", "--param", "ref_audio=null",
                      "--param", "ref_text=null"], "via": "gateway", "tag": tag} for v in voices]


def sweep_n(concurrencies: list[int], *args: str) -> list[list[str]]:
    """Argument lists for a sweep with n = max(16, 2c): concurrencies that share n share one command."""
    groups: dict[int, list[int]] = {}
    for c in concurrencies:
        groups.setdefault(max(16, 2 * c), []).append(c)
    return [[*args, "--sweep", ",".join(map(str, cs)), "-n", str(n)] for n, cs in groups.items()]


PHASES: list[dict] = [
    {"name": "P0_smoke", "engine": engine("default"), "gateway": True,
     "note": "1 short request per voice, non-stream + stream, engine direct and via the gateway",
     "bench": [direct("--voice", *VOICES, "--size", "short", "-n", "1", "-c", "1", "--warmup", "0", *extra,
                      tag="direct") for extra in ([], ["--stream"])]
              + [cmd for extra in ([], ["--stream"])
                 for cmd in via_gateway(VOICES, "--size", "short", "-n", "1", "-c", "1", "--warmup", "0", *extra,
                                        tag="gw")]},
]

PHASES += [
    {"name": f"P1_screen_{variant}" + ("" if venv == "engine" else f"_{venv}"), "engine": engine(variant, venv),
     "note": f"screen {variant} ({venv}): medium, c=1,8,32, n=max(16,2c)",
     "bench": [direct(*a) for a in sweep_n([1, 8, 32], "--voice", *VOICES, "--size", "medium")]
              + ([direct(*a, "--stream") for a in sweep_n([1, 8, 32], "--voice", *VOICES, "--size", "medium")]
                 if (variant, venv) in SCREEN_STREAM else [])}
    for variant, venv in SCREEN
]

PHASES += [
    {"name": "P2_matrix", "engine": engine(CHOSEN, CHOSEN_VENV),
     "note": "throughput matrix: 4 sizes x c=1..64, non-stream",
     "bench": [direct("--voice", v, "--size", "short", "medium", "long", "xlong", "--sweep", FULL_SWEEP)
               for v in VOICES]},
    {"name": "P3_stream", "engine": engine(CHOSEN_STREAM, CHOSEN_VENV),
     "note": "latency matrix: 4 sizes x c=1..64, streaming (TTFA)",
     "bench": [direct("--voice", v, "--size", "short", "medium", "long", "xlong", "--sweep", FULL_SWEEP, "--stream")
               for v in VOICES]},
    {"name": "P4_voice_mode", "engine": engine(CHOSEN, CHOSEN_VENV),
     "note": "registered (POST /v1/audio/voices once) vs inline ref_audio in every request, engine direct",
     "bench": [direct("--voice", *VOICES, "--size", "medium", "--sweep", "1,8,32", "--voice-mode", mode, tag=tag)
               for mode, tag in (("upload", "registered"), ("inline", "inline"))]},
]

PHASES += [
    {"name": f"P5_urdu_rp_{rp}", "engine": engine(variant, CHOSEN_VENV),
     "note": f"repetition_penalty {rp} (variant {variant}): Urdu failure rates, English control",
     "bench": [direct("--voice", "shehbaz", "--size", "long", "xlong", "-n", "43", "-c", "16", "--takes", "3"),
               direct("--voice", "trump", "--size", "xlong", "-n", "43", "-c", "16", "--takes", "2", tag="en")]}
    for rp, variant in RP_VARIANTS.items()
]

PHASES += [
    {"name": "P6_auralis", "engine": engine(CHOSEN, CHOSEN_VENV), "gateway": True,
     "note": "Auralis Urdu pools: n=20 c=20 (the Auralis default) and a sweep engine direct; n=20 c=20 through the "
             "gateway (Auralis was measured through its full proxy stack)",
     "bench": [direct("--voice", "shehbaz", "--pools", AURALIS_POOLS, "--size", "short", "medium", "long",
                      "-n", "20", "-c", "20", tag="n20c20"),
               direct("--voice", "shehbaz", "--pools", AURALIS_POOLS, "--size", "short", "medium", "long",
                      "--sweep", "1,4,8,16,32,64", tag="sweep"),
               *via_gateway(["shehbaz"], "--pools", AURALIS_POOLS, "--size", "short", "medium", "long",
                            "-n", "20", "-c", "20", tag="gw_n20c20")]},
    {"name": "P7_gateway", "engine": engine(CHOSEN, CHOSEN_VENV), "gateway": {"TTS_RETRY_MAX": "1"},
     "note": "gateway overhead and live retries: engine direct vs gateway retries=0 vs retries=1",
     "bench": [direct("--voice", *VOICES, "--size", "medium", "xlong", "--sweep", "1,16", tag="direct")]
              + [cmd for r in (0, 1) for cmd in via_gateway(VOICES, "--size", "medium", "xlong", "--sweep", "1,16",
                                                              "--param", f"retries={r}", tag=f"gw_r{r}")]},
]
