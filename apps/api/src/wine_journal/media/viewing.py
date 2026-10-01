"""Owner-only status and ready-derivative capabilities; never expose original files."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.integrations.storage import Storage, StorageError
from wine_journal.media.models import UploadAsset
from wine_journal.media.photo_processing import derivative_keys
from wine_journal.media.schemas import PhotoStatus, PhotoView, PhotoViewRequest
from wine_journal.media.uploads import locked_account, owned_asset


def photo_status(session: Session, principal: Principal, asset_id: UUID) -> PhotoStatus:
    with session.begin():
        account = read_account(session, principal)
        asset = owned_asset(session, account.id, asset_id)
        return PhotoStatus.model_validate(
            {
                "asset_id": asset.id,
                "state": asset.state,
                "error_code": "PHOTO_PROCESSING_FAILED" if asset.state == "FAILED" else None,
                "width": asset.width if asset.state == "READY" else None,
                "height": asset.height if asset.state == "READY" else None,
            }
        )


def ready_asset(session: Session, owner: UUID, asset_id: UUID) -> UploadAsset:
    asset = owned_asset(session, owner, asset_id)
    if asset.state != "READY":
        raise ApiError(409, "PHOTO_NOT_READY", "This photo is not available for viewing.")
    return asset


def photo_view(
    session: Session, principal: Principal, asset_id: UUID, body: PhotoViewRequest, storage: Storage
) -> PhotoView:
    with locked_account(session, principal) as owner:
        ready_asset(session, owner, asset_id)
        display, thumbnail = derivative_keys(asset_id)
        key = display if body.variant == "display" else thumbnail
    try:
        capability = storage.sign_view(key)
    except StorageError:
        raise ApiError(
            503, "STORAGE_UNAVAILABLE", "Photo viewing is unavailable. Try again."
        ) from None
    # A disablement during provider I/O must prevent returning the newly minted capability.
    with locked_account(session, principal) as owner:
        ready_asset(session, owner, asset_id)
        if capability.expires_at <= datetime.now(UTC):
            raise ApiError(503, "STORAGE_UNAVAILABLE", "Photo viewing is unavailable. Try again.")
    return PhotoView(
        asset_id=asset_id,
        variant=body.variant,
        view_url=capability.url.get_secret_value(),
        expires_at=capability.expires_at,
    )
