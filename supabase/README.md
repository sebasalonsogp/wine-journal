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

## Docker Desktop port binding

On the current Windows host (Docker Engine 29.7.2), Supabase published its ports as `0.0.0.0`/`::` even with `com.docker.network.bridge.host_binding_ipv4=127.0.0.1` on the requested network. This is observed behavior, not a claim about every Docker installation. The wrapper detects it, stops this project's services, retains volumes and exits unsuccessfully. Do not bypass the check or leave the development database/inbox exposed.

A separate temporary `docker run --network wine-journal-local --publish 5432` probe reproduced the same result without Supabase; the probe was removed afterward. This points to the current Docker runtime's treatment of the network default, rather than an application authentication defect. Explicit `127.0.0.1` port publication works for the isolated database tests. Do not claim that the network option alone is effective without inspecting actual bindings.

Resolved on this host by setting Docker Desktop's **Settings → Resources → Network → Port binding behavior → Localhost by default**, then restarting the idle engine. The installed setting is `PortBindingBehavior: "default-local-port-binding"` (previously absent, meaning the default). This is a machine-wide default for unspecified bindings; explicit network bindings remain possible. Revert through the same setting to **Open (Default)** if needed, but the Wine Journal guard will refuse unsafe startup again.

A disposable container then reported both `127.0.0.1` and `::1`. The guarded Supabase startup passed, all four published service ports were verified on loopback, existing roles/migration reapplied successfully, and the two-account real email-code smoke passed again. F02 is complete. No firewall rules, container data, or application credentials were changed by this fix.

Independent API tests remain available: `uv run --project apps/api --locked python scripts/run_api_tests.py` creates a separate database with an explicit loopback port mapping. See [Docker Desktop networking](https://docs.docker.com/desktop/features/networking/) for its separate host port setting; do not assume that a bridge option overrides the Desktop default.

The guard also stops the stack if port inspection or setup fails. If shutdown itself fails, it reports that explicitly; stop the Wine Journal containers before continuing. No failed check should be reclassified as a successful startup.

Supabase SQL migrations and seed loading remain disabled: Alembic owns `apps/api/migrations`. The `app` schema is unexposed; `anon`/`authenticated` have no app privileges, and automatic grants for new public tables are disabled. `wine_migrator` owns app DDL and `wine_api` has only required usage/table grants. Provider-managed Auth/Storage schemas stay outside autogeneration. Review Data API configuration separately for a hosted project.

The storage size setting is a CLI development default, not a product media limit. Private buckets, grants, signed uploads, iPhone decoding/transcoding, quotas, and job processing belong to the media slice. Realtime, Edge Functions, analytics, and vector storage are disabled until needed.

References: [Supabase local network guidance](https://supabase.com/docs/guides/local-development), [email OTP](https://supabase.com/docs/guides/auth/auth-email-passwordless), [JWT verification](https://supabase.com/docs/guides/auth/jwts).
