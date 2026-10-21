# ADR 0007: Keep reviewed public wine data separate from private identities

Date: October 19, 2026. Status: accepted implementation decision for C01.

## Context

Manual journal identities already require an owner and participate in composite ownership foreign keys. The original logical model proposed nullable ownership to distinguish shared catalog rows. That would weaken an established privacy boundary and complicate every existing journal query. We now have a small reviewed identity dataset, but no verified barcode/image coverage, prices, artwork or retail market.

## Decision

Add `catalog_definitions`, `catalog_releases` and `catalog_sources` in the existing catalog module and Postgres `app` schema. Preserve every private table, owner constraint and capture endpoint. Public catalog rows are reviewed wine facts, never a serialization of a private wine, drinking entry or memory. This supersedes the nullable-owner proposal in the logical model, without adding a service or database.

Catalog rows have UUID primary keys. A curator-controlled definition key provides repeatable imports; it is not a barcode or an identity inferred from a name. Releases are unique by definition, vintage status, year and optional edition. PostgreSQL's `NULLS NOT DISTINCT` uniqueness prevents absent years/editions from allowing duplicate releases. Keep UNKNOWN observations private; known non-vintage and multi-vintage references retain null years. [SQLAlchemy PostgreSQL support](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html), [PostgreSQL constraints](https://www.postgresql.org/docs/17/ddl-constraints.html).

The initial importer accepts the reviewed R01a CSV format only, with 1 MiB/1,000-row bounds and full-batch validation. It never fetches a URL or selects a provider. Conflicting producer/name values for a stored definition key reject the batch; no implicit rename, merge, delete or overwrite occurs. Source URL and retrieval date are retained per release; new source observations append without replacing earlier evidence. Market and evidence markers currently admit only UNVERIFIED and SOURCE_ONLY. Add richer facts and their provenance when they are actually sourced.

The command defaults to preview and requires `--apply` to write. It uses the existing offline `wine_migrator` configuration; the running API never receives that credential. Grant `wine_api` SELECT only. Supabase client roles remain unable to access the schema. A separate importer role is unnecessary for this manually operated portfolio dataset; reconsider before scheduling imports or delegating them to another operator.

One transaction locks the three catalog tables in SHARE ROW EXCLUSIVE mode before comparing/inserting. This serializes rare imports and concurrent administrative writes while allowing ordinary SELECTs. Five-second lock and ten-second statement timeouts fail rather than wait indefinitely. The preview takes the same locks to obtain a consistent plan but issues no inserts. PostgreSQL constraints remain the last defense against duplicates. [PostgreSQL locking](https://www.postgresql.org/docs/17/explicit-locking.html).

## Consequences

The importer can be retried without duplicating data, and a later write failure rolls back definitions, releases and sources together. Empty-schema migration rollback is supported; populated catalog downgrade is refused. Roll back application code while retaining the additive schema.

Separate public and private representations introduce an explicit translation/linking step for future catalog-to-journal capture. C02 must implement that deliberately; a public UUID cannot currently be passed as a private release ID. No guest catalog endpoint or publishing endpoint is added by C01. Public reviews, provider mappings, barcode ambiguity, metadata enrichment and catalog corrections remain separate work. Structured validation does not prove a source is accurate: review the source before an operator applies a manifest.

## C02 implementation follow-up — October 20, 2026

C02a adds anonymous read-only search and detail endpoints. C02b adds the explicit
`catalogReleaseId` entry input and nullable `wine_releases.catalog_release_id`
foreign key, with unique owner/catalog-release pairs. The first save snapshots
public facts into private owner-scoped rows; repeats reuse those rows under an
account lock acquired before occasion/wine locks. No global/private owner
constraint is relaxed. Manual wines retain NULL links and are never merged by
name. Catalog edits do not silently change existing journal snapshots.

Identity links are written at INSERT time using existing runtime grants.
Release UPDATE remains denied; public catalog tables remain SELECT-only to the
API role. This is not a public publishing capability. Migration 0023 refuses a
downgrade that would discard links. Guest drafts retain only a public release
selection plus user-entered context, and an explicit authenticated save remains
necessary before creating journal rows.
