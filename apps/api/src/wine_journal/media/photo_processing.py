"""Private photo publication; external I/O never holds an application DB connection."""

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from wine_journal.accounts.models import AppUser
from wine_journal.integrations.storage import ObjectChanged, ObjectInfo, OutputConflict, Storage
from wine_journal.media.jobs import Claim, renew
from wine_journal.media.models import Job, UploadAsset
from wine_journal.media.photo_protocol import PhotoRejected, PhotoResult
from wine_journal.media.photo_sandbox import PhotoSandbox

SOURCE_TYPES = {
    "JPEG": ("image/jpeg",),
    "PNG": ("image/png",),
    "WEBP": ("image/webp",),
    "HEIF": ("image/heic", "image/heif"),
}


class LeaseLost(RuntimeError):
    pass


def derivative_keys(asset_id: UUID) -> tuple[str, str]:
    # v1 is persisted on the asset and constrained by migration 0013. A new conversion
    # recipe needs an explicit version migration; never change outputs beneath this key.
    prefix = f"photos/{asset_id.hex}/v1"
    return f"{prefix}/display.jpg", f"{prefix}/thumbnail.webp"


class PhotoPublisher:
    def __init__(self, engine: Engine, storage: Storage, decoder: PhotoSandbox) -> None:
        self.engine, self.storage, self.decoder = engine, storage, decoder

    @contextmanager
    def _asset(self, work: Claim) -> Iterator[UploadAsset | None]:
        with Session(self.engine) as session, session.begin():
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            # Account -> job -> asset. Queue terminalization takes job -> asset only.
            account = session.scalar(
                select(AppUser).where(AppUser.id == work.owner_id).with_for_update()
            )
            job = session.scalar(
                select(Job)
                .where(
                    Job.id == work.id,
                    Job.owner_id == work.owner_id,
                    Job.reference_id == work.reference_id,
                    Job.operation_key == work.reference_id,
                    Job.kind == "process_photo",
                    Job.state == "RUNNING",
                    Job.lease_token == work.token,
                    Job.lease_until > func.clock_timestamp(),
                )
                .with_for_update()
            )
            if job is None:
                raise LeaseLost("Photo claim is no longer current.")
            asset = session.scalar(
                select(UploadAsset)
                .where(UploadAsset.id == work.reference_id, UploadAsset.owner_id == work.owner_id)
                .with_for_update()
            )
            if account is None or asset is None or asset.state != "PROCESSING":
                yield None
            elif account.state != "ACTIVE":
                asset.state, asset.processing_error = "FAILED", "ACCOUNT_UNAVAILABLE"
                yield None
            else:
                yield asset
            # Roll back even a flushed change if its lease expired while waiting on a lock.
            # Holding the job row prevents another claimant publishing during this transaction.
            session.flush()
            if not session.scalar(
                select(Job.id).where(Job.id == work.id, Job.lease_until > func.clock_timestamp())
            ):
                raise LeaseLost("Photo claim expired before publication.")

    def _renew(self, work: Claim) -> None:
        if not renew(self.engine, work, lease_seconds=120):
            raise LeaseLost("Photo claim is no longer current.")

    def _failed(self, work: Claim, reason: str) -> None:
        with self._asset(work) as asset:
            if asset is not None:
                asset.state, asset.processing_error = "FAILED", reason

    def _ready(self, work: Claim, result: PhotoResult) -> None:
        with self._asset(work) as asset:
            if asset is None:
                return
            asset.display_bytes, asset.thumbnail_bytes = len(result.display), len(result.thumbnail)
            asset.width, asset.height = result.width, result.height
            asset.thumbnail_width, asset.thumbnail_height = (
                result.thumbnail_width,
                result.thumbnail_height,
            )
            asset.display_sha256 = hashlib.sha256(result.display).hexdigest()
            asset.thumbnail_sha256 = hashlib.sha256(result.thumbnail).hexdigest()
            asset.state = "READY"

    def __call__(self, work: Claim) -> None:
        self._renew(work)
        with self._asset(work) as asset:
            if asset is None:
                return  # Already published/rejected: acknowledgement can safely be replayed.
            assert asset.object_id is not None and asset.object_etag is not None
            expected = ObjectInfo(
                id=asset.object_id,
                name=asset.object_key,
                size=asset.declared_bytes,
                content_type=asset.declared_type,
                etag=asset.object_etag,
            )
        try:
            self.storage.check_private_bucket()
            source = self.storage.download(expected)
            self._renew(work)
            result = self.decoder.convert(source)
            if expected.content_type not in SOURCE_TYPES[result.source_format]:
                self._failed(work, "SOURCE_TYPE_MISMATCH")
                return
            for key, contents in zip(
                derivative_keys(work.reference_id), (result.display, result.thumbnail), strict=True
            ):
                self._renew(work)
                self.storage.put_derivative(key, contents)
            self._ready(work, result)
        except PhotoRejected as error:
            if error.reason == "DECODER_UNAVAILABLE":
                raise  # Infrastructure failures use the queue's bounded retry policy.
            self._failed(work, error.reason)
        except ObjectChanged:
            self._failed(work, "SOURCE_CHANGED")
        except OutputConflict:
            self._failed(work, "OUTPUT_CONFLICT")
