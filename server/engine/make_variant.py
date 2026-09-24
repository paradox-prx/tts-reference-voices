#!/usr/bin/env python3
"""Generate vLLM-Omni deploy YAML variants for the benchmark from a base deploy YAML.

  make_variant.py NAME [overrides]     write engine/deploy/variants/NAME.yaml
  make_variant.py --standard           write every variant the benchmark plan uses (see STANDARD)
  make_variant.py --validate FILE...   only validate existing deploy YAMLs

Every file is checked against the deploy schema of vllm_omni 0.28.0 / 0.30.0rc1 config/stage_config.py
(unknown keys are silently dropped by the upstream loader, so typos are errors here). With --check VENV the
files are also loaded by the REAL upstream loader inside that engine venv (load_deploy_config +
merge_pipeline_deploy with the Qwen3-TTS pipeline; GPUs hidden, nothing touches CUDA) and the resolved per-stage
engine args are compared with the file. Needs PyYAML (run it with venvs/gateway/bin/python).

Where things live (0.28.0 source):
  async_chunk        top-level `async_chunk:` (DeployConfig, stage_config.py L507/L715), copied into every stage's
                     engine args (L912); the CLI --async-chunk/--no-async-chunk overrides it (config_factory.py
                     L456-458). 0.30 also accepts a per-stage opt-out, which must match across the 0->1 edge.
  chunking/batching  connectors.connector_of_shared_memory.extra (read by qwen3_tts_code2wav.py L663-688 and
                     stage_input_processors/qwen3_tts.py L106)
  per-stage knobs    stages[i] (StageDeployConfig; other keys such as `dtype` pass through to vLLM EngineArgs)
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ENGINE = Path(__file__).resolve().parent
BASE = ENGINE / "deploy" / "qwen3_tts_prod.yaml"
OUT_DIR = ENGINE / "deploy" / "variants"
CONNECTOR = "connector_of_shared_memory"
DTYPES = ("bfloat16", "float16", "float32")

# name -> (overrides, why). "default" is the production file itself.
STANDARD: dict[str, tuple[list[str], str]] = {
    "default": ([], "production settings (engine/deploy/qwen3_tts_prod.yaml)"),
    "no_async_chunk": (["--async-chunk", "false"],
                       "whole-utterance Code2Wav (same as the CLI --no-async-chunk); streaming returns at the end"),
    "eager": (["--enforce-eager", "both"], "no CUDA graphs in either stage"),
    "fp16_talker": (["--talker-dtype", "float16"], "talker + code predictor in fp16"),
    "fp32_talker": (["--talker-dtype", "float32", "--mem0", "0.55", "--max-num-batched-tokens", "8192"],
                    "talker + code predictor in fp32: weights double to ~7.4 GiB and KV to 224 KiB/token, so stage 0 "
                    "gets 0.55 and a smaller profiling batch (8192) to leave ~4 GiB of KV (~19k tokens)"),
    "seqs32": (["--max-num-seqs", "32"], "32 sequences per stage"),
    "seqs128": (["--max-num-seqs", "128"],
                "128 sequences per stage at the production memory budget (KV ~45k tokens is the real limit)"),
    "rp110": (["--rep-penalty", "1.10"], "talker repetition_penalty 1.10"),
    "rp115": (["--rep-penalty", "1.15"], "talker repetition_penalty 1.15"),
    "rp120": (["--rep-penalty", "1.20"], "talker repetition_penalty 1.20"),
    "decode8": (["--decode-batch-max-size", "8", "--decode-graph-batch-sizes", "1,2,4,8"],
                "Code2Wav decodes up to 8 streams per group, with CUDA graphs for batch 1/2/4/8"),
    "mrv2": (["--model-runner", "v2", "--max-num-batched-tokens", "512", "--code2wav-dtype", "bfloat16"],
             "0.30.0rc1 upstream defaults (MRV2 runner, 512-token steps, bf16 Code2Wav); 0.28 ignores model_runner"),
}

# Deploy schema, read from vllm_omni config/stage_config.py (DeployConfig, StageDeployConfig, load_deploy_config).
TOP_KEYS = {"async_chunk", "session_mode", "active_stream_window", "duplex_session", "connectors", "edges", "stages",
            "platforms", "pipeline", "trust_remote_code", "distributed_executor_backend", "dtype", "quantization",
            "enable_prefix_caching", "enable_chunked_prefill", "data_parallel_size", "pipeline_parallel_size",
            "custom_voice_dir"}
TOP_KEYS_030 = {"model_runner"}
STAGE_KEYS = {"stage_id", "devices", "num_replicas", "env", "output_connectors", "input_connectors",
              "default_sampling_params", "default_pooling_params", "subtalker_sampling_params", "silence_ban_frames",
              "tensor_parallel_size", "enable_expert_parallel", "gpu_memory_utilization", "max_num_seqs",
              "max_num_batched_tokens", "max_model_len", "enforce_eager", "async_scheduling",
              "disable_hybrid_kv_cache_manager", "mm_processor_cache_gb", "compilation_config", "profiler_config",
              "skip_mm_profiling", "enable_flashinfer_autotune", "config_format", "load_format", "tokenizer_mode",
              "engine_extras", "engine_args", "runtime",
              # pass-through vLLM EngineArgs used per stage
              "trust_remote_code", "enable_prefix_caching", "dtype", "kv_cache_dtype", "kv_cache_memory_bytes",
              "seed", "block_size", "quantization"}
STAGE_KEYS_030 = {"async_chunk"}
SAMPLING_KEYS = {"temperature", "top_p", "top_k", "min_p", "max_tokens", "min_tokens", "repetition_penalty",
                 "presence_penalty", "frequency_penalty", "seed", "stop_token_ids", "detokenize", "ignore_eos"}
MEMORY_WARN = 0.75  # summed utilisation per device above this may not fit next to the ~4.4 GiB tenant on GPU 1


def _bool(text: str) -> bool:
    if text.lower() in ("true", "1", "yes", "on"):
        return True
    if text.lower() in ("false", "0", "no", "off"):
        return False
    raise argparse.ArgumentTypeError(f"expected true/false, got {text!r}")


def _fraction(text: str) -> float:
    value = float(text)
    if not 0.0 < value <= 1.0:
        raise argparse.ArgumentTypeError(f"expected a fraction in (0, 1], got {text}")
    return value


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"expected an integer >= 1, got {text}")
    return value


def _int_list(text: str) -> list[int]:
    values = [int(part) for part in text.split(",") if part.strip()]
    if not values or min(values) < 1:
        raise argparse.ArgumentTypeError(f"expected a comma-separated list of integers >= 1, got {text!r}")
    return sorted(set(values))


def add_override_args(parser: argparse.ArgumentParser) -> list[argparse.Action]:
    """Register the override flags; returns their actions so a namespace can be turned back into flags."""
    g = parser.add_argument_group("overrides (stage 0 = talker + code predictor, stage 1 = Code2Wav)")
    actions = [
        g.add_argument("--talker-dtype", choices=DTYPES,
                       help="stage 0 dtype (talker + code predictor; the speaker and codec encoders stay bf16)"),
        g.add_argument("--code2wav-dtype", choices=DTYPES,
                       help="stage 1 dtype. Honoured by 0.30.0rc1 only: 0.28.0 always runs the decoder in fp32 "
                            "(qwen3_tts_code2wav.py L561)"),
        g.add_argument("--max-num-seqs", type=_positive_int, help="max_num_seqs of both stages"),
        g.add_argument("--code2wav-max-num-seqs", type=_positive_int,
                       help="stage 1 max_num_seqs (applied after --max-num-seqs)"),
        g.add_argument("--mem0", type=_fraction, help="stage 0 gpu_memory_utilization"),
        g.add_argument("--mem1", type=_fraction, help="stage 1 gpu_memory_utilization"),
        g.add_argument("--async-chunk", type=_bool, metavar="{true,false}", help="top-level async_chunk"),
        g.add_argument("--enforce-eager", choices=("none", "talker", "code2wav", "both"),
                       help="stages that run without CUDA graphs"),
        g.add_argument("--rep-penalty", type=float, help="stage 0 default repetition_penalty (codebook 0 only)"),
        g.add_argument("--decode-batch-max-size", type=int, help="Code2Wav streams per decode group (0 = unlimited)"),
        g.add_argument("--decode-graph-batch-sizes", type=_int_list, metavar="N,N,...",
                       help="Code2Wav CUDA graph batch buckets (decode_cudagraph_batch_sizes)"),
        g.add_argument("--max-num-batched-tokens", type=_positive_int,
                       help="stage 0 max_num_batched_tokens (stage 1 keeps 65536, a correctness floor)"),
        g.add_argument("--initial-chunk-frames", type=int,
                       help="initial_codec_chunk_frames: frames in the first streamed chunk (0 = load-based dynamic)"),
        g.add_argument("--model-runner", choices=("v1", "v2"),
                       help="top-level model_runner. 0.30.0rc1 only; 0.28.0 ignores the key"),
    ]
    return actions


def stage(doc: dict[str, Any], stage_id: int) -> dict[str, Any]:
    for entry in doc.get("stages") or []:
        if entry.get("stage_id") == stage_id:
            return entry
    raise SystemExit(f"base YAML has no stage {stage_id}")


def apply_overrides(doc: dict[str, Any], a: argparse.Namespace) -> dict[str, Any]:
    """Return a copy of doc with the overrides applied."""
    doc = copy.deepcopy(doc)
    talker, code2wav = stage(doc, 0), stage(doc, 1)
    extra = doc["connectors"][CONNECTOR].setdefault("extra", {})
    if a.talker_dtype:
        talker["dtype"] = a.talker_dtype
    if a.code2wav_dtype:
        code2wav["dtype"] = a.code2wav_dtype
    if a.max_num_seqs:
        talker["max_num_seqs"] = code2wav["max_num_seqs"] = a.max_num_seqs
    if a.code2wav_max_num_seqs:
        code2wav["max_num_seqs"] = a.code2wav_max_num_seqs
    if a.mem0:
        talker["gpu_memory_utilization"] = a.mem0
    if a.mem1:
        code2wav["gpu_memory_utilization"] = a.mem1
    if a.async_chunk is not None:
        doc["async_chunk"] = a.async_chunk
    if a.enforce_eager:
        talker["enforce_eager"] = a.enforce_eager in ("talker", "both")
        code2wav["enforce_eager"] = a.enforce_eager in ("code2wav", "both")
    if a.rep_penalty is not None:
        talker.setdefault("default_sampling_params", {})["repetition_penalty"] = a.rep_penalty
    if a.decode_batch_max_size is not None:
        extra["decode_batch_max_size"] = a.decode_batch_max_size
    if a.decode_graph_batch_sizes:
        extra["decode_cudagraph_batch_sizes"] = a.decode_graph_batch_sizes
    if a.max_num_batched_tokens:
        talker["max_num_batched_tokens"] = a.max_num_batched_tokens
    if a.initial_chunk_frames is not None:
        extra["initial_codec_chunk_frames"] = a.initial_chunk_frames
    if a.model_runner:
        doc["model_runner"] = a.model_runner
    return doc


def validate(doc: Any) -> tuple[list[str], list[str]]:
    """Schema and value checks for a Qwen3-TTS deploy YAML. Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(doc, dict):
        return ["top level is not a mapping"], warnings
    for key in sorted(set(doc) - TOP_KEYS - TOP_KEYS_030):
        errors.append(f"unknown top-level key {key!r} (the loader would drop it)")
    if "model_runner" in doc:
        if doc["model_runner"] not in ("v1", "v2"):
            errors.append("model_runner must be v1 or v2")
        warnings.append("model_runner is read by 0.30.0rc1 only; 0.28.0 ignores it")
    if not isinstance(doc.get("async_chunk", True), bool):
        errors.append("async_chunk must be a boolean")

    connectors = doc.get("connectors")
    if not isinstance(connectors, dict) or not isinstance(connectors.get(CONNECTOR), dict):
        errors.append(f"connectors.{CONNECTOR} is missing (0.28 does not merge connectors from the bundled YAML)")
        extra: dict[str, Any] = {}
    else:
        extra = connectors[CONNECTOR].get("extra") or {}
        if connectors[CONNECTOR].get("name") != "SharedMemoryConnector":
            errors.append(f"connectors.{CONNECTOR}.name must be SharedMemoryConnector")
    for key in ("codec_chunk_frames", "codec_left_context_frames"):
        if not isinstance(extra.get(key), int) or extra[key] <= 0:
            errors.append(f"connector extra {key} must be a positive integer")
    for key in ("initial_codec_chunk_frames", "decode_batch_max_size"):
        if key in extra and (not isinstance(extra[key], int) or extra[key] < 0):
            errors.append(f"connector extra {key} must be an integer >= 0")
    sizes = extra.get("decode_cudagraph_batch_sizes")
    if sizes is not None and (not isinstance(sizes, list) or not all(isinstance(s, int) and s > 0 for s in sizes)):
        errors.append("decode_cudagraph_batch_sizes must be a list of positive integers")

    stages = doc.get("stages")
    if not isinstance(stages, list) or not all(isinstance(s, dict) for s in stages) \
            or [s.get("stage_id") for s in stages] not in ([0, 1], [1, 0]):
        errors.append("stages must list exactly stage_id 0 (talker) and 1 (code2wav)")
        return errors, warnings
    memory: dict[str, float] = {}
    for s in stages:
        sid = s["stage_id"]
        where = f"stage {sid}"
        for key in sorted(set(s) - STAGE_KEYS - STAGE_KEYS_030):
            errors.append(f"{where}: unknown key {key!r} (it would reach vLLM EngineArgs unchecked)")
        if "async_chunk" in s:
            warnings.append(f"{where}: per-stage async_chunk is read by 0.30.0rc1 only")
        util = s.get("gpu_memory_utilization")
        if not isinstance(util, (int, float)) or not 0.0 < util <= 1.0:
            errors.append(f"{where}: gpu_memory_utilization must be in (0, 1]")
        else:
            device = str(s.get("devices", "0"))
            memory[device] = memory.get(device, 0.0) + float(util)
        if not isinstance(s.get("devices"), str):
            errors.append(f"{where}: devices must be a quoted string such as \"0\"")
        for key in ("max_num_seqs", "max_num_batched_tokens", "max_model_len"):
            if not isinstance(s.get(key), int) or s[key] < 1:
                errors.append(f"{where}: {key} must be a positive integer")
        for key in ("enforce_eager", "async_scheduling", "enable_prefix_caching", "trust_remote_code"):
            if key in s and not isinstance(s[key], bool):
                errors.append(f"{where}: {key} must be a boolean")
        if "dtype" in s and s["dtype"] not in (*DTYPES, "auto", "half", "float"):
            errors.append(f"{where}: unsupported dtype {s['dtype']!r}")
        sampling = s.get("default_sampling_params") or {}
        for key in sorted(set(sampling) - SAMPLING_KEYS):
            errors.append(f"{where}: unknown default_sampling_params key {key!r}")
        rp = sampling.get("repetition_penalty", 1.0)
        if isinstance(rp, bool) or not isinstance(rp, (int, float)) or not math.isfinite(rp) or rp <= 0:
            errors.append(f"{where}: repetition_penalty must be a finite number > 0")
        if sampling.get("min_tokens", 0) > sampling.get("max_tokens", math.inf):
            errors.append(f"{where}: min_tokens exceeds max_tokens")
    talker, code2wav = stage(doc, 0), stage(doc, 1)
    if (talker.get("output_connectors") or {}).get("to_stage_1") != CONNECTOR:
        errors.append(f"stage 0 output_connectors.to_stage_1 must be {CONNECTOR}")
    if (code2wav.get("input_connectors") or {}).get("from_stage_0") != CONNECTOR:
        errors.append(f"stage 1 input_connectors.from_stage_0 must be {CONNECTOR}")
    if isinstance(code2wav.get("max_num_batched_tokens"), int) and code2wav["max_num_batched_tokens"] % 16:
        errors.append("stage 1 max_num_batched_tokens must be divisible by the 16 codebooks")
    if isinstance(talker.get("max_num_batched_tokens"), int) and isinstance(talker.get("max_num_seqs"), int) \
            and talker["max_num_batched_tokens"] < talker["max_num_seqs"]:
        errors.append("stage 0 max_num_batched_tokens is below max_num_seqs")
    for device, total in memory.items():
        if total > 1.0:
            errors.append(f"device {device}: gpu_memory_utilization sums to {total:.2f} > 1")
        elif total > MEMORY_WARN:
            warnings.append(f"device {device}: gpu_memory_utilization sums to {total:.2f}; "
                            "tight next to the ~4.4 GiB tenant on GPU 1")
    return errors, warnings


