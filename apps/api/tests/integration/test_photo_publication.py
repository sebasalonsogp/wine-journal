import hashlib
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.core.auth import Principal
from wine_journal.core.database import database_engine
from wine_journal.integrations.storage import (
    ObjectChanged,
    ObjectInfo,
    OutputConflict,
    Storage,
    StorageError,
    new_staging_key,
)
from wine_journal.media.jobs import claim, enqueue, finish
from wine_journal.media.models import Job, PhotoWriteAttempt, UploadAsset
from wine_journal.media.photo_processing import LeaseLost, PhotoPublisher, derivative_keys
from wine_journal.media.photo_protocol import PhotoRejected, PhotoResult
from wine_journal.media.photo_sandbox import PhotoSandbox
from wine_journal.media.uploads import RESERVATION_BYTES
from wine_journal.media.write_attempts import acknowledge, register
from wine_journal.worker import run_once

RESULT = PhotoResult(16, 16, 16, 16, "JPEG", b"display", b"thumbnail")


@dataclass
class Publication:
    engine: Engine
    admin: Engine
    owner: UUID
    asset_id: UUID
    storage: Mock
    decoder: Mock
    outputs: dict[str, bytes]

    @property
    def publisher(self) -> PhotoPublisher:
        return PhotoPublisher(self.engine, self.storage, self.decoder)

    def asset(self) -> UploadAsset:
        with Session(self.engine) as session:
            asset = session.get(UploadAsset, self.asset_id)
            assert asset
            session.expunge(asset)
            return asset

    def job(self) -> Job:
        with Session(self.engine) as session:
            job = session.scalar(select(Job).where(Job.reference_id == self.asset_id))
            assert job
            session.expunge(job)
            return job

    def writes(self) -> list[PhotoWriteAttempt]:
        with Session(self.engine) as session:
            attempts = list(
                session.scalars(
                    select(PhotoWriteAttempt).where(PhotoWriteAttempt.asset_id == self.asset_id)
                )
            )
            session.expunge_all()
            return attempts

    def expire(self) -> None:
        with self.admin.begin() as connection:
            connection.execute(
                text(
                    "UPDATE app.jobs SET lease_until = clock_timestamp() - interval '1 second' "
                    "WHERE reference_id = :id"
                ),
                {"id": self.asset_id},
            )

    def due(self) -> None:
        with self.admin.begin() as connection:
            connection.execute(
                text("UPDATE app.jobs SET run_after = clock_timestamp() WHERE reference_id = :id"),
                {"id": self.asset_id},
            )


@pytest.fixture
def publication(database_urls: dict[str, SecretStr]) -> Iterator[Publication]:
    engine = database_engine(database_urls["runtime"])
    admin = database_engine(database_urls["migration"], role="wine_migrator")
    with Session(engine) as session:
        owner = bootstrap_account(session, Principal("https://publication.test", uuid4())).id
    identifier = uuid4()
    with Session(engine) as session, session.begin():
        session.add(
            UploadAsset(
                id=identifier,
                owner_id=owner,
                operation_key=uuid4(),
                object_key=new_staging_key(identifier),
                declared_bytes=6,
                declared_type="image/jpeg",
                reserved_bytes=RESERVATION_BYTES,
                state="PROCESSING",
                object_id=uuid4(),
                object_etag="original",
                unsettled_grants=1,
            )
        )
        enqueue(
            session,
            owner_id=owner,
            operation_key=identifier,
            kind="process_photo",
            reference_id=identifier,
        )
    storage, decoder = Mock(spec=Storage), Mock(spec=PhotoSandbox)
    outputs: dict[str, bytes] = {}

    def download(expected: ObjectInfo) -> bytes:
        assert engine.pool.checkedout() == 0  # type: ignore[attr-defined]
        assert expected.etag == "original" and expected.size == 6
        return b"source"

    def convert(source: bytes) -> PhotoResult:
        assert engine.pool.checkedout() == 0  # type: ignore[attr-defined]
        assert source == b"source"
        return RESULT

    def put(key: str, contents: bytes) -> bool:
        assert engine.pool.checkedout() == 0  # type: ignore[attr-defined]
        with Session(engine) as session:
            asset = session.get(UploadAsset, identifier)
            assert asset is not None and asset.unsettled_writes > 0
            assert session.scalar(
                select(PhotoWriteAttempt.id).where(
                    PhotoWriteAttempt.asset_id == identifier,
                    PhotoWriteAttempt.derivative
                    == ("display" if key.endswith("display.jpg") else "thumbnail"),
                    PhotoWriteAttempt.acknowledged_at.is_(None),
                )
            )  # Both the exact attempt and its hold committed before external I/O.
        assert key not in outputs or outputs[key] == contents
        outputs[key] = contents
        return True

    storage.download.side_effect, storage.put_derivative.side_effect = download, put
    decoder.convert.side_effect = convert
    try:
        yield Publication(engine, admin, owner, identifier, storage, decoder, outputs)
    finally:
        with admin.begin() as connection:
            connection.execute(
                text("DELETE FROM app.jobs WHERE reference_id = :id"), {"id": identifier}
            )
            connection.execute(
                text("DELETE FROM app.upload_assets WHERE id = :id"), {"id": identifier}
            )
        engine.dispose()
        admin.dispose()


