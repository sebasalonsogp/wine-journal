# Wine Journal planning and delivery tasks

Working backlog. The user authorized repository scaffolding under `repo/` after architecture review; [ADR 0005](../docs/decisions/0005-repository-foundation.md) records the accepted direction. Product scope is in [plan.md](plan.md) and [story-map.md](story-map.md). My Wines is primary; multi-wine occasions are secondary; Browse Wines is first in navigation. Preserve distinct releases, independent rating history, standalone entries and optional guidance. Public reviews, collaboration, calendar and native iOS remain later. Scaffolding does not implement those product features or authorize paid services.

Current sequencing: create the P1a foundation, then resolve the sign-in method and implement P1b. D5's detailed schema and D2/D3 provider experiments remain open. Weekly effort, free-host/provider choices and media limits remain unresolved. Budget direction is local/free-first; commercial licensing research is deferred; common iPhone media support is required. Online saves are the current baseline; automatic offline synchronization remains later.

## Active product review

- [x] Discuss the [architecture alternatives review](../docs/architecture-options.md), including domain organization, modular core versus microservices, long-term supporting services, and serverless execution. The user accepted the direction and subsequently authorized scaffolding.

- [x] Begin the user-requested UX phase with an interactive first walkthrough and burgundy/olive/brown/cream direction; review scenarios are in [ux-review.md](ux-review.md).
- [x] Revise both directions of the wine/occasion creation flow, add official/custom location concepts and manual bottle covers, and explore Browse Wines plus Guides; see [UX review 02](ux-review-02.md).
- [x] Export the second walkthrough for Stitch with DESIGN.md, a continuation prompt, portable HTML, and desktop/mobile references; install the requested Stitch skills and Impeccable. See [design-tooling.md](design-tooling.md).
- [x] Review and refine the walkthrough through the connected Stitch iteration and follow-up feedback; [UX review 04](ux-review-04.md) records navigation, condensed occasion wines and wine photo highlights. Guide breadth and some controls remain open.
- [ ] During provider feasibility, assess Google Places costs/quotas, attribution and storage rules, while retaining a custom-location fallback.
- [x] Complete sufficient prototype review to begin architecture planning, following the user's explicit request. Detailed acceptance and real-device checks remain part of implementation.

- [x] Create the draft capability map and current/later story inventory.
- [x] Resolve minimum capture: save wine/date now, optionally enrich the same experience later; allow the distinct intent of looking up specs without saving.
- [x] Resolve access: visitors can look up wine details; sign-in is required to save experiences.
- [x] Resolve personal rating ownership: one current wine rating with retained past scores/change dates, independent of drinking occasions.
- [x] Promote multi-wine occasions to core scope; retain primary My Wines and add secondary occasion scrapbooks.
- [x] Separate standalone drinking entries and optional time/location from titled occasions; record later collaboration stories SC-01 through SC-05.
- [x] Research wine identity using Calculated Risk and other primary examples; preserve distinct releases and flexible browsing in `wine-identity.md`.
- [x] Research optional tasting guidance and add it alongside free-form notes to MVP direction in `tasting-notes.md`.
- [ ] Validate library layouts/grouping and exact sort/filter controls through low-fidelity UX; per-release rating/history is the working recommendation.
- [ ] Review rating scale, guidance controls, media behavior, and remaining stories one area at a time in `story-map.md`.
- [ ] Review linking/unlinking entries, occasion context defaults, independent when/where, and preserving entry/media ownership when occasions are removed.
- [ ] Refine MVP acceptance/recovery behavior, then map journeys and low-fidelity UX before technical work.

## D1: Confirm the first user and success criteria

Description: Turn the intended audience and portfolio outcome into a short product brief, retaining expansion goals separately.

Acceptance criteria:
- [x] Identify the first user and problem: the creator wants to track wines and develop preferences; the wider audience includes enthusiasts and social users.
- [ ] Confirm the demo journey, weekly effort, service budget, initial market, and private-video limits; private-first/public-later, Python preference, and primary wine history are established.
- [ ] Record scope choices and unresolved assumptions without presenting recommendations as agreed requirements.

Verification: Compare the brief against `notes.md` and the user's answers; review the core journey together.
Dependencies: None.
Files likely touched: `tasks/plan.md`, `tasks/todo.md`.
Estimated scope: Small.

## D2: Prepare an identification evaluation set

Description: Define approximately 30 representative bottles and label/barcode images with known identities and vintages to test the biggest external dependency.

