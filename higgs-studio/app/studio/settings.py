"""Settings from environment variables (prefix STUDIO_), optionally read from higgs-studio/.env. No secrets needed."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]  # higgs-studio/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STUDIO_", env_file=str(ROOT / ".env"), extra="ignore")

    engine_url: str = "http://127.0.0.1:8095"   # the Higgs engine (vLLM-Omni /v1/audio/speech)
    engine_api_key: str = ""                    # only if the engine was started with an API key
    host: str = "0.0.0.0"                       # internal network / VPN only: there is no login
    port: int = 8100
    data_dir: Path = ROOT / "data"              # jobs, uploads, takes, reference cache, sqlite
    voices_dir: Path = ROOT / "voices"          # preset voices: <folder>/{*.wav, transcripts.json, persona.json?}

    max_inflight: int = 28                      # requests in flight at the engine (its max_num_seqs is 32)
    dev_max_inflight: int = 24                  # dev jobs never take the last (max_inflight - dev) slots
    customer_queue_max: int = 40                # customer requests waiting beyond this -> 503 "server busy"
    request_timeout_s: float = 240.0
    max_ref_s: float = 29.5                     # the engine rejects reference clips over 30 s
    max_part_s: float = 25.0                    # estimated speech per generation request (~30 s engine ceiling)
    join_gap_s: float = 0.3
    take_ttl_h: float = 24.0                    # customer takes are kept this long
    max_upload_mb: int = 50


    def model_post_init(self, _ctx) -> None:
        # relative paths in .env are relative to higgs-studio/, not to the working directory
        for name in ("data_dir", "voices_dir"):
            p = getattr(self, name).expanduser()
            setattr(self, name, p if p.is_absolute() else ROOT / p)


settings = Settings()
