#!/usr/bin/env python3
"""Convert the Higgs TTS 3 checkpoint (bosonai/higgs-tts-3-4b, HF safetensors) to a single GGUF file.

    python scripts/convert_higgs_to_gguf.py --outtype q8_0
    python scripts/convert_higgs_to_gguf.py --outtype bf16 --model /path/to/snapshot --out weights/x/model.gguf

Writes weights/higgs-tts-3-4b-<OUTTYPE>/model.gguf plus the config/tokenizer files vLLM needs next to it (the same
files are also embedded in the GGUF metadata; scripts/gguf_model_dir.py re-extracts them from a lone .gguf).

Every tensor of the checkpoint is kept (929). The text and audio output heads are bit-identical copies of the
input embeddings in this checkpoint (tied weights); they are stored once and recorded as aliases that readers
re-emit, which saves 0.8 GB. Tensor names and quantisation policy: higgs_gguf/names.py, higgs_gguf/quant.py.
The file is streamed tensor by tensor, so RAM use stays around the largest tensor (~3 GB for the 151936 x 2560
embedding in float32 while quantising).

Licence: the weights are under Boson's research / non-commercial licence; a converted file inherits it.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from gguf import GGMLQuantizationType as T, GGUFWriter  # noqa: E402
from gguf.quants import quantize  # noqa: E402
from safetensors import safe_open  # noqa: E402

from higgs_gguf import names, quant  # noqa: E402

DEFAULT_REPO = "bosonai/higgs-tts-3-4b"


def hf_snapshot(repo: str) -> Path:
    import os
    hub = Path(os.environ.get("HF_HUB_CACHE") or Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "hub")
    d = hub / f"models--{repo.replace('/', '--')}"
    ref = d / "refs" / "main"
    if not ref.is_file():
        sys.exit(f"{repo} is not in the HF cache ({hub}); pass --model <snapshot dir>")
    return d / "snapshots" / ref.read_text().strip()


def open_checkpoint(model_dir: Path) -> dict[str, Path]:
    """checkpoint tensor name -> safetensors file holding it. Reads the keys of every file rather than trusting
    model.safetensors.index.json: Boson's index omits the two tied output heads that the file does contain (and
    vLLM's safetensors iterator yields)."""
    files = sorted(model_dir.glob("*.safetensors"))
    if not files:
        sys.exit(f"no *.safetensors in {model_dir}")
    out = {}
    for f in files:
        with safe_open(str(f), "pt") as sf:
            out.update({k: f for k in sf.keys()})
    return out


