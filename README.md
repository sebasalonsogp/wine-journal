# Wine Journal

A private journal for the wines you discover and the memories around them. Record a wine and date quickly, then return to add notes, a personal rating, photos, or video. My Wines is the primary view; optional occasions group several wines into a scrapbook. Guest lookup is separate from recording consumption.

**Stage:** connected private journal. Email-code sign-in, manual capture, searchable/filterable My Wines, paginated history, repeated drinking, entry editing/deletion, wine-level ratings and private occasions work with local Supabase and FastAPI. My Wines can sort by recently tried, name or current rating; applied filters survive reload and navigation. Each release has one current score and dated rating history; clearing a score preserves history, while erasure requires confirmation. Wine records and ratings survive their last drinking entry being deleted. Drafts survive interruptions; save retries prevent duplicates and stale changes require review. Wine capture can select an existing occasion or create one inline. New and saved occasions can also stage up to 20 drinking entries and save them together, with independent dates/notes and one bottle card per wine. Recognition, media and live social-provider registrations remain upcoming. The [connected design walkthrough](design/prototype-v3/walkthrough.html) remains a separate simulation; the application uses real persisted records.

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

This is one repository with two runtime projects. Use npm inside `apps/web` and uv inside `apps/api`; there is no root package manager workspace. The backend is a modular monolith with a cohesive Journal core. Its durable media worker runs as a separate process from the same Python project, using Postgres jobs. See [architecture](docs/architecture.md) and [ADR 0005](docs/decisions/0005-repository-foundation.md).

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

The background job runner is available with `uv run --directory apps/api --locked python -m wine_journal.worker --once`. Private image uploads, processing and entry galleries are implemented. Enable/configure local media and build the isolated decoder as described in [worker operation and handler requirements](apps/api/src/wine_journal/media/README.md). Choose a personal bottle cover during manual capture or through Manage bottle cover on a saved wine. Covers stay separate from memories; failed replacements retain the existing cover.

This repository is public. Read [security and environment configuration](docs/security.md) before adding credentials. Real local values are generated into ignored files; GitHub secret scanning, push protection, and CI secret/file checks provide additional safeguards.

## Verify and continue

Follow [development and verification](docs/development.md) for exact check commands and [the access checkpoint](tasks/access-checkpoint.md) for evidence and remaining setup work.

- [Phased implementation plan](tasks/plan.md), [59-task backlog](tasks/todo.md), and [story coverage](tasks/story-coverage.md)
- [Product story map](tasks/story-map.md)
- [Architecture and boundaries](docs/architecture.md), [alternatives review](docs/architecture-options.md)
- [Logical data model](docs/data-model.md) and [planned API](docs/api-contracts.md)
- [Design references](design/README.md) and [latest UX decisions](tasks/ux-review-04.md)

Saved drinking entries offer **Organize occasion** in My Wines to link, move or unlink them. Occasion detail offers confirmed **Delete occasion**, preserving every drinking entry, its own context and wine ratings. You can now select photos during capture or open **Photos & memories** on a saved entry to upload, caption and remove them. Text saves independently; interrupted photos retry without another drinking entry. See the [entry-photo checkpoint](tasks/entry-photos-checkpoint.md). Selected files stay in memory until uploaded; preview storage remains limited until M08 cleanup. Media is enabled locally; the example configuration stays disabled until Storage and the decoder are configured. Google, Apple, Facebook and X require external registration and live verification before enabling their buttons.
