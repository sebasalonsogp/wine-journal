# C02b — Catalog selection into a private journal

October 20, 2026.

## Behavior

Guest wine details offer **I tried this wine**. Capture shows the exact vintage
or edition, defaults the date and accepts optional notes and an existing/new
occasion. Sign-in retains the selection and context; it does not save an entry
automatically. Saving creates or reuses that account's wine for the public
release. Different vintages stay separate and matching manually entered names
are not merged.

An unfinished draft is not silently overwritten. Continue it or explicitly
discard it for the new selection; an unconfirmed save must be resumed first.
Owned drafts remain hidden while signed out and are cleared for another account.
A narrowly validated catalog return path preserves the pending public selection
through that sign-in. Malformed or missing selections have recovery links.

## Implementation and invariants

- Migration 0023 adds an optional public-release FK to private releases and
  unique owner/public-release pairs. Existing owner constraints and manual rows
  remain unchanged. The link is inserted once; runtime identity UPDATE stays
  denied. Downgrade refuses to discard populated links.
- SaveEntry requires exactly one manual, owned or public-catalog selection.
  Catalog facts are read on the backend, never trusted from client display data.
  A first capture snapshots facts; later public catalog edits do not rewrite
  that private snapshot.
- Catalog saves take the account lock before occasion/wine locks. Snapshot,
  optional occasion, entry and save receipt commit together. A missing release
  rolls everything back. Concurrent distinct saves reuse one owned wine;
  same-key retries retain one entry. Absent new fields preserve legacy hashes.
- Stored version-1 drafts remain readable. Public catalog input is mutually
  exclusive with private release IDs. No new secret or environment variable,
  external service, dependency or background job is introduced.

The occasion batch composer still selects manual/already-owned wines; direct
catalog selection inside that composer is not added here. The wine-first
catalog flow can create or select an occasion. Personal covers are managed
after saving a catalog wine; entry photos retain the existing upload flow.

## Verification

Local migration 0023 preserved journal/catalog/media row counts, reserved bytes
and unsettled write/grant totals. Every preexisting manual release remained
unlinked. The test runner uses a separate disposable database.

- All 409 API tests passed with disposable Postgres, real local Storage and
  Docker-isolated decoding. New cases cover concurrent capture, retry, rollback,
  owner isolation, separate vintages/manual identities, immutable snapshots,
  database constraints, legacy receipt compatibility and guarded downgrade.
- All 35 frontend unit tests and all 29 browser journeys passed. The three new
  journeys exercise guest sign-in/save/repeat, lost responses, draft choices,
  uncertain saves and account changes. Desktop/390px screenshots were inspected;
  axe found no violations and the phone layout had no horizontal overflow.
- Ruff, formatting, mypy (130 source files), frontend lint/types, production
  build, backend package build and generated API contracts passed. The browser
  secret scan checked 19 scripts without finding generated private values.
- The regression run exposed a cover Retry button briefly visible before an
  initial upload started. Retry now requires an actual error. The existing cover
  journey and all subsequent media journeys pass with CI's one-shot workers.
- The old receipt fixture now freezes the original request bytes instead of
  reconstructing an old payload using today's expanded schema. The compatibility
  assertion and downgrade/upgrade replay remain intact.

The existing full npm development dependency audit blocker is not waived by
this feature: braces GHSA-vfj7-8cjw-p6xm in Next's development lint chain.
The previous head's API/browser CI jobs passed; web failed only at that audit.
The gate remains enabled and the PR remains unmerged.
