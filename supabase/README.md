# Local Supabase

`config.toml` is local development configuration based on Supabase CLI 2.117.0. Local Auth and Postgres have been exercised; no hosted project or media bucket has been provisioned. Application accounts are created by Alembic, not Supabase migrations.

Install/start Docker, then from the repository root:

```sh
uv sync --project apps/api --locked
uv run --project apps/api --locked python scripts/start_local.py
```

The wrapper generates an ignored ES256 signing-key file, requests a Docker network bound to loopback, starts services with credential output suppressed, and inspects actual published ports. Only after that check does it generate local environment files, provision limited roles and apply the accounts migration. Existing credential files are preserved. Generated Windows files use existing workspace ACLs; keep this workspace restricted to your user. Never share its ignored files.

Stop services with `npx --yes supabase@2.117.0 stop`; volumes are retained. Avoid sharing `supabase status` output: it includes local database/API credentials. The setup script reads it privately instead.

The local API is on port 54321, Postgres on 54322, Studio on 54323, and the Mailpit email testing inbox on 54324. The six-digit email-code template expires after ten minutes. A hosted email provider is not configured. Google/Apple/Facebook registration and web sign-in are subsequent work; see [authentication setup](../docs/authentication.md).

## Observed Docker Desktop limitation

On the current Windows host (Docker Engine 29.7.2), Supabase published its ports as `0.0.0.0`/`::` even with `com.docker.network.bridge.host_binding_ipv4=127.0.0.1` on the requested network. This is observed behavior, not a claim about every Docker installation. The wrapper detects it, stops this project's services, retains volumes and exits unsuccessfully. Do not bypass the check or leave the development database/inbox exposed.

The local Auth/Postgres smoke tests succeeded before this guard was added. The guarded full stack is now stopped; persistent local development needs the Docker/CLI binding issue resolved and actual loopback bindings verified first. Independent API tests remain available: `uv run --project apps/api --locked python scripts/run_api_tests.py` creates a separate database with an explicit loopback port mapping, which was verified to work here. No Windows firewall or global Docker settings were modified.

The guard also stops the stack if port inspection or setup fails. If shutdown itself fails, it reports that explicitly; stop the Wine Journal containers before continuing. No failed check should be reclassified as a successful startup.

Supabase SQL migrations and seed loading remain disabled: Alembic owns `apps/api/migrations`. The `app` schema is unexposed; `anon`/`authenticated` have no app privileges, and automatic grants for new public tables are disabled. `wine_migrator` owns app DDL and `wine_api` has only required usage/table grants. Provider-managed Auth/Storage schemas stay outside autogeneration. Review Data API configuration separately for a hosted project.

The storage size setting is a CLI development default, not a product media limit. Private buckets, grants, signed uploads, iPhone decoding/transcoding, quotas, and job processing belong to the media slice. Realtime, Edge Functions, analytics, and vector storage are disabled until needed.

References: [Supabase local network guidance](https://supabase.com/docs/guides/local-development), [email OTP](https://supabase.com/docs/guides/auth/auth-email-passwordless), [JWT verification](https://supabase.com/docs/guides/auth/jwts).
