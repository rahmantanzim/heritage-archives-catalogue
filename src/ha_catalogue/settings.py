"""Configuration, read from environment variables or a `.env` file."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # e.g. postgresql+psycopg://ha:password@127.0.0.1:5432/ha_catalogue
    database_url: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # raises a clear error if DATABASE_URL is missing
