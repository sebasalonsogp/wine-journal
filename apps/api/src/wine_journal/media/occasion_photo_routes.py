from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.database import database_session
from wine_journal.core.errors import ErrorResponse
from wine_journal.media.occasion_attachments import (
    attach_photo,
    edit_caption,
    list_photos,
    remove_photo,
)
from wine_journal.media.schemas import (
    AttachPhoto,
    EditPhotoCaption,
    OccasionPhotoResponse,
    OccasionPhotos,
    RemovedPhoto,
)

router = APIRouter(
    prefix="/occasions/{occasion_id}/photos",
    tags=["media"],
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 500, 503)},
)
Identity = Annotated[Principal, Depends(require_principal)]
Database = Annotated[Session, Depends(database_session)]


@router.get("", response_model=OccasionPhotos, operation_id="list_occasion_photos")
def list_occasion_photos(
    occasion_id: UUID, principal: Identity, session: Database, response: Response
) -> OccasionPhotos:
    response.headers["Cache-Control"] = "no-store"
    return list_photos(session, principal, occasion_id)


@router.put(
    "/{asset_id}", response_model=OccasionPhotoResponse, operation_id="attach_occasion_photo"
)
def attach_occasion_photo(
    occasion_id: UUID,
    asset_id: UUID,
    body: AttachPhoto,
    principal: Identity,
    session: Database,
    response: Response,
) -> OccasionPhotoResponse:
    response.headers["Cache-Control"] = "no-store"
    return attach_photo(session, principal, occasion_id, asset_id)


@router.patch(
    "/{asset_id}", response_model=OccasionPhotoResponse, operation_id="edit_occasion_photo"
)
def edit_occasion_photo(
    occasion_id: UUID,
    asset_id: UUID,
    body: EditPhotoCaption,
    principal: Identity,
    session: Database,
    response: Response,
) -> OccasionPhotoResponse:
    response.headers["Cache-Control"] = "no-store"
    return edit_caption(session, principal, occasion_id, asset_id, body)


@router.delete("/{asset_id}", response_model=RemovedPhoto, operation_id="remove_occasion_photo")
def remove_occasion_photo(
    occasion_id: UUID,
    asset_id: UUID,
    principal: Identity,
    session: Database,
    response: Response,
    version: Annotated[int, Query(ge=1)],
) -> RemovedPhoto:
    response.headers["Cache-Control"] = "no-store"
    remove_photo(session, principal, occasion_id, asset_id, version)
    return RemovedPhoto(asset_id=asset_id)
