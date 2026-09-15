# API contract

`schema.d.ts` is generated from the implemented FastAPI OpenAPI snapshot. Run `npm run generate:api`; never edit generated types manually. `transport.ts` connects the account flow through `openapi-fetch`, uses bearer tokens without cookies, and permits one refresh/retry after a 401. The web session endpoint retains refresh credentials in HTTP-only cookies. Planned endpoints remain in `docs/api-contracts.md` until implemented.