def test_ready_requires_both_outputs_and_replays_after_commit(publication: Publication) -> None:
    p = publication
    work = claim(p.engine)
    assert work
    p.publisher(work)  # Simulate losing the queue acknowledgement after asset publication.
    asset = p.asset()
    assert asset.state == "READY" and asset.processing_error is None
    assert asset.display_sha256 == hashlib.sha256(RESULT.display).hexdigest()
    assert asset.thumbnail_sha256 == hashlib.sha256(RESULT.thumbnail).hexdigest()
    assert (asset.width, asset.height, asset.thumbnail_width, asset.thumbnail_height) == (
        16,
        16,
        16,
        16,
    )
    assert asset.reserved_bytes == RESERVATION_BYTES and asset.unsettled_grants == 1
    assert asset.unsettled_writes == 0
    assert len(p.writes()) == 2 and all(row.acknowledged_at for row in p.writes())
    assert set(p.outputs) == set(derivative_keys(p.asset_id))
    p.expire()
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.job().state == "SUCCEEDED" and p.job().attempts == 2
    assert p.decoder.convert.call_count == 1
    assert p.storage.put_derivative.call_count == 2


def test_partial_publication_reuses_exact_output_on_retry(publication: Publication) -> None:
    p = publication
    write = p.storage.put_derivative.side_effect

    def interrupt(key: str, contents: bytes) -> bool:
        if key.endswith("thumbnail.webp"):
            assert p.asset().state == "PROCESSING"
            raise StorageError("synthetic interruption")
        return bool(write(key, contents))

    p.storage.put_derivative.side_effect = interrupt
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().state == "PROCESSING" and p.job().state == "PENDING"
    assert p.asset().unsettled_writes == 1
    assert len(p.outputs) == 1
    p.storage.put_derivative.side_effect = write
    p.due()
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().state == "READY" and len(p.outputs) == 2
    assert p.asset().unsettled_writes == 1  # Retry success cannot settle the earlier request.
    assert len(p.writes()) == 4
    assert sum(row.acknowledged_at is None for row in p.writes()) == 1


def test_readback_after_timeout_retains_write_holds(publication: Publication) -> None:
    p = publication
    write = p.storage.put_derivative.side_effect

    def uncertain(key: str, contents: bytes) -> bool:
        write(key, contents)
        return False

    p.storage.put_derivative.side_effect = uncertain
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().state == "READY" and p.asset().unsettled_writes == 2
    assert p.asset().reserved_bytes == RESERVATION_BYTES


