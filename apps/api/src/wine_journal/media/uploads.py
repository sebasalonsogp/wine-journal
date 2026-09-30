"""Short database transactions around private Storage calls; never across them."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from wine_journal.accounts.models import AppUser
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.integrations.storage import (
    MAX_UPLOAD_BYTES,
    ObjectMissing,
    Storage,
    StorageError,
    new_staging_key,
)
from wine_journal.media.jobs import enqueue
from wine_journal.media.models import UploadAsset
from wine_journal.media.schemas import UploadCompletion, UploadGrant, UploadRequest

RESERVATION_BYTES = MAX_UPLOAD_BYTES + 5 * 1024 * 1024 + 512 * 1024
ACCOUNT_BYTES = 100 * 1024 * 1024
ACCOUNT_ASSETS = 100
INFLIGHT_ASSETS = 2


@contextmanager
def locked_account(session: Session, principal: Principal) -> Iterator[UUID]:
    # All media mutations take the account lock first, including completion.
    try:
        with session.begin():
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            account = session.scalar(
                select(AppUser)
                .where(
                    AppUser.auth_issuer == principal.issuer,
                    AppUser.auth_subject == principal.subject,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if account is None:
                raise ApiError(
                    404, "ACCOUNT_NOT_FOUND", "Finish signing in to create your journal."
                )
            if account.state != "ACTIVE":
                raise ApiError(403, "ACCOUNT_DISABLED", "This account is unavailable.")
            yield account.id
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) == "55P03":
            raise ApiError(409, "UPLOAD_BUSY", "Another upload is saving. Try again.") from None
        raise


def owned_asset(session: Session, owner: UUID, asset_id: UUID) -> UploadAsset:
    asset = session.scalar(
        select(UploadAsset)
        .where(UploadAsset.owner_id == owner, UploadAsset.id == asset_id)
        .execution_options(populate_existing=True)
    )
    if asset is None:
        raise ApiError(404, "UPLOAD_NOT_FOUND", "This upload is unavailable.")
    return asset


def reserve_upload(
    session: Session, principal: Principal, operation: UUID, body: UploadRequest
) -> tuple[UUID, str]:
    with locked_account(session, principal) as owner:
        asset = session.scalar(
            select(UploadAsset).where(
                UploadAsset.owner_id == owner, UploadAsset.operation_key == operation
            )
        )
        if asset is not None:
            if (asset.declared_bytes, asset.declared_type) != (body.size_bytes, body.content_type):
                raise ApiError(409, "UPLOAD_CONFLICT", "This upload key was used for another file.")
            if asset.state != "PENDING":
                raise ApiError(
                    409, "UPLOAD_ALREADY_COMPLETED", "This upload has already completed."
                )
        else:
            count, reserved, inflight = session.execute(
                select(
                    func.count(),
                    func.coalesce(func.sum(UploadAsset.reserved_bytes), 0),
                    func.count().filter(UploadAsset.state.in_(("PENDING", "PROCESSING"))),
                ).where(UploadAsset.owner_id == owner)
            ).one()
            if count >= ACCOUNT_ASSETS or reserved + RESERVATION_BYTES > ACCOUNT_BYTES:
                raise ApiError(
                    409, "MEDIA_QUOTA_EXCEEDED", "There is not enough photo storage available."
                )
            if inflight >= INFLIGHT_ASSETS:
                raise ApiError(409, "UPLOAD_LIMIT", "Wait for your current uploads to finish.")
            asset_id = uuid4()
            asset = UploadAsset(
                id=asset_id,
                owner_id=owner,
                operation_key=operation,
                object_key=new_staging_key(asset_id),
                declared_bytes=body.size_bytes,
                declared_type=body.content_type,
                reserved_bytes=RESERVATION_BYTES,
                state="PENDING",
                unsettled_grants=0,
            )
            session.add(asset)
        # Persist BEFORE contacting Storage. Only a recorded, successful response settles
        # this attempt. A crash, timeout or failed commit leaves an explicit cleanup hold.
        asset.unsettled_grants += 1
        return asset.id, asset.object_key


def initiate_upload(
    session: Session, principal: Principal, operation: UUID, body: UploadRequest, storage: Storage
) -> UploadGrant:
    asset_id, key = reserve_upload(session, principal, operation, body)
    try:
        capability = storage.sign_upload(key)
    except StorageError:
        raise ApiError(
            503, "STORAGE_UNAVAILABLE", "Photo storage is unavailable. Retry this upload."
        ) from None
    with locked_account(session, principal) as owner:
        asset = owned_asset(session, owner, asset_id)
        asset.grant_expires_at = max(
            asset.grant_expires_at or capability.expires_at, capability.expires_at
        )
        asset.unsettled_grants -= 1
        pending = asset.state == "PENDING"
    # Recording a concurrent grant is necessary even if completion won the race.
    if not pending:
        raise ApiError(409, "UPLOAD_ALREADY_COMPLETED", "This upload has already completed.")
    if capability.expires_at <= datetime.now(UTC):
        raise ApiError(409, "UPLOAD_EXPIRED", "This upload link expired. Request another link.")
    return UploadGrant(
        asset_id=asset_id,
        upload_url=capability.url.get_secret_value(),
        expires_at=capability.expires_at,
        content_type=body.content_type,
    )


def completed(asset: UploadAsset) -> UploadCompletion:
    return UploadCompletion.model_validate({"asset_id": asset.id, "state": asset.state})


def require_live_grant(asset: UploadAsset) -> None:
    if asset.grant_expires_at is None or asset.grant_expires_at <= datetime.now(UTC):
        raise ApiError(409, "UPLOAD_EXPIRED", "Request another upload link, then retry completion.")


def complete_upload(
    session: Session, principal: Principal, asset_id: UUID, storage: Storage
) -> UploadCompletion:
    with locked_account(session, principal) as owner:
        asset = owned_asset(session, owner, asset_id)
        if asset.state != "PENDING":
            return completed(asset)
        require_live_grant(asset)
        key = asset.object_key
    try:
        info = storage.info(key)
    except ObjectMissing:
        raise ApiError(
            409, "UPLOAD_MISSING", "Upload the photo before completing this step."
        ) from None
    except StorageError:
        raise ApiError(
            503, "STORAGE_UNAVAILABLE", "Photo storage is unavailable. Try again."
        ) from None
    with locked_account(session, principal) as owner:
        asset = owned_asset(session, owner, asset_id)
        if asset.state != "PENDING":
            return completed(asset)
        require_live_grant(asset)
        if (info.name, info.size, info.content_type) != (
            asset.object_key,
            asset.declared_bytes,
            asset.declared_type,
        ):
            # Keep both object and reservation: deleting would let a live link recreate it.
            raise ApiError(
                422, "UPLOAD_MISMATCH", "The uploaded file does not match its declaration."
            )
        asset.object_id, asset.object_etag = info.id, info.etag
        asset.state = "PROCESSING"
        enqueue(
            session,
            owner_id=owner,
            operation_key=asset.id,
            kind="process_photo",
            reference_id=asset.id,
        )
        return completed(asset)
