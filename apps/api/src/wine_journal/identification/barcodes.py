"""Bounded, read-only lookup over curated public evidence. No provider requests."""

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from wine_journal.catalog.barcode_importer import BarcodeRow
from wine_journal.catalog.models import CatalogBarcodeObservation, CatalogDefinition, CatalogRelease
from wine_journal.catalog.queries import details, public_wine
from wine_journal.catalog.schemas import CatalogDetails, CatalogReference
from wine_journal.core.errors import ApiError
from wine_journal.identification.schemas import BarcodeCandidate, BarcodeConfirmation, BarcodeLookup

MAX_OBSERVATIONS = 100
MAX_OFFERINGS = 10
MAX_RELEASES = 240


def lookup(session: Session, gtin: str) -> BarcodeLookup:
    # Evidence, release options and confirmation details use one consistent snapshot.
    session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    session.execute(text("SET LOCAL statement_timeout = '3s'"))
    rows = session.execute(
        select(CatalogBarcodeObservation, CatalogDefinition)
        .join(CatalogDefinition, CatalogDefinition.id == CatalogBarcodeObservation.definition_id)
        .where(CatalogBarcodeObservation.gtin == gtin)
        .order_by(CatalogDefinition.id, CatalogBarcodeObservation.id)
        .limit(MAX_OBSERVATIONS + 1)
    ).all()
    overflow = BarcodeLookup(gtin=gtin, status="TOO_MANY_MATCHES", candidates=[])
    if len(rows) > MAX_OBSERVATIONS:
        return overflow
    candidates: dict[UUID, BarcodeCandidate] = {}
    for evidence, definition in rows:
        # Revalidate stored source data before exposing or relying on the association.
        try:
            BarcodeRow.model_validate(
                {
                    "gtin": evidence.gtin,
                    "definition_key": definition.key,
                    "producer": definition.producer,
                    "wine_name": definition.name,
                    "bottle_ml": evidence.bottle_ml,
                    "source_url": evidence.url,
                    "retrieved_on": evidence.retrieved_on,
                    "market": evidence.market,
                    "evidence_status": evidence.evidence_status,
                    "source_sha256": evidence.source_sha256,
                }
            )
        except ValueError:
            continue
        candidate = candidates.setdefault(
            definition.id,
            BarcodeCandidate(
                definition_id=definition.id,
                name=definition.name,
                producer=definition.producer,
                bottle_sizes_ml=[],
                sources=[],
                releases=[],
            ),
        )
        if evidence.bottle_ml not in candidate.bottle_sizes_ml:
            candidate.bottle_sizes_ml.append(evidence.bottle_ml)
        source = CatalogReference(url=evidence.url, retrieved_on=evidence.retrieved_on)
        if source not in candidate.sources:
            candidate.sources.append(source)
    if len(candidates) > MAX_OFFERINGS:
        return overflow
    if candidates:
        releases = session.scalars(
            select(CatalogRelease)
            .where(CatalogRelease.definition_id.in_(candidates))
            .order_by(
                CatalogRelease.year.desc().nulls_last(),
                CatalogRelease.edition.asc().nulls_last(),
                CatalogRelease.id,
            )
            .limit(MAX_RELEASES + 1)
        ).all()
        if len(releases) > MAX_RELEASES:
            return overflow
        definitions = {definition.id: definition for _, definition in rows}
        for release in releases:
            candidates[release.definition_id].releases.append(
                public_wine(definitions[release.definition_id], release)
            )
    items = sorted(
        candidates.values(),
        key=lambda c: (c.producer.casefold(), c.name.casefold(), c.definition_id),
    )
    for item in items:
        item.bottle_sizes_ml.sort()
        item.sources.sort(key=lambda s: (s.url, s.retrieved_on))
    return BarcodeLookup(
        gtin=gtin, status="NEEDS_CONFIRMATION" if items else "NOT_FOUND", candidates=items
    )


def confirm(session: Session, choice: BarcodeConfirmation) -> CatalogDetails:
    result = lookup(session, choice.gtin)
    selected = next(
        (
            release
            for candidate in result.candidates
            for release in candidate.releases
            if release.id == choice.catalog_release_id
        ),
        None,
    )
    if selected is None or (selected.vintage_status, selected.year, selected.edition) != (
        choice.vintage_status,
        choice.year,
        choice.edition,
    ):
        raise ApiError(
            409,
            "BARCODE_SELECTION_CHANGED",
            "Look up the barcode again and confirm the wine and vintage.",
        )
    return details(session, selected.id)
