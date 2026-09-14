# Development and verification

All commands below assume a checkout of the repository. Node.js 24 LTS is the CI baseline; Python is pinned to 3.12 in both the repository and API metadata. npm manages only `apps/web`; uv manages only `apps/api`.

## Checks

From `apps/web`:

```sh
npm ci
npm run format:check
npm run lint
npm run typecheck
npm run build
npm audit --audit-level=high
```

`typecheck` runs Next route-type generation before TypeScript, including on a fresh checkout. `build` does not replace linting. The startup screen uses system fonts, so the build does not need a font-service connection.

From `apps/api`:

```sh
uv sync --locked
uv run --locked ruff check . ../../scripts/export_openapi.py
uv run --locked ruff format --check . ../../scripts/export_openapi.py
uv run --locked mypy
uv run --locked pytest
uv build
uv run --locked pip-audit --skip-editable
```

The two HTTP checks cover liveness without external services and browser-origin handling. They do not establish authentication, database isolation, or production readiness. Unit tests, Postgres integration tests, and Playwright user journeys will be added with real domain behavior. CORS is browser policy, not authorization.

## Contracts

From the repository root:

```sh
uv run --project apps/api python scripts/export_openapi.py
npm --prefix apps/web run generate:api
git diff -- contracts/openapi.json apps/web/src/lib/api/schema.d.ts
```

Review and commit changes to both generated files. FastAPI is the source of truth for implemented endpoints; `docs/api-contracts.md` describes future endpoints. No network service needs to be running for generation.

## CI and dependencies

GitHub Actions runs web and API checks separately on pushes to `main` and pull requests. Actions are pinned to verified commit revisions. No deployment, paid service, or branch-protection setting is configured by this scaffold.

Use the committed `package-lock.json` and `uv.lock`. Update dependencies deliberately and run checks before committing the new locks. The generator-compatible ESLint 9 release currently produces an upstream end-of-support warning; Next's bundled import/React/accessibility plugins still declare ESLint 9 compatibility. Upgrade the lint stack together once those plugins support ESLint 10. The current FastAPI/Starlette test stack also emits upstream deprecation warnings; they are not suppressed.

## Working boundaries

- Keep routes thin and work in feature slices. Do not build all proposed database tables before the first usable flow.
- Backend modules own their writes; Journal coordinates entry/occasion/rating transactions. Provider calls and media work stay outside those transactions.
- `core` and web `lib` must not import business features. Shared components contain presentation, not private-record access.
- The schema model is a design until implemented with migrations and isolation tests. Direct SQLAlchemy access will require explicit ownership enforcement.
- Secrets, local environments, uploads, and backups are ignored by Git. Configuration examples contain names and safe defaults only.
- Keep active planning and design changes inside this repository. The parent workspace holds the earlier archive.

Docker is needed only when starting the local Supabase stack. It was not running during initial scaffolding, so local Auth/Postgres/Storage integration is still unverified. See [Supabase setup](../supabase/README.md).