Acceptance criteria:
- [ ] Include common/obscure wines, multiple vintages with similar labels, non-vintage cases, and imperfect photos.
- [ ] Document image/data provenance and permission to use the samples.
- [ ] Separate barcode readability, catalog identity, and vintage truth in the evaluation fields.

Verification: Spot-check sample labels against recorded identities; confirm the set reflects D1's audience and market.
Dependencies: D1 for final sample selection; schema can be drafted earlier.
Files likely touched: `tasks/identification-evaluation.md`, `assets/evaluation/manifest.csv`.
Estimated scope: Small; sample media count is separate from authored files.

## D3: Establish provider feasibility

Description: Check a small shortlist of free accessible sources for practical coverage and quotas. Commercial licensing research/procurement is deferred per the user; a curated demo catalog can unblock development.

Acceptance criteria:
- [ ] Verify usable free endpoints, basic source requirements and quotas as integrations are chosen; defer a broader commercial licensing assessment.
- [ ] Evaluate available authorized trials against D2, recording correct candidates, vintage accuracy, missing fields, latency, correction effort, and cost.
- [ ] Recommend a provider combination or clearly bounded demo-catalog fallback, listing anything still untested.

Verification: Retain reproducible evaluation inputs/results without API secrets or disallowed provider data; distinguish observed behavior from marketing claims.
Dependencies: D2 for benchmarking. Documentation/access research may precede D2.
Files likely touched: `tasks/provider-evaluation.md`, `tasks/identification-evaluation.md`, `tasks/plan.md`.
Estimated scope: Medium; split individual provider experiments if they exceed a focused session.

## Checkpoint: Product and feasibility

- [ ] The journal's value is clear independently of lookup accuracy.
- [ ] At least one affordable identification route is established, or limited coverage is explicitly accepted.
- [ ] The audience, scope proposal, and evidence are reviewed with the user before becoming a final specification.

## D4: Storyboard capture and retrieval

Description: Map primary My Wines with all drinking entries, standalone quick capture, optional titled occasions, secondary occasion scrapbooks, barcode/photo/text capture, and private taste profile. Include linking existing entries later. Draft scenarios are in `occasion-journeys.md`. Calendar, shared occasions, and public reviews remain later.

Acceptance criteria:
- [ ] Show barcode-to-details for a clear match, directly accessible photo recognition/text lookup, and no-match/manual recovery.
- [ ] Show wine-first history with distinct releases, configurable sorting/filtering, encounter notes/photo/video, and a sample-backed taste summary. Show the secondary occasion scrapbook and optional beginner note guidance; calendar remains a later navigator.
- [ ] Account for denied camera permission, unknown vintage, backdated/same-day entries, and failed media upload without losing notes; preserve private/public boundaries.

Verification: Walk through the demo and failure scenarios from the perspective of D1's user; count required inputs and remove unnecessary steps.
Dependencies: D1; provider-specific wording follows D3.
Files likely touched: `tasks/user-journeys.md`, `assets/wireframes/flows.md`.
Estimated scope: Small.

## D5: Specify wine identity and journal ownership

Description: Refine the conceptual model before writing database migrations.

Acceptance criteria:
- [ ] Model wine versus release versus drinking entry and optional occasion, including unknown/non-vintage distinctions, entry consumed date/optional time/location, several wines in one occasion, separate same-date entries/events, entry versus occasion media, and consumed-date sorting.
- [ ] Define ownership, provisional manual records, provider references, and catalog correction behavior.
- [ ] Define private profile aggregation, later public review/rating aggregation, and media publication/deletion boundaries without exposing private data.

Verification: Walk sample records through two users, two vintages, repeated tastings, no-match creation, a correction, and unpublishing.
Dependencies: D1 and D4; provider field mappings depend on D3.
Draft produced: [data model](../docs/data-model.md), including correction cases, owner constraints and gallery/deletion semantics. Acceptance below remains subject to review; no database exists yet.

Files likely touched: `docs/data-model.md`, `tasks/plan.md`.
Estimated scope: Small.

## D6: Finalize the smallest viable architecture

Description: Review the proposed stack and boundaries now; finalize provider-dependent choices after feasibility and budgeting. Current drafts: [architecture](../docs/architecture.md), [contracts](../docs/api-contracts.md), and [decisions](../docs/decisions/0004-nextjs-and-portfolio-budget.md).

