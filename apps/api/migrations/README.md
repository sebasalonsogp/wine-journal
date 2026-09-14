# Application migrations

Alembic will be the sole authority for application tables, constraints, indexes, and grants. Initialize its environment and add the first migration with the accounts/database slice; this folder does not contain an executable migration setup yet.

Use an application schema that is not exposed by the Supabase Data API. Keep provider-owned auth/storage schemas under Supabase management. Run migrations explicitly, never automatically on each API process startup.
