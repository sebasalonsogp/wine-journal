"""Provision only local application roles/schema. Does not run migrations."""

import os
import sys

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url


def main() -> None:
    admin = make_url(os.environ["WINE_JOURNAL_ADMIN_DATABASE_URL"])
    if admin.host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("This setup command is for a local database only.")
    roles = {
        "wine_migrator": make_url(os.environ["WINE_JOURNAL_MIGRATION_DATABASE_URL"]),
        "wine_api": make_url(os.environ["WINE_JOURNAL_DATABASE_URL"]),
    }
    for name, value in roles.items():
        if (
            value.username != name
            or not value.password
            or (value.host, value.port, value.database) != (admin.host, admin.port, admin.database)
        ):
            raise ValueError("Local role connections must target the same database.")

    with psycopg.connect(
        admin.set(drivername="postgresql").render_as_string(hide_password=False)
    ) as db:
        for name, value in roles.items():
            exists = db.execute("SELECT oid FROM pg_roles WHERE rolname = %s", (name,)).fetchone()
            if exists:
                elevated = db.execute(
                    "SELECT rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication "
                    "OR rolbypassrls FROM pg_roles WHERE rolname = %s",
                    (name,),
                ).fetchone()
                if elevated and elevated[0]:
                    raise ValueError("Refusing to reuse an elevated application role.")
                memberships = db.execute(
                    "SELECT 1 FROM pg_auth_members WHERE member = %s", (exists[0],)
                ).fetchone()
                if memberships:
                    raise ValueError("Refusing to reuse a role with unexpected memberships.")
            operation = sql.SQL("ALTER ROLE") if exists else sql.SQL("CREATE ROLE")
            db.execute(
                sql.SQL("{} {} LOGIN NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD {}").format(
                    operation, sql.Identifier(name), sql.Literal(value.password)
                )
            )
            db.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(admin.database or ""), sql.Identifier(name)
                )
            )
        # Managed Postgres role creators may receive ADMIN but not SET membership.
        # The provisioning administrator needs SET to assign schema ownership.
        administrator = db.execute("SELECT current_user").fetchone()
        if administrator is None:
            raise RuntimeError("Missing database administrator identity.")
        db.execute(
            sql.SQL("GRANT wine_migrator TO {} WITH SET TRUE, INHERIT FALSE").format(
                sql.Identifier(administrator[0])
            )
        )
        owner = db.execute(
            "SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname = 'app'"
        ).fetchone()
        if owner and owner[0] != "wine_migrator":
            raise ValueError("Refusing to take ownership of an existing application schema.")
        db.execute("CREATE SCHEMA IF NOT EXISTS app AUTHORIZATION wine_migrator")
        db.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        db.execute("SET LOCAL ROLE wine_migrator")
        db.execute("REVOKE ALL ON SCHEMA app FROM PUBLIC")
        for role in ("anon", "authenticated"):
            if db.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
                db.execute(sql.SQL("REVOKE ALL ON SCHEMA app FROM {}").format(sql.Identifier(role)))
        db.execute("GRANT USAGE ON SCHEMA app TO wine_api")
        db.execute(
            "ALTER DEFAULT PRIVILEGES FOR ROLE wine_migrator IN SCHEMA app "
            "REVOKE ALL ON TABLES FROM PUBLIC"
        )
        db.execute(
            "ALTER DEFAULT PRIVILEGES FOR ROLE wine_migrator IN SCHEMA app "
            "REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC"
        )
    print("Local application roles and schema are ready; credentials were not displayed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Connection/driver errors can contain a DSN. Never echo the exception value.
        sys.exit(f"Local provisioning failed ({type(exc).__name__}); check private configuration.")
