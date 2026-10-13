# qwen-server

The whole `qwen-server` workspace, laid out as it is on disk:

| folder | what |
|---|---|
| [`tts-reference-voices/`](tts-reference-voices/README.md) | the Qwen3-TTS voice-clone server (`server/`), its benchmark, report and results, the Higgs TTS 3 benchmark (`higgs/`), published samples |
| [`higgs-studio/`](higgs-studio/README.md) | dev dataset console + customer Studio on Higgs TTS 3 (one-shot `setup.sh`, systemd units) |
| [`qwen-train/`](qwen-train/README.md) | the Qwen3-TTS Urdu fine-tuning pipeline (derive, QC, corrected trainer, alignment check, eval, export) |
| [`higgs-gguf/`](higgs-gguf/README.md) | Higgs TTS 3 → GGUF converter and vLLM-Omni loader harness, with results |

Not in git (each folder's `.gitignore`): model weights (Hugging Face cache, `higgs-gguf/weights/`), Python
environments, `.env` files, training data, voice references of private people, and generated audio other than the
labelled published sets. All generated audio is AI-generated; Higgs TTS 3 is licensed for research and non-commercial
use only.