def encode(x: torch.Tensor, qtype: T) -> np.ndarray:
    """torch tensor -> the bytes (uint8, or float32 for F32) GGUFWriter.write_tensor_data expects for `qtype`."""
    if qtype == T.F32:
        return x.to(torch.float32).contiguous().numpy()
    if qtype == T.BF16:
        return x.to(torch.bfloat16).contiguous().view(torch.int16).numpy().view(np.uint8)
    return quantize(x.to(torch.float32).contiguous().numpy(), qtype)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", help=f"checkpoint dir (default: {DEFAULT_REPO} from the HF cache)")
    ap.add_argument("--outtype", choices=list(quant.OUTTYPES), default="q8_0")
    ap.add_argument("--out", help="output .gguf (default weights/higgs-tts-3-4b-<OUTTYPE>/model.gguf)")
    ap.add_argument("--quantize-audio", action="store_true", help="also quantise audio_embd/audio_head to Q8_0")
    ap.add_argument("--keep-tied-heads", action="store_true",
                    help="store output / audio_head even when they are bit-identical copies of the embeddings")
    ap.add_argument("--no-side-files", action="store_true", help="do not write config/tokenizer files next to it")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output")
    a = ap.parse_args()

    model_dir = Path(a.model).resolve() if a.model else hf_snapshot(DEFAULT_REPO).resolve()
    out = Path(a.out) if a.out else ROOT / "weights" / f"higgs-tts-3-4b-{a.outtype.upper()}" / "model.gguf"
    if out.exists() and not a.force:
        sys.exit(f"{out} exists (use --force)")
    out.parent.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((model_dir / "config.json").read_text())
    tc = cfg["text_config"]
    where = open_checkpoint(model_dir)
    handles = {f: safe_open(str(f), "pt") for f in set(where.values())}

    def load(name: str) -> torch.Tensor:
        return handles[where[name]].get_tensor(name)

    def shape_of(name: str) -> tuple[int, ...]:
        return tuple(handles[where[name]].get_slice(name).get_shape())

    alias: dict[str, str] = {}  # dropped copy -> stored source
    if not a.keep_tied_heads:
        for head, src in names.TIED_HEADS.items():
            if head in where and src in where and torch.equal(load(head), load(src)):
                alias[head] = src
    order = [n for n in where if n not in alias]

    plan = []  # (hf name, gguf name, shape, qtype)
    seen: dict[str, str] = {}
    for n in order:
        g = names.hf_to_gguf(n)
        if g in seen:
            sys.exit(f"GGUF name clash: {n} and {seen[g]} -> {g}")
        seen[g] = n
        shp = shape_of(n)
        plan.append((n, g, shp, quant.choose(n, shp, a.outtype, a.quantize_audio)))

    qt, ftype = quant.OUTTYPES[a.outtype]
    w = GGUFWriter(str(out), names.ARCH)
    w.add_name("Higgs TTS 3 4B")
    w.add_basename("higgs-tts-3")
    w.add_size_label("4B")
    w.add_file_type(int(ftype))
    w.add_quantization_version(2)
    w.add_string("general.license", "Boson Higgs Audio research / non-commercial licence (see source repo LICENSE)")
    w.add_string("general.source.huggingface.repository", DEFAULT_REPO)
    a_ = names.ARCH
    w.add_uint32(f"{a_}.context_length", tc["max_position_embeddings"])
    w.add_uint32(f"{a_}.embedding_length", tc["hidden_size"])
    w.add_uint32(f"{a_}.block_count", tc["num_hidden_layers"])
    w.add_uint32(f"{a_}.feed_forward_length", tc["intermediate_size"])
    w.add_uint32(f"{a_}.attention.head_count", tc["num_attention_heads"])
    w.add_uint32(f"{a_}.attention.head_count_kv", tc["num_key_value_heads"])
    w.add_uint32(f"{a_}.attention.key_length", tc["head_dim"])
    w.add_uint32(f"{a_}.attention.value_length", tc["head_dim"])
    w.add_float32(f"{a_}.attention.layer_norm_rms_epsilon", tc["rms_norm_eps"])
    w.add_float32(f"{a_}.rope.freq_base", float(tc.get("rope_parameters", {}).get("rope_theta", tc.get("rope_theta", 1e6))))
    w.add_uint32(f"{a_}.vocab_size", tc["vocab_size"])
    ac = cfg.get("audio_encoder_config") or {}
    w.add_uint32(f"{a_}.audio.num_codebooks", ac.get("num_codebooks", 8))
    w.add_uint32(f"{a_}.audio.codebook_size", ac.get("vocab_size", 1026))
    w.add_string(names.KEY_SOURCE_REPO, DEFAULT_REPO)
    w.add_string(names.KEY_SOURCE_REVISION, model_dir.name)
    w.add_string(names.KEY_CONVERTER_VERSION, names.CONVERTER_VERSION)
    if alias:
        w.add_array(names.KEY_ALIAS_HF, list(alias))
        w.add_array(names.KEY_ALIAS_SRC, list(alias.values()))
    w.add_array(names.KEY_MAP_GGUF, [p[1] for p in plan])
    w.add_array(names.KEY_MAP_HF, [p[0] for p in plan])
    for fname, key in names.HF_SIDE_FILES.items():
        f = model_dir / fname
        if f.is_file():
            w.add_string(key, f.read_text(encoding="utf-8"))
    if (model_dir / "chat_template.jinja").is_file():
        w.add_chat_template((model_dir / "chat_template.jinja").read_text(encoding="utf-8"))

    for n, g, shp, q in plan:
        w.add_tensor_info(g, shp, np.dtype(np.float32), quant.nbytes(q, shp), raw_dtype=q)
    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_ti_data_to_file()

    t0 = time.time()
    counts: dict[str, list[int]] = {}
    for i, (n, g, shp, q) in enumerate(plan, 1):
        data = encode(load(n), q)
        assert data.nbytes == quant.nbytes(q, shp), (n, q, data.nbytes)
        w.write_tensor_data(data)
        c = counts.setdefault(q.name, [0, 0])
        c[0] += 1
        c[1] += data.nbytes
        if i % 50 == 0 or i == len(plan):
            print(f"  {i}/{len(plan)} tensors, {time.time() - t0:.0f}s", flush=True)
    w.close()

    size = out.stat().st_size
    print(f"wrote {out} ({size / 2**30:.2f} GiB, {len(plan)} tensors, tied heads stored as aliases: {sorted(alias) or "none"}) in {time.time() - t0:.0f}s")
    for k, (cnt, b) in sorted(counts.items()):
        print(f"  {k:6s} {cnt:4d} tensors {b / 2**30:6.2f} GiB")
    summary = {"source": str(model_dir), "outtype": a.outtype, "quantize_audio": a.quantize_audio,
               "aliases": alias, "tensors": len(plan), "bytes": size,
               "by_type": {k: {"tensors": c, "bytes": b} for k, (c, b) in counts.items()},
               "seconds": round(time.time() - t0, 1)}
    (out.parent / "conversion.json").write_text(json.dumps(summary, indent=2) + "\n")
    if not a.no_side_files:
        from higgs_gguf.reader import write_side_files
        for p in write_side_files(out, overwrite=True):
            print(f"  side file {p.name}")


if __name__ == "__main__":
    main()
