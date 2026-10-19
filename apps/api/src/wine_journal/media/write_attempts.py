"""Account for exact derivative attempts; acknowledgements never authorize publication."""

from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, object_session

from wine_journal.accounts.models import AppUser
from wine_journal.media.models import PhotoWriteAttempt, UploadAsset


def register(
    asset: UploadAsset, lease_token: UUID, derivative: Literal["display", "thumbnail"]
) -> UUID:
    """Caller must hold the account/job/asset locks and validate its lease at commit."""
    session = object_session(asset)
    if session is None or not session.in_transaction():
        raise RuntimeError("Write registration requires an asset transaction.")
    identifier = uuid4()
    session.add(
        PhotoWriteAttempt(
            id=identifier,
            owner_id=asset.owner_id,
            asset_id=asset.id,
            lease_token=lease_token,
            derivative=derivative,
        )
    )
    asset.unsettled_writes += 1
    return identifier


def acknowledge(engine: Engine, owner_id: UUID, asset_id: UUID, attempt_id: UUID) -> bool:
    """Only call for this exact request's confirmed successful provider response.

    No lease check: settlement records completed I/O, not a worker's right to publish.
    The attempt and counter change commit together; retries cannot settle twice.
    """
    with Session(engine) as session, session.begin():
        session.execute(text("SET LOCAL lock_timeout = '3s'"))
        account = session.scalar(select(AppUser).where(AppUser.id == owner_id).with_for_update())
        if account is None:
            return False
        asset = session.scalar(
            select(UploadAsset)
            .where(UploadAsset.id == asset_id, UploadAsset.owner_id == owner_id)
            .with_for_update()
        )
        attempt = session.scalar(
            select(PhotoWriteAttempt)
            .where(
                PhotoWriteAttempt.id == attempt_id,
                PhotoWriteAttempt.owner_id == owner_id,
                PhotoWriteAttempt.asset_id == asset_id,
            )
            .with_for_update()
        )
        if asset is None or attempt is None or attempt.acknowledged_at is not None:
            return False
        if asset.unsettled_writes < 1:
            raise RuntimeError("Write accounting is inconsistent; retain the attempt.")
        attempt.acknowledged_at = session.scalar(select(func.clock_timestamp()))
        asset.unsettled_writes -= 1
        return True
