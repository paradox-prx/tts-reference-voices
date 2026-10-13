"""Model side of the qwen-tts baseline: references and voices, the voice-clone prompt cache, the single model worker
thread, and the dynamic batcher that feeds it.

Threading model. qwen-tts is not thread-safe (the talker keeps rope_deltas as instance state; qwen-tts-internals
finding 15), so every call into the model (load, prompt creation, speaker embeddings, generate) runs on ONE worker
thread: a ThreadPoolExecutor(max_workers=1) owned by the server. Engine methods are only called on that thread.
The Batcher lives on the asyncio event loop: it queues jobs, forms batches and hands one batch at a time to the worker.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import dataclasses
import hashlib
import io
import json
import logging
import threading
import time
from collections import OrderedDict, Counter
from concurrent.futures import Executor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np
import soundfile as sf
import torch

log = logging.getLogger("qwen_tts_baseline")

SAMPLE_RATE = 24000                 # model output and speaker-encoder rate
SAMPLES_PER_FRAME = 1920            # 12.5 codec frames/s at 24 kHz (decoder output is exactly frames x 1920 samples)
REF_MIN_S, REF_MAX_S = 1.0, 30.0    # vLLM-Omni 0.28 serving_speech.py _REF_AUDIO_MIN/MAX_DURATION
UPLOAD_MAX_BYTES = 10 * 1024 * 1024  # vLLM-Omni 0.28 upload_voice MAX_FILE_SIZE
# vLLM-Omni 0.28 tts_adapters/qwen3_tts.py codec budget for a Base request without max_new_tokens:
# min(max(192, 12 x text_tokens), 4096); request max_new_tokens must be 1..4096 (_TTS_MAX_NEW_TOKENS_MAX).
MIN_CODEC_FRAMES, FRAMES_PER_TEXT_TOKEN, MAX_NEW_TOKENS_MAX = 192, 12, 4096


class CodecLimitError(RuntimeError):
    """A row reached its max_new_tokens without codec EOS (vLLM-Omni: Qwen3TTSCodecLimitError -> HTTP 500)."""


class QueueFull(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------ references

def sha1(data: bytes | str) -> str:
    return hashlib.sha1(data.encode() if isinstance(data, str) else data).hexdigest()


def decode_ref_audio_string(value: str) -> bytes:
    """Audio file bytes of a request's ref_audio: a data: URL (data:audio/...;base64,...) or plain base64.
    URLs (http/https/file/...) are refused: the baseline never fetches anything."""
    s = value.strip()
    if s[:5].lower() == "data:":
        head, sep, payload = s.partition(",")
        if not sep or ";base64" not in head.lower():
            raise ValueError("ref_audio data: URL must be base64-encoded (data:audio/wav;base64,...)")
    else:
        scheme = urlparse(s).scheme
        if scheme:
            raise ValueError(f"ref_audio '{scheme}:' URLs are not supported by the qwen-tts baseline; send the audio "
                             "inline as a data:audio/...;base64 URL or plain base64")
        payload = s
    try:
        data = base64.b64decode("".join(payload.split()), validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("ref_audio is not valid base64") from None
    if not data:
        raise ValueError("ref_audio is empty")
    return data


def decode_audio(data: bytes) -> tuple[np.ndarray, int]:
    """(float32 mono waveform, sample rate) of an audio file's bytes (anything libsndfile reads)."""
    try:
        audio, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
    except Exception as exc:  # noqa: BLE001 - libsndfile raises several types
        raise ValueError(f"could not decode audio: {exc}") from None
    if audio.shape[0] == 0 or sr <= 0:
        raise ValueError("audio has no samples")
    return np.ascontiguousarray(audio.mean(axis=1), dtype=np.float32), int(sr)


