"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = (
        "postgresql+asyncpg://datapal:datapal_dev_2026@localhost:5432/datapalestine"
    )
    database_url_sync: str = (
        "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine"
    )

    # Application
    environment: str = "development"
    secret_key: str = ""
    cors_origins: str = "http://localhost:3000"

    # Rate limiting
    rate_limit_per_minute: int = 100


settings = Settings()

# Fail loudly in production if secret_key is not set
if settings.environment != "development" and not settings.secret_key:
    raise RuntimeError("SECRET_KEY must be set in production. Set the SECRET_KEY environment variable.")
