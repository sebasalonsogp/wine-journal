from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session, sessionmaker

from wine_journal.accounts import service
from wine_journal.accounts.schemas import AccountResponse, BootstrapAccount
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.errors import ApiError, ErrorResponse

router = APIRouter(
    tags=["accounts"],
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 422, 500, 503)},
)


def database_session(request: Request) -> Iterator[Session]:
    factory: sessionmaker[Session] | None = request.app.state.session_factory
    if factory is None:
        raise ApiError(503, "DATABASE_UNAVAILABLE", "The journal is not configured.")
    with factory() as session:
        yield session


@router.post("/me", response_model=AccountResponse)
def bootstrap(
    body: BootstrapAccount,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> AccountResponse:
    response.headers["Cache-Control"] = "no-store"
    return AccountResponse.model_validate(service.bootstrap_account(session, principal))


@router.get("/me", response_model=AccountResponse)
def read_me(
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> AccountResponse:
    response.headers["Cache-Control"] = "no-store"
    return AccountResponse.model_validate(service.read_account(session, principal))
