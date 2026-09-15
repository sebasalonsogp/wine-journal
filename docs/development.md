# Development and verification

All commands below assume a checkout of the repository. Node.js 24 LTS is the CI baseline; Python is pinned to 3.12 in both the repository and API metadata. npm manages only `apps/web`; uv manages only `apps/api`.

## Checks

From `apps/web`:

```sh
npm ci
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
npm audit --audit-level=high
```

`typecheck` runs Next route-type generation before TypeScript, including on a fresh checkout. `build` does not replace linting. The reviewed interface uses system fonts, so the build does not need a font-service connection.

From `apps/api`:

```sh
uv sync --locked
uv run --locked ruff check --config pyproject.toml . ../../scripts
uv run --locked ruff format --check --config pyproject.toml . ../../scripts
uv run --locked mypy
uv run --locked python ../../scripts/run_api_tests.py
uv build
uv run --locked pip-audit --skip-editable
```

The full runner creates a disposable Postgres 17 container, generates credentials in memory, binds it explicitly to loopback, verifies migrations/roles and runs the API tests. It removes only its own container afterward. No hosted secrets are required, including on fork pull requests. Run `uv run --locked pytest` for fast checks without Docker; database-dependent cases explicitly skip in that mode, so it does not replace the full runner. Current coverage includes JWT claims/signatures/rotation, account isolation/concurrency, migration downgrade/upgrade, privilege denial, safe error responses and tracked-secret-file checks. CORS is browser policy, not authorization.

With a verified local Supabase stack, `uv run --locked python ../../scripts/smoke_local_auth.py` performs two real email-code sign-ins via the local Mailpit inbox and sends their signed tokens through the account API. It prints no codes or tokens, refuses a hosted issuer, and leaves synthetic local identities for inspection.

For the complete browser journey, first run guarded Supabase setup, then `npm run build` and `npm run test:e2e` from `apps/web`. Playwright starts the production web/API servers when needed. Install Chromium with `npx playwright install chromium`, or use an installed Edge on Windows with `$env:PLAYWRIGHT_CHANNEL='msedge'`. See [browser test boundaries](../apps/web/tests/e2e/README.md). After a build, `uv run --project apps/api --locked python scripts/check_browser_secrets.py` from the root checks browser scripts against generated local private values without displaying them.

## Contracts

From the repository root:

```sh
uv run --project apps/api python scripts/export_openapi.py
npm --prefix apps/web run generate:api
git diff -- contracts/openapi.json apps/web/src/lib/api/schema.d.ts
```

Review and commit changes to both generated files. FastAPI is the source of truth for implemented endpoints; `docs/api-contracts.md` describes future endpoints. No network service needs to be running for generation.

## CI and dependencies

GitHub Actions runs web, API and real browser checks separately on pushes to `main` and pull requests. The browser job starts disposable local Supabase with generated credentials and uploads only a credential-free test summary. A separate workflow checks tracked credential paths and complete Git history with redacted Gitleaks output. Actions and the scanner download are pinned to verified revisions/checksums. Secret scanning and push protection are enabled on GitHub. No deployment, paid service, or branch-protection ruleset has been configured.

Use the committed `package-lock.json` and `uv.lock`. Update dependencies deliberately and run checks before committing the new locks. The generator-compatible ESLint 9 release currently produces an upstream end-of-support warning; Next's bundled import/React/accessibility plugins still declare ESLint 9 compatibility. Upgrade the lint stack together once those plugins support ESLint 10. The current FastAPI/Starlette test stack also emits upstream deprecation warnings; they are not suppressed.

## Working boundaries

- Keep routes thin and work in feature slices. Do not build all proposed database tables before the first usable flow.
- Backend modules own their writes; Journal coordinates entry/occasion/rating transactions. Provider calls and media work stay outside those transactions.
- `core` and web `lib` must not import business features. Shared components contain presentation, not private-record access.
- Only accounts have been implemented from the broader schema design. Their API lookup is scoped to verified issuer/subject. Every later private-data slice must add its own ownership constraints and isolation tests; SQLAlchemy is not automatic RLS.
- Secrets, local environments, uploads, and backups are ignored by Git. Configuration examples contain names and safe defaults only.
- Keep active planning and design changes inside this repository. The parent workspace holds the earlier archive.

Docker is needed for the full API suite and local Supabase. Local email Auth/Postgres and browser access are exercised; the Storage/media workflow remains unimplemented. See [Supabase setup](../supabase/README.md) for the resolved Docker Desktop port-binding issue and the retained startup guard. A guard refusal is never a successful startup.
