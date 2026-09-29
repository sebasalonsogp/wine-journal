from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.database import database_session
from wine_journal.core.errors import ErrorResponse
from wine_journal.journal.rating_schemas import RatingChange, RatingHistory, RatingState
from wine_journal.journal.ratings import change_rating, rating_history

router = APIRouter(
    tags=["journal"],
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 500, 503)},
)


@router.put("/me/wines/{wine_id}/rating", response_model=RatingState)
def update_rating(
    wine_id: UUID,
    body: RatingChange,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> RatingState:
    response.headers["Cache-Control"] = "no-store"
    return change_rating(session, principal, wine_id, body.version, body.score)


@router.get("/me/wines/{wine_id}/rating-history", response_model=RatingHistory)
def history(
    wine_id: UUID,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    before_version: Annotated[int | None, Query(alias="beforeVersion", ge=1)] = None,
) -> RatingHistory:
    response.headers["Cache-Control"] = "no-store"
    return rating_history(
        session, read_account(session, principal).id, wine_id, limit, before_version
    )


@router.delete("/me/wines/{wine_id}/rating-history", response_model=RatingState)
def erase_rating_history(
    wine_id: UUID,
    version: Annotated[int, Query(ge=0)],
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> RatingState:
    response.headers["Cache-Control"] = "no-store"
    return change_rating(session, principal, wine_id, version, None, erase_history=True)
