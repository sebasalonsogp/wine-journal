from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.database import database_session
from wine_journal.core.errors import ErrorResponse
from wine_journal.media.covers import ChangeCover, CoverState, change_cover

router = APIRouter(
    tags=["media"],
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 500, 503)},
)


@router.put(
    "/me/wines/{wine_id}/cover", response_model=CoverState, operation_id="change_wine_cover"
)
def change_wine_cover(
    wine_id: UUID,
    body: ChangeCover,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> CoverState:
    response.headers["Cache-Control"] = "no-store"
    return change_cover(session, principal, wine_id, body)
