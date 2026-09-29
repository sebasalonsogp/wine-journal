from alembic import context

from wine_journal.accounts.models import AppUser
from wine_journal.catalog import models as catalog_models  # noqa: F401
from wine_journal.core.config import MigrationSettings
from wine_journal.core.database import database_engine
from wine_journal.journal import models as journal_models  # noqa: F401

target_metadata = AppUser.metadata


def include_name(name: str | None, type_: str, parent_names: dict[str, str]) -> bool:
    if type_ == "schema":
        return name == "app"
    return True


if context.is_offline_mode():
    context.configure(
        dialect_name="postgresql",
        target_metadata=target_metadata,
        literal_binds=True,
        version_table_schema="app",
        include_schemas=True,
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    settings = MigrationSettings()
    engine = database_engine(settings.migration_database_url, role="wine_migrator")
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                version_table_schema="app",
                include_schemas=True,
                include_name=include_name,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
