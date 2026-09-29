# First manual journal browser journey

September 29, 2026. J04 and J05 complete the first persisted manual journal experience.

## Implementation slices

- Shared typed transport and lifecycle: reuse bounded refresh for journal endpoints, reject late responses after session clearing, and clear tab-scoped drafts on sign-out.
- Capture: `/capture` accepts a wine name and consumed date, with optional vintage status/year, producer and edition. Guests can type before signing in. Existing wine detail can start another entry for the same release.
- Private read screens: My Wines shows cards ordered by latest consumed date, with one personal record per release; detail lists dated encounters. Lists and history load additional pages from server cursors.
- Connected verification: real local Supabase codes and Postgres, dropped responses after commit, reload/retry, separate intentional repeat entries, validation recovery, expired-cookie draft hiding, account switching and cross-tab cleanup.

## Design contract

Operate mode: quickly remember a wine, then revisit its history. Inherit the approved Stitch/prototype composition, burgundy/olive/cream tokens, serif headings, bottle placeholders and Browse-first navigation. Manual fields have explicit labels and optional identity details are disclosed on demand. Wine cards show actual persisted names, release distinctions, last consumed dates and counts. Hide unimplemented rating/media controls; the interface states that enrichment arrives later. Small screens stack cards and form fields; controls remain keyboard accessible.

## Draft and retry boundary

One draft per browser tab uses `sessionStorage`, never durable offline sync or a credential store. Guest intent is adopted by the account that signs in. Owned drafts require the same verified account; another account clears them. Sign-out clears drafts across open tabs. A blocked storage write keeps input in memory and prevents a sign-in redirect that would lose it.

Once a save is sent, its UUID key and body remain fixed. A lost response locks editing and offers Retry save; a committed response is replayed by the API. Explicit discard warns that an uncertain entry may already exist. A server validation error unlocks correction. No background retries or implicit occasions/ratings are created. A successful save clears the draft and starts a fresh document at the wine record, dropping prior query caches.

## Verification

- Nine web unit tests pass, including restricted return paths, draft parsing/payload selection, shared refresh and rejecting an old session's late response.
- Seven real browser scenarios pass across the access and journal suites. The three journal scenarios verify guest-to-saved capture, repeat-save replay, owner isolation, and real 21-wine/21-entry pagination. A fixture race was corrected by waiting for account bootstrap before direct API seeding.
- Axe checks pass for capture, populated list and detail. Desktop and phone screenshots were inspected in a bounded pass; no horizontal overflow was found. Screenshots contain only synthetic wine records, never codes or account details.
- TypeScript, lint, formatting and production build pass. The browser secret scan checks built assets against generated private local values. Public-repository secret checks run before each commit/push.

Docker was started by the user. Guarded startup verified loopback services and applied the additive migrations successfully, preserving the existing environment files. The previous workstation startup blocker is resolved. Notes/time/place editing remains J06; ratings, media, occasions and identification remain later work.
