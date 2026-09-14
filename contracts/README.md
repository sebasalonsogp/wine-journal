# Implemented HTTP contract

`openapi.json` is generated from FastAPI and contains only implemented endpoints. The design for future endpoints remains in `../docs/api-contracts.md`.

From the repository root:

```sh
uv run --project apps/api python scripts/export_openapi.py
npm --prefix apps/web run generate:api
```

Commit both the OpenAPI snapshot and generated TypeScript types. CI regenerates them and checks for drift. Generating the contract requires no database or provider credentials.
