# Wine Journal implementation tasks

Status: proposed phased execution plan for review, September 14, 2026. This replans the same project backlog after the completed scaffold. **59 tasks remain; no product implementation is started by this planning change.** The [roadmap](plan.md#phased-roadmap) explains milestones, [verification protocol](plan.md#verification-protocol) applies to each task, and [story coverage](story-coverage.md) accounts for all 65 stories.

One checkbox represents completion of a task's outcome, acceptance criteria and verification. S = a narrow decision/content/configuration change; M = one bounded behavior or technical enabler, normally one or two focused work blocks. These are relative scope estimates, not calendar promises or literal file counts. Primary change areas are code-navigation hints, not instructions to generate every listed file in advance.

Before executing a task, list its concrete files and test cases. If it requires more than about five handwritten source files, crosses an additional independent concern, or exceeds two focused blocks, split it into child tasks under the same ID and retain the parent acceptance criteria. Generated contracts and existing fixtures do not justify separate business services. Do not check off a task with placeholder output or a mocked provider in place of its required real integration.

## Phase 0: Completed repository foundation

<a id="base"></a>
### BASE: Scaffold and recorded decisions

- [x] Next.js/FastAPI foundations, domain/workflow folders, local Supabase configuration, lockfiles, environment examples, API contract generation, smoke tests and CI.
- [x] Architecture, story map, Stitch sources and the connected walkthrough are versioned in the private [repository](https://github.com/sebasalonsogp/wine-journal).
- [x] Local lint/types/builds, two API smoke tests, browser smoke and the [initial Linux CI](https://github.com/sebasalonsogp/wine-journal/actions/runs/34895334930) passed.

Local Docker/Supabase startup, real authentication, database tables, all journal features and hosted application deployment remain unimplemented. Existing tests verify the scaffold, not those capabilities. Preserve [ADR 0005](../docs/decisions/0005-repository-foundation.md).

## Early feasibility lane: Start alongside Phase 1

These are bounded evidence tasks, not one prerequisite wall. R02/R03 gate their identification integrations; R04 gates photos; R05 gates video; R06 gates official places; R07 gates hosted operation. None blocks F01/F02 or the manual journal merely because another provider is unresolved. Limit each experiment to one or two focused blocks before recording its evidence and next decision; do not spend indefinitely searching for a free universal wine catalog.

<a id="r01"></a>
### R01: Prepare representative lookup fixtures

- [ ] **Outcome:** Create a bounded evaluation set before judging provider coverage.

**Acceptance:**

- Include roughly 30 identified bottles: repeated labels across vintages, distinct releases, unknown/non-vintage cases, and imperfect barcode/label images.
- Record expected identity, source and market; keep personal memories and credentials out of fixtures.

**Verify:** Inspect the manifest against actual bottles/sources; retain known answers independently of provider output.

**Dependencies:** [BASE](#base). **Size:** S.

**Primary change areas:** tasks/identification-evaluation.md; assets/evaluation/manifest.csv.

**Stories:** WC-06, WI-03.

<a id="r02"></a>
### R02: Prove the barcode route

- [ ] **Outcome:** Choose a viable decoder and free/local catalog lookup path.

**Acceptance:**

- Measure readable codes, resolved releases, ambiguity, missing fields, latency, and call limits against R01.
- Test camera decoding on a physical iPhone; record a supported route or an explicit coverage limitation with text/manual recovery.

**Verify:** Run the recorded sample script plus a real camera check; report counts and failures, not just a successful example.

**Dependencies:** [R01](#r01). **Size:** M.

**Primary change areas:** tasks/provider-evaluation.md; scripts/evaluate_barcode.py.

**Stories:** WI-01, WI-03, WI-04.

<a id="r03"></a>
### R03: Prove the label-photo route

- [ ] **Outcome:** Compare bounded photo recognition with OCR plus catalog matching.

**Acceptance:**

- Evaluate a small shortlist on the same R01 answers, including low-confidence results, missing years, no match, and provider downtime.
- Record access, image handling, latency, and free-use limits; decide whether the planned request deadline is feasible or needs a contract revision.

**Verify:** Retain reproducible sample results and a recommendation; a web reverse-search page alone is not proof of structured identity.

**Dependencies:** [R01](#r01). **Size:** M.

**Primary change areas:** tasks/provider-evaluation.md; scripts/evaluate_label.py.

**Stories:** WI-02, WI-03, WI-04.

**Evidence checkpoint (R01–R02–R03):** Retain reproducible inputs, observed outcomes, limits and a recommendation. A failed spike is useful evidence; its dependent feature remains blocked until a viable path or explicit scope decision exists.

<a id="r04"></a>
### R04: Prove iPhone photo conversion

- [ ] **Outcome:** Resolve HEIF/HEIC handling before building the photo pipeline.

**Acceptance:**

- Exercise rotated JPEG and HEIF/HEIC samples, malformed files, and oversized dimensions using a candidate decoder.
- Measure resource use and verify oriented JPEG/WebP derivatives with location metadata removed; propose input byte/pixel and account limits.

**Verify:** Inspect decoded output and metadata on real samples; record failed formats and the recovery message.

**Dependencies:** [BASE](#base). **Size:** M.

**Primary change areas:** tasks/media-feasibility.md; scripts/evaluate_photos.py; assets/evaluation/photo-manifest.json.

**Stories:** OM-01, WC-07.

<a id="r05"></a>
### R05: Prove iPhone video conversion

- [ ] **Outcome:** Choose bounded video behavior using actual device clips.

**Acceptance:**

- Exercise H.264 and HEVC in MOV/MP4, portrait rotation, HDR, and silent clips with FFmpeg/ffprobe.
- Verify browser-playable H.264/AAC MP4 and posters; measure time/memory/disk and propose duration/byte limits plus a trim/export recovery path.

**Verify:** Play the converted samples in iPhone Safari and desktop; record source codec, output properties, and processing measurements.

**Dependencies:** [BASE](#base). **Size:** M.

**Primary change areas:** tasks/media-feasibility.md; scripts/evaluate_video.py; assets/evaluation/video-manifest.json.

**Stories:** OM-02.

<a id="r06"></a>
### R06: Evaluate official-place lookup

- [ ] **Outcome:** Establish whether official places can run within the chosen budget.

**Acceptance:**

- Check supported place search/selection, free access or quotas, attribution, and which fields can be stored.
- Document a provider decision and custom-label fallback; no billed account is required merely to finish this plan or spike.

**Verify:** Demonstrate a permitted example when access exists, or record the exact access gap; do not claim integration from documentation alone.

**Dependencies:** [BASE](#base). **Size:** S.

**Primary change areas:** tasks/places-feasibility.md.

**Stories:** TJ-11.

**Evidence checkpoint (R04–R05–R06):** Retain reproducible inputs, observed outcomes, limits and a recommendation. A failed spike is useful evidence; its dependent feature remains blocked until a viable path or explicit scope decision exists.

<a id="r07"></a>
### R07: Check deployment viability early

- [ ] **Outcome:** Test the operating assumptions before depending on hosted media processing.

**Acceptance:**

- Identify a local demo path and a candidate free hosting arrangement for Next, persistent Python API, Postgres/Auth/Storage, and a worker.
- Compare R04/R05 measurements with runtime, upload, database-connection and storage limits; record how the demo works if no suitable free worker host exists.

**Verify:** Write a cost/resource worksheet and a go/no-go per component; no claim of a fully hosted MVP if required processing only works on an unavailable laptop.

**Dependencies:** [R04](#r04), [R05](#r05). **Size:** S.

**Primary change areas:** tasks/hosting-feasibility.md; docs/architecture.md.

**Stories:** OM-02.

<a id="phase-1"></a>
## Phase 1: Access and a trustworthy development environment

**Milestone:** An owner signs in to a real private shell; guest access remains available.

<a id="f01"></a>
### F01: Settle the first sign-in flow

- [ ] **Outcome:** Select one manageable authentication method.

**Acceptance:**

- Confirm email OTP/magic link or one OAuth provider after checking delivery/setup; define recovery and allowed return destinations.
- Record the choice in an ADR and update the sign-in UX; keep lookup guest-accessible and saving authenticated.

**Verify:** Walk new-user, returning-user, expired-link/session, and cancel/return scenarios; record the user's choice before dependent integration.

**Dependencies:** [BASE](#base). **Size:** S.

**Primary change areas:** docs/decisions/; tasks/story-map.md; tasks/ux-review-04.md.

**Stories:** AC-01, AC-02.

<a id="f02"></a>
### F02: Establish the local data boundary

- [ ] **Outcome:** Make real Postgres and application migrations usable in development and CI.

**Acceptance:**

- Start local Supabase with Docker; add SQLAlchemy/psycopg/Alembic and only the application schema/accounts migration required next.
- Separate migration and runtime privileges, leave application tables unexposed to the Data API, and supply isolated test fixtures with two accounts.

**Verify:** Run migration from empty Postgres and verify runtime grants; CI uses disposable Postgres, never hosted personal data.

**Dependencies:** [BASE](#base). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/core and accounts models; apps/api/migrations; apps/api/tests/integration; .github/workflows/ci.yml.

**Stories:** AC-03.

<a id="f03"></a>
### F03: Verify caller identity

- [ ] **Outcome:** Create the reusable FastAPI authentication boundary.

**Acceptance:**

- Validate JWT signature, expected issuer/audience/expiry and subject through rotation-aware signing keys; reject missing or invalid credentials.
- Keep tokens and private data out of logs; ownership can never be chosen through request fields.

**Verify:** Exercise wrong signature/issuer/audience, expired token, missing subject, key rotation, and signing-key retrieval failure with deterministic fixtures.

**Dependencies:** [F01](#f01). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/core/auth.py; core/errors.py; tests/unit/test_auth.py.

**Stories:** AC-01, AC-03.

**Checkpoint after F01, F02, F03:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="f04"></a>
### F04: Resolve the application account

- [ ] **Outcome:** Expose the first real authenticated API operation.

**Acceptance:**

- Map verified issuer/subject to one app UUID through an explicit idempotent bootstrap operation; keep GET account reads read-only and reject disabled accounts.
- Apply the agreed JSON/error/request-ID conventions and required CORS methods, including PUT; generate the implemented OpenAPI contract.

**Verify:** Use two identities and concurrent bootstrap requests to prove uniqueness, no owner substitution, readable errors, and no account creation by GET; check browser preflight.

**Dependencies:** [F02](#f02), [F03](#f03). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/accounts; apps/api/src/wine_journal/core/errors.py; apps/api/src/wine_journal/main.py; docs/api-contracts.md; integration tests.

**Stories:** AC-01, AC-03.

<a id="f05"></a>
### F05: Sign in to the journal shell

- [ ] **Outcome:** Connect the first web flow to the real identity API.

**Acceptance:**

- Use Supabase sessions and a typed FastAPI transport with TanStack Query to sign in, bootstrap the account, and open the private shell.
- Compose thin Next routes; implement the reviewed navigation order and distinguish guest routes from private destinations without faking saved wine data.

**Verify:** Run a real local Supabase sign-in and API call; verify keyboard/error states and absence of backend credentials in the browser bundle.

**Dependencies:** [F01](#f01), [F04](#f04). **Size:** M.

**Primary change areas:** apps/web/src/features/auth; src/app; src/lib/api and session/query helpers; focused web tests.

**Stories:** AC-01, AC-03.

<a id="f06"></a>
### F06: Handle expired and ended sessions

- [ ] **Outcome:** Keep account transitions predictable and private.

**Acceptance:**

- Support the selected recovery flow and bounded session refresh; an invalid refresh returns to sign-in without looping.
- On sign-out/account switch clear private query caches and owned drafts; validate return paths and preserve only explicitly retained capture intent across re-authentication.

**Verify:** Exercise expiry during a request, failed refresh, two-account switching, recovery, and browser back navigation after sign-out.

**Dependencies:** [F05](#f05). **Size:** M.

**Primary change areas:** apps/web/src/features/auth; src/lib/session and API transport; auth tests.

**Stories:** AC-01, AC-02, AC-03.

**Checkpoint after F04, F05, F06:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="f07"></a>
### F07: Automate the first authenticated journey

- [ ] **Outcome:** Establish browser verification on a functioning flow.

**Acceptance:**

- Add Playwright configuration and a sign-in/sign-out journey using disposable local test identities; document setup and fixtures.
- Run focused API tests and the critical browser journey in CI, with no production keys or data; capture failure artifacts without tokens.

**Verify:** Execute from a clean test environment and prove an unauthenticated private API call fails independently of the UI guard.

**Dependencies:** [F06](#f06). **Size:** M.

**Primary change areas:** apps/web/tests/e2e; browser configuration; .github/workflows/ci.yml; docs/development.md.

**Stories:** AC-01, AC-03.

**Phase 1 exit:** Use two accounts to sign in, switch, recover access and sign out. The API verifies identity independently of UI guards, data migrations run on fresh Postgres, and the auth journey passes in CI.

<a id="phase-2"></a>
## Phase 2: A useful private wine journal

**Milestone:** Save a wine/date, return later, record repeats, revise ratings and find the bottle again.

<a id="j01"></a>
### J01: Represent private wine identities

- [ ] **Outcome:** Add only the wine identity records needed for manual capture.

**Acceptance:**

- Model a named offering and distinct release using UUIDs; distinguish year, non-vintage, multivintage, and unknown status.
- Allow a recognizable name with optional facts under the approved manual-entry rule; owner-only provisional records cannot appear in public reads or another user's selectors.

**Verify:** Test two vintages, separate releases with similar names, unknown versus non-vintage, invalid field combinations, and cross-owner access against Postgres.

**Dependencies:** [F04](#f04). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/catalog models and schemas; migrations; catalog integration tests; docs/data-model.md.

**Stories:** WC-03, WC-06, AC-03.

<a id="j02"></a>
### J02: Persist a minimal drinking entry

- [ ] **Outcome:** Implement the reliable save boundary before the capture UI.

**Acceptance:**

- Atomically save or reuse an owned user-wine record and an entry with only wine/date; create no occasion or rating implicitly.
- Use owner-scoped foreign keys and idempotency keys/request hashes; replay a lost-response retry once, reject changed payload reuse, and allow a new intentional same-date entry.

**Verify:** Real Postgres tests prove rollback, concurrent retries, ownership failures, and distinct intentional repeats; export the API contract.

**Dependencies:** [J01](#j01). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal models, schemas, routes/use case; migrations; save integration tests.

**Stories:** TJ-01, TJ-02, WC-03, WC-06, AC-03.

<a id="j03"></a>
### J03: Read private wine history

- [ ] **Outcome:** Provide bounded read models for the wine-first experience.

**Acceptance:**

- Return owned My Wines cards, one wine detail, and paginated entries using consumed dates with stable ties.
- Keep identity distinctions and empty history explicit; backdated entry creation must not incorrectly promote a wine, and guessed IDs disclose no private record.

**Verify:** Use two accounts, same-day ties, backdated entries, unrated wines, and multi-page fixtures; inspect query counts for per-card fetching.

**Dependencies:** [J02](#j02). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal queries and routes; response schemas; read integration tests.

**Stories:** HB-01, HB-02, WC-06, AC-03.

**Checkpoint after J01, J02, J03:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="j04"></a>
### J04: Save and revisit a first wine

- [ ] **Outcome:** Deliver the first complete manual journal journey.

**Acceptance:**

- Implement the reviewed manual capture, My Wines list, and detail/history screens using real endpoints; wine/date are enough.
- Retain typed input after validation/network failure and through sign-in; repeat-click/retry uses the same intended save and success invalidates the appropriate queries.

**Verify:** Browser journey: enter a manual wine/date, sign in if needed, save, reload, and reopen the same persisted entry; simulate a lost save response.

**Dependencies:** [F07](#f07), [J03](#j03). **Size:** M.

**Primary change areas:** apps/web/src/features/capture and my-wines; thin routes; shared UI primitives; browser journey.

**Stories:** TJ-01, WC-03, HB-01, HB-02, AC-01.

<a id="j05"></a>
### J05: Log the same wine again

- [ ] **Outcome:** Separate repeat drinking from new wine identity.

**Acceptance:**

- Offer Log this wine from an existing personal record; a new deliberate submit creates another entry linked to the same release.
- Keep previous entries intact, including same-date encounters; update consumed-date order without changing the wine's rating.

**Verify:** Log twice and reload: one personal wine, two entry IDs; replay one submission and confirm the count stays two.

**Dependencies:** [J04](#j04). **Size:** M.

**Primary change areas:** apps/web/src/features/capture and my-wines; journal save adjustments if needed; repeat-entry tests.

**Stories:** TJ-02, HB-02.

<a id="j06"></a>
### J06: Enrich an existing entry

- [ ] **Outcome:** Let users fill in memories without logging another drink.

**Acceptance:**

- Edit consumed date, optional local time/timezone, custom location label and free-form notes on the same entry; omission differs from explicit clearing.
- Use version checks to surface stale edits without discarding the user's draft; unknown time remains unknown and travel does not shift a calendar date.

**Verify:** Test PATCH omission/null, two stale editors, backdating and timezone boundaries; browser save/reload preserves the original entry ID.

**Dependencies:** [J04](#j04). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal edit use case and schemas; apps/web/src/features/capture; edit tests.

**Stories:** TJ-03, TJ-04.

**Checkpoint after J04, J05, J06:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="j07"></a>
### J07: Remove an entry safely

- [ ] **Outcome:** Define deletion before media adds more references.

**Acceptance:**

- Delete only the chosen owned entry after explicit UI confirmation; keep its personal wine record and any rating/history.
- Refresh affected lists and show a wine with no remaining entries honestly; ensure later attachment cleanup can hook into the same operation.

**Verify:** Delete one of two encounters, then the last; test wrong-owner and repeated deletion behavior without deleting other records.

**Dependencies:** [J05](#j05), [J06](#j06). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal deletion; apps/web/src/features/my-wines and entry controls; deletion tests.

**Stories:** TJ-04, AC-03.

<a id="j08"></a>
### J08: Store the current rating and revisions

- [ ] **Outcome:** Implement wine-level rating changes under the confirmed rating decision.

**Acceptance:**

- Finalize scale, clearing, no-op updates and history-erasure semantics before the migration; update current value and revision atomically with a version check.
- Rating changes do not create drinks, average past scores, or affect another release; concurrent edits cannot silently overwrite each other.

**Verify:** Postgres tests cover concurrent revisions, same-value no-op, clear/erase as approved, and unchanged entry counts.

**Dependencies:** [J02](#j02). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal rating model/use case/routes; migrations; rating tests; docs/data-model.md.

**Stories:** TP-04, AC-03.

<a id="j09"></a>
### J09: Show current rating and history

- [ ] **Outcome:** Make changing opinions understandable in the wine view.

**Acceptance:**

- Show one current personal rating plus dated past choices; offer approved change/clear/history controls with appropriate confirmation.
- Handle version conflicts and invalidate list/detail/profile queries; never present the history average as the current rating.

**Verify:** Change 4 to 4.5 if the proposed scale is approved, reload, inspect both revisions, then test a stale edit and clearing behavior.

**Dependencies:** [J04](#j04), [J08](#j08). **Size:** M.

**Primary change areas:** apps/web/src/features/my-wines; rating UI primitives; rating browser/component tests.

**Stories:** TP-04, HB-01.

**Checkpoint after J07, J08, J09:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="j10"></a>
### J10: Search and sort My Wines

- [ ] **Outcome:** Make the wine record useful once it grows.

**Acceptance:**

- Confirm and implement a small filter set plus consumed-date, name, and rating sorts; preserve distinct releases and stable pagination.
- Keep filters in shareable navigation state without exposing private records; handle unknown metadata, empty matches and removal/backdating consistently.

**Verify:** Verify filtered page boundaries have no duplicates/skips and test a partially remembered wine on mobile; compare query plans on a representative fixture.

**Dependencies:** [J03](#j03), [J09](#j09). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal queries; apps/web/src/features/my-wines filters; query/browser tests.

**Stories:** HB-03, HB-06, WC-06.

**Phase 2 exit:** Save a manual wine/date, reload, log a second glass, backdate/edit an entry, change a release rating and inspect its history. Search/filter without mixing vintages. Retry and two-account cases pass; no occasion is required.

<a id="phase-3"></a>
## Phase 3: Occasions and both capture loops

**Milestone:** Several wine entries can belong to one optional occasion without duplicating history.

<a id="o01"></a>
### O01: Create and revisit an occasion

- [ ] **Outcome:** Introduce explicit occasions as the secondary journal view.

**Acceptance:**

- Create, list, open and edit an owned occasion with title/date and optional time/place/general notes using the agreed title/date rule.
- An occasion may exist without wines while being organized; creating ordinary entries still never generates an occasion automatically.

**Verify:** Save and reopen a titled and untitled occasion, test stale edits and two-account access, and verify the secondary navigation.

**Dependencies:** [J06](#j06). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal occasion model/routes; migrations; apps/web/src/features/occasions; occasion tests.

**Stories:** TJ-08, HB-05, AC-03.

<a id="o02"></a>
### O02: Create an occasion during wine capture

- [ ] **Outcome:** Finish the wine-first creation loop.

**Acceptance:**

- Let entry capture select an existing occasion or create one inline without losing wine/date/notes.
- Commit a new occasion, manual identity if present, and entry together; cancellation/failure creates no partial journal records.

**Verify:** Exercise forward/back/cancel/retry in the browser and force a nested validation failure in Postgres; verify both-or-neither persistence.

**Dependencies:** [O01](#o01), [J04](#j04). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal nested save; apps/web/src/features/capture; transaction and browser tests.

**Stories:** TJ-10, TJ-05.

<a id="o03"></a>
### O03: Add new wines from an occasion

- [ ] **Outcome:** Finish the occasion-first creation loop.

**Acceptance:**

- Stage several new/manual wine entries inside an occasion draft, retain their own context, and save the bounded batch atomically.
- Allow adding a new wine to a saved occasion; cancelling a child returns to the parent draft without logging the child.

**Verify:** Dinner fixture: three releases and four intentional entries; test duplicate-submit retry and one invalid staged entry rolling back the whole new occasion save.

**Dependencies:** [O02](#o02). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal occasion creation; apps/web/src/features/capture and occasions; nested-flow tests.

**Stories:** TJ-05, TJ-06, WC-03.

**Checkpoint after O01, O02, O03:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="o04"></a>
### O04: Link and unlink existing entries

- [ ] **Outcome:** Organize prior memories without copying them.

**Acceptance:**

- Link selected owned entries to an occasion or unlink them while preserving IDs, consumed context, notes and ratings.
- Reject an entry already linked elsewhere unless the user explicitly chooses a re-link; occasion edits only prefill new entries, never overwrite existing ones.

**Verify:** Link/unlink two entries, attempt a cross-owner link and conflicting association, then compare original fields and row counts.

**Dependencies:** [O03](#o03). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal association operations; apps/web/src/features/occasions; association tests.

**Stories:** TJ-09, TJ-03, AC-03.

<a id="o05"></a>
### O05: Condense and remove occasions

- [ ] **Outcome:** Keep the secondary view clear and deletion predictable.

**Acceptance:**

- Show one card per distinct release while retaining all of its entries; use personal cover, catalog image, then placeholder when available.
- Deleting an occasion removes only its context and occasion-owned attachments, preserves entries and their own memories, and warns about the general album.

**Verify:** Prove three wine cards for four entries; delete a group and verify all retained entries remain reachable from My Wines; rerun with media after M06.

**Dependencies:** [O04](#o04). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal occasion reads/deletion; apps/web/src/features/occasions; deletion/grouping tests.

**Stories:** HB-05, TJ-04, OM-04.

**Phase 3 exit:** Complete wine-first inline occasion creation and occasion-first creation with three releases/four entries. Re-link/unlink and delete the occasion while retaining the entries and their consumed context.

<a id="phase-4"></a>
## Phase 4: Photos, covers and connected scrapbooks

**Milestone:** Private photos work on standalone entries and occasions, with correct wine highlights.

<a id="m01"></a>
### M01: Run durable background jobs

- [ ] **Outcome:** Introduce the smallest reliable worker for media work.

**Acceptance:**

- Use a Postgres jobs table with atomic claiming, expiring leases, bounded retries and unique operation keys; run the worker separately from the API in the same Python project.
- Handlers are idempotent, release database locks before heavy work, record safe status/error metadata, and recover after termination.

**Verify:** Run two workers against disposable Postgres, kill one mid-job, reclaim its lease and prove eventual completion without duplicate side effects.

**Dependencies:** [F02](#f02). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/media job model/runner; worker.py; migrations; worker integration tests.

**Stories:** OM-03.

<a id="m02"></a>
### M02: Authorize staged private uploads

- [ ] **Outcome:** Separate text persistence from upload lifecycle.

**Acceptance:**

- Create private storage configuration and owner-scoped pending assets with quota reservation, random immutable keys and bounded signed upload capability.
- Validate completion against the expected object, transition state and enqueue once in the same transaction; duplicate/forged/oversized completions fail safely.

**Verify:** Use local Storage and two accounts; test a guessed asset ID, repeated completion, oversized object, expired capability and parallel quota reservations.

**Dependencies:** [M01](#m01), [R04](#r04), [F04](#f04). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/media upload routes/service; integrations/storage; migrations; storage integration tests.

**Stories:** OM-01, OM-03, AC-03.

<a id="m03"></a>
### M03: Process photos into private derivatives

- [ ] **Outcome:** Turn supported uploads into usable images.

**Acceptance:**

- Apply the R04 decoder choice with actual-content validation, pixel/resource limits, orientation correction and metadata removal; publish only validated ready derivatives.
- Expose authorized status/download URLs and deterministic derivative outputs; malformed files fail without losing a saved entry.

**Verify:** Check JPEG/HEIC samples and malformed files; restart conversion, verify output metadata and unauthorized signing denial, and demonstrate signed-URL expiry behavior.

**Dependencies:** [M02](#m02), [R04](#r04). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/media photo handler; integrations/storage; worker handlers; photo integration tests.

**Stories:** OM-01, AC-03.

**Checkpoint after M01, M02, M03:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="m04"></a>
### M04: Attach photos to an entry

- [ ] **Outcome:** Let a standalone glass have its own memories.

**Acceptance:**

- Select and stage photos before or after entry save, attach only owned assets, and render pending/ready/failed states with captions/removal.
- Allow text-only save to succeed while a photo fails; retry/remove does not log another entry or duplicate an attachment.

**Verify:** Phone journey: save text during a failed upload, reconnect/retry, reload the entry and remove one attachment; test cross-owner parent/asset combinations.

**Dependencies:** [M03](#m03), [J06](#j06). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/media entry attachments; apps/web/src/features/capture and shared MediaGallery; upload journey.

**Stories:** OM-01, OM-03, TJ-04, AC-03.

<a id="m05"></a>
### M05: Use a personal bottle cover

- [ ] **Outcome:** Keep bottle recognition artwork independent from memories.

**Acceptance:**

- Choose a cover during manual entry or later; stage it before the wine exists and attach it through the deliberate save, retaining typed fields on failure.
- Preview, replace or remove the cover with catalog/placeholder fallback; changing it neither adds an album memory nor edits shared catalog artwork.

**Verify:** Create a manual wine with a cover, retry a failed upload, replace/remove it and verify entry count and memory gallery membership stay unchanged.

**Dependencies:** [M04](#m04). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/media cover operation; journal save attachment; apps/web/src/features/capture and BottleCover; cover tests.

**Stories:** WC-07, AC-03.

<a id="m06"></a>
### M06: Compose the occasion scrapbook

- [ ] **Outcome:** Combine general occasion memories with its wine-entry memories.

**Acceptance:**

- Support occasion-owned uploads and one deduplicated album containing them plus linked-entry attachments, with captions and source links.
- Preserve original attachment ownership when entries are unlinked or the occasion is deleted; show one wine card per release with cover priority.

**Verify:** Fixture includes one asset referenced twice, standalone entry media and general occasion photos; verify album membership before/after unlink and deletion.

**Dependencies:** [M05](#m05), [O05](#o05). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal/media album query; occasion attachment routes; apps/web/src/features/occasions and gallery; album tests.

**Stories:** OM-01, OM-03, OM-04, HB-05.

**Checkpoint after M04, M05, M06:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="m07"></a>
### M07: Show photo highlights by wine

- [ ] **Outcome:** Bring shared occasions back into the primary wine record.

**Acceptance:**

- Show three eligible ready-photo highlights plus a paginated full gallery from that wine's own entries and general linked-occasion albums.
- Deduplicate assets and repeated occasion joins; exclude another wine's entry-only photos and all covers; sort by source dates and omit empty/guest highlights.

**Verify:** Use the documented multi-wine fixture, repeated links, backdating and unlinking; assert exact asset IDs, order, counts and source links.

**Dependencies:** [M06](#m06). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal wine moments query; apps/web/src/features/my-wines and gallery; eligibility/privacy tests.

**Stories:** HB-01, HB-02, OM-04, AC-03.

<a id="m08"></a>
### M08: Reconcile abandoned and deleted media

- [ ] **Outcome:** Keep storage and quota accounting correct after failures.

**Acceptance:**

- Delete unreferenced assets only after checking active references, processing leases and outstanding upload-capability lifetimes; retain tombstones/retries for late objects.
- Reconcile failed object deletion, abandoned drafts and quota reservations; removal of one attachment must not delete an asset still used elsewhere.

**Verify:** Simulate late upload after cancellation, worker restart, shared references and storage deletion failure; reconcile twice with the same final state.

**Dependencies:** [M06](#m06). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/media cleanup handlers and quota accounting; worker schedule; cleanup integration tests.

**Stories:** OM-03, AC-03, TJ-04.

**Phase 4 exit:** Upload an iPhone photo, preserve text through upload failure, replace a cover, reopen the occasion album and the wine's three highlights. The exact-asset fixture proves deduplication, source links and exclusion of another wine's entry-only photos; worker/deletion retries pass.

<a id="phase-5"></a>
## Phase 5: Guest discovery and assisted capture

**Milestone:** Look up specs without signing in, scan a barcode, recognize a label photo and correct mistakes.

<a id="c01"></a>
### C01: Load a sourced catalog

- [ ] **Outcome:** Make public wine knowledge available without crowdsourced private data.

**Acceptance:**

- Import a small curated or accessible-provider dataset through a controlled path with distinct releases, source references and retrieval dates.
- Keep private provisional identities separate; retain unknown facts and price source/currency/market/date rather than invented availability.

**Verify:** Import twice, inspect identity/source constraints, and verify private records cannot become public through a client payload.

**Dependencies:** [J01](#j01), [R01](#r01). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/catalog import/service/models; migrations; scripts/seed_catalog.py; catalog fixtures/tests.

**Stories:** WC-06, WC-02, AC-03.

<a id="c02"></a>
### C02: Browse and read wine details as a guest

- [ ] **Outcome:** Deliver the look-it-up-with-friends scenario.

**Acceptance:**

- Implement public catalog text search, bounded browsing and detail pages showing available specs, producer notes, permitted bottle artwork and clearly labeled outbound links.
- Viewing never logs a drink; saving routes through sign-in/capture, while public responses and Next rendering exclude private notes, covers and profile fields.

**Verify:** Guest search/detail/save-return journey with two vintages, no match, missing price/link, invalid outbound URL and private-field checks.

**Dependencies:** [C01](#c01), [J04](#j04). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/catalog public queries/routes; apps/web/src/features/browse and public routes; guest journey tests.

**Stories:** WC-01, WC-02, WC-05, WD-04, AC-01.

<a id="c03"></a>
### C03: Correct private identity mistakes

- [ ] **Outcome:** Allow safe correction before adding automatic identification.

**Acceptance:**

- Edit owned provisional facts with impact context, or move one mistaken entry to an accessible existing/new wine while preserving entry ID, context, occasion and attachments.
- Leave the old wine's rating/history intact; never auto-merge conflicting records or change the public catalog. Keep whole-record merge conflicts accessible for later resolution.

**Verify:** Correct an entry and compare stable IDs/context/ratings; add real attachment/occasion regression cases once M07 lands. Test cross-owner targets and an already-owned destination.

**Dependencies:** [J09](#j09), [C02](#c02). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/catalog corrections and journal retargeting; apps/web/src/features/capture/my-wines; correction tests.

**Stories:** WC-04, WC-06, AC-03.

**Checkpoint after C01, C02, C03:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="c04"></a>
### C04: Resolve barcode candidates on the API

- [ ] **Outcome:** Add the provider boundary with honest identity outcomes.

**Acceptance:**

- Implement the R02 lookup route with GTIN validation, provenance, candidate statuses and server-validated selection; a barcode is not a globally unique vintage ID.
- Apply guest/user request budgets, timeouts and safe provider-error mapping; provider fields cannot directly create shared catalog data and no lookup creates an entry.

**Verify:** Contract tests cover clear match, unresolved year, multiple releases, no match, malformed provider response, timeout and exhausted quota.

**Dependencies:** [C02](#c02), [R02](#r02), [F04](#f04). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/identification routes/service; integrations/wine lookup; candidate schemas; adapter tests.

**Stories:** WI-01, WI-03, WI-04.

<a id="c05"></a>
### C05: Scan a bottle in the browser

- [ ] **Outcome:** Connect camera decoding to the verified lookup flow.

**Acceptance:**

- Use the R02-supported browser decoder on real phones; clear resolved matches open details automatically and ambiguous ones ask for only missing identity choices.
- Stop camera tracks when leaving; denial/unreadable code/provider failure offers text or manual continuation without losing the capture draft.

**Verify:** Physical iPhone camera checks plus deterministic decoder/provider fixtures; confirm guest lookup, deliberate save, re-authentication return and no duplicate logging.

**Dependencies:** [C04](#c04), [C03](#c03). **Size:** M.

**Primary change areas:** apps/web/src/features/capture scanner and candidate screen; browser fixtures/journey; device test notes.

**Stories:** WI-01, WI-03, WI-04, AC-01.

<a id="c06"></a>
### C06: Recognize a temporary label photo

- [ ] **Outcome:** Implement bounded recognition without making label uploads journal memories.

**Acceptance:**

- Offer the R03 provider/OCR route with ingress/content limits before unbounded buffering, temporary-image cleanup and explicit processing timeout/retention behavior.
- Return normalized candidates and unresolved fields under the shared request budget; client-supplied facts never bypass server validation or become public artwork.

**Verify:** Exercise representative files, malformed images, timeout, no match, quota limits and successful cleanup after both success and error.

**Dependencies:** [C04](#c04), [R03](#r03), [R04](#r04). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/identification photo operation; integrations/recognition; request limits; recognition tests.

**Stories:** WI-02, WI-03, WI-04, AC-03.

**Checkpoint after C04, C05, C06:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="c07"></a>
### C07: Identify a wine from a photo

- [ ] **Outcome:** Make photo lookup directly reachable without a barcode step.

**Acceptance:**

- Provide camera/file input and selectable candidate results to guests and owners; unresolved vintage and no-match paths preserve typed details.
- Keep recognition-only photos separate from personal covers and memories; a later save/sign-in remains a deliberate action.

**Verify:** Run the R01 images and real iPhone upload flow; test cancellation, failure, correction and sign-in return without implicit journaling.

**Dependencies:** [C06](#c06), [C03](#c03). **Size:** M.

**Primary change areas:** apps/web/src/features/capture photo input and candidates; browser/device checks.

**Stories:** WI-02, WI-03, WI-04, WC-02.

<a id="c08"></a>
### C08: Select official or custom places

- [ ] **Outcome:** Complete place entry while preserving the lightweight save flow.

**Acceptance:**

- Add the approved R06 provider adapter and reusable selector for entry/occasion forms with required attribution and permitted fields.
- Keep custom labels independent; editing a selected name clears stale provider association and lookup failure never prevents saving a custom place.

**Verify:** Test ambiguous selections, provider error/limit, custom-label edits and existing-entry context not being overwritten by an occasion.

**Dependencies:** [R06](#r06), [O04](#o04). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal place routes; integrations/places; apps/web/shared place field; place tests.

**Stories:** TJ-11, TJ-03, TJ-08.

**Phase 5 exit:** Demonstrate clear and ambiguous barcode/photo results on a real phone, text/no-match recovery, deliberate save through sign-in, private correction and official/custom places. Viewing details never records consumption; measured coverage limits are visible.

<a id="phase-6"></a>
## Phase 6: Video, learning and the taste profile

**Milestone:** The planned media and beginner/enthusiast experience is complete.

<a id="v01"></a>
### V01: Process bounded video reliably

- [ ] **Outcome:** Extend the proven media pipeline to moving memories.

**Acceptance:**

- Use the agreed R05 limits and actual stream inspection to produce compatible MP4 plus poster, including orientation, audio absence and HDR handling.
- Run conversion in bounded worker jobs with retry/lease recovery, deterministic outputs and accurate quota reconciliation; unsupported inputs fail with a recovery action.

**Verify:** Replay the real iPhone sample matrix, terminate a transcode and recover it, and verify output properties/resource limits without duplicating assets.

**Dependencies:** [R05](#r05), [M03](#m03), [M08](#m08). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/media video handler; worker runtime dependencies; video integration tests.

**Stories:** OM-02, OM-03.

<a id="v02"></a>
### V02: Attach and play private videos

- [ ] **Outcome:** Complete video behavior in entries and occasion albums.

**Acceptance:**

- Add bounded clip selection/upload, poster/playback, processing/failure/retry/removal states using the existing private attachment protocol.
- Keep text saves independent, refresh authorized playback access when needed, and retain videos in albums while initial wine highlights remain photo-only.

**Verify:** Use iPhone Safari and desktop to play portrait/landscape/silent clips; test interruption, limits, expired URLs and unauthorized access.

**Dependencies:** [V01](#v01), [M06](#m06), [M07](#m07). **Size:** M.

**Primary change areas:** apps/web/media picker/player and galleries; media browser/device checks.

**Stories:** OM-02, OM-04, AC-03.

<a id="l01"></a>
### L01: Offer beginner tasting prompts

- [ ] **Outcome:** Help users describe wine without requiring expert input.

**Acceptance:**

- Add optional original prompts or vocabulary beside free-form notes; wine/date alone still saves.
- Only explicit user choices enter personal notes; producer tasting claims are labeled and never inserted as personal observations.

**Verify:** Review copy against existing tasting research and verify keyboard/screen-reader use, skip-all save and editing existing notes.

**Dependencies:** [J06](#j06). **Size:** S.

**Primary change areas:** apps/web/src/features/capture note guidance; sourced prompt content; focused form tests.

**Stories:** TJ-07.

**Checkpoint after V01, V02, L01:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="l02"></a>
### L02: Publish a small Guides section

- [ ] **Outcome:** Deliver useful learning content without a CMS project.

**Acceptance:**

- Confirm a bounded initial set covering tasting language, styles/grapes, pairings and regions; include source/review dates and links to relevant catalog searches.
- Use public accessible routes and existing design tokens; guide visits do not record consumption or inferred likes.

**Verify:** Editorial/source review and link/navigation check on mobile and keyboard; test empty related results and guest access.

**Dependencies:** [C02](#c02), [L01](#l01). **Size:** M.

**Primary change areas:** apps/web/src/content/guides; features/guides; public routes; content/link verification.

**Stories:** WG-01.

<a id="l03"></a>
### L03: Summarize the private taste profile

- [ ] **Outcome:** Show what the user's own records actually support.

**Acceptance:**

- Agree simple summary semantics; count each release's current rating once, distinguish frequently tried from liked, and expose contributing records/sample counts.
- Handle sparse data, unknown attributes and multi-grape wines without unsupported precision; edits, rating clearing and identity correction refresh the summary.

**Verify:** Golden fixtures cover revisions, repeated drinks, two vintages, unknown metadata and corrections; check exact counts and two-account isolation.

**Dependencies:** [J09](#j09), [J10](#j10), [C03](#c03). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/journal profile query; apps/web/src/features/profile; profile fixtures/tests.

**Stories:** TP-01, AC-03.

**Phase 6 exit:** Play supported iPhone clips in both album contexts, skip guidance or use it explicitly, read the curated guides as a guest, and verify preference summaries against current-rating fixtures. Video and photo recognition are not silently removed to call the product an MVP.

<a id="phase-7"></a>
## Phase 7: Recovery, operation and portfolio release

**Milestone:** A reproducible portfolio release with verified privacy, recovery and runtime limits.

<a id="e01"></a>
### E01: Export owned journal data

- [ ] **Outcome:** Provide a practical way to take memories out of the app.

**Acceptance:**

- Create an authenticated bounded export job with structured wine/entry/occasion/rating metadata and owned media, preserving relationships and dates.
- Protect download access, show progress/failure/retry and expire output artifacts; shared references do not duplicate all media bytes.

**Verify:** Export a seeded account and validate archive contents against source records; test another account, failed download generation and artifact cleanup.

**Dependencies:** [M08](#m08), [V02](#v02), [C03](#c03). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/accounts export use case; media/job integration; account UI; export tests.

**Stories:** AC-04, AC-03.

<a id="e02"></a>
### E02: Delete an account without resurrection

- [ ] **Outcome:** Make erasure resumable and immediately stop new private access.

**Acceptance:**

- Require explicit confirmation, mark the account disabled immediately, and durably remove private data/media then provider identity with retryable cleanup.
- Retain minimal tombstone/job state until completion so a still-valid token cannot bootstrap the account again; communicate signed-URL grace and backup expiry accurately.

**Verify:** Test retained JWTs, delayed signed upload, provider deletion failure, worker restart and repeated delete requests; another account remains intact.

**Dependencies:** [E01](#e01), [M08](#m08). **Size:** M.

**Primary change areas:** apps/api/src/wine_journal/accounts deletion and auth-state checks; cleanup jobs; account UI; deletion tests.

**Stories:** AC-04, AC-03.

<a id="e03"></a>
### E03: Rehearse backup and restore

- [ ] **Outcome:** Prove that stored memories can actually be recovered.

**Acceptance:**

- Back up the database and media objects with a documented cadence/retention; provider database export alone is insufficient.
- Restore a representative journal into an isolated environment and verify IDs, rating history, attachments and account mapping; describe deletion expiry in backups.

**Verify:** Run a restore drill with expected record/asset counts and gallery checks; record observed recovery time and the approved data-loss window.

**Dependencies:** [E01](#e01), [E02](#e02). **Size:** M.

**Primary change areas:** scripts/backup and restore; docs/operations.md; restoration fixture/checks.

**Stories:** AC-04, AC-03.

**Checkpoint after E01, E02, E03:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="e04"></a>
### E04: Deploy the web and API together

- [ ] **Outcome:** Turn the verified local app into an honest portfolio environment.

**Acceptance:**

- Use the approved R07 arrangement with HTTPS, environment separation, narrow database credentials and reviewed auth callback/CORS settings.
- Automate checks and one explicit migration step, preserve a compatible previous release for rollback, and keep private responses out of shared caches.

**Verify:** Deploy a disposable seeded environment, run guest and authenticated smoke flows, then rehearse application rollback with its schema compatibility constraints.

**Dependencies:** [R07](#r07), [F07](#f07), [C05](#c05), [C07](#c07), [C08](#c08), [L02](#l02), [L03](#l03), [E03](#e03). **Size:** M.

**Primary change areas:** apps/api/Dockerfile; deployment workflow/config; environment examples; docs/operations.md.

**Stories:** AC-03, WI-01, WI-02.

<a id="e05"></a>
### E05: Operate the worker and service limits

- [ ] **Outcome:** Ensure hosted capture continues working after the API returns.

**Acceptance:**

- Run the worker/cleanup scheduler in the chosen environment with bounded CPU/storage/concurrency, graceful shutdown and restart recovery.
- Expose useful liveness/readiness, queue age, conversion failure, storage and provider-budget signals; log request/job IDs rather than private content or tokens.

**Verify:** Restart API/worker independently, exhaust a test quota and simulate provider outage; confirm visible recovery and alert/log usefulness without leaking data.

**Dependencies:** [E04](#e04), [V02](#v02), [M08](#m08). **Size:** M.

**Primary change areas:** worker/deployment config; API readiness/observability; docs/operations.md; failure drills.

**Stories:** OM-02, OM-03, AC-03.

<a id="e06"></a>
### E06: Audit privacy across complete journeys

- [ ] **Outcome:** Check boundaries using the completed feature set.

**Acceptance:**

- Exercise two-account reads/writes, nested IDs, attachment signing, guest catalog responses, disabled accounts and private cache invalidation.
- Review upload validation, request budgets, secret handling and export/deletion behavior; fix findings in the owning feature instead of accepting an untracked release exception.

**Verify:** Run a reproducible abuse/ownership matrix and inspect browser/network/log outputs; include retries and expired signed capabilities.

**Dependencies:** [E02](#e02), [E05](#e05). **Size:** M.

**Primary change areas:** apps/api/tests/integration; apps/web/tests/e2e; docs/release-checklist.md; affected feature fixes.

**Stories:** AC-03, AC-04.

**Checkpoint after E04, E05, E06:** Run the relevant verification protocol, retain evidence for these acceptance cases, and keep the existing app usable. Resolve regressions before extending this flow; request product feedback when a decision changes the experience.

<a id="e07"></a>
### E07: Validate the mobile user experience

- [ ] **Outcome:** Test the actual product on the device it is intended for.

**Acceptance:**

- Complete guest lookup, quick save, later editing, ratings, both occasion loops and photo/video retrieval on a real iPhone plus desktop.
- Check keyboard/focus/labels, contrast, touch targets, layout, camera denial, interrupted connection and clear upload states; log and resolve material usability issues.

**Verify:** Run the scripted acceptance journeys with real-device notes and focused accessibility checks; include empty, loading and failure states, not only populated screenshots.

**Dependencies:** [E05](#e05), [L01](#l01), [L02](#l02), [L03](#l03). **Size:** M.

**Primary change areas:** apps/web/tests/e2e; tasks/ux-acceptance.md; affected components/styles.

**Stories:** TJ-01, TJ-05, TJ-06, TJ-10, OM-04, HB-01.

<a id="e08"></a>
### E08: Measure retrieval and media performance

- [ ] **Outcome:** Verify bounded behavior under a defined portfolio workload.

**Acceptance:**

- Agree a representative dataset/device/network profile and separate cold starts/provider latency from normal journal requests.
- Measure query counts, page/payload sizes, gallery loading and worker backlog; address observed bottlenecks without introducing speculative services.

**Verify:** Record repeatable baselines and query plans; review against proposed targets such as common-read p95 below 500 ms once workload/host are defined, rather than asserting an unmeasured SLA.

**Dependencies:** [E05](#e05), [M07](#m07), [J10](#j10). **Size:** M.

**Primary change areas:** scripts/performance fixture/probe; tasks/performance-results.md; affected queries/components.

**Stories:** HB-01, HB-02, HB-03, OM-04.

<a id="e09"></a>
### E09: Prepare the portfolio demonstration

- [ ] **Outcome:** Make the release reproducible and its limits clear.

**Acceptance:**

- Provide a fresh-clone setup, resettable synthetic demo account/catalog, key user journeys and architecture tradeoff notes.
- Record measured provider coverage, device/media limits, current operating cost and actual versus simulated paths; do not present mock recognition or seeded popularity as live features.

**Verify:** A clean environment can run the documented demo; complete the phase exit checklist and product walkthrough before calling it the private portfolio MVP.

**Dependencies:** [E06](#e06), [E07](#e07), [E08](#e08). **Size:** M.

**Primary change areas:** README.md; docs/portfolio-case-study.md; docs/release-checklist.md; demo seed/reset scripts.

**Stories:** WC-02, WI-01, WI-02, OM-02.

**Phase 7 exit:** Export, delete and restore synthetic account data/media; restart the hosted worker; verify guest/private journeys, real-device UX, measured performance and documented provider limits. Resolve material findings before release. No irreplaceable-user-memory promise precedes the restore gate.

## Later phases: Separate activation decisions

The following are outcome-level sequences, **not implementation-ready tickets or additions to the private MVP**. When a branch is selected, refine it into the same task/verification format before coding. These branches are not a forced serial queue: private collaboration, recommendations and iOS do not require a public feed.

<a id="opt-01"></a>
### OPT-01: Explicit preferences beyond ratings

TP-02 remains an unselected MVP proposal. Decide whether like/dislike or would-buy-again deserves a control and how it interacts with ratings; if selected, add one preference-write task and one summary/UI task with contradictory-input and account-isolation tests. L03 must not pretend these inputs already exist. Its deferral does not remove the current-rating profile.

<a id="x1"></a>
### X1: Personal organization and deeper tasting

**Prerequisites:** Private journal and media foundations; independent of public reviews.

**Sequence:** Define calendar/want-to-try/structured-tasting semantics → implement one selected view or field set → verify it reads the existing journal without duplicating consumption.

**Readiness check:** Calendar includes standalone entries; a want-to-try item creates no drinking entry. Detailed tasting remains optional.

**Stories:** HB-04, TP-03, EX-01.

<a id="x2"></a>
### X2: Public wine reviews and recent feed

**Prerequisites:** Stable private product and explicit publication/aggregate-rating rules.

**Sequence:** Specify a separate public review model and copy/preview boundary → add publish/read/profile/edit/unpublish flows → add reporting/moderation and recent-public-review browsing before opening publication.

**Readiness check:** Public responses never serialize private notes, places or albums; unpublish and moderation work. Agree public rating/count rules rather than reusing private rating revisions as votes.

**Stories:** PC-01, PC-02, PC-03, PC-04, PC-05, PC-06, WD-01.

<a id="x3"></a>
### X3: Shared occasions

**Prerequisites:** Occasion/media foundations; can precede X2. Joint public reviews additionally require X2.

**Sequence:** Define invitations, membership, contribution ownership and revocation → evolve the same-owner constraints into deliberate shared contributions → add selected shared notes/albums with conflict handling.

**Readiness check:** Sharing an occasion grants access only to explicitly shared content, never all participants' private entries or personal ratings. Revocation, deletion and concurrent edits are tested.

**Stories:** SC-01, SC-02, SC-03, SC-04, SC-05.

<a id="x4"></a>
### X4: Recommendations and meaningful trends

**Prerequisites:** Attribute-based similarity needs a reliable catalog/profile; public trends need X2 plus sufficient genuine public activity.

**Sequence:** Start with explainable attribute similarity and sparse-profile fallback → evaluate recommendation quality → define distinct-contributor thresholds/time windows for public trends and optional profile-linked guides.

**Readiness check:** Guide views are not likes; private drinking does not become public popularity. Never label seeded data as trending. Collaborative filtering waits for evidence and adequate data.

**Stories:** WD-02, WD-03, WG-02.

<a id="x5"></a>
### X5: Native iOS

**Prerequisites:** Stable versioned API/auth/media contracts and working capture flows; no dependency on a public feed.

**Sequence:** Choose Swift/native versus React Native from device needs and prototype a real capture/auth slice → add journal and scrapbook screens against the same API → verify secure token storage, deep links, media permissions and distribution requirements.

**Readiness check:** Test on a physical iPhone, including expired sessions and unsupported media. UI/camera code is new client work; backend business rules stay shared.

**Stories:** CH-01.

<a id="x6"></a>
### X6: Unidentified drafts and offline synchronization

**Prerequisites:** Explicit product choice about offline save guarantees, device storage and conflict resolution.

**Sequence:** Define account-scoped durable drafts and retained media → implement stable client IDs/outbox and retry rules → add conflict, logout, deletion and multi-device reconciliation tests before claiming offline saves.

**Readiness check:** Airplane-mode capture survives restart, syncs once and handles stale edits without exposing another account's drafts. Error-preserved online forms are not marketed as offline support.

**Stories:** EX-02, EX-03.

<a id="x7"></a>
### X7: Additional social and retail features

**Prerequisites:** Select independently after usage feedback; social/public media need X2 and expanded moderation, offers need viable merchant data.

**Sequence:** Scope follows/comments/reactions, selectively published media, or current merchant offers separately → define visibility/freshness/ownership rules → expand into bounded implementation tasks for the selected feature.

**Readiness check:** Public media has a deliberate publication lifecycle; offers show market/source/time and do not imply inventory or checkout. No automatic expansion of the private MVP.

**Stories:** EX-04, EX-05, EX-06, EX-08.

## Continuity with the prior backlog

This is the same work being replanned. Completed P1a is BASE; open product/research work is carried forward below and in [story coverage](story-coverage.md). The [previous backlog at b8a2515](https://github.com/sebasalonsogp/wine-journal/blob/b8a2515/tasks/todo.md) retains all original discovery checkboxes and their historical status; it is not a competing active task list.

| Previous area | Current location / remaining work |
| --- | --- |
| D1 audience, success, budget and availability | Existing story map; decision gates G1–G6 in plan.md; R07 and E09. Weekly capacity is still unknown. |
| D2 sample set | R01 |
| D3 provider feasibility | R02, R03, R06, R07 |
| D4 journeys and remaining UX | Reviewed prototype retained; J04–J10, O01–O05, C05/C07, L01/L02 and E07 verify actual implementation |
| D5 identity/ownership model | J01/J02/J08, O01/O04/O05, M02/M06/M07/M08, C03 |
| D6 architecture | Direction accepted in ADR 0005; F01, R07 and E04/E05 settle execution details |
| D7 phased backlog | This plan is produced for review; completion of planning does not complete feature tasks |
| P0 inputs | F01, R01–R07 and the decision gates |
| P1a / P1b | BASE complete / F01–F07 pending |
| P2 private journal | J01–J07 |
| P3 rating/history | J08–J09 |
| P4 occasions | O01–O05 |
| P5 photo/cover lifecycle | M01–M05, M08 |
| P6 scrapbook/highlights | M06–M07 |
| P7 video | V01–V02 |
| P8 catalog/search/correction | C01–C03, J10 |
| P9 barcode | C04–C05 |
| P10 photo recognition | C06–C07 |
| P11 places | R06, C08 |
| P12 guidance/profile | L01–L03; optional TP-02 remains OPT-01 |
| P13 data controls/readiness | E01–E09 |
| Calendar/public/collaboration/discovery/native/offline ideas | X1–X7; no expansion silently becomes MVP scope |

The active backlog stays here. Creating GitHub issues or another tracker is a separate organizational choice; do not maintain conflicting checkbox copies.
