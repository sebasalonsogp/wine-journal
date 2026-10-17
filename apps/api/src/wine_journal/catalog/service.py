from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from wine_journal.catalog.models import WineDefinition, WineRelease
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
