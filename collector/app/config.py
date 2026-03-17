"""Application settings via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Collector service configuration."""

    database_url: str = "sqlite+aiosqlite:///./agenttrace.db"
    collector_host: str = "0.0.0.0"
    collector_port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
