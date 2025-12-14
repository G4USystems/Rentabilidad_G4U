"""Application configuration settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Rentabilidad G4U"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # Qonto API
    qonto_api_key: str = ""
    qonto_organization_slug: str = ""
    qonto_iban: str = ""
    qonto_api_base_url: str = "https://thirdparty.qonto.com/v2"

    # Database (Supabase)
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/rentabilidad_g4u"

    # Supabase specific (optional, for direct access)
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Report Settings
    default_currency: str = "EUR"
    fiscal_year_start_month: int = 1

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
