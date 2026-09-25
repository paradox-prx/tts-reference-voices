"""The benchmark plan run by run_plan.py: an ordered list of phases, run one by one. Edit freely, then check with
`run_plan.py --list` (status, estimated audio hours and GPU minutes per phase) and `run_plan.py --dry-run --only NAME`.

Phase keys:
  name      results/<name>/ and logs/{engine,gateway,qc}_<name>.log
  engine    {"kind": "vllm", "variant": V, "venv": "engine" | "engine30", "args": [...]}: engine/deploy/variants/V.yaml
            ("prod" = engine/deploy/qwen3_tts_prod.yaml) via engine/run_engine.sh, args after `--`;
            {"kind": "qwentts", "args": [...]}: the plain qwen-tts baseline (baseline/qwen_tts_server.py);
            {"kind": "fake"} / {"kind": "stub"}: CPU stand-ins; "none": whatever already runs on the engine port.
            Consecutive phases with the same engine reuse it unless "fresh_engine": True
  gateway   False: off. True or {TTS_* env overrides}: our gateway runs in front of the engine for this phase
  qc        True: start the QC sidecar (server/qc) and set the gateway's TTS_QC_URL
  bench     bench_tts.py argument lists, or {"args": [...], "via": "engine" | "gateway", "tag": "x", "timeout_s": s}.
            via defaults to the gateway when it is on. run_plan.py appends --url, --out results/<name>/, --gpus,
            --tag, --meta (phase, engine, gateway) and the API key (through the environment). Run folders are
            results/<name>/<tag>_<voice>_<size>_c<c>_n<n>[_k<takes>]_<stream|nonstream>_<voice mode>/
  checks    verify_knobs.py specs, run after startup; a check that fails fails the phase. They prove that a knob is
            read: an invalid value is refused (400) where it must be read, ignored (200) where it is dropped, a custom
            voice is listed, a tiny max_new_tokens ends in the codec-EOS error (500)
  requires  paths (relative to server/) that must exist before the phase starts
  kind      "perf" or "quality" (a label; no phase may send --seed: see below)
  optional  True: not run unless --optional or --only names it; listed separately by --list
  note      shown by --list and stored in phase.json

Rules (HANDOFF.md §5.1, §8; docs/EXPERIMENTS.md E01-E04):
- vLLM-Omni silently ignores top-level temperature/top_k/top_p/repetition_penalty, so engine-direct commands send
  sampling through --extra-param (extra_params); per-request repetition_penalty needs engine/patches (applied in
  venvs/engine; P0 and P5 check it).
- NO seeds anywhere: on vLLM-Omni 0.28 (CUDA graphs) a seed does not reproduce even sequentially at c=1 (E04), it
  serialises the code predictor of the whole batch and it disables the engine's built-in retry. Repeated takes are
  unseeded and identified by take index; settings are compared by prompt (43 prompts x K takes), not by seed.
- Gateway retries off in the perf phases (TTS_RETRY_MAX=0); retries are measured in P7 and P8.
- Every output is kept (no --no-audio).
- The main matrix (P2) and the other engine-direct perf phases send the production request shape: the gateway's
  sampling (SAMPLING) and its length cap as max_new_tokens (CAP: --max-new-tokens auto = min(words cap, the voice's
  pace cap), the numbers the gateway computes). An Urdu runaway (~1-1.5% of shehbaz requests in E01) then ends at
  ~2.2x its expected length as HTTP 500 and counts as an error, instead of running to the engine's own cap (~190 s)
  and setting the run's wall time; P7 shows the gateway's retries turning those into successes and X4 runs the
  engine's own cap + built-in retry for comparison. Every run also reports x_realtime_p90wall and stragglers, and
  phase.json counts the engine's built-in retries.
- Default engine: engine/deploy/variants/custom_voices.yaml = the prod YAML (stage 0 at 0.60, KV ~91k tokens) +
  custom_voice_dir state/custom_voices (trump-avg, trump-prompt, shehbaz-avg, shehbaz-prompt from
  engine/precompute_voices.py). Inline, upload and registered voices work with it as with prod.

Sizes: short = 1 sentence (~3 s), medium (~7.5 s) and long (~18 s) from the pools, xlong = one benchmark prompt
(~37 s en / ~28 s ur: the user's "medium ~30 s"), xxlong = two prompts (~73 s / ~56 s: the user's "long ~60 s"),
prompts = the 43 benchmark prompts with their ids. n per cell: --n-rule MIN:MULT[:MAX] = max(MIN, MULT x c) capped
at MAX, so a sweep keeps walking through distinct texts; cells are sized so the default plan stays at ~25 h of audio
(~4.4 GB of WAV).
"""

