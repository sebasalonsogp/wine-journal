# Local Supabase

`config.toml` is local development configuration generated with Supabase CLI 2.117.0 and adjusted for this project. No hosted project, account, bucket, application table, or migration has been created.

Install and start a compatible Docker engine before running, from the repository root:

```sh
npx --yes supabase@2.117.0 start
npx --yes supabase@2.117.0 status
```

The first start downloads service images. This was not run during scaffolding because the Docker engine was unavailable. Stop local services with `npx --yes supabase@2.117.0 stop`; keep the volumes if you want to preserve local development data.

The local API is on port 54321, Postgres on 54322, Studio on 54323, and the email testing inbox on 54324. This configuration is not a hosted production security configuration. No email provider or final sign-in method is selected.

Supabase SQL migrations and seed loading are disabled: Alembic will own application migrations in `apps/api/migrations`. No application schema is exposed by the local Data API, and automatic grants for new public tables are disabled. Auth/Storage use their provider-managed schemas. Review and disable unused Data API access when configuring the actual hosted project.

The storage size setting is a CLI development default, not a product media limit. Private buckets, grants, signed uploads, iPhone decoding/transcoding, quotas, and job processing belong to the media slice. Realtime, Edge Functions, analytics, and vector storage are disabled until needed.
