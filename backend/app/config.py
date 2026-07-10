"""Application configuration loaded from environment / .env.

Required environment variables:
    GROQ_API_KEY     – Groq API key
    DATABASE_URL     – SQLAlchemy URL (Postgres recommended; SQLite works)
    APP_ENV         – development | production
    FRONTEND_ORIGIN – CORS allow-origin for the Vite dev server
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    database_url: str = "sqlite:///./crm_hcp.db"
    app_env: str = "development"
    frontend_origin: str = "http://localhost:5173"

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