Acceptance criteria:
- [x] Reassess Vite savings and migration effort; propose Next.js now in ADR 0004 while retaining the Python/FastAPI boundary, PostgreSQL rationale and SQLAlchemy/Alembic plus Supabase recommendation.
- [x] Draft HTTP contracts, auth context, provider fallbacks, transaction rules and media flow.
- [x] Document operating assumptions, privacy checks, deployment/backup approach and iOS reuse limits. Final review and vendor selection remain open.

Verification: Trace capture, save, retrieval, and public review requests through the proposed components; confirm no client secret, unscoped privileged database call, or required unsupported long-running request.
Dependencies: D5 for the model; D3 for final provider claims, not for drafting the architecture.
Files likely touched: `docs/architecture.md`, `docs/api-contracts.md`, `docs/decisions/`, `tasks/plan.md`.
Estimated scope: Medium.

## D7: Translate agreed scope into implementation slices

Description: Produce the build backlog only after discovery, with one visible behavior per task and dependencies made explicit.

Acceptance criteria:
- [ ] Start with sign-in/manual wine-first journal and standalone drinking entries, then add optional titled occasions, repeat history/time/places, search/sort/filter, photos, occasion scrapbook browsing, optional note guidance, bounded private video, basic taste profile, barcode details, and directly accessible photo matching. Calendar, shared participation, and public capabilities remain later. This sequence is provisional; no development is authorized now.
- [ ] Every task has at most three acceptance criteria, focused verification, dependencies, and a small likely file set; split oversized tasks.
- [ ] Include checkpoints for usable journal, reliable capture, ownership/privacy, and private portfolio readiness; define a separate public-phase checkpoint and estimate effort against the user's availability.

Verification: Check every agreed MVP story maps to a task, no expansion feature quietly enters the MVP, and failure/privacy scenarios are covered.
Dependencies: D4, D5, and D6.
Files likely touched: `tasks/plan.md`, `tasks/todo.md`.
Estimated scope: Small.

## Checkpoint: Ready to build

- [ ] The user has reviewed the concrete scope and architecture.
- [ ] Provider limits and untested claims are visible.
- [ ] Acceptance criteria and quality checks are agreed.
- [ ] The build backlog is ordered in independently verifiable slices.

Future build milestones are described below; no application setup, deployment, or purchases were performed in this planning pass.

## Proposed implementation sequence

