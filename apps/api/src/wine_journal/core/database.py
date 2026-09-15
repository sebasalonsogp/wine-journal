from pydantic import SecretStr
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def database_engine(url: SecretStr, *, role: str = "wine_api") -> Engine:
    try:
        parsed = make_url(url.get_secret_value())
    except Exception:
        raise ValueError("Invalid database connection configuration.") from None
    if parsed.drivername != "postgresql+psycopg" or not parsed.password:
        raise ValueError("Use a password-authenticated postgresql+psycopg connection.")
    # Session-pooler usernames may append a project reference after the role.
    if (parsed.username or "").split(".")[0] != role:
        raise ValueError(f"This process requires the {role} database role.")
    local = parsed.host in {"localhost", "127.0.0.1", "::1"}
    if not local and parsed.query.get("sslmode") != "verify-full":
        raise ValueError("Remote database connections require sslmode=verify-full.")
    return create_engine(
        parsed,
        pool_size=5,
        max_overflow=0,
        pool_timeout=5,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )
