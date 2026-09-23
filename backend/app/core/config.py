"""Application configuration.

All secrets and environment-specific values are read from environment
variables (optionally via a local .env file). Nothing is hardcoded.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Runtime settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "sqlite:///./drishti.db"
    app_env: str = "development"
    # Backlog #2 — auth. Production MUST set a real secret; the default only
    # exists so the demo stack boots. Warned about at startup in production.
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:5173,http://localhost:5317,http://localhost:5199,http://127.0.0.1:5317,http://127.0.0.1:5199"

    model_version: str = "iforest-v1"
    ruleset_version: str = "rules-v1"
    report_storage_path: str = str(BASE_DIR / "reports")

    demo_autoseed: bool = True

    session_ttl_hours: int = 8
    demo_accounts_enabled: bool = True

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
