from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.core.errors import ApiError
from wine_journal.integrations.storage import (
    ObjectInfo,
    ObjectMissing,
    Storage,
    StorageError,
    UploadCapability,
)
from wine_journal.main import create_app
from wine_journal.media.models import Job, UploadAsset
from wine_journal.media.schemas import UploadRequest
from wine_journal.media.uploads import RESERVATION_BYTES, complete_upload, initiate_upload

BODY = UploadRequest.model_validate({"sizeBytes": 12, "contentType": "image/jpeg"})


@pytest.fixture
def uploads(
    database_urls: dict[str, SecretStr],
) -> Iterator[tuple[Engine, Engine, Principal, Principal]]:
    engine = database_engine(database_urls["runtime"])
    admin = database_engine(database_urls["migration"], role="wine_migrator")
    people = (
        Principal("https://uploads.test", uuid4()),
        Principal("https://uploads.test", uuid4()),
    )
    for person in people:
        with Session(engine) as session:
            bootstrap_account(session, person)
    try:
        yield engine, admin, *people
    finally:
        with admin.begin() as connection:
            connection.execute(text("DELETE FROM app.jobs WHERE kind = 'process_photo'"))
            connection.execute(text("DELETE FROM app.upload_assets"))
        engine.dispose()
        admin.dispose()


def provider(engine: Engine) -> Mock:
    storage = Mock(spec=Storage)

    def sign(key: str) -> UploadCapability:
        assert engine.pool.checkedout() == 0  # type: ignore[attr-defined]
        return UploadCapability(
            SecretStr("https://storage.test/" + key), datetime.now(UTC) + timedelta(hours=2)
        )

    def info(key: str) -> ObjectInfo:
        assert engine.pool.checkedout() == 0  # type: ignore[attr-defined]
        return ObjectInfo(
            id=uuid4(), name=key, size=12, content_type="image/jpeg", etag="synthetic"
        )

    storage.sign_upload.side_effect = sign
    storage.info.side_effect = info
    return storage


def test_replay_isolation_completion_and_immutable_grants(
    uploads: tuple[Engine, Engine, Principal, Principal],
) -> None:
    engine, _, person, other = uploads
    storage, key = provider(engine), uuid4()
    with Session(engine) as session:
        first = initiate_upload(session, person, key, BODY, storage)
        again = initiate_upload(session, person, key, BODY, storage)
        assert first.asset_id == again.asset_id and first.upload_url == again.upload_url
        for identifier in (first.asset_id, uuid4()):
            with pytest.raises(ApiError, match="unavailable") as failure:
                complete_upload(session, other, identifier, storage)
            assert failure.value.status == 404
        assert storage.info.call_count == 0
        with pytest.raises(ApiError) as conflict:
            initiate_upload(
                session,
                person,
                key,
                UploadRequest.model_validate({"sizeBytes": 13, "contentType": "image/jpeg"}),
                storage,
            )
        assert conflict.value.code == "UPLOAD_CONFLICT"
        assert initiate_upload(session, other, key, BODY, storage).asset_id != first.asset_id
        result = complete_upload(session, person, first.asset_id, storage)
        assert result.state == "PROCESSING"
        assert complete_upload(session, person, first.asset_id, storage) == result
        assert storage.info.call_count == 1
        with pytest.raises(ApiError) as finished:
            initiate_upload(session, person, key, BODY, storage)
        assert finished.value.code == "UPLOAD_ALREADY_COMPLETED"
        asset = session.get(UploadAsset, first.asset_id)
        assert asset and asset.reserved_bytes == RESERVATION_BYTES and asset.unsettled_grants == 0
        assert asset.object_id and asset.object_etag == "synthetic"
        assert asset.grant_expires_at == again.expires_at
        assert (
            session.scalar(
                select(func.count()).select_from(Job).where(Job.reference_id == first.asset_id)
            )
            == 1
        )
    for column in (
        "owner_id",
        "operation_key",
        "object_key",
        "declared_bytes",
        "declared_type",
        "reserved_bytes",
    ):
        with engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text(f"UPDATE app.upload_assets SET {column} = {column}"))
    with engine.begin() as connection, pytest.raises(ProgrammingError):
        connection.execute(text("DELETE FROM app.upload_assets"))


