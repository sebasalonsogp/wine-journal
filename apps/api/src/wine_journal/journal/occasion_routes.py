from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.database import database_session
from wine_journal.core.errors import ErrorResponse
from wine_journal.journal import occasions
from wine_journal.journal.occasion_batch import CreateOccasion, OccasionWines
from wine_journal.journal.occasion_schemas import (
    EditOccasion,
    OccasionPage,
    OccasionResponse,
)
from wine_journal.journal.occasion_wines import list_occasion_wines
from wine_journal.journal.schemas import WinePage

router = APIRouter(
    tags=["journal"],
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 500, 503)},
)


@router.post("/occasions", response_model=OccasionResponse)
def create(
    body: CreateOccasion,
    idempotency_key: Annotated[UUID, Header()],
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> OccasionResponse:
    response.headers["Cache-Control"] = "no-store"
    return occasions.create_occasion(session, principal, idempotency_key, body)


@router.post("/occasions/{occasion_id}/wines", response_model=OccasionResponse)
def add_wines(
    occasion_id: UUID,
    body: OccasionWines,
    idempotency_key: Annotated[UUID, Header()],
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> OccasionResponse:
    response.headers["Cache-Control"] = "no-store"
    return occasions.save_occasion_wines(session, principal, idempotency_key, body, occasion_id)


@router.get("/occasions/{occasion_id}/wines", response_model=WinePage)
def wines(
    occasion_id: UUID,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> WinePage:
    response.headers["Cache-Control"] = "no-store"
    return list_occasion_wines(
        session, read_account(session, principal).id, occasion_id, limit, cursor
    )


@router.get("/occasions", response_model=OccasionPage)
def listing(
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> OccasionPage:
    response.headers["Cache-Control"] = "no-store"
    return occasions.list_occasions(session, read_account(session, principal).id, limit, cursor)


@router.get("/occasions/{occasion_id}", response_model=OccasionResponse)
def detail(
    occasion_id: UUID,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> OccasionResponse:
    response.headers["Cache-Control"] = "no-store"
    return OccasionResponse.model_validate(
        occasions.read_occasion(session, read_account(session, principal).id, occasion_id)
    )


@router.put("/occasions/{occasion_id}", response_model=OccasionResponse)
def edit(
    occasion_id: UUID,
    body: EditOccasion,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> OccasionResponse:
    response.headers["Cache-Control"] = "no-store"
    return occasions.edit_occasion(session, principal, occasion_id, body)
