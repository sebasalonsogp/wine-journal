# M01: Durable media jobs

Delivered September 30, 2026. This slice delivers the Postgres queue and separate Python worker; uploads and media handlers follow R04/M02/M03.

## Delivered

- Migration `0011_media_jobs` adds owner-scoped operation keys, bounded attempts, pending/expired-lease indexes and restricted column grants. Enqueue shares the caller's transaction; repeating the same operation returns its existing job, while conflicting work is rejected.
- Claims use `FOR UPDATE SKIP LOCKED`; handlers run after the claiming transaction releases its connection. Expired work can be reclaimed. Finish and renewal require the current token and an unexpired lease.
- The separate Python runner polls with bounded retry scheduling, an explicit handler registry and metadata-only logs. Only fixed error codes are stored. No new infrastructure service or credential is required.

## Verification

- Six new integration scenarios bring the retained API suite to **98 tests**. Coverage includes transactional rollback/deduplication, runtime grant restrictions, concurrent claims, skipped locks, renewal, stale acknowledgement rejection, bounded attempts, safe logging and migration downgrade/upgrade.
- Two real worker subprocesses use disposable Postgres. The first writes a synthetic idempotent result and is forcibly stopped before acknowledging. The second reclaims the expired lease and completes the job: two attempts, one saved result. This also caught and fixed standalone model registration that API imports had previously supplied implicitly.
- All **18 authentication and journal browser scenarios passed** against local Supabase and the production web build after the dependency update below. CI checks the final retained suite and both runtimes.
- Ruff, formatting, mypy, API package build, dependency audit, tracked-file boundaries and browser-secret scanning passed. API contracts remain unchanged.
- The additive local migration was applied without resetting journal records. One-shot worker startup succeeded; the API preview was restarted after the authentication dependency update.

## Security follow-up

The audit found advisories in PyJWT 2.14.0 and urllib3 2.7.0. A separate targeted dependency change raises PyJWT's minimum and lock to 2.15.0, and updates the development audit tool's transitive urllib3 to 2.8.0. No new package is introduced. The installed environment now reports no known vulnerabilities. See the upstream [PyJWT changelog](https://pyjwt.readthedocs.io/en/stable/changelog.html) and [urllib3 2.8.0 release](https://github.com/urllib3/urllib3/releases/tag/2.8.0).

The first CI run also detected the newly indexed [Next.js ImageResponse advisory](https://github.com/vercel/next.js/security/advisories/GHSA-vcvr-r3jv-pc5j). The application has no `next/og` or `ImageResponse` use, but the affected framework version is still replaced: Next.js and its matching ESLint configuration advance from 16.3.5 to the fixed 16.3.6. The frozen reinstall disables package scripts; `npm audit` reports zero vulnerabilities. Frontend checks and the production browser suite are rerun for this framework patch.

## Limits and next step

The production handler registry is empty; no upload UI, storage authorization or image processing is exposed yet. The demonstrated deduplication is for the synthetic test effect: actual media handlers must separately prove safe repeated storage/database writes. Queue fencing does not guarantee exactly-once external effects. Handlers must use bounded operations and renew between chunks; the runner cannot interrupt a hung Python handler. Resource limits, supervision, retention and cleanup follow their planned media/deployment tasks.

Next: R04 photo conversion/storage feasibility, then M02 staged private uploads and M03 validated image derivatives. See the [worker operating instructions](../apps/api/src/wine_journal/media/README.md).
