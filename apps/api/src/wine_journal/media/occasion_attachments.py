"""Occasion references are separate from both journal saves and upload processing."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.models import Occasion
from wine_journal.media.models import OccasionPhoto, UploadAsset
from wine_journal.media.schemas import EditPhotoCaption, OccasionPhotoResponse, OccasionPhotos
from wine_journal.media.uploads import locked_account, owned_asset

MAX_OCCASION_PHOTOS = 24


def require_occasion(
    session: Session, owner: UUID, occasion_id: UUID, *, lock: bool = False
) -> None:
    query = select(Occasion.id).where(Occasion.owner_id == owner, Occasion.id == occasion_id)
    # Serialize with occasion deletion; every attachment mutation locks account, then occasion.
    if lock:
        query = query.with_for_update()
    if session.scalar(query) is None:
        raise ApiError(404, "OCCASION_NOT_FOUND", "This occasion is unavailable.")


def response(photo: OccasionPhoto, asset: UploadAsset) -> OccasionPhotoResponse:
    return OccasionPhotoResponse.model_validate(
        {
            "occasion_id": photo.occasion_id,
            "asset_id": asset.id,
            "caption": photo.caption,
            "version": photo.version,
            "state": asset.state,
            "error_code": "PHOTO_PROCESSING_FAILED" if asset.state == "FAILED" else None,
            "width": asset.width if asset.state == "READY" else None,
            "height": asset.height if asset.state == "READY" else None,
        }
    )


def list_photos(session: Session, principal: Principal, occasion_id: UUID) -> OccasionPhotos:
    with session.begin():
        owner = read_account(session, principal).id
        require_occasion(session, owner, occasion_id)
        rows = session.execute(
            select(OccasionPhoto, UploadAsset)
            .join(
                UploadAsset,
                (UploadAsset.id == OccasionPhoto.asset_id) & (UploadAsset.owner_id == owner),
            )
            .where(
                OccasionPhoto.owner_id == owner,
                OccasionPhoto.occasion_id == occasion_id,
                ~OccasionPhoto.removed,
            )
            .order_by(OccasionPhoto.created_at, OccasionPhoto.asset_id)
            .limit(MAX_OCCASION_PHOTOS)
        )
        return OccasionPhotos(items=[response(photo, asset) for photo, asset in rows])


def find_photo(
    session: Session, owner: UUID, occasion_id: UUID, asset_id: UUID
) -> OccasionPhoto | None:
    return session.scalar(
        select(OccasionPhoto)
        .where(
            OccasionPhoto.owner_id == owner,
            OccasionPhoto.occasion_id == occasion_id,
            OccasionPhoto.asset_id == asset_id,
        )
        .execution_options(populate_existing=True)
    )


def attach_photo(
    session: Session, principal: Principal, occasion_id: UUID, asset_id: UUID
) -> OccasionPhotoResponse:
    with locked_account(session, principal) as owner:
        require_occasion(session, owner, occasion_id, lock=True)
        asset = owned_asset(session, owner, asset_id)
        photo = find_photo(session, owner, occasion_id, asset_id)
        if photo is not None and photo.removed:
            raise ApiError(409, "PHOTO_REMOVED", "This photo was removed from the occasion.")
        if photo is None:
            count = session.scalar(
                select(func.count())
                .select_from(OccasionPhoto)
                .where(
                    OccasionPhoto.owner_id == owner,
                    OccasionPhoto.occasion_id == occasion_id,
                    ~OccasionPhoto.removed,
                )
            )
            if count is not None and count >= MAX_OCCASION_PHOTOS:
                raise ApiError(409, "OCCASION_PHOTO_LIMIT", "This occasion already has 24 photos.")
            photo = OccasionPhoto(owner_id=owner, occasion_id=occasion_id, asset_id=asset_id)
            session.add(photo)
            session.flush()
        return response(photo, asset)


def edit_caption(
    session: Session,
    principal: Principal,
    occasion_id: UUID,
    asset_id: UUID,
    body: EditPhotoCaption,
) -> OccasionPhotoResponse:
    caption = (body.caption.strip() or None) if body.caption is not None else None
    with locked_account(session, principal) as owner:
        require_occasion(session, owner, occasion_id, lock=True)
        asset = owned_asset(session, owner, asset_id)
        photo = find_photo(session, owner, occasion_id, asset_id)
        if photo is None or photo.removed:
            raise ApiError(404, "PHOTO_NOT_FOUND", "This photo is unavailable.")
        if photo.version == body.version + 1 and photo.caption == caption:
            return response(photo, asset)
        if photo.version != body.version:
            raise ApiError(409, "PHOTO_CONFLICT", "This photo changed. Reload before editing.")
        photo.caption = caption
        photo.version += 1
        session.flush()
        return response(photo, asset)


def remove_photo(
    session: Session, principal: Principal, occasion_id: UUID, asset_id: UUID, version: int
) -> None:
    with locked_account(session, principal) as owner:
        require_occasion(session, owner, occasion_id, lock=True)
        photo = find_photo(session, owner, occasion_id, asset_id)
        if photo is None:
            raise ApiError(404, "PHOTO_NOT_FOUND", "This photo is unavailable.")
        if photo.removed:
            return
        if photo.version != version:
            raise ApiError(409, "PHOTO_CONFLICT", "This photo changed. Reload before removing.")
        photo.removed = True
        photo.caption = None
        photo.version += 1