# Runs inside an engine venv. The real upstream loader resolves each file; GPUs are hidden and the platform is fixed
# to "cuda" so nothing queries NVML or initialises CUDA.
LOADER_CHECK = r"""
import json, sys
from vllm_omni.config import stage_config as sc
from vllm_omni.model_executor.models.qwen3_tts.pipeline import QWEN3_TTS_PIPELINE

_platform = sc._apply_platform_overrides
sc._apply_platform_overrides = lambda deploy, platform=None: _platform(deploy, "cuda")
out = {}
for path in sys.argv[1:]:
    deploy = sc.load_deploy_config(path)
    connectors = sc.to_dict(sc.create_config(deploy.connectors or {}))
    stages = {}
    for cfg in sc.merge_pipeline_deploy(QWEN3_TTS_PIPELINE, deploy, {}):
        stages[str(cfg.stage_id)] = sc.to_dict(cfg.to_omegaconf())
    out[path] = {"model_runner_supported": hasattr(sc.DeployConfig, "model_runner"),
                 "connectors": connectors, "stages": stages}
print(json.dumps(out, default=str))
"""


def loader_python(target: str) -> str:
    path = Path(target)
    return str(path / "bin" / "python") if path.is_dir() else str(path)


def run_loader_check(python: str, files: list[Path]) -> dict[str, Any]:
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTORCH_NVML_BASED_CUDA_CHECK": "1",
           "VLLM_LOGGING_LEVEL": "WARNING", "PYTHONDONTWRITEBYTECODE": "1"}
    r = subprocess.run([python, "-c", LOADER_CHECK, *map(str, files)], capture_output=True, text=True, env=env,
                       timeout=600)
    if r.returncode != 0:
        raise SystemExit(f"upstream loader failed ({python}):\n{r.stderr.strip()[-3000:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def compare_resolved(doc: dict[str, Any], resolved: dict[str, Any]) -> list[str]:
    """Differences between what the file says and what the upstream loader resolved."""
    problems: list[str] = []
    extra = doc["connectors"][CONNECTOR].get("extra") or {}
    got_extra = resolved["connectors"].get(CONNECTOR, {}).get("extra", {})
    problems += [f"connector extra {k}: file {v!r}, loader {got_extra.get(k)!r}"
                 for k, v in extra.items() if got_extra.get(k) != v]
    for s in doc["stages"]:
        sid = str(s["stage_id"])
        if (got := resolved["stages"].get(sid)) is None:
            problems.append(f"stage {sid} missing after merge")
            continue
        args, runtime = got["engine_args"], got["runtime"]
        wanted = {k: s[k] for k in ("gpu_memory_utilization", "max_num_seqs", "max_num_batched_tokens",
                                    "max_model_len", "enforce_eager", "dtype") if k in s}
        wanted["async_chunk"] = doc.get("async_chunk", True)
        if resolved["model_runner_supported"]:
            wanted["use_v2_model_runner"] = doc.get("model_runner") == "v2"
        problems += [f"stage {sid} {k}: file {v!r}, loader {args.get(k)!r}"
                     for k, v in wanted.items() if args.get(k) != v]
        if runtime.get("devices") != s.get("devices"):
            problems.append(f"stage {sid} devices: file {s.get('devices')!r}, loader {runtime.get('devices')!r}")
        sampling = got.get("default_sampling_params") or {}
        problems += [f"stage {sid} default_sampling_params.{k}: file {v!r}, loader {sampling.get(k)!r}"
                     for k, v in (s.get("default_sampling_params") or {}).items() if sampling.get(k) != v]
    return problems


def override_tokens(actions: list[argparse.Action], ns: argparse.Namespace) -> list[str]:
    """The override flags set in ns, in canonical form (stored in the variant header)."""
    tokens: list[str] = []
    for action in actions:
        value = getattr(ns, action.dest)
        if value is None:
            continue
        if isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, list):
            value = ",".join(map(str, value))
        tokens += [action.option_strings[0], str(value)]
    return tokens