def to_24k(audio: np.ndarray, sr: int) -> np.ndarray:
    """Resample to 24 kHz exactly as qwen-tts does before extract_speaker_embedding (librosa.resample)."""
    if sr == SAMPLE_RATE:
        return audio.astype(np.float32, copy=False)
    import librosa  # heavy import (numba); only needed for non-24 kHz audio

    return librosa.resample(y=audio.astype(np.float32), orig_sr=int(sr), target_sr=SAMPLE_RATE)


@dataclass(frozen=True, eq=False)
class Reference:
    """One voice-clone reference. `key` is its prompt-cache key: sha1 of the audio file bytes + mode (+ sha1 of the
    transcript in ICL mode) (+ ':avg' when the speaker embedding is replaced by the clip average)."""

    key: str
    audio: np.ndarray            # float32 mono at `sr`
    sr: int
    ref_text: str | None
    x_vector_only: bool
    source: str                  # repo | upload | inline
    name: str | None = None
    language: str = "Auto"       # used when the request has no language
    spk_override: Any = None     # float32 CPU tensor: averaged speaker embedding (--avg-embedding, repo voices)

    @property
    def seconds(self) -> float:
        return len(self.audio) / self.sr

    def as_x_vector_only(self) -> "Reference":
        if self.x_vector_only:
            return self
        key = _ref_key(self.key.split(":")[0], None, True, self.spk_override is not None)
        return dataclasses.replace(self, key=key, ref_text=None, x_vector_only=True)


def _ref_key(audio_sha1: str, ref_text: str | None, x_vector_only: bool, avg: bool = False) -> str:
    mode = "xvec" if x_vector_only else "icl:" + sha1(ref_text or "")[:12]
    return f"{audio_sha1[:20]}:{mode}" + (":avg" if avg else "")


def make_reference(data: bytes, ref_text: str | None, x_vector_only: bool, source: str, name: str | None = None,
                   language: str = "Auto") -> Reference:
    """Decode and validate reference audio (1-30 s, like vLLM-Omni). Raises ValueError with a client-facing message."""
    audio, sr = decode_audio(data)
    seconds = len(audio) / sr
    if seconds < REF_MIN_S:
        raise ValueError(f"Reference audio too short ({seconds:.1f}s). At least {REF_MIN_S:.0f}s of clear speech is "
                         "required.")
    if seconds > REF_MAX_S:
        raise ValueError(f"Reference audio too long ({seconds:.1f}s). Maximum {REF_MAX_S:.0f}s supported.")
    text = (ref_text or "").strip() or None
    if not x_vector_only and not text:
        raise ValueError("Base task requires non-empty 'ref_text' (transcript of the reference audio) unless "
                         "'x_vector_only_mode' is enabled")
    return Reference(key=_ref_key(sha1(data), text, x_vector_only), audio=audio, sr=sr,
                     ref_text=None if x_vector_only else text, x_vector_only=x_vector_only, source=source, name=name,
                     language=language)


@dataclass
class RepoVoice:
    id: str
    ref: Reference
    ref_file: Path
    clips: list[Path]
    lang: str                    # voice.json language (en, ur, ...)
    sha256_ok: bool | None       # reference file vs references.json sha256 (None: no sha256 listed)


def load_repo_voices(voices_dir: Path) -> list[RepoVoice]:
    """voices/<id>/: references/references.json 'qwen3-tts' entry {file, text, sha256} + voice.json language.
    Language default: English for 'en', otherwise Auto (Urdu is not a Qwen3-TTS language). Clips for
    --avg-embedding: clips.json clips[].file, else every *.wav in the voice folder."""
    voices = []
    for folder in sorted(p for p in Path(voices_dir).iterdir() if p.is_dir()):
        refs_json = folder / "references" / "references.json"
        if not refs_json.is_file():
            continue
        entry = json.loads(refs_json.read_text(encoding="utf-8")).get("qwen3-tts")
        if not entry:
            continue
        meta_path = folder / "voice.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
        lang = str(meta.get("language") or "").lower()
        ref_file = folder / "references" / entry["file"]
        data = ref_file.read_bytes()
        want = entry.get("sha256")
        sha_ok = None if not want else hashlib.sha256(data).hexdigest() == want
        ref = make_reference(data, entry["text"], False, "repo", name=folder.name,
                             language="English" if lang == "en" else "Auto")
        clips_json = folder / "clips.json"
        if clips_json.is_file():
            clips = [folder / c["file"] for c in json.loads(clips_json.read_text(encoding="utf-8")).get("clips", [])]
        else:
            clips = sorted(folder.glob("*.wav"))
        voices.append(RepoVoice(folder.name, ref, ref_file, [c for c in clips if c.is_file()], lang, sha_ok))
    return voices


