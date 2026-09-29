# Browser journeys

Run `npm run test:e2e` after guarded local Supabase setup and `npm run build`. Playwright starts the production web/API servers if they are not already running. Default browser: Chromium (`npx playwright install chromium`); on Windows an installed Edge can be selected with `$env:PLAYWRIGHT_CHANNEL='msedge'`. Always use `http://localhost:3000`, matching the configured Origin.

Stop a running production web server before rebuilding, then restart it; an older server process must not serve newly replaced build assets. The local test setup checks configured Auth/API/database origins and rejects hosted environments before the tests run.

The tests use randomized `@example.test` identities and retrieve their own six-digit codes from local Mailpit. They exercise the real Auth service and FastAPI: guest rejection, email sign-in, account bootstrap/reload, one forced API 401 followed by a real refresh, revoked-refresh rejection, two-account switching, cross-tab sign-out, browser-back protection, invalid code recovery, keyboard access, axe and 320/768/1024/1440 px layouts. Synthetic accounts stay in local development volumes; CI uses disposable services. Never point these tests at a hosted environment.

The journal scenarios exercise guest drafts through sign-in, committed saves with deliberately dropped responses, replay after reload, repeated same-date encounters, validation recovery, hidden owned drafts after cookie loss, account-switch cleanup and cross-tab sign-out. A separate real-data scenario loads 21 wines and 21 entries through the paginated UI. Direct fixture seeding waits for the account-backed journal before making private API calls.

Entry editing verifies draft recovery after reload, two simultaneous browser editors, explicit conflict review/replacement, the unchanged entry ID, date-line/local-time display, clearing optional details, and recovering an update whose success response was dropped. Desktop and phone screenshots use synthetic notes only; axe checks cover the populated conflict form.

Deletion verifies dialog cancellation and keyboard focus, stale confirmation after an edit in another tab, deletion of one of two entries, a committed deletion with a dropped response and safe retry, and the preserved wine card after the final entry is removed. Confirmation screenshots and axe checks use synthetic data only.

No traces, HAR, storage state, or videos are recorded. The pinned runner's automatic DOM snapshot feature is disabled. Explicit screenshots cover blank sign-in, synthetic wine lists/detail and capture forms, never code fields or account details. CI uploads only `auth-check-summary.json`, containing fixed test titles, statuses, durations and error counts. Do not broaden the artifact glob to `test-results/**`; local failure files may still include diagnostic data. Codes/tokens/cookies remain only in process memory and are never printed by fixtures.
