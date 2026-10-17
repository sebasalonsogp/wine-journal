from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.database import database_session
from wine_journal.core.errors import ErrorResponse
from wine_journal.media.wine_moments import WineMoments, wine_moments

router = APIRouter(
    prefix="/me/wines/{wine_id}/moments",
    tags=["media"],
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 422, 500, 503)},
)


@router.get("", response_model=WineMoments, operation_id="read_wine_moments")
def read_wine_moments(
    wine_id: UUID,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> WineMoments:
    response.headers["Cache-Control"] = "no-store"
    return wine_moments(session, principal, wine_id, limit, cursor)
