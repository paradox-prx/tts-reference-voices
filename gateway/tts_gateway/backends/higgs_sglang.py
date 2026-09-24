"""Placeholder for a Higgs Audio v3 backend served by SGLang-Omni. Not implemented yet."""

from __future__ import annotations

from ..config import Settings
from ..voices import VoiceRegistry


class HiggsSglangBackend:
    """What a Higgs Audio v3 / SGLang-Omni backend must do to plug into the gateway:

    - Advertise its limits through `capabilities`: `max_seconds_per_call=30` (Higgs generates at most ~30 s per
      call), so the gateway packs whole sentences into parts under that ceiling (`textproc.split_for_ceiling`),
      runs them in order within one admission slot, and joins the PCM with short silences, both non-streaming and
      streaming. Set `per_request_repetition_penalty` / `streaming` to what the SGLang-Omni API really accepts, and
      `sample_rate` to the codec's output rate (the gateway writes the streaming WAV header before the first chunk).
    - Keep Higgs inline tags intact: the text may carry tags such as `[laugh]` or `<SE>...</SE>`; send it verbatim,
      and make sure a tag never straddles a part boundary (sentence splitting only cuts at . ! ? ۔ ؟ and newlines).
    - Apply its own sampling defaults when the request leaves them unset (`req.temperature is None` etc.):
      temperature 0.8, top_k 50. The gateway's TTS_DEFAULT_TEMPERATURE / TTS_DEFAULT_TOP_K are tuned for Qwen3-TTS.
    - Translate `req.max_new_tokens` (Qwen3-TTS codec frames, 12.5 per second) to its own token rate, or ignore it
      and rely on the 30 s ceiling.
    - Clone from `voice.ref_audio` / `voice.data_url` + `voice.ref_text` (or `req.ref_audio` + `req.ref_text` for
      inline requests); if the server has no voice store, set `voice_registry=False` and make `register_voice` a
      no-op that only validates the reference.
    - Return PCM16 mono (`SynthesisResult.pcm`, `stream()` chunks) and map failures to the typed errors in
      `backends.base`: EngineUnavailable (connection refused, 503), EngineTimeout, EngineBadRequest (4xx from the
      server), EngineFailure(retryable=True) for runaways / transient 5xx, retryable=False otherwise.
    - `health()` must reflect the SGLang-Omni server's own health endpoint, so /ready turns red when it dies.
    """

    name = "higgs_sglang"

    def __init__(self, settings: Settings, voices: VoiceRegistry) -> None:
        raise NotImplementedError("the Higgs Audio v3 (SGLang-Omni) backend is not implemented yet; "
                                  "use TTS_BACKEND=vllm_omni or stub")
