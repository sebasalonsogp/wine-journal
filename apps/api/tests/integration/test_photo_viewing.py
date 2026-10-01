from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.integrations.storage import Storage, StorageError, ViewCapability, new_staging_key
from wine_journal.main import create_app
from wine_journal.media.models import UploadAsset
from wine_journal.media.uploads import RESERVATION_BYTES


@pytest.fixture
def viewing(
    database_urls: dict[str, SecretStr],
) -> Iterator[tuple[Engine, Engine, Principal, Principal, UUID]]:
    engine = database_engine(database_urls["runtime"])
    admin = database_engine(database_urls["migration"], role="wine_migrator")
    person, other = (Principal("https://photo-view.test", uuid4()) for _ in range(2))
    with Session(engine) as session:
        owner = bootstrap_account(session, person).id
    with Session(engine) as session:
        bootstrap_account(session, other)
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
                state="READY",
                object_id=uuid4(),
                object_etag="source",
                display_bytes=6,
                thumbnail_bytes=6,
                width=16,
                height=24,
                thumbnail_width=16,
                thumbnail_height=24,
                display_sha256="a" * 64,
                thumbnail_sha256="b" * 64,
            )
        )
    try:
        yield engine, admin, person, other, identifier
    finally:
        with admin.begin() as connection:
            connection.execute(
                text("DELETE FROM app.upload_assets WHERE id = :id"), {"id": identifier}
            )
        engine.dispose()
        admin.dispose()


@pytest.mark.parametrize("state", ["PENDING", "PROCESSING", "READY", "FAILED"])
def test_status_and_view_are_owned_ready_only_and_no_store(
    viewing: tuple[Engine, Engine, Principal, Principal, UUID],
    database_urls: dict[str, SecretStr],
    state: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    engine, admin, person, other, asset_id = viewing
    with admin.begin() as connection:
        connection.execute(
            text(
                "UPDATE app.upload_assets SET state = :state, processing_error = :error "
                "WHERE id = :id"
            ),
            {
                "state": state,
                "error": "INVALID_IMAGE" if state == "FAILED" else None,
                "id": asset_id,
            },
        )
    storage = Mock(spec=Storage)
    capability = ViewCapability(
        SecretStr("https://storage.test/signed-private"), datetime.now(UTC) + timedelta(seconds=120)
    )

    def sign(key: str) -> ViewCapability:
        assert engine.pool.checkedout() == 0  # type: ignore[attr-defined]
        assert app.state.session_factory.kw["bind"].pool.checkedout() == 0
        assert key.startswith(f"photos/{asset_id.hex}/v1/")
        return capability

    storage.sign_view.side_effect = sign
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.state.storage = storage
    path = f"/api/v1/media/{asset_id}"
    with TestClient(app) as api:
        assert api.get(path).status_code == 401
        assert api.post(path + "/view", json={"variant": "display"}).status_code == 401
        app.dependency_overrides[require_principal] = lambda: other
        for target in (path, f"/api/v1/media/{uuid4()}"):
            assert api.get(target).status_code == 404
            response = api.post(target + "/view", json={"variant": "display"})
            assert response.status_code == 404 and response.headers["cache-control"] == "no-store"
        assert not storage.sign_view.called
        app.dependency_overrides[require_principal] = lambda: person
        response = api.get(path)
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "assetId": str(asset_id),
            "state": state,
            "errorCode": "PHOTO_PROCESSING_FAILED" if state == "FAILED" else None,
            "width": 16 if state == "READY" else None,
            "height": 24 if state == "READY" else None,
        }
        assert "INVALID_IMAGE" not in response.text and "staging" not in response.text
        for body in (
            {},
            {"variant": "original"},
            {"variant": "display", "objectKey": "forged"},
            {"variant": "thumbnail", "expiresIn": 999},
        ):
            assert api.post(path + "/view", json=body).status_code == 422
        for variant, suffix in (("display", "display.jpg"), ("thumbnail", "thumbnail.webp")):
            response = api.post(path + "/view", json={"variant": variant})
            assert response.headers["cache-control"] == "no-store"
            if state != "READY":
                assert (
                    response.status_code == 409
                    and response.json()["error"]["code"] == "PHOTO_NOT_READY"
                )
                assert not storage.sign_view.called
            else:
                assert response.status_code == 200
                assert set(response.json()) == {"assetId", "variant", "viewUrl", "expiresAt"}
                storage.sign_view.assert_called_with(f"photos/{asset_id.hex}/v1/{suffix}")
        app.state.storage = None
        assert api.get(path).status_code == 200  # Status does not depend on provider availability.
        assert api.post(path + "/view", json={"variant": "display"}).status_code == 503
    assert "signed-private" not in caplog.text


@pytest.mark.parametrize(
    "problem", ["disabled-before", "disabled-during", "state-during", "storage", "expired"]
)
def test_signing_rechecks_account_state_and_hides_provider_errors(
    viewing: tuple[Engine, Engine, Principal, Principal, UUID],
    database_urls: dict[str, SecretStr],
    problem: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    engine, admin, person, _, asset_id = viewing

    def disable() -> None:
        with admin.begin() as connection:
            connection.execute(
                text("UPDATE app.app_users SET state = 'DISABLED' WHERE auth_subject = :subject"),
                {"subject": person.subject},
            )

    storage = Mock(spec=Storage)

    def sign(_: str) -> ViewCapability:
        assert engine.pool.checkedout() == 0  # type: ignore[attr-defined]
        assert app.state.session_factory.kw["bind"].pool.checkedout() == 0
        if problem == "disabled-during":
            disable()
        elif problem == "state-during":
            with admin.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE app.upload_assets SET state = 'FAILED', "
                        "processing_error = 'PROCESSING_FAILED' WHERE id = :id"
                    ),
                    {"id": asset_id},
                )
        elif problem == "storage":
            raise StorageError("SYNTHETIC_PRIVATE_PROVIDER_BODY")
        return ViewCapability(
            SecretStr("https://storage.test/SYNTHETIC_PRIVATE_CAPABILITY"),
            datetime.now(UTC) + timedelta(seconds=-1 if problem == "expired" else 120),
        )

    storage.sign_view.side_effect = sign
    if problem == "disabled-before":
        disable()
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.state.storage = storage
    app.dependency_overrides[require_principal] = lambda: person
    with TestClient(app) as api:
        response = api.post(f"/api/v1/media/{asset_id}/view", json={"variant": "display"})
        assert response.status_code == (
            403 if problem.startswith("disabled") else 409 if problem == "state-during" else 503
        )
        assert response.headers["cache-control"] == "no-store"
        assert "SYNTHETIC_PRIVATE" not in response.text + caplog.text
        if problem == "disabled-before":
            assert not storage.sign_view.called
            assert api.get(f"/api/v1/media/{asset_id}").status_code == 403
