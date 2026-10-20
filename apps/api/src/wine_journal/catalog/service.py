from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from wine_journal.catalog.models import (
    CatalogDefinition,
    CatalogRelease,
    WineDefinition,
    WineRelease,
)
from wine_journal.catalog.schemas import ManualWine
from wine_journal.core.errors import ApiError


def create_manual_release(session: Session, owner_id: UUID, wine: ManualWine) -> WineRelease:
    """Called inside the journal transaction; never publishes or merges a label."""
    definition = WineDefinition(owner_id=owner_id, name=wine.name, producer=wine.producer)
    session.add(definition)
    session.flush()
    release = WineRelease(
        owner_id=owner_id,
        definition_id=definition.id,
        vintage_status=wine.vintage_status,
        year=wine.year,
        edition=wine.edition,
    )
    session.add(release)
    session.flush()
    return release


def read_owned_release(session: Session, owner_id: UUID, release_id: UUID) -> WineRelease:
    release = session.scalar(
        select(WineRelease).where(WineRelease.id == release_id, WineRelease.owner_id == owner_id)
    )
    if release is None:
        raise ApiError(404, "WINE_NOT_FOUND", "This wine is unavailable.")
    return release


def capture_catalog_release(
    session: Session, owner_id: UUID, catalog_release_id: UUID
) -> WineRelease:
    """Caller holds the account lock, before occasion/wine locks, in its save transaction."""
    existing = session.scalar(
        select(WineRelease).where(
            WineRelease.owner_id == owner_id,
            WineRelease.catalog_release_id == catalog_release_id,
        )
    )
    if existing is not None:
        return existing
    row = session.execute(
        select(CatalogDefinition, CatalogRelease)
        .join(CatalogRelease, CatalogRelease.definition_id == CatalogDefinition.id)
        .where(CatalogRelease.id == catalog_release_id)
    ).one_or_none()
    if row is None:
        raise ApiError(404, "CATALOG_WINE_NOT_FOUND", "This wine is no longer in the catalog.")
    definition, release = row
    # A snapshot preserves the journal if catalog facts later change. No name-based merge.
    owned_definition = WineDefinition(
        owner_id=owner_id, name=definition.name, producer=definition.producer
    )
    session.add(owned_definition)
    session.flush()
    # Link at INSERT time: runtime permissions intentionally forbid identity UPDATEs.
    owned = WineRelease(
        owner_id=owner_id,
        definition_id=owned_definition.id,
        catalog_release_id=catalog_release_id,
        vintage_status=release.vintage_status,
        year=release.year,
        edition=release.edition,
    )
    session.add(owned)
    session.flush()
    return owned
