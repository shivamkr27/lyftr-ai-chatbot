import os
from dataclasses import dataclass
from typing import List


def _csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    llm_api_keys: List[str]
    database_url: str
    allowed_origins: List[str]
    enable_failure_simulation: bool
    llm_model: str
    cache_enabled: bool


def get_settings() -> Settings:
    keys = _csv(os.getenv("LLM_API_KEYS", ""))
    if len(keys) < 2:
        raise RuntimeError("LLM_API_KEYS must configure at least two API keys")

    return Settings(
        llm_api_keys=keys,
        database_url=os.getenv("DATABASE_URL", "sqlite:////data/app.db"),
        allowed_origins=_csv(os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")),
        enable_failure_simulation=os.getenv("ENABLE_FAILURE_SIMULATION", "false").lower() == "true",
        llm_model=os.getenv("LLM_MODEL", "groq/llama-3.3-70b-versatile"),
        cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
    )
