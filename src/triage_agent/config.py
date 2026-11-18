"""Settings, read from TRIAGE_* environment variables and an optional .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings. Each value can be overridden with a TRIAGE_* environment variable."""

    model_config = SettingsConfigDict(env_prefix="TRIAGE_", env_file=".env", extra="ignore")

    log_level: str = Field(default="INFO", description="Python logging level name.")
    classifier: Literal["rules", "llm"] = Field(
        default="rules", description="rules needs nothing; llm needs an OpenAI-compatible endpoint."
    )
    llm_base_url: str = Field(
        default="http://localhost:11434/v1",
        description="Ollama's OpenAI-compatible API by default.",
    )
    llm_model: str = Field(default="qwen2.5:3b", description="Model name sent to the endpoint.")
    llm_api_key: str = Field(default="", description="Bearer token, if the endpoint needs one.")
    review_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    checkpoint_db: Path = Field(default=Path("data/checkpoints.sqlite"))
    tickets_file: Path = Field(default=Path("data/tickets.jsonl"))
    results_dir: Path = Field(default=Path("results"))
    trace_exporter: Literal["none", "console", "otlp"] = Field(default="none")


@lru_cache
def get_settings() -> Settings:
    """Return the settings, created once per process."""
    return Settings()
