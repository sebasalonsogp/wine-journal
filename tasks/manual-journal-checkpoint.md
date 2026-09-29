# Manual journal implementation checkpoint

September 29, 2026. Work is proceeding through the existing J01–J04 acceptance criteria.

- J01: catalog models/schemas/service, migration 0002, and Postgres identity tests. Prove vintage distinctions, invalid combinations and owner isolation.
- J02: journal models/schemas/service/routes, migration 0003, and save tests. Prove atomic saves, retry identity, concurrency, rollback and intentional repeated glasses.
- J03: bounded journal queries and response schemas with read tests. Prove consumed-date sorting, pagination and cross-owner 404s.
- J04 is split into capture/list/detail UI and connected browser verification. Typed drafts must survive failures; no fake data or implicit occasions/ratings.

Each backend slice updates the generated contract when an endpoint is exposed. The UI consumes that contract. Public catalog, recognition, media, rating changes and occasions remain later tasks.