P1a is the authorized foundation slice; product feature slices remain unstarted. Each feature includes its own database/API/UI changes; do not implement the entire proposed schema before a usable flow. File areas are relative to the Git root in [architecture.md](../docs/architecture.md#proposed-folder-structure). Verification commands are in [development.md](../docs/development.md). Split medium slices further when they reveal independent work; no schedule is claimed without weekly availability.

### P0: Resolve implementation inputs

- [ ] Review ADRs and confirm initial auth method and rating scale; use local/free-first budgeting. Choose email OTP or an OAuth provider after checking delivery/setup requirements; use managed auth either way.
- [ ] Carry out D2/D3 identification/provider feasibility and an iPhone HEIF/HEIC and HEVC/MOV compatibility spike with proposed upload/clip/account limits and compatible playback derivatives. Retain fallback scope and measured results.
- [ ] Record minimum manual-identity fields, first retail market and real-user backup requirements.

Verification: evidence and remaining limits in provider/media research; no claims based only on a demo. Dependencies: none for research; user choices before dependent integrations. Files: `tasks/provider-evaluation.md`, `tasks/media-feasibility.md`, relevant ADRs. Size: separate small research tasks per provider/format, not one implementation ticket.

### P1a: Repository foundation

- [x] Create the agreed domain/workflow folders under `repo/`, with clear responsibility markers and preserved planning/design references.
- [x] Add a runnable Next startup page, FastAPI liveness endpoint, per-app environment examples, and committed dependency locks.
- [x] Generate the OpenAPI snapshot and TypeScript types; configure lint, format, types, API smoke tests, package/build checks and CI.
- [x] Initialize local Supabase configuration without provisioning a hosted project. Keep Alembic as the future application migration authority.
- [x] Finish local verification, create the private GitHub repository, and confirm its first CI run. [Repository](https://github.com/sebasalonsogp/wine-journal); [successful initial CI](https://github.com/sebasalonsogp/wine-journal/actions/runs/34895334930).

Verification: [development commands](../docs/development.md), browser smoke, generated-contract drift, and hosted CI. Local Supabase startup remains unverified until Docker is running; auth/persistence tests are part of P1b. No journal feature is marked implemented by this scaffold.

Observed September 14, 2026: local lint/format/types passed, two API smoke tests passed, the Python wheel/source package and Next production build succeeded, generated contracts had no drift, and package audits reported no known vulnerabilities. The page returned HTTP 200 with no script errors or horizontal overflow at 320, 768, and 1440 pixels. Hosted CI passed both API and web jobs on Linux, including Node 24. See `docs/development.md` for upstream tooling warnings and limits of these checks.

### P1b: Sign in and reach an empty private journal

- [ ] Start and verify local Supabase, initialize SQLAlchemy/Alembic, and implement the first account/schema migration with isolation checks.
- [ ] Sign in, resolve an active app identity and open an empty My Wines page; sign out clears private state.
- [ ] Verify invalid tokens and a second account cannot access private records; provide account recovery consistent with the chosen method.

Verification: auth integration tests and one browser journey. Dependencies: architecture review and P0 auth choice. Files: `apps/web/src/features/auth/`, `apps/web/src/app/`, `apps/api/src/wine_journal/core/`, `accounts/`, tooling/config. Size: foundation work split into setup and auth tasks before execution. Stories: AC-01/02/03.

### P2: Save and revisit a standalone glass

- [ ] Enter a recognizable manual wine and date, save once, and retrieve it from My Wines with no occasion required.
- [ ] Add a second encounter, enrich notes/time/custom place, edit or delete one entry without changing the other.
- [ ] Preserve input on failure and prevent duplicate saves on retry; keep provisional identity private.

Verification: transaction/ownership tests and wine → save → reload → repeat browser flow. Dependencies: P1. Files: API `catalog/`, `journal/`, migrations; web `capture/`, `my-wines/`. Size: medium; split first save from edit/repeat if needed. Stories: WC-03/06, TJ-01/02/03/04, HB-01.

### P3: Record current rating and history

- [ ] Change a release rating without creating a drinking entry and show current value plus dated revisions.
- [ ] Handle stale edits, no-op same values, clearing a score and explicit history deletion consistently.

Verification: real Postgres concurrent-update tests and rating display flow. Dependencies: P2 and rating-scale decision. Files: API `journal/ratings.py`, schemas/models/migration; web `my-wines/`. Size: medium. Stories: TP-04.

### P4: Group entries into occasions

- [ ] Create an occasion inline from entry capture or add new/manual wines from an occasion draft, preserving the parent draft.
- [ ] Commit nested saves atomically; deliberately link/unlink existing entries without changing their original when/where.
- [ ] Show one card per release with all its entries, and delete an occasion without deleting those entries.

Verification: both nested browser journeys, rollback, duplicate retry and ownership cases. Dependencies: P2. Files: API `journal/occasions.py`, migrations; web `capture/`, `occasions/`. Size: split wine-first creation, occasion-first creation and existing-entry management into focused tasks. Stories: TJ-05/06/08/09/10, OM-03/04.

**Checkpoint: usable private journal.** Demonstrate standalone capture, repeated entries, rating history and both occasion flows with a second account for privacy checks. Confirm behavior before enriching media.

### P5: Add bottle covers and entry photos

- [ ] Upload an owned photo through staged private storage, validate/process it durably, and expose only authorized ready derivatives.
- [ ] Set/replace/remove a personal cover independently of entry memories; failed uploads leave saved text intact.
- [ ] Handle late completion, worker restart and abandoned-file cleanup with bounded quotas.

Verification: storage/worker integration tests, cross-account signed-link denial and interrupted upload on a phone. Dependencies: P2, P0 media decision. Files: API `media/`, `integrations/`, `worker.py`, migrations; web media components and capture. Size: split upload lifecycle, derivatives/cleanup and cover UI. Stories: WC-07, OM-01, AC-03.

### P6: Connect scrapbook albums and wine highlights

- [ ] Add occasion-owned photos and compose one album with linked entry media, preserving source links and captions.
- [ ] Show the wine's first three eligible photo highlights with View all, deduplication, correct dates and no other wine's entry-only photos.

Verification: the cases in `docs/data-model.md`, mobile gallery navigation and empty/failed-image states. Dependencies: P4/P5. Files: API journal/media read queries; web `occasions/`, `my-wines/`, gallery components. Size: medium. Stories: OM-03/04, HB-01 plus UX review 04.

### P7: Add bounded private video

- [ ] Accept common iPhone HEVC/H.264 MOV/MP4 clips within agreed limits; validate actual streams and produce an H.264/AAC MP4 derivative and poster with correct orientation/color.
- [ ] Resume durable processing after interruption; playback and failure/retry work on target iPhone Safari and desktop browsers.

Verification: real-device clips, resource limits, upload/worker failure and quota exhaustion. Dependencies: P5 and media feasibility; no silent video omission from MVP. Files: API media worker/handlers; web media picker/player. Size: medium, with transcoding separated if needed. Stories: OM-02.

### P8: Browse sourced wines and recover identification mistakes

- [ ] Guest catalog search/detail and filters show licensed/curated facts, sources, unknowns and clearly labeled purchase/search links.
- [ ] Selecting a result requires deliberate save/sign-in; manual fallback and private-entry identity correction preserve memories.
- [ ] My Wines search/sort/filter uses private records and consumed dates, independent of catalog browsing.

Verification: public/private separation, two vintages, correction conflicts and browser search flows. Dependencies: P2; D3 for real provider data. Files: API `catalog/` browse queries and `journal/` correction; web `browse/`, `my-wines/`, capture. Size: split catalog, private search and correction. Stories: WC-01/02/04/05/06, WD-04, HB-03/06.

### P9: Barcode capture

- [ ] Read supported codes on real target phones, open resolved details, and request only unresolved vintage/identity information.
- [ ] Camera denial, unreadable/unknown code, provider failure and spend limits lead to preserved text/manual fallback.

Verification: D2 evaluation set, provider contract tests and physical iPhone camera. Dependencies: P8 and D3. Files: API `identification/`, provider adapter; web `capture/`. Size: medium. Stories: WI-01/03/04.

### P10: Label photo recognition

- [ ] Offer direct capture/upload with bounded processing and selectable candidates; preserve provenance and unknown fields.
- [ ] Guest usage is limited, images are temporary, and timeout/no match leaves manual entry available.

Verification: D2 measured candidates/vintage accuracy, timeout/cost controls and physical-device uploads. Dependencies: P8 and D3; reuse P9's candidate UI where useful. Files: API identification/provider module; web capture. Size: medium. Stories: WI-02/03/04.

### P11: Official places

- [ ] Search/disambiguate official places in entry and occasion forms with permitted attribution and stored fields.
- [ ] Custom labels remain independent; editing a selected label clears a stale association and a failed search does not block save.

Verification: provider terms/quotas plus custom/official/failure form paths. Dependencies: P4 and Places feasibility. Files: API journal place routes and `integrations/places.py`; shared web place field. Size: medium. Stories: TJ-11.

### P12: Beginner guidance and private profile

- [ ] Publish a small sourced guide collection and optional entry prompts without making expert fields mandatory.
- [ ] Show private preference summaries with counts from distinct current release ratings; distinguish often tried from liked and keep unknown metadata honest.

Verification: editorial/source review, guide navigation, summary fixtures including sparse data and rating revisions. Dependencies: P3/P8. Files: web `guides/`, content and note fields; API `journal/` profile queries; web profile. Size: split guides/prompts from private profile. Stories: WG-01, TJ-07, TP-01; TP-02 remains optional pending preference semantics.

### P13: Export, deletion and portfolio readiness

- [ ] Export journal data and owned media; delete an account through resumable cleanup with documented backup expiry.
- [ ] Verify restore, deployment rollback, secret isolation, accessibility, gallery performance and real phone capture.
- [ ] Document demo-data provenance, measured provider limits, architecture tradeoffs and operating cost; test the full journey with another account.

Verification: restore a seeded journal with media into a separate local environment; end-to-end and privacy checks; inspect mobile UX. Dependencies: preceding MVP slices. Files: account/media jobs, UI account controls, deployment/backup scripts and documentation. Size: separate export, deletion, operations and final review tasks. Stories: AC-04 and cross-cutting MVP quality.

**Checkpoint: private portfolio MVP.** Both identification paths, bounded video and privacy must be implemented or explicitly renegotiated; a mocked path is labeled. Basic browse/guide breadth follows review. No public posting is included.

**Later checkpoint: public/collaboration phase.** Define publication and aggregate ratings, moderation, shared-occasion membership/contribution permissions and public rendering before implementation. Calendar, similarity/trending and iOS are separate follow-on slices; do not create their tables or services now.
