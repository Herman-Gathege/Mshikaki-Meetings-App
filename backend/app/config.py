"""Application settings.

Environment variables are the single source of truth (12-factor). A local `.env`
file is read as a convenience; the container receives its values from Compose.
Startup fails loudly on a missing or obviously unsafe value rather than
half-working.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root when running from backend/, otherwise the working directory.
_ENV_FILES = (
    Path(".env"),
    Path("../.env"),
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_env: str = "development"
    app_secret_key: str = "change-me-generate-a-real-secret"
    app_port: int = 8080
    root_url: str = "http://localhost:8080"
    log_level: str = "info"
    team_timezone: str = "Africa/Nairobi"

    # Database
    postgres_user: str = "mshikaki"
    postgres_password: str = "change-me"
    postgres_db: str = "mshikaki"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    # Sessions
    session_cookie_secure: bool = False
    session_ttl_days: int = 14

    # Digest email (Phase 4)
    digest_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = True
    mail_from: str = "mshikaki@localhost"

    # Where the built SPA lives in the production image.
    static_dir: Path = Field(default=Path(__file__).resolve().parent.parent / "static")

    @field_validator("log_level")
    @classmethod
    def _known_log_level(cls, value: str) -> str:
        allowed = {"critical", "error", "warning", "info", "debug", "trace"}
        if value.lower() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed)}")
        return value.lower()

    @model_validator(mode="after")
    def _guard_production(self) -> Settings:
        if self.app_env == "production":
            if self.app_secret_key.startswith("change-me"):
                raise ValueError(
                    "APP_SECRET_KEY still has its default value. Generate one with: "
                    'python3 -c "import secrets; print(secrets.token_urlsafe(48))"'
                )
            if self.postgres_password == "change-me":
                raise ValueError("POSTGRES_PASSWORD still has its default value.")
        return self

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def sqlalchemy_url(self) -> str:
        """Explicit DATABASE_URL wins; otherwise build the DSN from the parts."""
        if self.database_url:
            return self.database_url
        password = quote_plus(self.postgres_password)
        return (
            f"postgresql+psycopg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