def test_lost_lease_settles_exact_acknowledged_write_without_publishing(
    publication: Publication,
) -> None:
    p = publication
    work = claim(p.engine)
    assert work
    write = p.storage.put_derivative.side_effect

    def delayed(key: str, contents: bytes) -> bool:
        write(key, contents)
        p.expire()
        return True

    p.storage.put_derivative.side_effect = delayed
    with pytest.raises(LeaseLost):
        p.publisher(work)
    assert p.asset().unsettled_writes == 0 and len(p.outputs) == 1
    assert p.asset().state == "PROCESSING" and p.writes()[0].acknowledged_at
    p.storage.put_derivative.side_effect = write
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().state == "READY" and p.asset().unsettled_writes == 0


def test_concurrent_acknowledgements_preserve_legacy_and_other_attempts(
    publication: Publication,
) -> None:
    p = publication
    with p.admin.begin() as connection:
        connection.execute(
            text("UPDATE app.upload_assets SET unsettled_writes = 1 WHERE id = :id"),
            {"id": p.asset_id},
        )
    p.storage.put_derivative.side_effect = lambda *_: False
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().unsettled_writes == 3
    attempt = p.writes()[0]
    assert not acknowledge(p.engine, uuid4(), p.asset_id, attempt.id)
    assert not acknowledge(p.engine, p.owner, uuid4(), attempt.id)
    assert not acknowledge(p.engine, p.owner, p.asset_id, uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(lambda _: acknowledge(p.engine, p.owner, p.asset_id, attempt.id), range(2))
        )
    assert sorted(outcomes) == [False, True]
    assert p.asset().unsettled_writes == 2
    assert sum(row.acknowledged_at is None for row in p.writes()) == 1


def test_old_acknowledgement_after_replacement_worker_finishes(publication: Publication) -> None:
    p = publication
    original = claim(p.engine)
    assert original
    write = p.storage.put_derivative.side_effect

    def delayed(key: str, contents: bytes) -> bool:
        write(key, contents)
        p.expire()
        p.storage.put_derivative.side_effect = write
        assert run_once(p.engine, {"process_photo": p.publisher})
        assert p.asset().state == "READY" and p.asset().unsettled_writes == 1
        assert p.job().state == "SUCCEEDED"
        return True

    p.storage.put_derivative.side_effect = delayed
    with pytest.raises(LeaseLost):
        p.publisher(original)
    assert p.asset().state == "READY" and p.asset().unsettled_writes == 0
    assert p.job().state == "SUCCEEDED" and p.job().attempts == 2
    assert len(p.writes()) == 3 and all(row.acknowledged_at for row in p.writes())


def test_write_registration_rolls_back_with_its_hold(publication: Publication) -> None:
    p = publication
    work = claim(p.engine)
    assert work
    with pytest.raises(RuntimeError, match="synthetic rollback"), p.publisher._asset(work) as asset:
        assert asset is not None
        register(asset, work.token, "display")
        raise RuntimeError("synthetic rollback")
    assert p.asset().unsettled_writes == 0 and not p.writes()
    with pytest.raises(RuntimeError, match="asset transaction"):
        register(p.asset(), work.token, "display")
    assert not p.storage.put_derivative.called


def test_inconsistent_counter_does_not_record_false_acknowledgement(
    publication: Publication,
) -> None:
    p = publication
    p.storage.put_derivative.side_effect = lambda *_: False
    assert run_once(p.engine, {"process_photo": p.publisher})
    with p.admin.begin() as connection:
        connection.execute(
            text("UPDATE app.upload_assets SET unsettled_writes = 0 WHERE id = :id"),
            {"id": p.asset_id},
        )
    with pytest.raises(RuntimeError, match="inconsistent"):
        acknowledge(p.engine, p.owner, p.asset_id, p.writes()[0].id)
    assert all(row.acknowledged_at is None for row in p.writes())


