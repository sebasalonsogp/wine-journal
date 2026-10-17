"""Entry references are separate from both journal saves and upload processing."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.models import DrinkingEntry
from wine_journal.media.models import EntryPhoto, UploadAsset
from wine_journal.media.schemas import EditPhotoCaption, EntryPhotoResponse, EntryPhotos
from wine_journal.media.uploads import locked_account, owned_asset

MAX_ENTRY_PHOTOS = 12


def require_entry(session: Session, owner: UUID, entry_id: UUID, *, lock: bool = False) -> None:
    query = select(DrinkingEntry.id).where(
        DrinkingEntry.owner_id == owner, DrinkingEntry.id == entry_id
    )
    # Serialize with entry deletion; every attachment mutation locks account, then entry.
    if lock:
        query = query.with_for_update()
    if session.scalar(query) is None:
        raise ApiError(404, "ENTRY_NOT_FOUND", "This entry is unavailable.")


def response(photo: EntryPhoto, asset: UploadAsset) -> EntryPhotoResponse:
    return EntryPhotoResponse.model_validate(
        {
            "entry_id": photo.entry_id,
            "asset_id": asset.id,
            "caption": photo.caption,
            "version": photo.version,
            "state": asset.state,
            "error_code": "PHOTO_PROCESSING_FAILED" if asset.state == "FAILED" else None,
            "width": asset.width if asset.state == "READY" else None,
            "height": asset.height if asset.state == "READY" else None,
        }
    )


def list_photos(session: Session, principal: Principal, entry_id: UUID) -> EntryPhotos:
    with session.begin():
        owner = read_account(session, principal).id
        require_entry(session, owner, entry_id)
        rows = session.execute(
            select(EntryPhoto, UploadAsset)
            .join(
                UploadAsset,
                (UploadAsset.id == EntryPhoto.asset_id) & (UploadAsset.owner_id == owner),
            )
            .where(
                EntryPhoto.owner_id == owner, EntryPhoto.entry_id == entry_id, ~EntryPhoto.removed
            )
            .order_by(EntryPhoto.created_at, EntryPhoto.asset_id)
            .limit(MAX_ENTRY_PHOTOS)
        )
        return EntryPhotos(items=[response(photo, asset) for photo, asset in rows])


def find_photo(session: Session, owner: UUID, entry_id: UUID, asset_id: UUID) -> EntryPhoto | None:
    return session.scalar(
        select(EntryPhoto)
        .where(
            EntryPhoto.owner_id == owner,
            EntryPhoto.entry_id == entry_id,
            EntryPhoto.asset_id == asset_id,
        )
        .execution_options(populate_existing=True)
    )


def attach_photo(
    session: Session, principal: Principal, entry_id: UUID, asset_id: UUID
) -> EntryPhotoResponse:
    with locked_account(session, principal) as owner:
        require_entry(session, owner, entry_id, lock=True)
        asset = owned_asset(session, owner, asset_id)
        photo = find_photo(session, owner, entry_id, asset_id)
        if photo is not None and photo.removed:
            raise ApiError(409, "PHOTO_REMOVED", "This photo was removed from the entry.")
        if photo is None:
            count = session.scalar(
                select(func.count())
                .select_from(EntryPhoto)
                .where(
                    EntryPhoto.owner_id == owner,
                    EntryPhoto.entry_id == entry_id,
                    ~EntryPhoto.removed,
                )
            )
            if count is not None and count >= MAX_ENTRY_PHOTOS:
                raise ApiError(409, "ENTRY_PHOTO_LIMIT", "This entry already has 12 photos.")
            photo = EntryPhoto(owner_id=owner, entry_id=entry_id, asset_id=asset_id)
            session.add(photo)
            session.flush()
        return response(photo, asset)


def edit_caption(
    session: Session, principal: Principal, entry_id: UUID, asset_id: UUID, body: EditPhotoCaption
) -> EntryPhotoResponse:
    caption = (body.caption.strip() or None) if body.caption is not None else None
    with locked_account(session, principal) as owner:
        require_entry(session, owner, entry_id, lock=True)
        asset = owned_asset(session, owner, asset_id)
        photo = find_photo(session, owner, entry_id, asset_id)
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
    session: Session, principal: Principal, entry_id: UUID, asset_id: UUID, version: int
) -> None:
    with locked_account(session, principal) as owner:
        require_entry(session, owner, entry_id, lock=True)
        photo = find_photo(session, owner, entry_id, asset_id)
        if photo is None:
            raise ApiError(404, "PHOTO_NOT_FOUND", "This photo is unavailable.")
        if photo.removed:
            return
        if photo.version != version:
            raise ApiError(409, "PHOTO_CONFLICT", "This photo changed. Reload before removing.")
        photo.removed = True
        photo.caption = None
        photo.version += 1
