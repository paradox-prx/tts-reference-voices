"""Model loading, trainable-parameter policy, the language tag, embedding assembly, losses and checkpoint export.

Everything here calls the same modules the inference path uses (talker.text_projection, the 16 codebook embeddings,
talker.forward, code_predictor.forward_finetune), so a model trained with these functions sees at training time
exactly the tensors it will see at serving time.
"""
from __future__ import annotations

import glob
import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import torch
import torch.nn.functional as F

NUM_GROUPS = 16
LANGUAGE_INIT_NORM_MAX = 0.1  # rows of the codec embedding below this norm are untrained (init std ~0.02)


def resolve_model_dir(model: str) -> str:
    if os.path.isdir(model):
        return model
    from huggingface_hub import snapshot_download
    return snapshot_download(model, allow_patterns=["*.json", "*.safetensors", "*.txt"])


def load_model(model: str, device: str = "cuda", dtype=torch.bfloat16, attn: str = "sdpa"):
    """The qwen_tts wrapper (processor + core Qwen3TTSForConditionalGeneration)."""
    from qwen_tts import Qwen3TTSModel
    path = resolve_model_dir(model)
    wrapper = Qwen3TTSModel.from_pretrained(path, device_map=device, dtype=dtype, attn_implementation=attn)
    wrapper.model.config._model_dir = path
    return wrapper


def add_language(core, name: str, row: int, init: str = "mean") -> bool:
    """Register `name` -> codec-vocabulary row `row` in the talker config and initialise the embedding row from the
    mean of the existing language rows (unless it is already trained). Returns True if the row was (re)initialised."""
    tcfg = core.talker.config
    lang_map = dict(tcfg.codec_language_id or {})
    emb = core.talker.get_input_embeddings().weight
    existing = [i for n, i in lang_map.items() if n != name]
    changed = False
    if name not in lang_map:
        assert row not in lang_map.values(), f"row {row} already used by {lang_map}"
        lang_map[name] = row
        tcfg.codec_language_id = lang_map
        core.config.talker_config.codec_language_id = lang_map
        if hasattr(core, "supported_languages") and name not in core.supported_languages:
            core.supported_languages.append(name)
    with torch.no_grad():
        if init == "mean" and emb[row].float().norm().item() < LANGUAGE_INIT_NORM_MAX:
            emb[row] = emb[existing].float().mean(0).to(emb.dtype)
            changed = True
    return changed


@dataclass
class TrainablePolicy:
    mode: str = "full"                  # full | lora
    train_text_embedding: bool = False  # the 151936 x 2048 Qwen text embedding (frozen by default)
    train_codec_head: bool = True
    lora_r: int = 64
    lora_alpha: int = 128
    lora_dropout: float = 0.05
    lora_targets: list[str] = field(default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj",
                                                             "up_proj", "down_proj"])
    lora_modules_to_save: list[str] = field(default_factory=lambda: ["codec_embedding", "text_projection"])


def set_trainable(core, policy: TrainablePolicy):
    """Freeze/unfreeze; for LoRA wrap core.talker with peft. Returns (module holding the trainable params, summary)."""
    for p in core.parameters():
        p.requires_grad_(False)
    if policy.mode == "full":
        for n, p in core.talker.named_parameters():
            if n.startswith("model.text_embedding") and not policy.train_text_embedding:
                continue
            if n.startswith("codec_head") and not policy.train_codec_head:
                continue
            p.requires_grad_(True)
        trained = core.talker
    elif policy.mode == "lora":
        from peft import LoraConfig, get_peft_model
        cfg = LoraConfig(r=policy.lora_r, lora_alpha=policy.lora_alpha, lora_dropout=policy.lora_dropout,
                         target_modules=policy.lora_targets, modules_to_save=policy.lora_modules_to_save, bias="none")
        core.talker = get_peft_model(core.talker, cfg)
        for n, p in core.talker.named_parameters():
            if p.requires_grad:
                p.data = p.data.float()  # adapters and saved modules in fp32 (updates are too small for bf16)
        trained = core.talker
    else:
        raise ValueError(policy.mode)
    n_train = sum(p.numel() for p in core.parameters() if p.requires_grad)
    n_all = sum(p.numel() for p in core.parameters())
    return trained, {"trainable": n_train, "total": n_all, "mode": policy.mode}


