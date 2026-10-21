"""Personal artwork never implicitly becomes an entry or album memory."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy.orm import Session

from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.ratings import owned_wine
from wine_journal.media.uploads import locked_account
from wine_journal.media.viewing import ready_asset


class CoverState(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    asset_id: UUID | None
    version: int


class ChangeCover(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel)
    asset_id: UUID | None
    version: int = Field(strict=True, ge=0)


def change_cover(
    session: Session, principal: Principal, wine_id: UUID, body: ChangeCover
) -> CoverState:
    with locked_account(session, principal) as owner:
        wine = owned_wine(session, owner, wine_id, lock=True)
        if body.asset_id is not None:
            ready_asset(session, owner, body.asset_id)
        # Reconcile a lost response only while this is still the immediately applied change.
        if wine.cover_version == body.version + 1 and wine.cover_asset_id == body.asset_id:
            return CoverState(asset_id=wine.cover_asset_id, version=wine.cover_version)
        if wine.cover_version != body.version:
            raise ApiError(409, "COVER_CONFLICT", "Your cover changed. Review it before replacing.")
        if wine.cover_asset_id != body.asset_id:
            wine.cover_asset_id = body.asset_id
            wine.cover_version += 1
        return CoverState(asset_id=wine.cover_asset_id, version=wine.cover_version)
