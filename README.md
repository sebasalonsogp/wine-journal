# Wine Journal

A private journal for the wines you discover and the memories around them. Record a wine and date quickly, then return to add notes, a personal rating, photos, or video. My Wines is the primary view; optional occasions group several wines into a scrapbook. Guest lookup is separate from recording consumption.

**Stage:** first access/backend checkpoint. FastAPI verifies Supabase access tokens and supports private account creation/reads backed by Postgres migrations. Local email-code sign-in has been exercised with real Supabase tokens. The web sign-in screens, connected journal, social-provider registrations, recognition and media remain upcoming. The [connected design walkthrough](design/prototype-v3/walkthrough.html) uses simulated data.

## Repository map

```text
apps/
  web/                  Next.js App Router, React, TypeScript, Tailwind
    src/app/            Thin routes and layouts
    src/features/       Auth, browse, capture, My Wines, occasions, guides, profile
    src/components/     Shared presentation and UI primitives
    src/lib/            API types and future transport/session infrastructure
    src/content/        Sourced editorial guides
    src/styles/         Reviewed design tokens
    tests/e2e/          Browser journeys added with working features
  api/                  Python/FastAPI application
    src/wine_journal/   Core, accounts, catalog, identification, journal, media, integrations
    migrations/         Alembic environment and initial accounts migration
    tests/              Unit and HTTP/integration checks
contracts/              Generated OpenAPI snapshot
supabase/               Local service configuration; no hosted project
scripts/                Local setup, isolated tests, credential checks and contract export
docs/                   Architecture, data/API designs, setup, decisions
tasks/                  Product stories, UX decisions, implementation backlog
design/                 Preserved Stitch exports and connected walkthrough
.github/workflows/      CI checks; no deployment workflow
```

This is one repository with two runtime projects. Use npm inside `apps/web` and uv inside `apps/api`; there is no root package manager workspace. The backend is a modular monolith with a cohesive Journal core. Background workers and supporting services can be introduced independently when their workload requires them. See [architecture](docs/architecture.md) and [ADR 0005](docs/decisions/0005-repository-foundation.md).

## Run locally

Prerequisites: Node.js 24 LTS with npm, Python 3.12, and uv. Docker is needed for local Supabase and database integration tests. The startup screen and liveness check still need no cloud account or credentials.

From the repository root:

```sh
npm --prefix apps/web ci
uv sync --project apps/api --locked
```

Start the web app:

```sh
npm --prefix apps/web run dev
```

Open `http://localhost:3000`. In a second terminal, start the API:

```sh
uv run --directory apps/api --locked uvicorn wine_journal.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: `http://127.0.0.1:8000/docs`. Liveness: `http://127.0.0.1:8000/api/v1/health/live`. The startup page does not call the API yet. For real local authentication/database setup, follow [Supabase setup](supabase/README.md), including the Docker port-binding check.

This repository is public. Read [security and environment configuration](docs/security.md) before adding credentials. Real local values are generated into ignored files; GitHub secret scanning, push protection, and CI secret/file checks provide additional safeguards.

## Verify and continue

Follow [development and verification](docs/development.md) for exact check commands and [the access checkpoint](tasks/access-checkpoint.md) for evidence and remaining setup work.

- [Phased implementation plan](tasks/plan.md), [59-task backlog](tasks/todo.md), and [story coverage](tasks/story-coverage.md)
- [Product story map](tasks/story-map.md)
- [Architecture and boundaries](docs/architecture.md), [alternatives review](docs/architecture-options.md)
- [Logical data model](docs/data-model.md) and [planned API](docs/api-contracts.md)
- [Design references](design/README.md) and [latest UX decisions](tasks/ux-review-04.md)

Next is the F05 web sign-in shell, followed by F06 session recovery and F07 browser automation. Resolve the local Docker binding issue before leaving development Auth/Postgres services running. R01/R04 provider/media evidence remains independent work. The first complete journal target is still J04: save wine/date and reopen it after reload.
