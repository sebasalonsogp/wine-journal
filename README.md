# Wine Journal

A private journal for the wines you discover and the memories around them. Record a wine and date quickly, then return to add notes, a personal rating, photos, or video. My Wines is the primary view; optional occasions group several wines into a scrapbook. Guest lookup is separate from recording consumption.

**Stage:** connected web access. Email-code sign-in, a private account-backed shell, session recovery and sign-out work with local Supabase and FastAPI. The reviewed navigation and colors are implemented. Wine logging, recognition, media and live social-provider registrations remain upcoming; empty screens are labeled accordingly. The [connected design walkthrough](design/prototype-v3/walkthrough.html) remains a separate simulation.

## Repository map

```text
apps/
  web/                  Next.js App Router, React, TypeScript, Tailwind
    src/app/            Thin routes and layouts
    src/features/       Auth, browse, capture, My Wines, occasions, guides, profile
    src/components/     Shared presentation and UI primitives
    src/lib/            Typed API and shared session transport
    src/content/        Sourced editorial guides
    src/styles/         Reviewed design tokens
    tests/e2e/          Real auth journeys, accessibility and viewport checks
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

Prerequisites: Node.js 24 LTS with npm, Python 3.12, and uv. Docker is needed for local Supabase and database integration tests. Guest placeholders and API liveness need no credentials; sign-in needs the local services and generated configuration.

From the repository root:

```sh
npm --prefix apps/web ci
uv sync --project apps/api --locked
uv run --project apps/api --locked python scripts/start_local.py
```

Start the web app:

```sh
npm --prefix apps/web run dev -- --hostname 127.0.0.1
```

Open `http://localhost:3000`. In a second terminal, start the API:

```sh
uv run --directory apps/api --locked uvicorn wine_journal.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: `http://127.0.0.1:8000/docs`. Liveness: `http://127.0.0.1:8000/api/v1/health/live`. Sign in at `http://localhost:3000/auth/sign-in` and read the development email code in Mailpit at `http://127.0.0.1:54324`. Local email never reaches an external mailbox. Follow [Supabase setup](supabase/README.md), including Docker Desktop's localhost-default setting when required.

This repository is public. Read [security and environment configuration](docs/security.md) before adding credentials. Real local values are generated into ignored files; GitHub secret scanning, push protection, and CI secret/file checks provide additional safeguards.

## Verify and continue

Follow [development and verification](docs/development.md) for exact check commands and [the access checkpoint](tasks/access-checkpoint.md) for evidence and remaining setup work.

- [Phased implementation plan](tasks/plan.md), [59-task backlog](tasks/todo.md), and [story coverage](tasks/story-coverage.md)
- [Product story map](tasks/story-map.md)
- [Architecture and boundaries](docs/architecture.md), [alternatives review](docs/architecture-options.md)
- [Logical data model](docs/data-model.md) and [planned API](docs/api-contracts.md)
- [Design references](design/README.md) and [latest UX decisions](tasks/ux-review-04.md)

See the [web access checkpoint](tasks/web-access-checkpoint.md) for current verification. Next is the first private journal slice, J01–J04: save wine/date and reopen it after reload. R01/R04 provider/media evidence remains independent work. Google, Apple and Facebook require external registration and live verification before enabling their buttons.
