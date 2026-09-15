from collections.abc import Callable
from uuid import uuid4

import psycopg
import pytest
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.accounts.models import AppUser
from wine_journal.core.database import database_engine


def test_fresh_migration_can_downgrade_and_upgrade(
    database_urls: dict[str, SecretStr],
    migrate: Callable[..., None],
) -> None:
    migrate("check")
    migrate("downgrade", "base")
    with psycopg.connect(database_urls["admin"].get_secret_value()) as db:
        assert db.execute("SELECT to_regclass('app.app_users')").fetchone() == (None,)
    migrate("upgrade", "head")
    migrate("check")


def test_runtime_role_is_limited_and_provider_roles_cannot_read_app(
    database_urls: dict[str, SecretStr],
) -> None:
    engine = database_engine(database_urls["runtime"])
    try:
        with engine.connect() as connection:
            permissions = connection.execute(
                text(
                    "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, "
                    "rolbypassrls, rolinherit "
                    "FROM pg_roles WHERE rolname = current_user"
                )
            ).one()
            assert permissions == (False,) * 6
        for statement in [
            "CREATE TABLE app.forbidden (id int)",
            "CREATE TABLE public.forbidden (id int)",
            "ALTER TABLE app.app_users ADD COLUMN forbidden int",
            "SELECT * FROM auth.users",
            "CREATE ROLE forbidden",
            "SET ROLE wine_migrator",
        ]:
            with engine.begin() as connection, pytest.raises(ProgrammingError):
                connection.execute(text(statement))
        with psycopg.connect(database_urls["admin"].get_secret_value()) as db:
            for role in ("anon", "authenticated"):
                row = db.execute(
                    "SELECT has_schema_privilege(%s, 'app', 'USAGE'), "
                    "has_table_privilege(%s, 'app.app_users', 'SELECT')",
                    (role, role),
                ).fetchone()
                assert row == (False, False)
    finally:
        engine.dispose()


def test_identity_uniqueness_and_state_constraint(database_urls: dict[str, SecretStr]) -> None:
    engine = database_engine(database_urls["runtime"])
    issuer, subject = "https://identity.example/auth/v1", uuid4()
    try:
        with Session(engine) as session, session.begin():
            session.add(AppUser(auth_issuer=issuer, auth_subject=subject))
        with Session(engine) as session, pytest.raises(IntegrityError), session.begin():
            session.add(AppUser(auth_issuer=issuer, auth_subject=subject))
        with Session(engine) as session, pytest.raises(IntegrityError), session.begin():
            session.add(AppUser(auth_issuer=issuer, auth_subject=uuid4(), state="UNKNOWN"))
        with Session(engine) as session:
            account = session.scalar(select(AppUser).where(AppUser.auth_subject == subject))
            assert account is not None and account.created_at.tzinfo is not None
    finally:
        engine.dispose()
