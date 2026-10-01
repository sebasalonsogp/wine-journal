"""Opt-in real Storage + disposable SQL integration; synthetic data only."""

import hashlib
import io
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pillow_heif
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.integrations.storage import ObjectInfo, OutputConflict, Storage, StorageError
from wine_journal.main import create_app
from wine_journal.media.models import Job, UploadAsset
from wine_journal.media.photo_processing import PhotoPublisher, derivative_keys
from wine_journal.media.photo_sandbox import PhotoSandbox
from wine_journal.media.uploads import RESERVATION_BYTES
from wine_journal.worker import run_once


@pytest.mark.skipif(
    os.environ.get("WINE_JOURNAL_TEST_STORAGE") != "1", reason="Opt-in local Storage probe"
)
@pytest.mark.parametrize(
    "source_format,content_type", [("JPEG", "image/jpeg"), ("HEIF", "image/heic")]
)
def test_real_private_upload_flow(
    database_urls: dict[str, SecretStr],
    monkeypatch: pytest.MonkeyPatch,
    source_format: str,
    content_type: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[4] / "scripts"))
    from configure_storage import local_credentials

    config, anon = local_credentials()  # Refuses anything except this project's loopback gateway.
    config = config.model_copy(update={"bucket": "wj-upload-flow-" + uuid4().hex})
    storage = Storage(config)
    engine = database_engine(database_urls["runtime"])
    admin = database_engine(database_urls["migration"], role="wine_migrator")
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.state.storage = storage
    person, other = (
        Principal("https://upload-flow.test", uuid4()),
        Principal("https://upload-flow.test", uuid4()),
    )
    app.dependency_overrides[require_principal] = lambda: person
    image = io.BytesIO()
    pillow_heif.register_heif_opener()
    exif = Image.Exif()
    exif[274], exif[315] = 6, "SYNTHETIC_PRIVATE_METADATA"
    # HEIF's encoder reads rotation from serialized EXIF, not a Pillow Exif object.
    Image.new("RGB", (16, 24), "olive").save(image, format=source_format, exif=exif.tobytes())
    contents = image.getvalue()
    payload = {"sizeBytes": len(contents), "contentType": content_type}
    headers = {
        "apikey": anon.get_secret_value(),
        "Authorization": "Bearer " + anon.get_secret_value(),
        "Content-Type": content_type,
    }
    service_headers = {
        "apikey": config.service_key.get_secret_value(),
        "Authorization": "Bearer " + config.service_key.get_secret_value(),
    }
    keys: list[str] = []
    cleanup_derivatives: list[str] = []
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
            assert api.get(f"/api/v1/media/{grant['assetId']}").status_code == 404
            assert (
                api.post(
                    f"/api/v1/media/{grant['assetId']}/view", json={"variant": "display"}
                ).status_code
                == 404
            )
            assert api.post(f"/api/v1/media/{uuid4()}/complete", json={}).status_code == 404
            app.dependency_overrides[require_principal] = lambda: person
            with ThreadPoolExecutor(max_workers=2) as workers:
                results = list(workers.map(lambda _: api.post(path, json={}).status_code, range(2)))
            assert results == [200, 200]
            status_path = f"/api/v1/media/{grant['assetId']}"
            assert api.get(status_path).json()["state"] == "PROCESSING"
            assert api.post(status_path + "/view", json={"variant": "display"}).status_code == 409
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
            # Independent known key exercises raw replay/conflict behavior before the worker.
            display_key = f"photos/{uuid4().hex}/v1/display.jpg"
            jpeg = io.BytesIO()
            Image.new("RGB", (16, 16), "olive").save(jpeg, format="JPEG")
            probe = jpeg.getvalue()
            cleanup_derivatives.append(display_key)
            storage.put_derivative(display_key, probe)
            first_output = storage.info(display_key)
            storage.put_derivative(display_key, probe)
            assert storage.info(display_key) == first_output
            with pytest.raises(OutputConflict):
                storage.put_derivative(display_key, probe + b"different")
            assert not client.get(
                f"{config.url}/object/authenticated/{config.bucket}/{display_key}", headers=headers
            ).is_success
            asset_id = UUID(grant["assetId"])
            display_key, thumbnail_key = derivative_keys(asset_id)
            cleanup_derivatives.extend((display_key, thumbnail_key))
            publisher = PhotoPublisher(engine, storage, PhotoSandbox())
            put = storage.put_derivative

            def interrupt(key: str, body: bytes) -> None:
                assert engine.pool.checkedout() == 0  # type: ignore[attr-defined]
                if key == thumbnail_key:
                    raise StorageError("Synthetic interruption between private outputs.")
                put(key, body)

            with monkeypatch.context() as patch:
                patch.setattr(storage, "put_derivative", interrupt)
                assert run_once(engine, {"process_photo": publisher})
            first_display = storage.info(display_key)
            with Session(engine) as session:
                asset = session.get(UploadAsset, asset_id)
                assert asset and asset.state == "PROCESSING"
                job = session.scalar(select(Job).where(Job.reference_id == asset_id))
                assert job and job.state == "PENDING" and job.attempts == 1
            with admin.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE app.jobs SET run_after = clock_timestamp() WHERE reference_id = :id"
                    ),
                    {"id": asset_id},
                )
            # Recover with the actual registered CLI worker, not an injected handler.
            environment = {
                key: value
                for key, value in os.environ.items()
                if not key.startswith("WINE_JOURNAL_")
            }
            environment.update(
                {
                    "WINE_JOURNAL_DATABASE_URL": database_urls["runtime"].get_secret_value(),
                    "WINE_JOURNAL_MEDIA_UPLOADS_ENABLED": "true",
                    "WINE_JOURNAL_STORAGE_URL": config.url,
                    "WINE_JOURNAL_STORAGE_BUCKET": config.bucket,
                    "WINE_JOURNAL_STORAGE_SERVICE_KEY": config.service_key.get_secret_value(),
                }
            )
            worker = subprocess.run(
                [sys.executable, "-m", "wine_journal.worker", "--once"],
                env=environment,
                capture_output=True,
                timeout=90,
            )
            assert worker.returncode == 0, (
                "Registered photo worker failed; private diagnostics withheld."
            )
            assert storage.info(display_key) == first_display
            display = storage.download(first_display)
            thumbnail = storage.download(storage.info(thumbnail_key))
            for output in (display, thumbnail):
                with Image.open(io.BytesIO(output)) as decoded:
                    assert decoded.size == (24, 16) and not decoded.getexif()
                    assert not {"icc_profile", "exif", "xmp", "comment"}.intersection(decoded.info)
                assert b"SYNTHETIC_PRIVATE_METADATA" not in output
            with Session(engine) as session:
                asset = session.get(UploadAsset, asset_id)
                assert (
                    asset and asset.state == "READY" and asset.reserved_bytes == RESERVATION_BYTES
                )
                assert asset.display_sha256 == hashlib.sha256(display).hexdigest()
                assert asset.thumbnail_sha256 == hashlib.sha256(thumbnail).hexdigest()
                job = session.scalar(select(Job).where(Job.reference_id == asset_id))
                assert job and job.state == "SUCCEEDED" and job.attempts == 2
            assert storage.download(expected) == contents  # A live upload grant still holds it.
            for key in (display_key, thumbnail_key):
                assert not client.get(
                    f"{config.url}/object/authenticated/{config.bucket}/{key}", headers=headers
                ).is_success
            status = api.get(status_path)
            assert (
                status.json()["state"] == "READY" and status.headers["cache-control"] == "no-store"
            )
            for variant, expected_body in (("display", display), ("thumbnail", thumbnail)):
                response = api.post(status_path + "/view", json={"variant": variant})
                assert (
                    response.status_code == 200 and response.headers["cache-control"] == "no-store"
                )
                view = response.json()
                expiry = datetime.fromisoformat(view["expiresAt"])
                assert 0 < (expiry - datetime.now(UTC)).total_seconds() <= 125
                viewed = client.get(view["viewUrl"])
                assert viewed.status_code == 200 and viewed.content == expected_body
                # Storage's signed route replaces Cache-Control with token-bound Expires.
                assert parsedate_to_datetime(viewed.headers["expires"]) == expiry
                assert view["viewUrl"] not in caplog.text
                # A token for one variant cannot read the other file or the original.
                if variant == "display":
                    for replacement in (thumbnail_key, expected.name):
                        changed = view["viewUrl"].replace(display_key, replacement)
                        assert not client.get(changed).is_success
            # Real provider-signed token, warmed before expiry; no secret inspection or forged JWT.
            short = storage.sign_view(display_key, seconds=2)
            short_url = short.url.get_secret_value()
            assert client.get(short_url).status_code == 200
            remaining = (short.expires_at - datetime.now(UTC)).total_seconds()
            time.sleep(max(0, remaining) + 1)
            assert not client.get(short_url).is_success
            assert short_url not in caplog.text
            private_read = client.get(
                f"{config.url}/object/authenticated/{config.bucket}/{display_key}",
                headers=service_headers,
            )
            assert private_read.status_code == 200 and "no-store" in private_read.headers.get(
                "cache-control", ""
            )
            app.dependency_overrides[require_principal] = lambda: other
            assert api.post(status_path + "/view", json={"variant": "display"}).status_code == 404
            app.dependency_overrides[require_principal] = lambda: person
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
                        json={"prefixes": keys + cleanup_derivatives},
                    )
                    assert result.status_code == 200, "Synthetic object cleanup failed."
                result = client.delete(
                    f"{config.url}/bucket/{config.bucket}", headers=service_headers
                )
                assert result.status_code == 200, "Synthetic bucket cleanup failed."
            finally:
                storage.close()
                engine.dispose()
                admin.dispose()
