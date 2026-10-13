#!/usr/bin/env python3
"""Check a Higgs GGUF against the original checkpoint, tensor by tensor, through the same reader the vLLM loader uses.

    python scripts/verify_gguf.py weights/higgs-tts-3-4b-BF16/model.gguf [--model <snapshot>] [--json out.json]

For every checkpoint tensor: present, same shape, and either bit-identical (stored as BF16/F32) or within the
quantisation error of its GGML type (reports relative RMS error and max abs error; fails above --max-rel-rms).
Exit status 0 only if every tensor passes.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import torch  # noqa: E402
from gguf import GGMLQuantizationType as T, GGUFReader  # noqa: E402

from convert_higgs_to_gguf import DEFAULT_REPO, hf_snapshot, open_checkpoint  # noqa: E402
from higgs_gguf.reader import aliases, tensor_map, to_torch  # noqa: E402
from safetensors import safe_open  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gguf")
    ap.add_argument("--model", help=f"checkpoint dir (default: {DEFAULT_REPO} from the HF cache)")
    ap.add_argument("--max-rel-rms", type=float, default=0.02, help="fail a quantised tensor above this (default 2%%)")
    ap.add_argument("--json", help="write per-tensor results here")
    a = ap.parse_args()

    model_dir = Path(a.model).resolve() if a.model else hf_snapshot(DEFAULT_REPO)
    where = open_checkpoint(model_dir)
    handles = {f: safe_open(str(f), "pt") for f in set(where.values())}
    r = GGUFReader(a.gguf, "r")
    gmap = tensor_map(r)
    alias_of = {dup: src for src, dups in aliases(r).items() for dup in dups}
    by_hf = {gmap[t.name]: t for t in r.tensors}

    t0 = time.time()
    rows, fails = [], []
    for hf in where:
        ref = handles[where[hf]].get_tensor(hf)
        src = alias_of.get(hf, hf)
        if src not in by_hf:
            fails.append((hf, "missing"))
            continue
        t = by_hf[src]
        got = to_torch(t, None)
        row = {"name": hf, "gguf": t.name, "alias_of": alias_of.get(hf), "type": t.tensor_type.name, "shape": list(ref.shape)}
        if tuple(got.shape) != tuple(ref.shape):
            fails.append((hf, f"shape {tuple(got.shape)} != {tuple(ref.shape)}"))
            continue
        if t.tensor_type in (T.BF16, T.F32, T.F16):
            row["exact"] = bool(torch.equal(got.to(ref.dtype), ref))
            if not row["exact"]:
                fails.append((hf, f"{t.tensor_type.name} not bit-identical"))
        else:
            rf, gf = ref.float(), got.float()
            err = gf - rf
            rel = (err.pow(2).mean().sqrt() / rf.pow(2).mean().sqrt().clamp_min(1e-12)).item()
            row |= {"rel_rms": rel, "max_abs": err.abs().max().item(),
                    "bf16_after_load_exact": bool(torch.equal(got.to(torch.bfloat16), ref))}
            if rel > a.max_rel_rms:
                fails.append((hf, f"rel RMS {rel:.4f} > {a.max_rel_rms}"))
        rows.append(row)
    extra = set(by_hf) - set(where)
    for e in sorted(extra):
        fails.append((e, "in GGUF but not in the checkpoint"))

    q = [x for x in rows if "rel_rms" in x]
    print(f"{a.gguf}: {len(r.tensors)} GGUF tensors, {len(where)} checkpoint tensors, {len(alias_of)} stored as aliases, "
          f"{time.time() - t0:.0f}s")
    print(f"  exact (BF16/F32): {sum(1 for x in rows if x.get('exact'))}/{sum(1 for x in rows if 'exact' in x)}")
    if q:
        rels = sorted(x["rel_rms"] for x in q)
        print(f"  quantised: {len(q)} tensors, rel RMS error median {rels[len(rels) // 2]:.5f}, max {rels[-1]:.5f}, "
              f"max abs {max(x['max_abs'] for x in q):.5f}")
    for name, why in fails[:20]:
        print(f"  FAIL {name}: {why}")
    print("PASS" if not fails else f"FAIL ({len(fails)} tensors)")
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps({"gguf": a.gguf, "source": str(model_dir), "aliases": alias_of,
                                            "pass": not fails, "fails": fails, "tensors": rows}, indent=1) + "\n")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