def parse_overrides(flags: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="override", add_help=False)
    add_override_args(parser)
    return parser.parse_args(flags)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(name: str, doc: dict[str, Any], base: Path, overrides: list[str], why: str) -> str:
    base = base.resolve()
    shown = base.relative_to(ENGINE.parent) if base.is_relative_to(ENGINE.parent) else base
    header = ["# GENERATED by engine/make_variant.py - do not edit, regenerate instead.",
              f"# variant:   {name}: {why}",
              f"# base:      {shown} (sha256 {sha256(base)[:16]})",
              f"# overrides: {' '.join(overrides) or '(none)'}"]
    body = yaml.safe_dump(doc, sort_keys=False, default_flow_style=False, allow_unicode=True, width=120)
    return "\n".join(header) + "\n" + body


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def report(path: Path, doc: Any) -> bool:
    errors, warnings = validate(doc)
    for w in warnings:
        print(f"{path}: warning: {w}")
    for e in errors:
        print(f"{path}: error: {e}")
    if not errors:
        print(f"{path}: ok")
    return not errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("name", nargs="?", help="variant name: writes <out-dir>/<name>.yaml")
    mode.add_argument("--standard", action="store_true", help=f"write the standard set: {', '.join(STANDARD)}")
    mode.add_argument("--validate", nargs="+", type=Path, metavar="YAML", help="validate existing files only")
    ap.add_argument("--base", type=Path, default=BASE, help="base deploy YAML (default: %(default)s)")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR, help="output directory (default: %(default)s)")
    ap.add_argument("--check", metavar="VENV|PYTHON",
                    help="also resolve the files with the real vllm_omni loader of this engine venv (no CUDA)")
    ap.add_argument("--why", default="custom variant", help="one-line description stored in the header")
    actions = add_override_args(ap)
    a = ap.parse_args()
    tokens = override_tokens(actions, a)
    if (a.standard or a.validate) and tokens:
        ap.error("overrides apply to a single named variant only")

    jobs: list[tuple[Path, Any]] = []
    if a.validate:
        jobs = [(path, load(path)) for path in a.validate]
    else:
        base_doc = load(a.base)
        if validate(base_doc)[0]:
            report(a.base, base_doc)
            return 1
        todo = STANDARD.items() if a.standard else [(a.name, (tokens, a.why))]
        a.out_dir.mkdir(parents=True, exist_ok=True)
        for name, (flags, why) in todo:
            if not name.replace("_", "").replace("-", "").isalnum():
                ap.error(f"bad variant name {name!r}")
            path = a.out_dir / f"{name}.yaml"
            path.write_text(render(name, apply_overrides(base_doc, parse_overrides(flags)), a.base, flags, why),
                            encoding="utf-8")
            jobs.append((path, load(path)))

    ok = all([report(path, doc) for path, doc in jobs])
    if ok and a.check:
        resolved = run_loader_check(loader_python(a.check), [p for p, _ in jobs])
        for path, doc in jobs:
            problems = compare_resolved(doc, resolved[str(path)])
            for problem in problems:
                print(f"{path}: loader mismatch: {problem}")
            if not problems:
                print(f"{path}: upstream loader ok")
            ok &= not problems
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
