from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = Field(default="change-me-in-production")

    # ── NewsAPI ───────────────────────────────────────────────
    NEWS_API_KEY: str
    NEWS_API_BASE_URL: str = "https://newsapi.org/v2"
    NEWS_API_TIMEOUT: int = 10
    NEWS_API_MAX_RETRIES: int = 3

    # ── Redis (Phase 1: disabled, Phase 3: enabled) ───────────
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_REDIS: bool = False

    # ── Database (Phase 1: in-memory, Phase 3: PostgreSQL) ────
    DATABASE_URL: Optional[str] = None

    # ── ML Model ──────────────────────────────────────────────
    MODEL_NAME: str = "sshleifer/distilbart-cnn-12-6"
    MODEL_VERSION: str = "sshleifer/distilbart-cnn-12-6"

    # ── Celery (Phase 3) ──────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Observability (Phase 4) ───────────────────────────────
    OTEL_SERVICE_NAME: str = "hubb-api"
    OTEL_SERVICE_VERSION: str = "1.0.0"
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None  # e.g. http://localhost:4317

    # ── Security ──────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60
    ALLOWED_ORIGINS: str = "*"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
