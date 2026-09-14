# Wine Journal API

FastAPI application assembled in `src/wine_journal/main.py`. Domain packages are reserved for their first working slices. Only `GET /api/v1/health/live` is implemented; it reports process liveness, not database or provider readiness.

Requires Python 3.12 and uv. From this directory:

```sh
uv sync --locked
uv run --locked uvicorn wine_journal.main:app --reload --host 127.0.0.1 --port 8000
```

No environment file, Supabase account, or database is needed for this scaffold. Optional settings are documented in `.env.example`; copy it to `.env` to customize the allowed browser origins. Interactive API documentation is at `http://127.0.0.1:8000/docs`.

```sh
uv run --locked ruff check . ../../scripts/export_openapi.py
uv run --locked ruff format --check . ../../scripts/export_openapi.py
uv run --locked mypy
uv run --locked pytest
uv build
```

`core` contains infrastructure and must not import business modules. Feature routes validate transport; service/use-case functions own authorization and transaction boundaries. Add `routes.py`, `schemas.py`, `models.py`, and `service.py` only as a feature needs them. Cross-module writes go through the owning module's operations.

SQLAlchemy, psycopg, and executable Alembic migrations will arrive with the first database slice. Provider SDKs, token verification, media workers, and FFmpeg arrive with their integrations. No private endpoint or worker is represented as implemented by an empty stub.