def test_write_evidence_cannot_be_rewritten_or_downgraded(
    publication: Publication,
    migrate: Callable[..., None],
) -> None:
    p = publication
    assert run_once(p.engine, {"process_photo": p.publisher})
    for statement in (
        "DELETE FROM app.photo_write_attempts",
        "UPDATE app.photo_write_attempts SET owner_id = owner_id",
        "UPDATE app.photo_write_attempts SET asset_id = asset_id",
        "UPDATE app.photo_write_attempts SET lease_token = lease_token",
        "UPDATE app.photo_write_attempts SET derivative = derivative",
        "UPDATE app.photo_write_attempts SET created_at = created_at",
    ):
        with p.engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text(statement))
    with p.engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(text("UPDATE app.photo_write_attempts SET acknowledged_at = NULL"))
    with pytest.raises(AssertionError, match="Migration verification failed"):
        migrate("downgrade", "0020_media_quota_release")
    assert all(row.acknowledged_at for row in p.writes())
    assert p.asset().unsettled_writes == 0


def test_attempt_migration_preserves_existing_unknown_holds(
    publication: Publication,
    migrate: Callable[..., None],
) -> None:
    p = publication
    migrate("downgrade", "0020_media_quota_release")
    with p.admin.begin() as connection:
        connection.execute(
            text("UPDATE app.upload_assets SET unsettled_writes = 3 WHERE id = :id"),
            {"id": p.asset_id},
        )
    migrate("upgrade", "head")
    migrate("check")
    assert p.asset().unsettled_writes == 3 and not p.writes()
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().unsettled_writes == 3
    assert len(p.writes()) == 2 and all(row.acknowledged_at for row in p.writes())


def test_changed_bucket_policy_stops_before_read_or_decode(publication: Publication) -> None:
    p = publication
    p.storage.check_private_bucket.side_effect = StorageError("configuration changed")
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().state == "PROCESSING" and p.job().state == "PENDING"
    assert not p.storage.download.called and not p.decoder.convert.called and not p.outputs


@pytest.mark.parametrize(
    "failure,reason",
    [
        (PhotoRejected("INVALID_IMAGE"), "INVALID_IMAGE"),
        (PhotoRejected("RESOURCE_LIMIT"), "RESOURCE_LIMIT"),
        (PhotoRejected("DECODER_PROTOCOL"), "DECODER_PROTOCOL"),
        (ObjectChanged("private"), "SOURCE_CHANGED"),
        (OutputConflict("private"), "OUTPUT_CONFLICT"),
    ],
)
def test_permanent_failure_is_safe_and_does_not_release_reservation(
    publication: Publication,
    failure: Exception,
    reason: str,
) -> None:
    p = publication
    p.decoder.convert.side_effect = failure
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().state == "FAILED" and p.asset().processing_error == reason
    assert p.asset().reserved_bytes == RESERVATION_BYTES and p.asset().unsettled_grants == 1
    assert p.job().state == "SUCCEEDED"  # The processing decision was successfully recorded.
    assert not p.outputs


def test_declared_type_must_agree_with_decoder(publication: Publication) -> None:
    p = publication
    p.decoder.convert.side_effect = lambda _: replace(RESULT, source_format="PNG")
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().processing_error == "SOURCE_TYPE_MISMATCH" and not p.outputs


@pytest.mark.parametrize("failure", [StorageError("private"), PhotoRejected("DECODER_UNAVAILABLE")])
def test_transient_failure_retries_then_exhausts(
    publication: Publication, failure: Exception, caplog: pytest.LogCaptureFixture
) -> None:
    p = publication
    with p.admin.begin() as connection:
        connection.execute(
            text("UPDATE app.jobs SET max_attempts = 2 WHERE reference_id = :id"),
            {"id": p.asset_id},
        )
    p.decoder.convert.side_effect = failure
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().state == "PROCESSING" and p.job().state == "PENDING"
    p.due()
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().processing_error == "PROCESSING_FAILED" and p.job().state == "FAILED"
    assert "private" not in caplog.text


