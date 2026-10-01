"""Opt-in real Storage + disposable SQL integration; synthetic data only."""

import io
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.integrations.storage import ObjectInfo, OutputConflict, Storage
from wine_journal.main import create_app
from wine_journal.media.models import Job, UploadAsset
from wine_journal.media.uploads import RESERVATION_BYTES


@pytest.mark.skipif(
    os.environ.get("WINE_JOURNAL_TEST_STORAGE") != "1", reason="Opt-in local Storage probe"
)
def test_real_private_upload_flow(
    database_urls: dict[str, SecretStr],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[4] / "scripts"))
    from configure_storage import local_credentials

    config, anon = local_credentials()  # Refuses anything except this project's loopback gateway.
    config = config.model_copy(update={"bucket": "wj-upload-flow-" + uuid4().hex})
    storage = Storage(config)
    engine = database_engine(database_urls["runtime"])
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.state.storage = storage
    person, other = (
        Principal("https://upload-flow.test", uuid4()),
        Principal("https://upload-flow.test", uuid4()),
    )
    app.dependency_overrides[require_principal] = lambda: person
    image = io.BytesIO()
    Image.new("RGB", (16, 16), "olive").save(image, format="JPEG")
    contents = image.getvalue()
    payload = {"sizeBytes": len(contents), "contentType": "image/jpeg"}
    headers = {
        "apikey": anon.get_secret_value(),
        "Authorization": "Bearer " + anon.get_secret_value(),
        "Content-Type": "image/jpeg",
    }
    service_headers = {
        "apikey": config.service_key.get_secret_value(),
        "Authorization": "Bearer " + config.service_key.get_secret_value(),
    }
    keys: list[str] = []
    derivative_keys: list[str] = []
    owners: list[UUID] = []
    # Never log httpx requests: their query strings contain signed upload capabilities.
    with (
        httpx.Client(timeout=15, trust_env=False, follow_redirects=False) as client,
        TestClient(app) as api,
    ):
        try:
            storage.ensure_private_bucket()
            account = api.post("/api/v1/me", json={})
            assert account.status_code == 200
            owners.append(UUID(account.json()["id"]))
            operation = {"Idempotency-Key": str(uuid4())}
            first = api.post("/api/v1/media/uploads", headers=operation, json=payload)
            assert first.status_code == 200
            grant = first.json()
            replay = api.post("/api/v1/media/uploads", headers=operation, json=payload)
            assert replay.status_code == 200 and replay.json()["assetId"] == grant["assetId"]
            path = f"/api/v1/media/{grant['assetId']}/complete"
            assert api.post(path, json={}).json()["error"]["code"] == "UPLOAD_MISSING"
            assert (
                client.put(grant["uploadUrl"], headers=headers, content=contents).status_code == 200
            )
            assert not client.put(
                replay.json()["uploadUrl"],
                headers={**headers, "x-upsert": "true"},
                content=b"replacement",
            ).is_success
            app.dependency_overrides[require_principal] = lambda: other
            account = api.post("/api/v1/me", json={})
            assert account.status_code == 200
            owners.append(UUID(account.json()["id"]))
            assert api.post(path, json={}).status_code == 404
            assert api.post(f"/api/v1/media/{uuid4()}/complete", json={}).status_code == 404
            app.dependency_overrides[require_principal] = lambda: person
            with ThreadPoolExecutor(max_workers=2) as workers:
                results = list(workers.map(lambda _: api.post(path, json={}).status_code, range(2)))
            assert results == [200, 200]
            with Session(engine) as session:
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(Job)
                        .where(Job.reference_id == grant["assetId"])
                    )
                    == 1
                )
                asset = session.get(UploadAsset, grant["assetId"])
                assert (
                    asset
                    and asset.reserved_bytes == RESERVATION_BYTES
                    and asset.state == "PROCESSING"
                )
                assert not client.get(
                    f"{config.url}/object/{config.bucket}/{asset.object_key}", headers=headers
                ).is_success
                assert asset.object_id is not None and asset.object_etag is not None
                expected = ObjectInfo(
                    id=asset.object_id,
                    name=asset.object_key,
                    size=asset.declared_bytes,
                    content_type=asset.declared_type,
                    etag=asset.object_etag,
                )
            assert storage.download(expected) == contents
            display_key = f"photos/{UUID(grant['assetId']).hex}/v1/display.jpg"
            derivative_keys.append(display_key)
            storage.put_derivative(display_key, contents)
            first_output = storage.info(display_key)
            storage.put_derivative(display_key, contents)
            assert storage.info(display_key) == first_output
            with pytest.raises(OutputConflict):
                storage.put_derivative(display_key, contents + b"different")
            assert not client.get(
                f"{config.url}/object/authenticated/{config.bucket}/{display_key}", headers=headers
            ).is_success
            mismatch = api.post(
                "/api/v1/media/uploads", headers={"Idempotency-Key": str(uuid4())}, json=payload
            ).json()
            assert (
                client.put(
                    mismatch["uploadUrl"], headers=headers, content=contents + b"oversize"
                ).status_code
                == 200
            )
            assert (
                api.post(f"/api/v1/media/{mismatch['assetId']}/complete", json={}).json()["error"][
                    "code"
                ]
                == "UPLOAD_MISMATCH"
            )
            app.dependency_overrides[require_principal] = lambda: other

            def reserve(_: int) -> int:
                return int(
                    api.post(
                        "/api/v1/media/uploads",
                        headers={"Idempotency-Key": str(uuid4())},
                        json=payload,
                    ).status_code
                )

            with ThreadPoolExecutor(max_workers=4) as workers:
                results = list(workers.map(reserve, range(4)))
            assert sorted(results) == [200, 200, 409, 409]
        finally:
            with Session(engine) as session:
                keys = list(
                    session.scalars(
                        select(UploadAsset.object_key).where(UploadAsset.owner_id.in_(owners))
                    ).all()
                )
            try:
                if keys:
                    result = client.request(
                        "DELETE",
                        f"{config.url}/object/{config.bucket}",
                        headers=service_headers,
                        json={"prefixes": keys + derivative_keys},
                    )
                    assert result.status_code == 200, "Synthetic object cleanup failed."
                result = client.delete(
                    f"{config.url}/bucket/{config.bucket}", headers=service_headers
                )
                assert result.status_code == 200, "Synthetic bucket cleanup failed."
            finally:
                storage.close()
                engine.dispose()
