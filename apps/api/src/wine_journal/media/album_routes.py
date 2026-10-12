from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.database import database_session
from wine_journal.core.errors import ErrorResponse
from wine_journal.media.album import AlbumPage, AlbumSources, album_page, album_sources

router = APIRouter(
    prefix="/occasions/{occasion_id}/album",
    tags=["media"],
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 422, 500, 503)},
)
Identity = Annotated[Principal, Depends(require_principal)]
Database = Annotated[Session, Depends(database_session)]


@router.get("", response_model=AlbumPage, operation_id="read_occasion_album")
def read_occasion_album(
    occasion_id: UUID,
    principal: Identity,
    session: Database,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> AlbumPage:
    response.headers["Cache-Control"] = "no-store"
    return album_page(session, principal, occasion_id, limit, cursor)


@router.get("/{asset_id}/sources", response_model=AlbumSources, operation_id="read_album_sources")
def read_album_sources(
    occasion_id: UUID,
    asset_id: UUID,
    principal: Identity,
    session: Database,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000000)] = 0,
) -> AlbumSources:
    response.headers["Cache-Control"] = "no-store"
    return album_sources(session, principal, occasion_id, asset_id, limit, offset)
