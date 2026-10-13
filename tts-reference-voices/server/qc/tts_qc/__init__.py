"""tts_qc: quality checks for voice-clone TTS takes (Qwen3-TTS, English + Urdu).

One code path serves both uses:
  * the online QC sidecar (`python -m tts_qc`, FastAPI on 127.0.0.1:8092): POST /v1/qc per non-streaming take;
  * the offline scorer (server/eval/score_run.py) for benchmark result dirs.

Modules: textnorm (Urdu/English normalizers), checks (loop/skip/silence detectors), audio (I/O, resampling, trim),
asr (faster-whisper large-v3), sim (WavLM speaker similarity), voices (reference clips, pace), policy (gate and
offline 'bad' label), scorer (models + one-take scoring), app (HTTP API). Design and calibration:
server/docs/research/eval-tooling.md; operator notes: server/qc/README.md.
"""

__version__ = "0.1.0"
