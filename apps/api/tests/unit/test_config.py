import secrets

import pytest
from pydantic import SecretStr, ValidationError
from pydantic_settings import SettingsConfigDict

from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine


class IsolatedSettings(Settings):
    model_config = SettingsConfigDict(env_file=None)


def test_secret_is_hidden_in_settings_and_engine_representation() -> None:
    password = secrets.token_urlsafe(24)
    value = SecretStr(f"postgresql+psycopg://wine_api:{password}@127.0.0.1:54322/postgres")
    settings = IsolatedSettings(database_url=value)
    engine = database_engine(value)
    try:
        assert password not in repr(settings)
        assert password not in repr(engine)
        assert engine.hide_parameters
    finally:
        engine.dispose()


@pytest.mark.parametrize("role", ["postgres", "wine_migrator"])
def test_api_rejects_administrative_database_roles(role: str) -> None:
    value = SecretStr(f"postgresql+psycopg://{role}:{secrets.token_urlsafe(24)}@localhost/db")
    with pytest.raises(ValueError, match="wine_api"):
        database_engine(value)


def test_remote_database_requires_verified_tls() -> None:
    value = SecretStr(f"postgresql+psycopg://wine_api:{secrets.token_urlsafe(24)}@db.example/db")
    with pytest.raises(ValueError, match="sslmode=verify-full"):
        database_engine(value)


@pytest.mark.parametrize(
    "issuer",
    [
        "http://example.com/auth/v1",
        "https://example.com/auth/v1?key=hidden",
        "https://u:p@example.com/auth/v1",
    ],
)
def test_invalid_issuer_configuration_is_rejected_without_echoing_input(issuer: str) -> None:
    with pytest.raises(ValidationError) as exc:
        IsolatedSettings(auth_issuer=issuer)
    assert issuer not in str(exc.value)