# ------------------------------------------------------------------------------------------------ jobs

@dataclass(frozen=True)
class Sampling:
    """Talker (codebook 0) sampling; one set per generate call. The sub-talker keeps generation_config values."""

    temperature: float
    top_k: int
    top_p: float
    repetition_penalty: float

    def kwargs(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(eq=False)
class Job:
    rid: str
    text: str
    language: str
    ref: Reference
    sampling: Sampling
    non_streaming_mode: bool = False
    max_new_tokens: int | None = None   # the request's explicit cap
    seed: int | None = None
    future: asyncio.Future | None = None
    queued_at: float = field(default_factory=time.perf_counter)
    retries: int = 0

    @property
    def group_key(self) -> tuple:
        """Rows share one generate call only when these match: qwen-tts takes ONE set of sampling kwargs and ONE
        non_streaming_mode per call. Language, voice, reference and ICL/x-vector mode may differ per row."""
        return (self.sampling, self.non_streaming_mode)


@dataclass
class RowResult:
    wav: np.ndarray          # float32 at sample_rate, never longer than cap frames
    sample_rate: int
    codec_frames: int        # frames of this row after the cap trim
    cap: int                 # this row's own max_new_tokens (request value or the vLLM-Omni text-scaled default)
    batch_cap: int           # max_new_tokens passed to generate (max of the rows generated together)
    finish_reason: str       # stop (EOS inside the cap) | length (no EOS inside the cap)
    batch_size: int          # rows in the generate call that produced this row
    batch_id: int
    queue_ms: float          # enqueue (or re-enqueue for the retry) -> batch start on the worker
    prompt_ms: float         # voice-clone prompt lookup/creation for the whole batch
    gen_ms: float            # generate_voice_clone wall time of this row's call (includes reference re-decode)
    prompt_cache: str        # hit | miss | off
    text_tokens: int

    @property
    def audio_s(self) -> float:
        return len(self.wav) / self.sample_rate


@dataclass
class _Row:
    idx: int
    job: Job
    item: Any
    cache: str
    tokens: int
    cap: int
    wav: np.ndarray | None = None
    sub_batch: int = 0
    batch_cap: int = 0
    gen_ms: float = 0.0


def _is_oom(exc: BaseException) -> bool:
    return type(exc).__name__ == "OutOfMemoryError" or "out of memory" in str(exc).lower()


# ------------------------------------------------------------------------------------------ engine (worker thread)

class Engine:
    """Wraps a loaded qwen_tts.Qwen3TTSModel. Every method except the constructor runs on the worker thread."""

    def __init__(self, tts: Any, *, prompt_cache: bool = True, cache_size: int = 256) -> None:
        self.tts = tts
        self.cache_on = prompt_cache
        self.cache_size = max(1, cache_size)
        self._cache: OrderedDict[str, Any] = OrderedDict()   # LRU: inline and uploaded references
        self._pinned: dict[str, Any] = {}                     # repo voices, prepared at startup, never evicted
        gd = dict(getattr(tts, "generate_defaults", None) or {})
        self.defaults = Sampling(float(gd.get("temperature", 0.9)), int(gd.get("top_k", 50)),
                                 float(gd.get("top_p", 1.0)), float(gd.get("repetition_penalty", 1.05)))
        self.generation_config = gd
        langs = tts.model.get_supported_languages() or []
        self.languages = sorted({"Auto"} | {str(x).title() for x in langs})
        st = getattr(tts.model, "speech_tokenizer", None)
        self.spf = _int_or(lambda: st.get_decode_upsample_rate(), SAMPLES_PER_FRAME)
        self.sample_rate = _int_or(lambda: st.get_output_sample_rate(), SAMPLE_RATE)
        self.stats: Counter = Counter()
        self._thread: int | None = None
        self._batch_seq = 0

    def _on_worker(self) -> None:
        me = threading.get_ident()
        if self._thread is None:
            self._thread = me
        elif self._thread != me:
            raise RuntimeError("qwen-tts called from two threads; the model is not thread-safe")

    # -- prompts

    def _create(self, ref: Reference) -> Any:
        self.stats["prompts_created"] += 1
        items = self.tts.create_voice_clone_prompt(ref_audio=(ref.audio, ref.sr), ref_text=ref.ref_text,
                                                   x_vector_only_mode=ref.x_vector_only)
        item = items[0]
        if ref.spk_override is not None:
            old = item.ref_spk_embedding
            item = dataclasses.replace(item, ref_spk_embedding=ref.spk_override.to(device=old.device, dtype=old.dtype))
        return item

    def prompt_for(self, ref: Reference) -> tuple[Any, str]:
        """(VoiceClonePromptItem, hit|miss|off). Cache off: create_voice_clone_prompt on every request."""
        self._on_worker()
        if not self.cache_on:
            self.stats["prompt_off"] += 1
            return self._create(ref), "off"
        item = self._pinned.get(ref.key)
        if item is None and ref.key in self._cache:
            self._cache.move_to_end(ref.key)
            item = self._cache[ref.key]
        if item is not None:
            self.stats["prompt_hits"] += 1
            return item, "hit"
        item = self._create(ref)
        self._cache[ref.key] = item
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)
            self.stats["prompt_evictions"] += 1
        self.stats["prompt_misses"] += 1
        return item, "miss"

    def speaker_embedding(self, audio: np.ndarray, sr: int) -> torch.Tensor:
        """float32 CPU copy of extract_speaker_embedding on 24 kHz audio."""
        self._on_worker()
        emb = self.tts.model.extract_speaker_embedding(audio=to_24k(audio, sr), sr=SAMPLE_RATE)
        return emb.detach().float().cpu().reshape(-1)

    def average_embedding(self, voice: RepoVoice) -> tuple[torch.Tensor, dict]:
        """NOTES.md / qwen-tts-internals finding 8: mean of extract_speaker_embedding over all the voice's clips
        (resampled to 24 kHz), rescaled to the mean per-clip norm."""
        if not voice.clips:
            raise ValueError(f"voice {voice.id!r}: --avg-embedding needs clips, found none")
        embs = []
        for path in voice.clips:
            audio, sr = decode_audio(path.read_bytes())
            embs.append(self.speaker_embedding(audio, sr))
        e = torch.stack(embs)
        norms = e.norm(dim=1)
        mean = e.mean(dim=0)
        target = norms.mean()
        avg = mean * (target / mean.norm())
        ref_emb = self.speaker_embedding(voice.ref.audio, voice.ref.sr)
        cos = torch.nn.functional.cosine_similarity
        stats = {
            "clips": [p.name for p in voice.clips],
            "clip_norms": [round(float(x), 4) for x in norms],
            "target_norm": round(float(target), 4),
            "mean_norm_before_rescale": round(float(mean.norm()), 4),
            "avg_norm": round(float(avg.norm()), 4),
            "reference_norm": round(float(ref_emb.norm()), 4),
            "cos_avg_vs_reference": round(float(cos(avg, ref_emb, dim=0)), 4),
            "cos_clip_vs_reference": [round(float(cos(x, ref_emb, dim=0)), 4) for x in e],
        }
        return avg, stats

    def prepare_voice(self, voice: RepoVoice, avg_embedding: bool) -> tuple[Reference, dict]:
        """Startup work for a repo voice: optional averaged embedding, then (cache on) its pinned prompt."""
        self._on_worker()
        stats: dict[str, Any] = {"voice": voice.id, "language": voice.ref.language,
                                 "ref_seconds": round(voice.ref.seconds, 3), "ref_sha256_ok": voice.sha256_ok}
        ref = voice.ref
        if avg_embedding:
            t = time.perf_counter()
            avg, stats["avg_embedding"] = self.average_embedding(voice)
            stats["avg_embedding_ms"] = round((time.perf_counter() - t) * 1000, 1)
            ref = dataclasses.replace(ref, key=ref.key + ":avg", spk_override=avg)
        if self.cache_on:
            t = time.perf_counter()
            item = self._create(ref)
            self._pinned[ref.key] = item
            stats["prompt_ms"] = round((time.perf_counter() - t) * 1000, 1)
            code = getattr(item, "ref_code", None)
            stats["ref_code_frames"] = None if code is None else int(code.shape[0])
            stats["spk_embedding_norm"] = round(float(item.ref_spk_embedding.float().norm()), 4)
        return ref, stats

    # -- generation

    def text_tokens(self, text: str) -> int:
        """Text tokens of the input, counted like vLLM-Omni _count_usage_text_tokens (0 on failure)."""
        try:
            ids = self.tts.processor.tokenizer(text, padding=False)["input_ids"]
            return int(ids.shape[-1]) if hasattr(ids, "shape") else len(ids)
        except Exception:  # noqa: BLE001
            return 0

    @staticmethod
    def default_cap(text_tokens: int) -> int:
        if text_tokens <= 0:
            return MAX_NEW_TOKENS_MAX
        return min(max(MIN_CODEC_FRAMES, FRAMES_PER_TEXT_TOKEN * text_tokens), MAX_NEW_TOKENS_MAX)

    def run_batch(self, jobs: list[Job]) -> list[RowResult | BaseException]:
        """Generate one batch (one set of sampling params, one non_streaming_mode). Returns a result or an exception
        per job, in order. A seeded job must be alone: torch.manual_seed(seed) then generate; afterwards the global
        RNG is re-seeded randomly (torch.seed()) so later unseeded batches are not deterministic by accident."""
        self._on_worker()
        if not jobs:
            return []
        if len({j.group_key for j in jobs}) != 1:
            raise ValueError("a batch must share sampling params and non_streaming_mode")
        seed = jobs[0].seed
        if any(j.seed is not None for j in jobs) and len(jobs) > 1:
            raise ValueError("seeded requests must run alone")
        self._batch_seq += 1
        bid = self._batch_seq
        t0 = time.perf_counter()
        queue_ms = [(t0 - j.queued_at) * 1000 for j in jobs]
        out: dict[int, RowResult | BaseException] = {}
        rows: list[_Row] = []
        for i, job in enumerate(jobs):
            try:
                item, status = self.prompt_for(job.ref)
                tokens = self.text_tokens(job.text)
                rows.append(_Row(i, job, item, status, tokens, job.max_new_tokens or self.default_cap(tokens)))
            except Exception as exc:  # noqa: BLE001 - one bad reference fails only its own row
                out[i] = exc
        prompt_ms = (time.perf_counter() - t0) * 1000
        if rows:
            try:
                if seed is not None:
                    torch.manual_seed(seed)
                self._generate(rows)
            except Exception as exc:  # noqa: BLE001
                for r in rows:
                    out[r.idx] = exc
                rows = []
            finally:
                if seed is not None:
                    torch.seed()
        for r in rows:
            out[r.idx] = self._finish(r, bid, queue_ms[r.idx], prompt_ms)
        self.stats["batches"] += 1
        self.stats["rows"] += len(jobs)
        return [out[i] for i in range(len(jobs))]

    def _generate(self, rows: list[_Row]) -> None:
        """One generate_voice_clone call for `rows`; max_new_tokens = the largest row cap. On CUDA out-of-memory
        the rows are split in halves and retried (recursively, down to single rows)."""
        cap = max(r.cap for r in rows)
        job0 = rows[0].job
        t = time.perf_counter()
        try:
            wavs, sr = self.tts.generate_voice_clone(
                text=[r.job.text for r in rows], language=[r.job.language for r in rows],
                voice_clone_prompt=[r.item for r in rows], non_streaming_mode=job0.non_streaming_mode,
                max_new_tokens=cap, **job0.sampling.kwargs())
        except Exception as exc:  # noqa: BLE001
            if not _is_oom(exc) or len(rows) == 1:
                raise
            self.stats["oom_splits"] += 1
            log.warning("oom_split", extra={"fields": {"rows": len(rows), "max_new_tokens": cap}})
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            half = len(rows) // 2
            self._generate(rows[:half])
            self._generate(rows[half:])
            return
        ms = (time.perf_counter() - t) * 1000
        if int(sr) != self.sample_rate:
            raise RuntimeError(f"model returned {sr} Hz, expected {self.sample_rate}")
        if len(wavs) != len(rows):
            raise RuntimeError(f"model returned {len(wavs)} waveforms for {len(rows)} texts")
        self.stats["generate_calls"] += 1
        for r, w in zip(rows, wavs, strict=True):
            r.wav, r.sub_batch, r.batch_cap, r.gen_ms = np.asarray(w, dtype=np.float32).reshape(-1), len(rows), cap, ms

    def _finish(self, r: _Row, bid: int, queue_ms: float, prompt_ms: float) -> RowResult:
        """Per-row cap. generate() ran to the batch's largest cap; a row whose own cap is smaller is cut to it. The
        decoder is causal and emits exactly 1920 samples per frame (the reference is cut off proportionally, which is
        exact), so cutting samples at cap x 1920 equals decoding only the first `cap` frames. frames >= cap means the
        row did not emit EOS within its own cap (exactly what a lone run with max_new_tokens=cap would report)."""
        wav = r.wav
        frames = int(round(len(wav) / self.spf))
        finish = "length" if frames >= r.cap else "stop"
        if frames > r.cap:
            wav, frames = wav[: r.cap * self.spf], r.cap
            self.stats["rows_trimmed"] += 1
        if finish == "length":
            self.stats["rows_length"] += 1
        return RowResult(wav=wav, sample_rate=self.sample_rate, codec_frames=frames, cap=r.cap, batch_cap=r.batch_cap,
                         finish_reason=finish, batch_size=r.sub_batch, batch_id=bid, queue_ms=queue_ms,
                         prompt_ms=prompt_ms, gen_ms=r.gen_ms, prompt_cache=r.cache, text_tokens=r.tokens)