def test_storage_uncertainty_keeps_reservation_and_retry_identity(
    uploads: tuple[Engine, Engine, Principal, Principal],
) -> None:
    engine, _, person, _ = uploads
    storage, key = provider(engine), uuid4()
    storage.sign_upload.side_effect = StorageError("SYNTHETIC_PRIVATE_PROVIDER_DETAIL")
    with Session(engine) as session:
        with pytest.raises(ApiError) as failure:
            initiate_upload(session, person, key, BODY, storage)
        assert failure.value.code == "STORAGE_UNAVAILABLE"
        assert "PRIVATE" not in str(failure.value)
        asset = session.scalar(select(UploadAsset).where(UploadAsset.operation_key == key))
        assert asset and asset.reserved_bytes == RESERVATION_BYTES and asset.unsettled_grants == 1
        identifier = asset.id
        session.rollback()
        result = initiate_upload(session, person, key, BODY, provider(engine))
        assert result.asset_id == identifier
        asset = session.get(UploadAsset, identifier)
        assert (
            asset and asset.unsettled_grants == 1
        )  # The earlier uncertain attempt is not forgotten.


@pytest.mark.parametrize(
    "kind", ["missing", "outage", "wrong-size", "oversized", "wrong-type", "wrong-key"]
)
def test_completion_rejects_missing_and_forged_objects(
    uploads: tuple[Engine, Engine, Principal, Principal], kind: str
) -> None:
    engine, _, person, _ = uploads
    storage = provider(engine)
    with Session(engine) as session:
        grant = initiate_upload(session, person, uuid4(), BODY, storage)
        if kind in {"missing", "outage"}:
            storage.info.side_effect = (
                ObjectMissing("missing") if kind == "missing" else StorageError("outage")
            )
        else:
            storage.info.side_effect = lambda key: ObjectInfo(
                id=uuid4(),
                name="wrong" if kind == "wrong-key" else key,
                size=21 * 1024 * 1024
                if kind == "oversized"
                else 13
                if kind == "wrong-size"
                else 12,
                content_type="image/png" if kind == "wrong-type" else "image/jpeg",
                etag="test",
            )
        with pytest.raises(ApiError) as failure:
            complete_upload(session, person, grant.asset_id, storage)
        assert failure.value.status == (
            409 if kind == "missing" else 503 if kind == "outage" else 422
        )
        asset = session.get(UploadAsset, grant.asset_id)
        assert asset and asset.state == "PENDING" and asset.reserved_bytes == RESERVATION_BYTES
        assert (
            session.scalar(
                select(func.count()).select_from(Job).where(Job.reference_id == grant.asset_id)
            )
            == 0
        )


def test_expiry_reissue_and_atomic_enqueue_rollback(
    uploads: tuple[Engine, Engine, Principal, Principal],
) -> None:
    engine, admin, person, _ = uploads
    storage, key = provider(engine), uuid4()
    with Session(engine) as session:
        grant = initiate_upload(session, person, key, BODY, storage)
        with admin.begin() as connection:
            connection.execute(
                text(
                    "UPDATE app.upload_assets SET grant_expires_at = now() - interval '1 second' "
                    "WHERE id = :id"
                ),
                {"id": grant.asset_id},
            )
        with pytest.raises(ApiError) as failure:
            complete_upload(session, person, grant.asset_id, storage)
        assert failure.value.code == "UPLOAD_EXPIRED" and storage.info.call_count == 0
        assert initiate_upload(session, person, key, BODY, storage).asset_id == grant.asset_id
        with (
            patch("wine_journal.media.uploads.enqueue", side_effect=RuntimeError("rollback")),
            pytest.raises(RuntimeError),
        ):
            complete_upload(session, person, grant.asset_id, storage)
        asset = session.get(UploadAsset, grant.asset_id)
        assert asset and asset.state == "PENDING" and asset.object_id is None
        session.rollback()
        assert complete_upload(session, person, grant.asset_id, storage).state == "PROCESSING"


