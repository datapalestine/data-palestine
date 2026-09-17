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

    # Admin auth
    admin_secret_key: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        _validate_production_settings(self)


def _validate_production_settings(s: "Settings") -> None:
    """Fail loudly in production if secret_key/admin_secret_key is unset or a known default."""
    if s.environment == "development":
        return
    if not s.secret_key:
        raise RuntimeError(
            "SECRET_KEY must be set in production. Set the SECRET_KEY environment variable."
        )
    if not s.admin_secret_key or s.admin_secret_key == "admin-dev-key-change-me":
        raise RuntimeError(
            "ADMIN_SECRET_KEY must be set to a non-default value in production. "
            "Set the ADMIN_SECRET_KEY environment variable."
        )


settings = Settings()
