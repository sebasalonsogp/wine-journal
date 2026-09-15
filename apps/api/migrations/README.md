# Application migrations

Alembic is the sole authority for application tables, constraints, indexes, and grants. Revision `0001_accounts` creates only the required application identities and runtime grants. Broader journal/media schemas remain future slices.

Use an application schema that is not exposed by the Supabase Data API. Keep provider-owned auth/storage schemas under Supabase management. Run migrations explicitly, never automatically on each API process startup.

From `apps/api`, run `uv run --locked alembic upgrade head` and `uv run --locked alembic check`. Migration credentials come from `WINE_JOURNAL_MIGRATION_DATABASE_URL` or the ignored `.env.migrations` file, loaded only by the migration process. The API uses its separate `.env`/runtime role. No connection URL belongs in `alembic.ini`.

Provision the local schema/roles through the [local setup](../../../supabase/README.md) before migrating. Autogeneration inspects only `app`; it must never propose migrations for Supabase-owned schemas. The full API test runner verifies a fresh upgrade, downgrade and re-upgrade in a disposable database. A downgrade that drops account data is a local test tool, not a production rollback/backup strategy.
