#!/usr/bin/env python3
"""Precompute vLLM-Omni custom voices (deploy YAML `custom_voice_dir`) for the repo's voices, including one with an
AVERAGED speaker embedding. Runs on the CPU in the engine venv:

  CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 nice venvs/engine/bin/python engine/precompute_voices.py [--voice ID ...]
  venvs/engine/bin/python engine/precompute_voices.py --verify-only      # only re-check an existing directory

For every voice-server/v1 folder voices/<id>/ it writes two in-context-learning (mode "icl") profiles:
  <id>-avg     ref_code of references/qwen3-tts.wav with its transcript (references.json "qwen3-tts"), and as speaker
               embedding the MEAN of the per-clip x-vectors over all the voice's clips (voices/<id>/*.wav plus
               references/qwen3-tts.wav, each resampled to 24 kHz), rescaled to the mean per-clip norm (the Kaggle
               recipe in NOTES.md: the x-vector is not normalised and its norm matters)
  <id>-prompt  the same ref_code and transcript with the x-vector of references/qwen3-tts.wav alone: what the engine
               itself derives from an inline or uploaded reference, for A/B against <id>-avg
Output (default server/state/custom_voices, gitignored): custom_voice_manifest.json, <name>.safetensors per profile
(speaker_embedding float32 [2048], ref_code int32 [T, 16]) and <id>-embeddings.json (per-clip norms and cosines).
Serve them with engine/deploy/variants/custom_voices.yaml; requests then send only voice="<id>-avg" (task_type Base,
no ref_audio / ref_text); GET /v1/audio/voices lists the names under "voices".

The computations are the engine's own (vllm_omni 0.28.0): x-vector = prompt_embeds_builder.py
extract_speaker_embedding (L643-688: pyav resampling to 24 kHz, mel_spectrogram, ECAPA speaker encoder in bf16),
ref_code = the 12 Hz speech-tokenizer encoder (modeling_qwen3_tts_tokenizer_v2.py encode L1649-1679, the same code
as qwen3_tts_talker.py _encode_ref_audio_batch L1039-1066), as in upstream
examples/online_serving/text_to_speech/qwen3_tts/precompute_custom_voice.py (v0.28.0). After writing, the files are
loaded by the engine's own loaders (the API side's load_precomputed_speakers and the talker's
_load_custom_voice_profiles) and checked. The profile format is utils/speaker_cache.py (L51-160).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

SERVER = Path(__file__).resolve().parents[1]
VOICES_DIR = Path(os.environ.get("TTS_VOICES_DIR") or SERVER.parent / "voices")
OUT_DIR = SERVER / "state" / "custom_voices"
MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
MANIFEST = "custom_voice_manifest.json"  # utils/speaker_cache.py _CUSTOM_VOICE_MANIFEST
REFERENCE_KEY = "qwen3-tts"  # references/references.json entry used for ICL
SAMPLE_RATE = 24000  # speaker encoder and speech tokenizer input rate
SUFFIX_AVG, SUFFIX_PROMPT = "avg", "prompt"


# ------------------------------------------------------------------ pure helpers (no torch; unit-tested)

def average_embedding(vectors: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    """Mean of the per-clip x-vectors [N, D], rescaled to the mean per-clip L2 norm, plus statistics."""
    vectors = np.asarray(vectors, dtype=np.float64)
    if vectors.ndim != 2 or len(vectors) == 0:
        raise ValueError(f"expected [N, D] embeddings, got shape {vectors.shape}")
    norms = np.linalg.norm(vectors, axis=1)
    mean = vectors.mean(axis=0)
    mean_norm = float(np.linalg.norm(mean))
    if not mean_norm or not np.all(np.isfinite(vectors)):
        raise ValueError("degenerate embeddings (zero mean or non-finite values)")
    target = float(norms.mean())
    averaged = mean * (target / mean_norm)
    stats = {"norms": [float(n) for n in norms], "target_norm": target, "mean_vector_norm": mean_norm,
             "cos_to_mean": [cosine(v, mean) for v in vectors]}
    return averaged.astype(np.float32), stats


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, dtype=np.float64).reshape(-1), np.asarray(b, dtype=np.float64).reshape(-1)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def voice_clips(folder: Path, reference: Path) -> list[Path]:
    """Every clip of a voice: voices/<id>/*.wav, then the ICL reference (references/qwen3-tts.wav)."""
    clips = sorted(p for p in folder.glob("*.wav") if p.is_file())
    return [*clips, reference]


def load_reference(folder: Path) -> dict[str, Any]:
    """references.json "qwen3-tts" entry (file, text, sha256), with the file resolved and its sha256 checked."""
    try:
        entry = json.loads((folder / "references" / "references.json").read_text(encoding="utf-8"))[REFERENCE_KEY]
        path = folder / "references" / entry["file"]
        text = str(entry["text"]).strip()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise SystemExit(f"{folder}: no usable references.json {REFERENCE_KEY!r} entry: {exc}") from exc
    if entry.get("sha256") and digest != entry["sha256"]:
        raise SystemExit(f"{path}: sha256 {digest} does not match references.json")
    if not text:
        raise SystemExit(f"{folder}: the {REFERENCE_KEY!r} reference has no transcript (ICL needs it)")
    return {"path": path, "text": text, "sha256": digest}


def profile_names(voice_id: str) -> tuple[str, str]:
    base = voice_id.strip().lower()
    return f"{base}-{SUFFIX_AVG}", f"{base}-{SUFFIX_PROMPT}"


def manifest_entry(name: str, filename: str, ref_text: str, ref_code_len: int, dim: int, description: str) -> dict:
    """One voices{} entry in the format of upstream precompute_custom_voice.py (_write_voice)."""
    return {"name": name, "file": filename, "mode": "icl", "embedding_dim": dim, "ref_code_length": ref_code_len,
            "ref_text": ref_text, "speaker_description": description}


def merge_manifest(existing: dict | None, model: str, hidden_size: int, entries: dict[str, dict]) -> dict:
    manifest = existing if isinstance(existing, dict) and existing.get("model_type") == "qwen3_tts" else {}
    manifest.setdefault("schema_version", 1)
    manifest["model_type"] = "qwen3_tts"
    manifest["model"] = model
    manifest["hidden_size"] = hidden_size
    voices = manifest.get("voices") if isinstance(manifest.get("voices"), dict) else {}
    voices.update(entries)
    manifest["voices"] = dict(sorted(voices.items()))
    return manifest


def write_atomic(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ------------------------------------------------------------------ model side (torch + vllm_omni, CPU)

class Encoders:
    """The engine's speaker encoder and speech-tokenizer encoder, on the CPU."""

    def __init__(self, model_dir: Path, dtype: str) -> None:
        import torch
        from safetensors import safe_open
        from vllm_omni.model_executor.models.qwen3_tts.configuration_qwen3_tts import Qwen3TTSConfig
        from vllm_omni.model_executor.models.qwen3_tts.qwen3_tts_talker import Qwen3TTSSpeakerEncoder
        from vllm_omni.model_executor.models.qwen3_tts.qwen3_tts_tokenizer import Qwen3TTSTokenizer

        self.torch = torch
        self.dtype = getattr(torch, dtype)
        self.config = Qwen3TTSConfig.from_pretrained(str(model_dir))
        enc_cfg = self.config.speaker_encoder_config
        if int(getattr(enc_cfg, "sample_rate", SAMPLE_RATE)) != SAMPLE_RATE:
            raise SystemExit(f"unexpected speaker encoder sample rate {enc_cfg.sample_rate}")
        self.speaker_encoder = Qwen3TTSSpeakerEncoder(enc_cfg)
        state: dict[str, Any] = {}
        with safe_open(str(model_dir / "model.safetensors"), framework="pt", device="cpu") as f:
            for key in f.keys():
                if key.startswith("speaker_encoder."):
                    state[key.removeprefix("speaker_encoder.")] = f.get_tensor(key)
        if not state:
            raise SystemExit(f"no speaker_encoder.* weights in {model_dir}/model.safetensors (not a Base checkpoint?)")
        self.speaker_encoder.load_state_dict(state)
        self.speaker_encoder.to(dtype=self.dtype).eval()

        try:
            self.tokenizer = Qwen3TTSTokenizer.from_pretrained(str(model_dir / "speech_tokenizer"), dtype=self.dtype)
        except TypeError:  # older transformers spell it torch_dtype
            self.tokenizer = Qwen3TTSTokenizer.from_pretrained(str(model_dir / "speech_tokenizer"),
                                                               torch_dtype=self.dtype)
        self.tokenizer.model.decoder = None  # encoder only, like the talker
        self.tokenizer.device = torch.device("cpu")
        self.downsample = int(self.tokenizer.config.encode_downsample_rate)

    @staticmethod
    def read_24k(path: Path) -> tuple[np.ndarray, int]:
        """Mono float32 at 24 kHz, resampled with vLLM's AudioResampler (pyav), like the engine."""
        import soundfile as sf
        from vllm.multimodal.audio import AudioResampler

        wav, sr = sf.read(str(path), dtype="float32", always_2d=False)
        if wav.ndim > 1:
            wav = wav.mean(axis=-1)
        if int(sr) != SAMPLE_RATE:
            wav = AudioResampler(target_sr=SAMPLE_RATE).resample(wav.astype(np.float32), orig_sr=int(sr))
        wav = np.asarray(wav, dtype=np.float32)
        if wav.size < 1024:
            raise SystemExit(f"{path}: too short ({wav.size} samples)")
        return wav, int(sr)

    def xvector(self, wav: np.ndarray) -> np.ndarray:
        """prompt_embeds_builder.extract_speaker_embedding on 24 kHz audio: mel (n_fft 1024, 128 mels, hop 256,
        fmax 12 kHz) -> ECAPA speaker encoder. Returns float32 [enc_dim]."""
        from vllm_omni.model_executor.models.qwen3_tts.prompt_embeds_builder import mel_spectrogram

        torch = self.torch
        with torch.inference_mode():
            mels = mel_spectrogram(torch.from_numpy(wav).float().unsqueeze(0), n_fft=1024, num_mels=128,
                                   sampling_rate=SAMPLE_RATE, hop_size=256, win_size=1024, fmin=0,
                                   fmax=12000).transpose(1, 2)
            spk = self.speaker_encoder(mels.to(dtype=self.dtype))[0]
        return spk.float().numpy().reshape(-1)

    def ref_code(self, wav: np.ndarray) -> Any:
        """Speech-tokenizer codes [T, 16] (int32) of 24 kHz audio."""
        torch = self.torch
        with torch.inference_mode():
            enc = self.tokenizer.encode(wav, sr=SAMPLE_RATE, return_dict=True)
        codes = enc.audio_codes[0] if isinstance(enc.audio_codes, list) else enc.audio_codes
        if codes.ndim == 3:
            codes = codes[0]
        codes = codes.to(dtype=torch.int32, device="cpu").contiguous()
        expected = math.ceil(wav.size / self.downsample)
        if codes.ndim != 2 or codes.shape[1] != 16 or codes.shape[0] != expected:
            raise SystemExit(f"unexpected ref_code shape {tuple(codes.shape)} (expected [{expected}, 16])")
        return codes


def resolve_model_dir(model: str) -> Path:
    if Path(model).is_dir():
        return Path(model).resolve()
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(model, local_files_only=True))


def precompute_voice(enc: Encoders, voice_dir: Path, out_dir: Path, model: str) -> dict[str, dict]:
    from safetensors.torch import save

    torch = enc.torch
    voice_id = voice_dir.name
    meta = json.loads((voice_dir / "voice.json").read_text(encoding="utf-8"))
    ref = load_reference(voice_dir)
    clips = voice_clips(voice_dir, ref["path"])
    t0 = time.monotonic()
    rows, vectors = [], []
    for clip in clips:
        wav, orig_sr = enc.read_24k(clip)
        vectors.append(enc.xvector(wav))
        rows.append({"file": str(clip.relative_to(voice_dir)), "seconds": round(wav.size / SAMPLE_RATE, 3),
                     "source_sample_rate": orig_sr})
    averaged, stats = average_embedding(np.stack(vectors))
    prompt = vectors[-1]  # the reference clip is last (voice_clips), and `wav` still holds it
    ref_code = enc.ref_code(wav)
    dim = int(averaged.size)
    hidden = int(enc.config.talker_config.hidden_size)
    if dim != hidden:
        raise SystemExit(f"x-vector dim {dim} != talker hidden_size {hidden}")

    label = meta.get("label") or voice_id
    name_avg, name_prompt = profile_names(voice_id)
    entries: dict[str, dict] = {}
    for name, vector, what in (
            (name_avg, averaged, f"averaged x-vector over {len(clips)} clips, rescaled to their mean norm"),
            (name_prompt, prompt, f"x-vector of references/{ref['path'].name} (the ICL reference) alone")):
        filename = f"{name}.safetensors"
        tensors = {"speaker_embedding": torch.from_numpy(np.ascontiguousarray(vector, dtype=np.float32)),
                   "ref_code": ref_code}
        write_atomic(out_dir / filename, save(tensors, metadata={"voice": voice_id, "kind": what}))
        entries[name] = manifest_entry(name, filename, ref["text"], int(ref_code.shape[0]), dim,
                                       f"{label}: ICL {ref['path'].name} + {what}")

    for row, norm, cos_mean, vector in zip(rows, stats["norms"], stats["cos_to_mean"], vectors, strict=True):
        row.update(norm=round(norm, 4), cos_to_mean=round(cos_mean, 5), cos_to_prompt=round(cosine(vector, prompt), 5))
    report = {
        "voice": voice_id, "model": model, "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "reference": {"file": str(ref["path"].relative_to(voice_dir)), "sha256": ref["sha256"],
                      "ref_code_frames": int(ref_code.shape[0]), "text_chars": len(ref["text"])},
        "profiles": {name_avg: "mean of all clip x-vectors, rescaled to target_norm",
                     name_prompt: "x-vector of the reference clip alone"},
        "clips": rows,
        "mean_clip_norm": round(stats["target_norm"], 4),
        "mean_vector_norm_before_rescale": round(stats["mean_vector_norm"], 4),
        "avg_norm": round(float(np.linalg.norm(averaged)), 4),
        "prompt_norm": round(float(np.linalg.norm(prompt)), 4),
        "cos_avg_vs_prompt": round(cosine(averaged, prompt), 5),
        "min_cos_to_mean": round(min(stats["cos_to_mean"]), 5),
        "encoder_dtype": str(enc.dtype).removeprefix("torch."),
        "seconds_to_compute": round(time.monotonic() - t0, 1),
    }
    write_atomic(out_dir / f"{voice_id}-embeddings.json",
                 (json.dumps(report, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    print(f"{voice_id}: {len(clips)} clips, per-clip norms {[r['norm'] for r in rows]}, "
          f"|mean| {stats['mean_vector_norm']:.3f} -> {stats['target_norm']:.3f}, cos(avg, prompt) "
          f"{report['cos_avg_vs_prompt']:.4f}, ref_code {tuple(ref_code.shape)}")
    return entries


def verify(out_dir: Path, model_dir: Path, expected: list[str]) -> None:
    """Load out_dir with the engine's own loaders (API side and talker side) and check every expected profile."""
    from types import SimpleNamespace

    import torch
    from vllm_omni.entrypoints.openai.tts_adapters.capabilities import load_precomputed_speakers
    from vllm_omni.model_executor.models.qwen3_tts.configuration_qwen3_tts import Qwen3TTSConfig
    from vllm_omni.model_executor.models.qwen3_tts.qwen3_tts_talker import Qwen3TTSTalkerForConditionalGeneration
    from vllm_omni.utils.speaker_cache import SpeakerEmbeddingCache, validate_qwen3_tts_profile

    config = Qwen3TTSConfig.from_pretrained(str(model_dir))
    config.custom_voice_dir = str(out_dir)  # what engine/stage_init_utils.py L1490-1492 sets on hf_config
    hidden = int(config.talker_config.hidden_size)
    # API side (tts_adapters/qwen3_tts.py _load_precomputed_speakers): validation against the talker hidden size.
    client = SimpleNamespace(model_config=SimpleNamespace(hf_config=config))
    api = load_precomputed_speakers(client, expected_model_type="qwen3_tts",
                                    validate_profile=lambda p, t: validate_qwen3_tts_profile(
                                        p, t, expected_embedding_dim=hidden))
    # Talker side (qwen3_tts_talker.py _load_custom_voice_profiles) into a fresh speaker cache.
    cache = SpeakerEmbeddingCache()
    Qwen3TTSTalkerForConditionalGeneration._load_custom_voice_profiles(
        SimpleNamespace(config=config, _speaker_cache=cache))
    problems = []
    for name in expected:
        profile = api.get(name)
        if profile is None:
            problems.append(f"{name}: rejected or missing on the API side")
            continue
        if profile.get("mode") != "icl" or profile.get("embedding_dim") != hidden or not profile.get("ref_code_length"):
            problems.append(f"{name}: API profile {profile}")
        hit = cache.get(cache.make_cache_key(name, model_type="qwen3_tts_icl", created_at=0))
        if hit is None:
            problems.append(f"{name}: not in the talker's speaker cache under (qwen3_tts_icl, {name}, 0)")
            continue
        spk, code = hit["ref_spk_embedding"], hit["ref_code"]
        if tuple(spk.shape) != (hidden,) or not torch.isfinite(spk).all():
            problems.append(f"{name}: speaker embedding shape {tuple(spk.shape)}")
        if code is None or code.ndim != 2 or code.shape[1] != 16 or code.shape[0] != profile["ref_code_length"]:
            problems.append(f"{name}: ref_code {None if code is None else tuple(code.shape)}")
        if hit["icl_mode"] is not True or not hit.get("ref_text"):
            problems.append(f"{name}: icl_mode {hit['icl_mode']!r}, ref_text {bool(hit.get('ref_text'))}")
        else:
            print(f"verify: {name}: ok (mode icl, embedding [{spk.shape[0]}] |x| {float(spk.norm()):.3f}, "
                  f"ref_code {tuple(code.shape)})")
    if problems:
        raise SystemExit("verify failed:\n  " + "\n  ".join(problems))
    print(f"verify: {len(expected)} profile(s) load with the engine's loaders from {out_dir}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voices-dir", type=Path, default=VOICES_DIR, help="voice-server/v1 folders (default %(default)s)")
    ap.add_argument("--voice", action="append", help="voice id (repeatable; default: every folder with voice.json)")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR, help="custom_voice_dir to write (default %(default)s)")
    ap.add_argument("--model", default=MODEL,
                    help="HF repo id (offline cache) or local model directory (default %(default)s)")
    ap.add_argument("--encoder-dtype", choices=("bfloat16", "float32"), default="bfloat16",
                    help="speaker/codec encoder dtype; bfloat16 = what the engine runs (default %(default)s)")
    ap.add_argument("--threads", type=int, default=4, help="CPU threads for torch (default %(default)s)")
    ap.add_argument("--verify-only", action="store_true", help="only load and check the existing out-dir")
    a = ap.parse_args()

    # CPU only: hide every GPU before torch is imported, and never contact the Hub.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", os.environ["HF_HUB_OFFLINE"])
    os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARNING")
    import torch

    torch.set_num_threads(max(1, a.threads))
    voices_dir, out_dir = a.voices_dir.resolve(), a.out_dir.resolve()
    ids = a.voice or sorted(p.name for p in voices_dir.iterdir() if (p / "voice.json").is_file())
    for voice_id in ids:
        if not (voices_dir / voice_id / "voice.json").is_file():
            ap.error(f"{voices_dir / voice_id} is not a voice folder")
    model_dir = resolve_model_dir(a.model)
    expected = [name for voice_id in ids for name in profile_names(voice_id)]
    if not a.verify_only:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_dir.chmod(0o700)
        enc = Encoders(model_dir, a.encoder_dtype)
        entries: dict[str, dict] = {}
        for voice_id in ids:
            entries.update(precompute_voice(enc, voices_dir / voice_id, out_dir, a.model))
        path = out_dir / MANIFEST
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        manifest = merge_manifest(existing, a.model, int(enc.config.talker_config.hidden_size), entries)
        write_atomic(path, (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        print(f"wrote {path} ({len(manifest['voices'])} voices: {', '.join(manifest['voices'])})")
    verify(out_dir, model_dir, expected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
