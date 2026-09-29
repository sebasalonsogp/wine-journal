# Manual journal implementation checkpoint

September 29, 2026. J01–J03 are implemented. J04 remains the next UI increment.

- J01: catalog models/schemas/service, migration 0002, and Postgres identity tests. Prove vintage distinctions, invalid combinations and owner isolation.
- J02: journal models/schemas/service/routes, migration 0003, and save tests. Prove atomic saves, retry identity, concurrency, rollback and intentional repeated glasses.
- J03: bounded journal queries and response schemas with read tests. Prove consumed-date sorting, pagination and cross-owner 404s.
- J04 is split into capture/list/detail UI and connected browser verification. Typed drafts must survive failures; no fake data or implicit occasions/ratings.

Each backend slice updates the generated contract when an endpoint is exposed. The UI consumes that contract. Public catalog, recognition, media, rating changes and occasions remain later tasks.

## Evidence and operating limits

The [CI run for the final backend code](https://github.com/sebasalonsogp/wine-journal/actions/runs/36625972878) verifies fresh migrations, downgrade/upgrade/schema drift, identity constraints, concurrent saves, lost-response replay, rollback, a bounded lock timeout with Retry-After, deliberate same-date repeats, cross-owner denial, stable pagination, and a single aggregate query for wine cards. It also runs the web/build/contract checks and the existing four browser access scenarios. Secret scanning covers every pushed commit; credentials are generated in disposable CI services.

Locally, 41 available API tests and five web unit tests passed, along with Python/TypeScript checks. Twelve database tests were explicitly skipped in that local run because Docker was unavailable; they are not counted as local passes. The final additional lock-contention test runs in CI with Postgres. Generated OpenAPI and TypeScript types are committed together.

Docker Desktop on this workstation currently fails to start because it cannot access `sailor-ingest.sock`. A process restart and an attempted move of that exact stale socket did not recover it. No factory reset, volume removal, persistent database downgrade, or settings change was performed. Local Supabase/email login and the interactive preview need Docker recovery before they can be demonstrated here again. Linux CI provides the real integration evidence; it does not imply the local runtime is healthy.

The My Wines screen still has its previous empty-state UI. The backend can save and read wines through its API, but manual capture, persisted list/detail screens, draft retention, and the lost-save-response browser journey remain J04. No complete journal UI or production deployment is claimed.
