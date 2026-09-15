from pathlib import Path
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIRECTORY = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WINE_JOURNAL_",
        env_file=API_DIRECTORY / ".env",
        extra="ignore",
        hide_input_in_errors=True,
    )

    cors_origins: list[str] = ["http://localhost:3000"]
    database_url: SecretStr | None = None
    auth_issuer: str | None = None

    @field_validator("auth_issuer")
    @classmethod
    def validate_issuer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or (parsed.scheme != "https" and not (local and parsed.scheme == "http"))
            or parsed.path != "/auth/v1"
        ):
            raise ValueError("Use the HTTPS Supabase auth issuer; HTTP is local-only.")
        return value


class MigrationSettings(BaseSettings):
    """Only the migration process loads this separate credential file."""

    model_config = SettingsConfigDict(
        env_prefix="WINE_JOURNAL_",
        env_file=API_DIRECTORY / ".env.migrations",
        extra="ignore",
        hide_input_in_errors=True,
    )
    migration_database_url: SecretStr
