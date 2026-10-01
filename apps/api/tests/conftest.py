import os
import secrets
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import psycopg
import pytest
from pydantic import SecretStr
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def database_urls() -> dict[str, SecretStr]:
    raw = os.environ.get("WINE_JOURNAL_TEST_ADMIN_DATABASE_URL")
    if not raw:
        pytest.skip("Use scripts/run_api_tests.py for real Postgres integration tests.")
    admin = make_url(raw)
    if admin.host != "127.0.0.1" or admin.database != "wine_journal_test" or admin.port == 54322:
        pytest.fail("Integration tests require the disposable local test database.")
    values = {"admin": SecretStr(raw)}
    environment = dict(os.environ)
    environment["WINE_JOURNAL_ADMIN_DATABASE_URL"] = raw
    for name, role, variable in [
        ("runtime", "wine_api", "WINE_JOURNAL_DATABASE_URL"),
        ("migration", "wine_migrator", "WINE_JOURNAL_MIGRATION_DATABASE_URL"),
    ]:
        value = admin.set(
            drivername="postgresql+psycopg", username=role, password=secrets.token_urlsafe(32)
        ).render_as_string(hide_password=False)
        values[name] = SecretStr(value)
        environment[variable] = value
    with psycopg.connect(raw) as db:
        # Stand-ins for provider-managed roles/schema to prove negative grants.
        db.execute("CREATE ROLE anon NOLOGIN")
        db.execute("CREATE ROLE authenticated NOLOGIN")
        db.execute("CREATE SCHEMA auth")
        db.execute("CREATE TABLE auth.users (id uuid PRIMARY KEY)")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/provision_database.py")],
        env=environment,
        capture_output=True,
    )
    assert result.returncode == 0, "Disposable role provisioning failed."
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT / "apps/api",
        env=environment,
        capture_output=True,
    )
    assert result.returncode == 0, "Fresh-database migration failed."
    return values


@pytest.fixture
def migrate(database_urls: dict[str, SecretStr]) -> Callable[..., None]:
    def run(*arguments: str) -> None:
        environment = dict(os.environ)
        environment["WINE_JOURNAL_MIGRATION_DATABASE_URL"] = database_urls[
            "migration"
        ].get_secret_value()
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=ROOT / "apps/api",
            env=environment,
            capture_output=True,
        )
        assert result.returncode == 0, "Migration verification failed."

    return run