def test_parallel_reservations_and_completions(
    uploads: tuple[Engine, Engine, Principal, Principal],
) -> None:
    engine, _, person, _ = uploads
    # Other threads can own a DB connection, but each provider call's own session cannot.
    barrier = Barrier(4)

    def reserve(_: int) -> UUID | str:
        storage = Mock(spec=Storage)
        with Session(engine) as session:

            def sign(key: str) -> UploadCapability:
                assert not session.in_transaction()
                return UploadCapability(
                    SecretStr("https://storage.test/" + key), datetime.now(UTC) + timedelta(hours=2)
                )

            storage.sign_upload.side_effect = sign
            barrier.wait(timeout=10)
            try:
                return initiate_upload(session, person, uuid4(), BODY, storage).asset_id
            except ApiError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(reserve, range(4)))
    identifiers = [item for item in results if isinstance(item, UUID)]
    assert len(identifiers) == 2 and results.count("UPLOAD_LIMIT") == 2
    barrier = Barrier(2)

    def complete(_: int) -> str:
        with Session(engine) as session:
            storage = Mock(spec=Storage)

            def info(key: str) -> ObjectInfo:
                assert not session.in_transaction()
                barrier.wait(timeout=10)
                return ObjectInfo(
                    id=uuid4(), name=key, size=12, content_type="image/jpeg", etag="test"
                )

            storage.info.side_effect = info
            return complete_upload(session, person, identifiers[0], storage).state

    with ThreadPoolExecutor(max_workers=2) as workers:
        assert list(workers.map(complete, range(2))) == ["PROCESSING", "PROCESSING"]
    with Session(engine) as session:
        assert (
            session.scalar(
                select(func.count()).select_from(Job).where(Job.reference_id == identifiers[0])
            )
            == 1
        )


def test_storage_quota_counts_full_allowance_and_failed_assets(
    uploads: tuple[Engine, Engine, Principal, Principal],
) -> None:
    engine, admin, person, _ = uploads
    with Session(engine) as session:
        for _ in range(3):
            grant = initiate_upload(session, person, uuid4(), BODY, provider(engine))
            with admin.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE app.upload_assets SET state = 'FAILED', "
                        "processing_error = 'PROCESSING_FAILED' WHERE id = :id"
                    ),
                    {"id": grant.asset_id},
                )
        with pytest.raises(ApiError) as failure:
            initiate_upload(session, person, uuid4(), BODY, provider(engine))
        assert failure.value.code == "MEDIA_QUOTA_EXCEEDED"


def test_upload_migration_round_trip(migrate: Callable[..., None]) -> None:
    migrate("downgrade", "0011_media_jobs")
    migrate("upgrade", "head")
    migrate("check")


def test_grant_reissue_racing_completion_still_records_retention(
    uploads: tuple[Engine, Engine, Principal, Principal],
) -> None:
    engine, _, person, _ = uploads
    storage, operation = provider(engine), uuid4()
    with Session(engine) as session:
        first = initiate_upload(session, person, operation, BODY, storage)
        expiry = first.expires_at + timedelta(minutes=1)

        def finish_before_sign_returns(key: str) -> UploadCapability:
            with Session(engine) as competing:
                complete_upload(competing, person, first.asset_id, provider(engine))
            return UploadCapability(SecretStr("https://storage.test/" + key), expiry)

        storage.sign_upload.side_effect = finish_before_sign_returns
        with pytest.raises(ApiError) as failure:
            initiate_upload(session, person, operation, BODY, storage)
        assert failure.value.code == "UPLOAD_ALREADY_COMPLETED"
        asset = session.get(UploadAsset, first.asset_id)
        assert asset and asset.grant_expires_at == expiry and asset.unsettled_grants == 0
        assert asset.state == "PROCESSING"


def test_asset_count_quota_includes_uncertain_signing(
    uploads: tuple[Engine, Engine, Principal, Principal],
) -> None:
    engine, _, person, _ = uploads
    storage, operation = provider(engine), uuid4()
    with Session(engine) as session:

        def signed_but_unrecorded(key: str) -> UploadCapability:
            # A provider link could exist even though its acknowledgement never commits.
            raise StorageError("response lost")

        storage.sign_upload.side_effect = signed_but_unrecorded
        with pytest.raises(ApiError):
            initiate_upload(session, person, operation, BODY, storage)
        with (
            patch("wine_journal.media.uploads.ACCOUNT_ASSETS", 1),
            pytest.raises(ApiError) as quota,
        ):
            initiate_upload(session, person, uuid4(), BODY, provider(engine))
        assert quota.value.code == "MEDIA_QUOTA_EXCEEDED"
        assert initiate_upload(session, person, operation, BODY, provider(engine)).asset_id