# ---- choices: edit after the P1 screen, then run P2 onwards ------------------------------------------------------
CHOSEN = "custom_voices"       # engine variant for P0 and P2+ (the prod YAML + the precomputed custom voices)
CHOSEN_VENV = "engine"         # "engine" (vllm-omni 0.28.0) or "engine30" (0.30.0rc1)
CHOSEN_STREAM = CHOSEN         # the streaming phase may want another variant (async_chunk must stay on)
CUSTOM_VOICES = ["trump-avg", "trump-prompt", "shehbaz-avg", "shehbaz-prompt"]
CUSTOM_VOICE_MANIFEST = "state/custom_voices/custom_voice_manifest.json"     # engine/precompute_voices.py writes it

VOICES = ["trump", "shehbaz"]
SWEEP = "1,2,4,8,16,32"
SAMPLING = ["--extra-param", "temperature=0.9", "--extra-param", "top_k=50"]   # what the gateway sends by default
CAP = ["--max-new-tokens", "auto"]                                            # the gateway's length cap
PRODUCTION = [*SAMPLING, *CAP]
AURALIS_POOLS = "bench/pools/auralis_ur.json"   # relative to the repo root (made absolute below)
GW_PERF = {"TTS_RETRY_MAX": "0"}                # gateway with retries off: failures stay visible
GUARD = {"TTS_RETRY_MAX": "2", "TTS_RETRY_ON": "suspect,engine_error,qc"}
QUALITY_TIMEOUT = "900"
# QC_CMD = ["{root}/venvs/eval/bin/python", "-m", "tts_qc"]   # override how the QC sidecar starts (cwd server/qc)
# extra TTS_QC_* settings for the sidecar. The first P8_quality_guard run (engine stage 0 at 0.45, QC float16) ran the
# card out of memory under 16 concurrent takes (engine ~15.9 GB + QC ~6 GB + ASR activations + desktop): 77 of 86 QC
# calls failed (CUDA OOM) and the gateway failed open. So the QC runs Whisper in int8_float16 (~1.5 GB less) with
# expandable segments, next to an engine at stage-0 0.40 (see P8_ENGINE)
QC_ENV: dict = {"TTS_QC_ASR_COMPUTE": "int8_float16", "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}


def engine(variant: str = CHOSEN, venv: str = CHOSEN_VENV, *args: str) -> dict:
    return {"kind": "vllm", "variant": variant, "venv": venv, **({"args": list(args)} if args else {})}


def qwentts(*args: str) -> dict:
    return {"kind": "qwentts", "args": list(args)}


def direct(*args: str, tag: str = "", timeout_s: float | None = None) -> dict:
    """A bench command against the engine itself, in the production request shape (sampling + length cap)."""
    return {"args": [*args, *PRODUCTION], "via": "engine", "tag": tag, **({"timeout_s": timeout_s} if timeout_s else {})}


def via_gateway(*args: str, tag: str = "gw") -> dict:
    """A bench command through the gateway: voice ids the gateway registered with the engine at startup; sampling,
    length cap and retries follow the gateway's settings."""
    return {"args": [*args, "--voice-mode", "server"], "via": "gateway", "tag": tag}


def pool_path(rel: str) -> str:
    from pathlib import Path
    return str(Path(__file__).resolve().parents[2] / rel)


# ---- knob checks (verify_knobs.py): validation, not determinism (seeds don't reproduce on 0.28, E04) ---------------

def request_fields_check() -> dict:
    """Every engine-direct knob the plan relies on is read (invalid value refused) or dropped (accepted) as expected,
    the length cap is enforced, and the custom voices are loaded."""
    return {"name": "request_fields", "via": "engine", "voice": "shehbaz",
            "fails": {"extra_rp_neg": {"extra_params": {"repetition_penalty": -1}},       # patched engine: 400
                      "extra_temperature_neg": {"extra_params": {"temperature": -1}},     # 400
                      "nsm_invalid": {"non_streaming_mode": "x"},                         # 400
                      "language_urdu": {"language": "Urdu"},                              # 400: use Auto
                      "cap40": {"max_new_tokens": 40}},                                   # 500: no codec EOS
            "succeeds": {"toplevel_rp_neg_ignored": {"repetition_penalty": -1},           # 200: top level dropped
                         "toplevel_temperature_neg_ignored": {"temperature": -1},
                         "custom_voice_avg": {"voice": "shehbaz-avg", "ref_audio": None, "ref_text": None}},
            "listed": CUSTOM_VOICES}


def rp_check(rp: str) -> dict:
    return {"name": f"rp_{rp}", "via": "engine", "voice": "shehbaz",
            "fails": {"extra_rp_neg": {"extra_params": {"repetition_penalty": -1}}},
            "succeeds": {f"extra_rp_{rp}": {"extra_params": {"repetition_penalty": float(rp)}}}}


def gateway_headers_check(name: str, headers: dict) -> dict:
    return {"name": name, "via": "gateway", "voice": "trump",
            "base": {"voice": "trump", "ref_audio": None, "ref_text": None, "task_type": None}, "headers": headers}


PHASES: list[dict] = [
    {"name": "P0_smoke", "engine": engine(), "gateway": GW_PERF,
     "note": "1 short request per voice: engine direct (inline, upload) non-stream + stream, and via the gateway",
     "bench": [direct("--voice", *VOICES, "--size", "short", "-n", "1", "-c", "1", "--warmup", "0", *extra, tag=tag)
               for extra, tag in (([], "direct"), (["--stream"], "direct"), (["--voice-mode", "upload"], "direct"))]
              + [via_gateway("--voice", *VOICES, "--size", "short", "-n", "1", "-c", "1", "--warmup", "0", *extra)
                 for extra in ([], ["--stream"])]},
    {"name": "P0_knobs", "engine": engine(), "checks": [request_fields_check()],
     "note": "knob verification on the engine: extra_params repetition_penalty/temperature -1 refused, the same "
             "values top-level ignored, non_streaming_mode 'x' and language 'Urdu' refused, max_new_tokens 40 ends in "
             "the codec-EOS error, the custom voices listed and usable (verify_knobs.py; takes in knobs/)",
     "bench": []},
]

# ---- P1: engine-variant screen. Both voices, medium (~7.5 s), c=1,8,32 with n=8,16,32. Every variant is generated
# from the prod YAML (engine/make_variant.py); "default" is the prod YAML itself, the reference arm ------------------
SCREEN = [("default", "engine"), ("no_async_chunk", "engine"), ("eager", "engine"), ("fp16_talker", "engine"),
          ("fp32_talker", "engine"), ("seqs32", "engine"), ("seqs128", "engine"), ("decode8", "engine"),
          # decode8 at stage-0 0.60 OOMs capturing stage 1's batch-8 decoder graphs: screen it at 0.45 next to the
          # prod YAML at 0.45 (KV 58k tokens: no preemption at c<=32 medium)
          ("decode8_m045", "engine"), ("default_m045", "engine"), ("decode4g_m045", "engine")]
SCREEN_OPTIONAL = [("default", "engine30"), ("mrv2", "engine30")]     # 0.30.0rc1: needs venvs/engine30
SCREEN_STREAM: set = set()      # streaming is measured on the chosen config in P3; add (variant, venv) to screen it
SCREEN_CELL = ["--voice", *VOICES, "--size", "medium", "--sweep", "1,8,32", "--n-rule", "8:2:32"]
# async_chunk off was already measured (E03: -5..-21% throughput, TTFA = whole generation, +3.5-4.5 GB VRAM): one
# small confirming cell only
SCREEN_SMALL = {("no_async_chunk", "engine"): ["--voice", "shehbaz", "--size", "medium", "-c", "8", "-n", "16"]}

PHASES += [
    {"name": f"P1_screen_{variant}" + ("" if venv == "engine" else f"_{venv}"), "engine": engine(variant, venv),
     "optional": (variant, venv) in SCREEN_OPTIONAL,
     "note": (f"variant screen {variant} ({venv}): " + ("one confirming cell (shehbaz medium c=8 n=16; E03 measured "
              "it)" if (variant, venv) in SCREEN_SMALL else "both voices, medium, c=1,8,32 (n=8,16,32), non-stream"
              + (" + stream" if (variant, venv) in SCREEN_STREAM else ""))),
     "bench": [direct(*SCREEN_SMALL.get((variant, venv), SCREEN_CELL))]
              + ([direct(*SCREEN_CELL, "--stream")] if (variant, venv) in SCREEN_STREAM else [])}
    for variant, venv in SCREEN + SCREEN_OPTIONAL
]

# ---- P2: the main matrix. Both voices x 5 sizes x c=1..32, non-stream, engine direct with the gateway's cap -------
P2_CELLS = [("short", "8:2"), ("medium", "8:2"), ("long", "4:1"), ("xlong", "6:1"), ("xxlong", "4:1")]
PHASES += [
    {"name": "P2_matrix", "engine": engine(),
     "note": "main throughput/latency matrix: both voices x short/medium/long/xlong/xxlong x c=1,2,4,8,16,32, "
             "non-stream, engine direct with the gateway's sampling and length cap (n: short/medium max(8,2c), long "
             "max(4,c), xlong max(6,c), xxlong max(4,c))",
     "bench": [direct("--voice", *VOICES, "--size", size, "--sweep", SWEEP, "--n-rule", rule) for size, rule in P2_CELLS]},
    {"name": "P2_high_c", "engine": engine(), "optional": True,
     "note": "c=48,64: short/medium (n=2c) and xlong at c=64 (n=64). The 91k-token KV cache holds 64 xxlong takes; "
             "the long pool at 48/64 was measured in E01",
     "bench": [direct("--voice", *VOICES, "--size", "short", "medium", "--sweep", "48,64", "--n-rule", "1:2"),
               direct("--voice", *VOICES, "--size", "xlong", "-c", "64", "-n", "64")]},
]

# ---- P3: streaming TTFA on the user's sizes (short, ~30 s, ~60 s) --------------------------------------------------
PHASES += [
    {"name": "P3_stream", "engine": engine(CHOSEN_STREAM),
     "note": "streaming (stream_format audio): TTFA past the WAV header and total latency; short/xlong x c=1..32, "
             "xxlong x c=1,8; the same cells (n) as P2, so stream vs non-stream compare run for run",
     "bench": [direct("--voice", *VOICES, "--size", "short", "--sweep", SWEEP, "--n-rule", "8:2", "--stream"),
               direct("--voice", *VOICES, "--size", "xlong", "--sweep", SWEEP, "--n-rule", "6:1", "--stream"),
               direct("--voice", *VOICES, "--size", "xxlong", "--sweep", "1,8", "--n-rule", "4:1", "--stream")]},
]

# ---- P4: voice-prompt cache: registered (upload) vs inline (cached) vs nocache (every reference new) ---------------
PHASES += [
    {"name": "P4_voice_cache", "engine": engine(), "fresh_engine": True,
     "note": "voice-prompt cache on/off, engine direct, fresh engine: upload (registered) vs inline vs nocache; short, "
             "c=1,8,32 (n=8,16,32), non-stream; streaming (TTFA) for inline vs nocache",
     "bench": [direct("--voice", *VOICES, "--size", "short", "--sweep", "1,8,32", "--n-rule", "8:2:32",
                      "--voice-mode", mode, *extra)
               for extra, modes in (([], ("upload", "inline", "nocache")), (["--stream"], ("inline", "nocache")))
               for mode in modes]},
]

# ---- P5: Urdu repetition_penalty sweep (per request, patched engine): 43 prompts x K=6 unseeded takes per value ------
RP_VALUES = ["1.05", "1.10", "1.15", "1.20"]
TRUMP_CONTROL = {"1.05", "1.20"}
PHASES += [
    {"name": f"P5_urdu_rp{rp.replace('.', '')}", "engine": engine(), "kind": "quality", "checks": [rp_check(rp)],
     "note": f"repetition_penalty {rp} per request (extra_params): shehbaz 43 prompts x 6 unseeded takes (c=16)"
             + ("; trump control 43 x 1" if rp in TRUMP_CONTROL else "") + ". Compare settings by prompt",
     "bench": [direct("--voice", "shehbaz", "--size", "prompts", "--takes", "6", "-c", "16",
                      "--extra-param", f"repetition_penalty={rp}", "--timeout", QUALITY_TIMEOUT, tag=f"rp{rp}")]
              + ([direct("--voice", "trump", "--size", "prompts", "-c", "16", "--extra-param", f"repetition_penalty={rp}",
                         "--timeout", QUALITY_TIMEOUT, tag=f"rp{rp}")] if rp in TRUMP_CONTROL else [])}
    for rp in RP_VALUES
]

# ---- P6: the Auralis Urdu pools (apples-to-apples with the team's XTTS/Auralis numbers; Auralis is never run) --------
PHASES += [
    {"name": "P6_auralis", "engine": engine(), "gateway": GW_PERF,
     "note": "Auralis Urdu pools short/medium/long: n=20 c=20 (their default) engine direct and via the gateway, "
             "plus a sweep c=1,4,8,16,32 (n=max(8,c))",
     "bench": [direct("--voice", "shehbaz", "--pools", pool_path(AURALIS_POOLS), "--size", "short", "medium", "long",
                      "-n", "20", "-c", "20", tag="n20c20"),
               direct("--voice", "shehbaz", "--pools", pool_path(AURALIS_POOLS), "--size", "short", "medium", "long",
                      "--sweep", "1,4,8,16,32", "--n-rule", "8:1", tag="sweep"),
               via_gateway("--voice", "shehbaz", "--pools", pool_path(AURALIS_POOLS), "--size", "short", "medium",
                           "long", "-n", "20", "-c", "20", tag="gw_n20c20")]},
]

# ---- P7: gateway overhead and live retries --------------------------------------------------------------------------
PHASES += [
    {"name": "P7_gateway", "engine": engine(), "gateway": {"TTS_RETRY_MAX": "1", "TTS_RETRY_ON": "suspect,engine_error"},
     "note": "gateway overhead (short, c=1,16, n=8,32: engine direct vs gateway retries 0) and live retries (shehbaz "
             "long c=32 n=64, where E01 saw runaways: engine direct with the cap vs gateway retries 1)",
     "bench": [direct("--voice", *VOICES, "--size", "short", "--sweep", "1,16", "--n-rule", "8:2", tag="direct"),
               via_gateway("--voice", *VOICES, "--size", "short", "--sweep", "1,16", "--n-rule", "8:2",
                           "--param", "retries=0", tag="gw_r0"),
               direct("--voice", "shehbaz", "--size", "long", "-c", "32", "-n", "64", tag="direct"),
               via_gateway("--voice", "shehbaz", "--size", "long", "-c", "32", "-n", "64", "--param", "retries=1",
                           tag="gw_r1")]},
]

# ---- extras (HANDOFF §8), on the default engine; compared by prompt with P5_urdu_rp105 (shehbaz K=6, trump K=1) ------
PHASES += [
    {"name": "X1_nsm", "engine": engine(), "kind": "quality",
     "checks": [{"name": "non_streaming_mode", "via": "engine", "voice": "shehbaz",
                 "fails": {"nsm_invalid": {"non_streaming_mode": "x"}},
                 "succeeds": {"nsm_true": {"non_streaming_mode": True}}}],
     "note": "non_streaming_mode=true (text not interleaved over the reference frames; source: serving_speech.py "
             "L2577 -> prompt_embeds_builder.py L952-963, Base default false): shehbaz 43 prompts x 1 take, vs P5_urdu_rp105",
     "bench": [direct("--voice", "shehbaz", "--size", "prompts", "-c", "16", "--extra-param", "repetition_penalty=1.05",
                      "--param", "non_streaming_mode=true", "--timeout", QUALITY_TIMEOUT, tag="nsm_true")]},
    {"name": "X1_nsm_trump", "engine": engine(), "kind": "quality", "optional": True,
     "note": "non_streaming_mode=true for trump: 43 prompts x 1, vs P5_urdu_rp105's trump control",
     "bench": [direct("--voice", "trump", "--size", "prompts", "-c", "16", "--extra-param", "repetition_penalty=1.05",
                      "--param", "non_streaming_mode=true", "--timeout", QUALITY_TIMEOUT, tag="nsm_true")]},
    {"name": "X6_nsm_long_urdu", "engine": engine(), "kind": "quality",
     "checks": [{"name": "non_streaming_mode", "via": "engine", "voice": "shehbaz",
                 "fails": {"nsm_invalid": {"non_streaming_mode": "x"}},
                 "succeeds": {"nsm_true": {"non_streaming_mode": True}}}],
     "note": "P2 found 31/68 shehbaz xxlong (~200 words, ~55 s) takes without EOS (hit the cap) vs 1/38 at xlong and "
             "0 for English. Hypothesis: with non_streaming_mode=false the text beyond the reference is fed one token "
             "per frame (12.5/s) and Urdu needs ~3.2 tokens/word, so the feed barely stays ahead of the speech. "
             "Paired arms, same 43 xxlong texts, c=16: non_streaming_mode false (default) vs true; plus xlong true",
     "bench": [direct("--voice", "shehbaz", "--size", "xxlong", "-n", "43", "-c", "16", "--timeout", QUALITY_TIMEOUT,
                      tag="nsm_false"),
               direct("--voice", "shehbaz", "--size", "xxlong", "-n", "43", "-c", "16", "--param",
                      "non_streaming_mode=true", "--timeout", QUALITY_TIMEOUT, tag="nsm_true"),
               direct("--voice", "trump", "--size", "xxlong", "-n", "43", "-c", "16", "--param",
                      "non_streaming_mode=true", "--timeout", QUALITY_TIMEOUT, tag="nsm_true")]},
    *[{"name": f"X7_split_{label}", "engine": engine(), "kind": "quality",
       "gateway": GW_PERF | {"TTS_RETRY_MAX": "0", "TTS_SPLIT_WORDS": words},
       "checks": [gateway_headers_check(f"split_{label}", {"x-tts-retries": ["0"]})],
       "note": f"gateway sentence splitting {label} (TTS_SPLIT_WORDS={words}; parts run in parallel on free slots), "
               "retries 0: shehbaz + trump xxlong (~200 words), 43 texts each, c=8 -- failure rate, skips and latency "
               "of long texts with and without splitting (P2: 31/68 unsplit shehbaz xxlong takes hit the cap)",
       "bench": [via_gateway("--voice", v, "--size", "xxlong", "-n", "43", "-c", "8", "--timeout", QUALITY_TIMEOUT,
                             tag=f"split_{label}") for v in ("shehbaz", "trump")]}
      for label, words in (("off", "0"), ("60", "60"))],
    {"name": "X2_language", "engine": engine(), "kind": "quality",
     "checks": [{"name": "language", "via": "engine", "voice": "trump", "fails": {"urdu": {"language": "Urdu"}},
                 "succeeds": {"auto": {"language": "Auto"}}}],
     "note": "trump with language Auto instead of English: 43 prompts x 1 take, vs P5_urdu_rp105's trump control",
     "bench": [direct("--voice", "trump", "--size", "prompts", "-c", "16", "--language", "Auto",
                      "--extra-param", "repetition_penalty=1.05", "--timeout", QUALITY_TIMEOUT, tag="lang_auto")]},
    {"name": "X3_custom_voice", "engine": engine(), "kind": "quality",
     "checks": [{"name": "custom_voices", "via": "engine", "voice": "shehbaz",
                 "base": {"voice": "shehbaz-prompt", "ref_audio": None, "ref_text": None},
                 "succeeds": {"avg": {"voice": "shehbaz-avg"}}, "listed": CUSTOM_VOICES}],
     "note": "engine custom voices: shehbaz-avg (speaker embedding averaged over the clips + ICL) vs shehbaz-prompt (the "
             "reference's own embedding + ICL), 43 prompts x 1 take each (trump has one clip: -avg = -prompt in effect)",
     "bench": [direct("--voice", "shehbaz", "--size", "prompts", "-c", "16", "--voice-mode", "server", "--voice-name",
                      "{voice}-" + name, "--timeout", QUALITY_TIMEOUT, tag=name) for name in ("prompt", "avg")]},
    {"name": "X4_length_cap", "engine": engine(),
     "checks": [{"name": "max_new_tokens", "via": "engine", "voice": "shehbaz", "fails": {"cap40": {"max_new_tokens": 40}}}],
     "note": "length cap on (the gateway's max_new_tokens) vs off (the engine's 12 x text-token cap + its built-in "
             "retry): shehbaz 43 prompts each, c=16",
     "bench": [direct("--voice", "shehbaz", "--size", "prompts", "-c", "16", tag="cap_on"),
               {"args": ["--voice", "shehbaz", "--size", "prompts", "-c", "16", *SAMPLING], "via": "engine",
                "tag": "cap_off"}]},
    {"name": "X5_mixed_voices", "engine": engine(),
     "note": "payload-leak guard (#4355): trump and shehbaz interleaved in one batch at c=16 (xlong n=16 per voice, "
             "short n=32 per voice); compare SIM with P2's single-voice runs; dup_audio counts identical PCM",
     "bench": [direct("--voice", *VOICES, "--mix", "--size", "xlong", "-c", "16", "-n", "16", tag="mix"),
               direct("--voice", *VOICES, "--mix", "--size", "short", "-c", "16", "-n", "32", tag="mix")]},
]

# ---- P8: quality on the 43 prompts per voice through the gateway: raw vs guardrails ---------------------------------
# The QC sidecar (Whisper large-v3 + WavLM) shares the GPU with the engine in the guard arm, and stage 0 at 0.60 leaves
# only ~4.4 GiB free. So all P8 arms run the engine with stage 0 at 0.45 (KV ~58k tokens: plenty for c=16) through
# `vllm serve --stage-overrides`, which 0.28 applies on top of --deploy-config (entrypoints/utils.py L405-407 ->
# config/config_factory.py L443-472 -> config/stage_config.py L47-89 and "CLI overrides take precedence over YAML
# defaults" ~L1085); phase.json's engine log findings show the resulting KV line. If the QC still does not fit, set
# QC_ENV = {"TTS_QC_DEVICE": "cpu"} above (slower checks; the gateway fails open on QC timeouts).
P8_ENGINE = engine(CHOSEN, CHOSEN_VENV, "--stage-overrides", '{"0": {"gpu_memory_utilization": 0.40}}')
P8_BENCH = ["--voice", *VOICES, "--size", "prompts", "-c", "16", "--timeout", QUALITY_TIMEOUT]
PHASES += [
    {"name": "P8_quality_raw", "engine": P8_ENGINE, "gateway": GW_PERF, "kind": "quality",
     "checks": [gateway_headers_check("raw_headers", {"x-tts-qc": ["off"], "x-tts-retries": ["0"]})],
     "note": "quality before guardrails: 43 prompts per voice via the gateway, retries 0, QC off (c=16)",
     "bench": [via_gateway(*P8_BENCH, tag="raw")]},
    {"name": "P8_quality_guard", "engine": P8_ENGINE, "gateway": GUARD, "qc": True, "kind": "quality",
     "checks": [gateway_headers_check("qc_consulted", {"x-tts-qc": ["pass", "fail"]})],
     "note": "quality after guardrails: the same prompts with retries (max 2 on suspect, engine error, QC fail) and "
             "the QC sidecar (ASR + SIM + audio checks) on the same GPU",
     "bench": [via_gateway(*P8_BENCH, tag="guard")]},
    {"name": "P8_quality_guard_fast", "engine": P8_ENGINE, "kind": "quality",
     "gateway": GUARD | {"TTS_QC_TIMEOUT_S": "120"},
     "qc": {"TTS_QC_BEAM": "1", "TTS_QC_WORKERS": "4"},
     "checks": [gateway_headers_check("qc_consulted", {"x-tts-qc": ["pass", "fail"]})],
     "note": "P8_quality_guard with a lighter online check: greedy Whisper (beam 1), 4 CTranslate2 workers, QC timeout "
             "120 s. The beam-5 sidecar needed p50 24 s (en) / 58 s (ur) per take next to the engine at c=16 and most "
             "calls hit the 30 s gateway timeout",
     "bench": [via_gateway(*P8_BENCH, tag="guardfast")]},
    {"name": "P8_quality_retry", "engine": P8_ENGINE, "gateway": {"TTS_RETRY_MAX": "2",
                                                                 "TTS_RETRY_ON": "suspect,engine_error"},
     "kind": "quality", "optional": True, "note": "ablation: retries on pace/engine errors only, no QC sidecar",
     "bench": [via_gateway(*P8_BENCH, tag="retry")]},
]

# ---- P9: the plain qwen-tts 0.1.1 baseline (static batching, no streaming) ------------------------------------------
PHASES += [
    {"name": "P9_baseline_b8", "engine": qwentts("--max-batch", "8"),
     "note": "qwen-tts baseline, max batch 8, prompt cache on: short + xlong c=1..16, xxlong c=1,8, both voices",
     "bench": [direct("--voice", *VOICES, "--size", "short", "--sweep", "1,2,4,8,16", "--n-rule", "8:2",
                      "--timeout", "1800"),
               direct("--voice", *VOICES, "--size", "xlong", "--sweep", "1,2,4,8,16", "--n-rule", "4:1",
                      "--timeout", "1800"),
               direct("--voice", *VOICES, "--size", "xxlong", "--sweep", "1,8", "--n-rule", "2:1", "--timeout", "2400")]},
    {"name": "P9_baseline_b1", "engine": qwentts("--max-batch", "1"),
     "note": "qwen-tts baseline, max batch 1 (requests queue): short + xlong at c=1,4",
     "bench": [direct("--voice", *VOICES, "--size", "short", "--sweep", "1,4", "-n", "8", "--timeout", "1800"),
               direct("--voice", *VOICES, "--size", "xlong", "--sweep", "1,4", "-n", "4", "--timeout", "2400")]},
    {"name": "P9_baseline_nocache", "engine": qwentts("--max-batch", "8", "--no-prompt-cache"),
     "note": "qwen-tts baseline, prompt cache off (reference re-encoded per request): short + xlong at c=1,8",
     "bench": [direct("--voice", *VOICES, "--size", "short", "--sweep", "1,8", "--n-rule", "8:2", "--timeout", "1800"),
               direct("--voice", *VOICES, "--size", "xlong", "--sweep", "1,8", "--n-rule", "4:1", "--timeout", "2400")]},
    {"name": "P9_baseline_avg", "engine": qwentts("--max-batch", "8", "--avg-embedding"), "optional": True,
     "note": "qwen-tts baseline with the averaged speaker embedding (NOTES.md recipe): shehbaz 43 prompts",
     "bench": [direct("--voice", "shehbaz", "--size", "prompts", "-c", "8", "--timeout", "2400")]},
]

for _ph in PHASES:                     # the custom-voices engine needs its precomputed voices
    if isinstance(_ph.get("engine"), dict) and _ph["engine"].get("variant") == "custom_voices":
        _ph.setdefault("requires", []).append(CUSTOM_VOICE_MANIFEST)