def talker_of(core):
    """The underlying talker (through the peft wrapper when present)."""
    t = core.talker
    return t.get_base_model() if hasattr(t, "get_base_model") else t


def set_gradient_checkpointing(core, on: bool = True) -> None:
    """HF-style checkpointing on the talker layers and the code predictor layers (non-reentrant)."""
    t = talker_of(core)
    if on:
        t.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        t.config.use_cache = False
        t.code_predictor.config.use_cache = False
    else:
        t.gradient_checkpointing_disable()


def assemble_embeddings(core, batch: dict, device) -> torch.Tensor:
    """inputs_embeds [B, L, D] from a collated batch, as generate() builds them."""
    t = talker_of(core)
    text_ids = batch["text_ids"].to(device)
    text = t.text_projection(t.get_text_embeddings()(text_ids)) * batch["text_present"].to(device).unsqueeze(-1)
    codec_ids = batch["codec_ids"].to(device)
    codec_emb = t.get_input_embeddings()
    codec = codec_emb(codec_ids.clamp(min=0)) * (codec_ids >= 0).unsqueeze(-1)
    frames = batch["frame_codes"].to(device)
    fm = batch["frame_mask"].to(device).unsqueeze(-1)
    fr = codec_emb(frames[..., 0])
    cp_embs = t.code_predictor.get_input_embeddings()
    for k in range(1, NUM_GROUPS):
        fr = fr + cp_embs[k - 1](frames[..., k])
    emb = text + codec + fr * fm
    if "xvec" in batch:
        spk = batch["spk_pos"].to(device)
        xv = batch["xvec"].to(device=device, dtype=emb.dtype)
        rows = torch.nonzero(spk >= 0).flatten()
        if len(rows):
            emb[rows, spk[rows]] = emb[rows, spk[rows]] + xv[rows]
    return emb


def code_predictor_logits(core, hidden: torch.Tensor, codes: torch.Tensor, chunk: int = 2048) -> torch.Tensor:
    """[N, 15, 2048] logits for codebooks 1..15 of the frames `codes` [N, 16], from the talker hidden states [N, D]
    that predicted them (forward_sub_talker_finetune without its shifted loss)."""
    t = talker_of(core)
    cp_embs = t.code_predictor.get_input_embeddings()
    outs = []
    for s in range(0, hidden.shape[0], chunk):
        h, c = hidden[s:s + chunk], codes[s:s + chunk]
        parts = [h.unsqueeze(1), t.get_input_embeddings()(c[:, :1])]
        for i in range(1, NUM_GROUPS - 1):
            parts.append(cp_embs[i - 1](c[:, i:i + 1]))
        inp = torch.cat(parts, dim=1)  # [n, 16, D]
        outs.append(t.code_predictor.forward_finetune(inputs_embeds=inp, labels=None).logits)
    return torch.cat(outs, dim=0)


