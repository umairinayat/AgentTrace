"""Application settings via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Collector service configuration."""

    database_url: str = "sqlite+aiosqlite:///./agenttrace.db"
    collector_host: str = "0.0.0.0"
    collector_port: int = 8000
    log_level: str = "INFO"
    # Comma-separated allowed origins. Defaults to the dashboard (compose) and
    # Vite dev server. Set to "*" only for fully open deployments (credentials
    # are then disabled, since browsers reject "*" together with credentials).
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
