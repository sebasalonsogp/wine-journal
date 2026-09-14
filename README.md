# Wine Journal

A private journal for the wines you discover and the memories around them. Record a wine and date quickly, then return to add notes, a personal rating, photos, or video. My Wines is the primary view; optional occasions group several wines into a scrapbook. Guest lookup is separate from recording consumption.

**Stage:** repository foundation. The Next.js startup page and FastAPI liveness endpoint run locally. Product screens, authentication, persistence, recognition, and media processing are not implemented yet. The [connected design walkthrough](design/prototype-v3/walkthrough.html) is the interactive UX reference and uses simulated data.

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
    migrations/         Reserved for Alembic; no migrations exist yet
    tests/              Unit and HTTP/integration checks
contracts/              Generated OpenAPI snapshot
supabase/               Local service configuration; no hosted project
scripts/                Contract export
docs/                   Architecture, data/API designs, setup, decisions
tasks/                  Product stories, UX decisions, implementation backlog
design/                 Preserved Stitch exports and connected walkthrough
.github/workflows/      CI checks; no deployment workflow
```

This is one repository with two runtime projects. Use npm inside `apps/web` and uv inside `apps/api`; there is no root package manager workspace. The backend is a modular monolith with a cohesive Journal core. Background workers and supporting services can be introduced independently when their workload requires them. See [architecture](docs/architecture.md) and [ADR 0005](docs/decisions/0005-repository-foundation.md).

## Run locally

Prerequisites: Node.js 24 LTS with npm, Python 3.12, and uv. The lockfiles capture package versions. The scaffold needs no cloud accounts or environment variables.

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

API docs: `http://127.0.0.1:8000/docs`. Liveness: `http://127.0.0.1:8000/api/v1/health/live`. The startup page does not call the API yet. Optional per-app environment templates are provided; actual secrets stay untracked.

## Verify and continue

Follow [development and verification](docs/development.md) for exact check commands and [local Supabase setup](supabase/README.md) when the database/auth slice starts.

- [Product plan](tasks/plan.md), [story map](tasks/story-map.md), and [delivery tasks](tasks/todo.md)
- [Architecture and boundaries](docs/architecture.md), [alternatives review](docs/architecture-options.md)
- [Logical data model](docs/data-model.md) and [planned API](docs/api-contracts.md)
- [Design references](design/README.md) and [latest UX decisions](tasks/ux-review-04.md)

The next product slice is sign-in and an empty private My Wines view. Auth method and the first account/schema migration need to be resolved there. Public reviews, collaboration, recommendations, calendar, and native iOS remain expansion directions.
