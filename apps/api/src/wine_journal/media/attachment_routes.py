from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.database import database_session
from wine_journal.core.errors import ErrorResponse
from wine_journal.media.attachments import attach_photo, edit_caption, list_photos, remove_photo
from wine_journal.media.schemas import (
    AttachPhoto,
    EditPhotoCaption,
    EntryPhotoResponse,
    EntryPhotos,
    RemovedPhoto,
)

router = APIRouter(
    prefix="/entries/{entry_id}/photos",
    tags=["media"],
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 500, 503)},
)
Identity = Annotated[Principal, Depends(require_principal)]
Database = Annotated[Session, Depends(database_session)]


@router.get("", response_model=EntryPhotos, operation_id="list_entry_photos")
def list_entry_photos(
    entry_id: UUID, principal: Identity, session: Database, response: Response
) -> EntryPhotos:
    response.headers["Cache-Control"] = "no-store"
    return list_photos(session, principal, entry_id)


@router.put("/{asset_id}", response_model=EntryPhotoResponse, operation_id="attach_entry_photo")
def attach_entry_photo(
    entry_id: UUID,
    asset_id: UUID,
    body: AttachPhoto,
    principal: Identity,
    session: Database,
    response: Response,
) -> EntryPhotoResponse:
    response.headers["Cache-Control"] = "no-store"
    return attach_photo(session, principal, entry_id, asset_id)


@router.patch("/{asset_id}", response_model=EntryPhotoResponse, operation_id="edit_entry_photo")
def edit_entry_photo(
    entry_id: UUID,
    asset_id: UUID,
    body: EditPhotoCaption,
    principal: Identity,
    session: Database,
    response: Response,
) -> EntryPhotoResponse:
    response.headers["Cache-Control"] = "no-store"
    return edit_caption(session, principal, entry_id, asset_id, body)


@router.delete("/{asset_id}", response_model=RemovedPhoto, operation_id="remove_entry_photo")
def remove_entry_photo(
    entry_id: UUID,
    asset_id: UUID,
    principal: Identity,
    session: Database,
    response: Response,
    version: Annotated[int, Query(ge=1)],
) -> RemovedPhoto:
    response.headers["Cache-Control"] = "no-store"
    remove_photo(session, principal, entry_id, asset_id, version)
    return RemovedPhoto(asset_id=asset_id)
