from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from wine_journal.catalog import queries
from wine_journal.catalog.schemas import CatalogDetails, CatalogPage
from wine_journal.core.database import database_session
from wine_journal.core.errors import ErrorResponse

router = APIRouter(
    prefix="/catalog/wines",
    tags=["catalog"],
    responses={status: {"model": ErrorResponse} for status in (404, 422, 500, 503)},
)


@router.get("", response_model=CatalogPage)
def browse_wines(
    session: Annotated[Session, Depends(database_session)],
    response: Response,
    q: Annotated[str, Query(max_length=200, pattern=r"^[^\x00-\x1f\x7f]*$")] = "",
    limit: Annotated[int, Query(ge=1, le=48)] = 24,
    offset: Annotated[int, Query(ge=0, le=queries.MAX_OFFSET)] = 0,
) -> CatalogPage:
    response.headers["Cache-Control"] = "no-store"
    return queries.browse(session, q=q, limit=limit, offset=offset)


@router.get("/{release_id}", response_model=CatalogDetails)
def wine_details(
    release_id: UUID,
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> CatalogDetails:
    response.headers["Cache-Control"] = "no-store"
    return queries.details(session, release_id)
