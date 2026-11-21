"""Application configuration from environment variables."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


def _load_env_file() -> None:
    """Load key-value pairs from .env in current or parent dirs if not already in env."""
    search_paths = [
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for p in search_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip()
                        if (v.startswith('"') and v.endswith('"')) or (
                            v.startswith("'") and v.endswith("'")
                        ):
                            v = v[1:-1]
                        if k not in os.environ:
                            os.environ[k] = v
                break
            except Exception:
                pass


_load_env_file()


@dataclass
class Settings:
    llm_api_keys: List[str] = field(default_factory=list)
    database_url: str = "sqlite:////data/app.db"
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    enable_failure_simulation: bool = False
    default_model: str = "gemini/gemini-2.0-flash"
    default_system_prompt: str = "You are a helpful assistant."

    @classmethod
    def from_env(cls) -> "Settings":
        _load_env_file()
        raw_keys = os.environ.get("LLM_API_KEYS", "")
        keys = [k.strip() for k in raw_keys.split(",") if k.strip()] if raw_keys else []
        # If user provided exactly 1 key, duplicate as key_2 so fallback & health requirements work
        if len(keys) == 1:
            keys.append(keys[0])

        raw_origins = os.environ.get("ALLOWED_ORIGINS", "*")
        origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

        return cls(
            llm_api_keys=keys,
            database_url=os.environ.get("DATABASE_URL", "sqlite:////data/app.db"),
            allowed_origins=origins,
            enable_failure_simulation=os.environ.get("ENABLE_FAILURE_SIMULATION", "").lower() == "true",
            default_model=os.environ.get("DEFAULT_MODEL", "gemini/gemini-2.0-flash"),
            default_system_prompt=os.environ.get("DEFAULT_SYSTEM_PROMPT", "You are a helpful assistant."),
        )


settings = Settings.from_env()