@pytest.mark.parametrize("published", [False, True])
def test_expired_final_attempt_cannot_strand_or_demote_asset(
    publication: Publication, published: bool
) -> None:
    p = publication
    with p.admin.begin() as connection:
        connection.execute(
            text("UPDATE app.jobs SET max_attempts = 1 WHERE reference_id = :id"),
            {"id": p.asset_id},
        )
    work = claim(p.engine)
    assert work
    if published:
        p.publisher(work)
    p.expire()
    assert claim(p.engine) is None
    assert p.job().state == "FAILED"
    assert p.asset().state == ("READY" if published else "FAILED")


@pytest.mark.parametrize("reject", [False, True])
def test_stale_worker_cannot_publish_or_fail_after_reclaim(
    publication: Publication, reject: bool
) -> None:
    p = publication
    original = claim(p.engine)
    assert original

    def reclaim(_: bytes) -> PhotoResult:
        p.expire()
        assert claim(p.engine)
        if reject:
            raise PhotoRejected("INVALID_IMAGE")
        return RESULT

    p.decoder.convert.side_effect = reclaim
    with pytest.raises(LeaseLost):
        p.publisher(original)
    assert p.asset().state == "PROCESSING" and not p.outputs
    assert not finish(p.engine, original, error="HANDLER_FAILED")
    assert p.asset().state == "PROCESSING"


def test_lease_expiring_during_last_write_prevents_ready(publication: Publication) -> None:
    p = publication
    write = p.storage.put_derivative.side_effect

    def expire_after_write(key: str, contents: bytes) -> None:
        write(key, contents)
        if key.endswith("thumbnail.webp"):
            p.expire()

    p.storage.put_derivative.side_effect = expire_after_write
    work = claim(p.engine)
    assert work
    with pytest.raises(LeaseLost):
        p.publisher(work)
    assert p.asset().state == "PROCESSING" and len(p.outputs) == 2
    p.storage.put_derivative.side_effect = write
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().state == "READY"


@pytest.mark.parametrize("before", [False, True])
def test_disabled_account_cannot_publish(publication: Publication, before: bool) -> None:
    p = publication

    def disable() -> None:
        with p.admin.begin() as connection:
            connection.execute(
                text("UPDATE app.app_users SET state = 'DISABLED' WHERE id = :id"), {"id": p.owner}
            )

    def during(_: bytes) -> PhotoResult:
        disable()
        return RESULT

    if before:
        disable()
    else:
        p.decoder.convert.side_effect = during
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().processing_error == "ACCOUNT_UNAVAILABLE"
    assert p.storage.download.call_count == (0 if before else 1)


def test_foreign_asset_reference_cannot_read_or_fail_other_owner(publication: Publication) -> None:
    p = publication
    with Session(p.engine) as session:
        other = bootstrap_account(session, Principal("https://publication.test", uuid4())).id
    with p.admin.begin() as connection:
        connection.execute(
            text(
                "UPDATE app.jobs SET owner_id = :other, max_attempts = 1 WHERE reference_id = :id"
            ),
            {"other": other, "id": p.asset_id},
        )
    work = claim(p.engine)
    assert work
    p.publisher(work)
    assert not p.storage.download.called and not p.outputs
    assert finish(p.engine, work, error="HANDLER_FAILED")
    assert p.asset().state == "PROCESSING"


def test_schema_grants_constraints_and_reversible_migration(
    publication: Publication, migrate: Callable[..., None]
) -> None:
    p = publication
    for statement in (
        "UPDATE app.upload_assets SET processing_version = processing_version",
        "UPDATE app.upload_assets SET reserved_bytes = reserved_bytes",
        "DELETE FROM app.upload_assets",
    ):
        with p.engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text(statement))
    with p.engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            text("UPDATE app.upload_assets SET state = 'READY' WHERE id = :id"), {"id": p.asset_id}
        )
    migrate("downgrade", "0012_media_uploads")
    migrate("upgrade", "head")
    migrate("check")
    assert p.asset().state == "PROCESSING"
    assert run_once(p.engine, {"process_photo": p.publisher})
    assert p.asset().state == "READY"
