# ADR 0002: Supabase services with API-owned journal access

Status: Direction accepted through [ADR 0005](0005-repository-foundation.md); integration remains unimplemented. Date: September 14, 2026.

## Context

The data is relational and includes private journal content and media. Supabase is a learning preference. A future native client needs the same business rules as the browser.

## Decision

Use Supabase Postgres, Auth and private Storage. All application data operations go through FastAPI and SQLAlchemy; use an unexposed application schema and disable unused Data API access. Keep application authorization explicit and database runtime privileges narrow. Supabase Auth verifies identity; it does not automatically scope direct SQL queries. Alembic is the sole migration authority for application tables and grants.

Map a provider subject to an application user ID. Keep storage objects outside Postgres and signing/admin credentials in a backend adapter. Browser clients use scoped signed capabilities after API authorization. No public journal bucket and no raw provider responses in public catalog output.

## Alternatives and consequences

- **Browser directly using Supabase tables with RLS:** a valid simpler stack when Supabase owns most application behavior. Combining it with a separate Python write path would split authorization and transaction rules; this plan chooses one journal access path.
- **Separate database/auth/storage vendors:** possible, but more configuration and vendor integration for a solo MVP. Plain Postgres migrations help a future move; identity and media migration remain work.
- **Self-host everything:** more operational responsibility than the present learning goal requires. Local Supabase provides useful development parity without committing to self-hosted production.

API authorization and two-account isolation tests are mandatory. Application-table RLS would be additional work, not an automatic security property. Free-tier pauses, media quotas, and missing automatic backups require an explicit hosting/backup decision before real use. [Supabase access models](https://supabase.com/docs/guides/database/secure-data), [pricing](https://supabase.com/pricing)

Revisit for budget/availability constraints or a concrete provider limitation. Full access and backup design: [architecture](../architecture.md).
