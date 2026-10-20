"""Correct shared manual facts without merging records or changing their IDs."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.catalog.models import WineDefinition, WineRelease
from wine_journal.catalog.schemas import ManualWine
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.queries import read_wine
from wine_journal.journal.ratings import owned_wine
from wine_journal.journal.schemas import WineResponse


class EditWineIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=0, strict=True)
    wine: ManualWine


def edit_wine_identity(
    session: Session, principal: Principal, wine_id: UUID, body: EditWineIdentity
) -> WineResponse:
    try:
        with session.begin():
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            owner = read_account(session, principal).id
            wine = owned_wine(session, owner, wine_id)
            release, definition = session.execute(
                select(WineRelease, WineDefinition)
                .join(WineDefinition, WineRelease.definition_id == WineDefinition.id)
                .where(WineRelease.id == wine.release_id, WineRelease.owner_id == owner)
                .with_for_update()
            ).one()
            # Definitions are currently created per private release. Guard the
            # boundary if a future importer starts sharing them across releases.
            siblings = session.scalar(
                select(func.count())
                .select_from(WineRelease)
                .where(WineRelease.owner_id == owner, WineRelease.definition_id == definition.id)
            )
            if release.catalog_release_id is not None or siblings != 1:
                raise ApiError(
                    409, "IDENTITY_PROTECTED", "These wine details cannot be edited here."
                )
            if release.identity_version != body.version:
                raise ApiError(
                    409, "IDENTITY_CONFLICT", "This wine changed. Review its saved details."
                )
            definition.name = body.wine.name
            definition.producer = body.wine.producer
            release.vintage_status = body.wine.vintage_status
            release.year = body.wine.year
            release.edition = body.wine.edition
            release.identity_version += 1
            session.flush()
            return read_wine(session, owner, wine_id)
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) == "55P03":
            raise ApiError(
                409, "IDENTITY_BUSY", "Another change is saving. Review and retry."
            ) from None
        raise