def forward_losses(core, batch: dict, device, cp_weight: float = 0.3, text_projection: bool = True,
                   label_shift: int = 0) -> dict:
    """Talker + code-predictor losses and top-1 accuracies. `text_projection=False` and `label_shift` reproduce the
    official script's bugs for check_alignment.py; training always uses the defaults."""
    t = talker_of(core)
    if text_projection:
        emb = assemble_embeddings(core, batch, device)
    else:
        proj = t.text_projection
        t.text_projection = torch.nn.Identity()
        try:
            emb = assemble_embeddings(core, batch, device)
        finally:
            t.text_projection = proj
    attn = batch["attention_mask"].to(device)
    out = core.talker(inputs_embeds=emb, attention_mask=attn, output_hidden_states=True, use_cache=False)
    logits = out.logits
    hidden = out.hidden_states[0][-1]  # the final normed hidden state: what feeds the code predictor at inference
    labels = batch["labels"].to(device)
    cp_mask = batch["cp_mask"].to(device)
    cp_codes = batch["cp_codes"].to(device)
    if label_shift:  # score position p against the label of p+shift (the official double shift = -1)
        labels = torch.roll(labels, shifts=label_shift, dims=1)
        cp_codes = torch.roll(cp_codes, shifts=label_shift, dims=1)
        cp_mask = torch.roll(cp_mask, shifts=label_shift, dims=1)
    sel = labels != -100
    lg = logits[sel].float()
    lb = labels[sel]
    talker_loss = F.cross_entropy(lg, lb)
    acc0 = (lg.argmax(-1) == lb).float().mean()
    h = hidden[cp_mask]
    c = cp_codes[cp_mask]
    if h.shape[0]:
        cp_logits = code_predictor_logits(core, h, c).float()  # [N, 15, 2048]
        cp_loss = F.cross_entropy(cp_logits.reshape(-1, cp_logits.shape[-1]), c[:, 1:].reshape(-1))
        cp_acc = (cp_logits.argmax(-1) == c[:, 1:]).float().mean(0)  # per codebook
    else:
        cp_loss = torch.zeros((), device=device)
        cp_acc = torch.zeros(NUM_GROUPS - 1, device=device)
    loss = talker_loss + cp_weight * cp_loss
    return {"loss": loss, "talker_loss": talker_loss.detach(), "cp_loss": cp_loss.detach(), "acc0": acc0.detach(),
            "cp_acc": cp_acc.detach(), "n_labels": int(sel.sum()), "n_frames": int(cp_mask.sum()),
            "n_tokens": int(attn.sum())}


def merge_lora(core):
    if hasattr(core.talker, "merge_and_unload"):
        core.talker = core.talker.merge_and_unload()
    return core


def save_checkpoint(core, out_dir: str | Path, extra_config: dict | None = None, adapter_only: bool = False,
                    copy_tokenizer: bool = False) -> Path:
    """A servable HF directory: the base model's json/txt files, config.json with the updated language map, and either
    the full weights (speaker encoder included, so voice cloning works) or the LoRA adapter."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    src = core.config._model_dir
    for f in glob.glob(os.path.join(src, "*")):
        if f.endswith((".json", ".txt")) and not f.endswith("config.json"):
            shutil.copy(f, out / os.path.basename(f))
    tok_src = Path(src) / "speech_tokenizer"  # the codec (Code2Wav) the wrapper and vLLM-Omni load from the model dir
    if tok_src.exists():
        tok_dst = out / "speech_tokenizer"
        if tok_dst.is_symlink() or tok_dst.exists():
            tok_dst.unlink() if tok_dst.is_symlink() else shutil.rmtree(tok_dst)
        if copy_tokenizer:
            shutil.copytree(tok_src.resolve(), tok_dst)
        else:
            os.symlink(tok_src.resolve(), tok_dst)  # 0.7 GB: symlinked to save disk; export.py --copy-tokenizer to bundle
    cfg = json.load(open(os.path.join(src, "config.json"), encoding="utf-8"))
    cfg["talker_config"]["codec_language_id"] = dict(core.talker.config.codec_language_id if not hasattr(core.talker, "get_base_model")
                                                     else talker_of(core).config.codec_language_id)
    for k, v in (extra_config or {}).items():
        cfg[k] = v
    json.dump(cfg, open(out / "config.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if adapter_only:
        core.talker.save_pretrained(out / "adapter")
        return out
    from safetensors.torch import save_file
    if hasattr(core.talker, "get_base_model"):  # LoRA: export merged weights
        import copy
        merged = copy.deepcopy(core.talker).merge_and_unload()
        state = {f"talker.{k}": v for k, v in merged.state_dict().items()}
        del merged
    else:
        state = {f"talker.{k}": v for k, v in core.talker.state_dict().items()}
    state.update({f"speaker_encoder.{k}": v for k, v in core.speaker_encoder.state_dict().items()})
    state = {k: v.detach().to("cpu", torch.bfloat16 if v.is_floating_point() else v.dtype).contiguous() for k, v in state.items()}
    save_file(state, str(out / "model.safetensors"), metadata={"format": "pt"})
    return out