def test_upload_routes_auth_validation_feature_gate_and_privacy(
    database_urls: dict[str, SecretStr],
    uploads: tuple[Engine, Engine, Principal, Principal],
    caplog: pytest.LogCaptureFixture,
) -> None:
    engine, _, person, other = uploads
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    storage = provider(engine)
    headers = {"Idempotency-Key": str(uuid4())}
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/v1/media/uploads", headers=headers, json=BODY.model_dump(by_alias=True)
            ).status_code
            == 401
        )
        assert client.post(f"/api/v1/media/{uuid4()}/complete", json={}).status_code == 401
        app.dependency_overrides[require_principal] = lambda: person
        assert (
            client.post(
                "/api/v1/media/uploads", headers=headers, json=BODY.model_dump(by_alias=True)
            ).json()["error"]["code"]
            == "MEDIA_UNAVAILABLE"
        )
        app.state.storage = storage
        for bad in (
            {"sizeBytes": 0, "contentType": "image/jpeg"},
            {"sizeBytes": True, "contentType": "image/jpeg"},
            {"sizeBytes": 20 * 1024 * 1024 + 1, "contentType": "image/jpeg"},
            {"sizeBytes": 12, "contentType": "text/html"},
            {**BODY.model_dump(by_alias=True), "ownerId": str(uuid4())},
            {**BODY.model_dump(by_alias=True), "objectKey": "private"},
        ):
            assert (
                client.post("/api/v1/media/uploads", headers=headers, json=bad).status_code == 422
            )
        assert (
            client.post("/api/v1/media/uploads", json=BODY.model_dump(by_alias=True)).status_code
            == 422
        )
        assert storage.sign_upload.call_count == 0
        response = client.post(
            "/api/v1/media/uploads", headers=headers, json=BODY.model_dump(by_alias=True)
        )
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        result = response.json()
        assert set(result) == {"assetId", "uploadUrl", "expiresAt", "method", "contentType"}
        path = f"/api/v1/media/{result['assetId']}/complete"
        assert client.post(path, json={"objectKey": "forged"}).status_code == 422
        app.dependency_overrides[require_principal] = lambda: other
        assert client.post(path, json={}).status_code == 404
        app.dependency_overrides[require_principal] = lambda: person
        response = client.post(path, json={})
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        assert response.json() == {"assetId": result["assetId"], "state": "PROCESSING"}
        assert result["uploadUrl"] not in response.text + caplog.text


def test_inactive_accounts_and_account_lock_timeout(
    uploads: tuple[Engine, Engine, Principal, Principal],
) -> None:
    engine, admin, person, _ = uploads
    storage = provider(engine)
    with admin.begin() as connection:
        connection.execute(
            text("SELECT id FROM app.app_users WHERE auth_subject = :subject FOR UPDATE"),
            {"subject": person.subject},
        )
        with Session(engine) as session, pytest.raises(ApiError) as busy:
            initiate_upload(session, person, uuid4(), BODY, storage)
        assert busy.value.code == "UPLOAD_BUSY"
    with admin.begin() as connection:
        connection.execute(
            text("UPDATE app.app_users SET state = 'DISABLED' WHERE auth_subject = :subject"),
            {"subject": person.subject},
        )
    with Session(engine) as session, pytest.raises(ApiError) as disabled:
        initiate_upload(session, person, uuid4(), BODY, storage)
    assert disabled.value.status == 403 and storage.sign_upload.call_count == 0


def test_completion_rechecks_account_and_grant_reissue_does_not_shorten_expiry(
    uploads: tuple[Engine, Engine, Principal, Principal],
) -> None:
    engine, admin, person, _ = uploads
    storage, key = provider(engine), uuid4()
    with Session(engine) as session:
        first = initiate_upload(session, person, key, BODY, storage)
        storage.sign_upload.side_effect = lambda key: UploadCapability(
            SecretStr("https://storage.test/" + key), first.expires_at - timedelta(minutes=1)
        )
        initiate_upload(session, person, key, BODY, storage)
        asset = session.get(UploadAsset, first.asset_id)
        assert asset and asset.grant_expires_at == first.expires_at
        session.rollback()

        def disable(key: str) -> ObjectInfo:
            assert not session.in_transaction()
            with admin.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE app.app_users SET state = 'DISABLED' WHERE auth_subject = :subject"
                    ),
                    {"subject": person.subject},
                )
            return ObjectInfo(id=uuid4(), name=key, size=12, content_type="image/jpeg", etag="test")

        storage.info.side_effect = disable
        with pytest.raises(ApiError) as disabled:
            complete_upload(session, person, first.asset_id, storage)
        assert disabled.value.status == 403
        asset = session.get(UploadAsset, first.asset_id)
        assert asset and asset.state == "PENDING"
