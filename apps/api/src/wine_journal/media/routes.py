from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session

from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.database import database_session
from wine_journal.core.errors import ApiError, ErrorResponse
from wine_journal.integrations.storage import Storage
from wine_journal.media.schemas import CompleteUpload, UploadCompletion, UploadGrant, UploadRequest
from wine_journal.media.uploads import complete_upload, initiate_upload

router = APIRouter(
    prefix="/media",
    tags=["media"],
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 500, 503)},
)


def private_storage(request: Request) -> Storage:
    storage = request.app.state.storage
    if not isinstance(storage, Storage):
        raise ApiError(503, "MEDIA_UNAVAILABLE", "Photo uploads are not available yet.")
    return storage


@router.post("/uploads", response_model=UploadGrant)
def upload(
    body: UploadRequest,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    storage: Annotated[Storage, Depends(private_storage)],
    operation: Annotated[UUID, Header(alias="Idempotency-Key")],
    response: Response,
) -> UploadGrant:
    response.headers["Cache-Control"] = "no-store"
    return initiate_upload(session, principal, operation, body, storage)


@router.post("/{asset_id}/complete", response_model=UploadCompletion)
def complete(
    asset_id: UUID,
    body: CompleteUpload,
    principal: Annotated[Principal, Depends(require_principal)],
    session: Annotated[Session, Depends(database_session)],
    storage: Annotated[Storage, Depends(private_storage)],
    response: Response,
) -> UploadCompletion:
    response.headers["Cache-Control"] = "no-store"
    return complete_upload(session, principal, asset_id, storage)