def _int_or(fn, default: int) -> int:
    try:
        return int(fn())
    except Exception:  # noqa: BLE001
        return default


# ------------------------------------------------------------------------------------------------ batcher (event loop)

class Batcher:
    """FIFO dynamic batching in front of the single worker thread.

    - The oldest pending job decides the next batch. Unseeded: all pending jobs with the same group_key (sampling
      params + non_streaming_mode), in arrival order, up to max_batch. Seeded: that job alone.
    - While the worker is idle, a new batch waits until max_batch compatible jobs are pending or `window_s` has
      passed since the oldest job arrived. Jobs that arrived while the worker was busy start at once.
    - One batch in flight at a time (the model is not thread-safe); jobs of other groups wait for later batches.
    - A row that ends with finish_reason 'length' (no EOS within its cap) is, with length_policy 'error' (vLLM-Omni
      0.28 behaviour), re-queued once at the front when the request sent neither seed nor max_new_tokens, and
      otherwise fails with CodecLimitError (HTTP 500). length_policy 'truncate' returns the capped audio instead.
    """

    def __init__(self, run_batch, executor: Executor, *, max_batch: int = 8, window_s: float = 0.02,
                 max_queue: int = 512, length_policy: str = "error", retry_length: bool = True) -> None:
        self.run_batch = run_batch
        self.executor = executor
        self.max_batch = max(1, max_batch)
        self.window_s = max(0.0, window_s)
        self.max_queue = max_queue
        self.length_policy = length_policy
        self.retry_length = retry_length
        self.pending: list[Job] = []
        self.busy = False
        self._wake = asyncio.Event()
        self.stats: Counter = Counter()
        self.batch_sizes: Counter = Counter()

    async def submit(self, job: Job) -> RowResult:
        if self.max_queue and len(self.pending) >= self.max_queue:
            self.stats["queue_full"] += 1
            raise QueueFull(f"queue full ({len(self.pending)} pending)")
        job.future = asyncio.get_running_loop().create_future()
        job.queued_at = time.perf_counter()
        self.pending.append(job)
        self.stats["submitted"] += 1
        self.stats["max_pending"] = max(self.stats["max_pending"], len(self.pending))
        self._wake.set()
        try:
            return await job.future
        except asyncio.CancelledError:
            if job in self.pending:
                self.pending.remove(job)
                self.stats["cancelled_pending"] += 1
            raise

    def _compatible(self, head: Job) -> int:
        return sum(1 for j in self.pending if j.seed is None and j.group_key == head.group_key)

    def _take(self, head: Job) -> list[Job]:
        if head.seed is not None:
            batch = [head]
        else:
            batch = [j for j in self.pending if j.seed is None and j.group_key == head.group_key][: self.max_batch]
        for j in batch:
            self.pending.remove(j)
        return batch

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            if not self.pending:
                self._wake.clear()
                await self._wake.wait()
                continue
            head = self.pending[0]
            if head.seed is None and self.max_batch > 1:
                deadline = head.queued_at + self.window_s
                while self._compatible(head) < self.max_batch:
                    remaining = deadline - time.perf_counter()
                    if remaining <= 0:
                        break
                    self._wake.clear()
                    try:
                        await asyncio.wait_for(self._wake.wait(), remaining)
                    except asyncio.TimeoutError:
                        break
                if not self.pending or self.pending[0] is not head:
                    continue  # the head was cancelled while we waited
            batch = self._take(head)
            self.batch_sizes[len(batch)] += 1
            self.busy = True
            try:
                results = await loop.run_in_executor(self.executor, self.run_batch, batch)
            except Exception as exc:  # noqa: BLE001 - the worker failed as a whole: fail every row
                results = [exc] * len(batch)
            finally:
                self.busy = False
            try:
                self._settle(batch, results)
            except Exception as exc:  # noqa: BLE001 - never let the batcher die: fail whatever is still open
                log.error("batcher_error", exc_info=exc, extra={"fields": {"rows": len(batch)}})
                for job in batch:
                    if job.future is not None and not job.future.done():
                        job.future.set_exception(exc)

    def _settle(self, batch: list[Job], results: list) -> None:
        requeue = []
        for job, res in zip(batch, results, strict=True):
            if job.future is None or job.future.done():
                continue  # the client went away (cancelled) while its batch ran
            if isinstance(res, RowResult) and res.finish_reason == "length":
                self.stats["length_rows"] += 1
                if self.length_policy == "error":
                    if self.retry_length and job.seed is None and job.max_new_tokens is None and job.retries == 0:
                        job.retries += 1
                        job.queued_at = time.perf_counter()
                        requeue.append(job)
                        self.stats["length_retries"] += 1
                        continue
                    res = CodecLimitError(
                        f"Qwen3-TTS Base did not emit codec EOS before its token budget ({res.codec_frames}/{res.cap} "
                        "codec tokens); the generated audio is incomplete.")
            fut = job.future
            if isinstance(res, BaseException):
                self.stats["failed"] += 1
                fut.set_exception(res)
            else:
                self.stats["completed"] += 1
                fut.set_result(res)
        if requeue:
            self.pending[0:0] = requeue
            self._wake.set()
