from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.database import database_session
from wine_journal.core.errors import ErrorResponse
from wine_journal.journal import queries
from wine_journal.journal.deletion import delete_entry
from wine_journal.journal.edits import edit_entry, read_entry
from wine_journal.journal.schemas import (
    DeletedEntry,
    EditEntry,
    EntryPage,
    EntryResponse,
    SaveEntry,
    WinePage,
    WineResponse,
)
from wine_journal.journal.service import save_entry
from wine_journal.journal.wine_filters import RatingFilter, VintageFilter, WineFilters, WineSort

router = APIRouter(
    tags=["journal"],
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 500, 503)},
)


@router.delete("/entries/{entry_id}", response_model=DeletedEntry)
def remove_entry(
    entry_id: UUID,
    version: Annotated[int, Query(ge=1)],
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> DeletedEntry:
    response.headers["Cache-Control"] = "no-store"
    return DeletedEntry(id=delete_entry(session, principal, entry_id, version))


@router.get("/entries/{entry_id}", response_model=EntryResponse)
def entry_details(
    entry_id: UUID,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> EntryResponse:
    response.headers["Cache-Control"] = "no-store"
    return EntryResponse.model_validate(
        read_entry(session, read_account(session, principal).id, entry_id)
    )


@router.patch("/entries/{entry_id}", response_model=EntryResponse)
def update_entry(
    entry_id: UUID,
    body: EditEntry,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> EntryResponse:
    response.headers["Cache-Control"] = "no-store"
    return edit_entry(session, principal, entry_id, body)


@router.post("/entries", response_model=EntryResponse)
def create_entry(
    body: SaveEntry,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    idempotency_key: Annotated[UUID, Header()],
    response: Response,
) -> EntryResponse:
    response.headers["Cache-Control"] = "no-store"
    return save_entry(session, principal, idempotency_key, body)


@router.get("/me/wines", response_model=WinePage)
def wines(
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
    q: Annotated[str, Query(max_length=200, pattern=r"^[^\x00]*$")] = "",
    sort: WineSort = "LAST_CONSUMED",
    rating: RatingFilter = "ALL",
    vintage: VintageFilter = "ALL",
) -> WinePage:
    response.headers["Cache-Control"] = "no-store"
    return queries.list_wines(
        session,
        read_account(session, principal).id,
        limit,
        cursor,
        WineFilters(q=q, sort=sort, rating=rating, vintage=vintage),
    )


@router.get("/me/wines/{wine_id}", response_model=WineResponse)
def wine(
    wine_id: UUID,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> WineResponse:
    response.headers["Cache-Control"] = "no-store"
    return queries.read_wine(session, read_account(session, principal).id, wine_id)


@router.get("/me/wines/{wine_id}/entries", response_model=EntryPage)
def entries(
    wine_id: UUID,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> EntryPage:
    response.headers["Cache-Control"] = "no-store"
    return queries.list_entries(
        session, read_account(session, principal).id, wine_id, limit, cursor
    )
