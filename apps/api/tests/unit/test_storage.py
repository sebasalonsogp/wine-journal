import secrets
import time
from uuid import uuid4

import httpx
import jwt
import pytest
from pydantic import SecretStr, ValidationError
from pydantic_settings import SettingsConfigDict

from wine_journal.integrations.storage import (
    MAX_UPLOAD_BYTES,
    UPLOAD_TYPES,
    ObjectMissing,
    Storage,
    StorageError,
    StorageSettings,
    new_staging_key,
)


class IsolatedSettings(StorageSettings):
    model_config = SettingsConfigDict(env_file=None)


def settings() -> StorageSettings:
    return IsolatedSettings(
        url="https://storage.example/storage/v1", service_key=SecretStr(secrets.token_urlsafe(32))
    )


def bucket(config: StorageSettings) -> dict[str, object]:
    return {
        "id": config.bucket,
        "public": False,
        "file_size_limit": MAX_UPLOAD_BYTES,
        "allowed_mime_types": list(UPLOAD_TYPES),
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://storage.example/storage/v1",
        "https://u:p@storage.example/storage/v1",
        "https://storage.example/storage/v1?secret=private",
        "https://storage.example/storage/v1#private",
        "https://storage.example/other",
    ],
)
def test_storage_settings_hide_credentials_and_reject_unsafe_endpoints(url: str) -> None:
    config = settings()
    assert config.service_key.get_secret_value() not in repr(config)
    with pytest.raises(ValidationError) as exc:
        IsolatedSettings(url=url, service_key=config.service_key)
    assert url not in str(exc.value)


@pytest.mark.parametrize(
    "change", [{"public": True}, {"file_size_limit": None}, {"allowed_mime_types": ["*"]}]
)
def test_existing_bucket_must_match_without_mutating_it(change: dict[str, object]) -> None:
    config = settings()
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request.method)
        return httpx.Response(200, json={**bucket(config), **change})

    storage = Storage(config, transport=httpx.MockTransport(respond))
    try:
        with pytest.raises(StorageError):
            storage.ensure_private_bucket()
        assert requests == ["GET", "GET"]
    finally:
        storage.close()


@pytest.mark.parametrize(
    "problem",
    [None, "external", "wrong-path", "expired", "long-lived", "upsert", "duplicate-token"],
)
def test_capabilities_are_bounded_path_specific_and_redacted(problem: str | None) -> None:
    config = settings()
    key = new_staging_key(uuid4())
    path = f"{config.bucket}/{key}"
    claims: dict[str, object] = {"url": path, "exp": int(time.time()) + 7200}
    if problem == "expired":
        claims["exp"] = 1
    elif problem == "long-lived":
        claims["exp"] = int(time.time()) + 86400
    elif problem == "upsert":
        claims["upsert"] = True
    elif problem == "wrong-path":
        claims["url"] = path + "x"
    token = jwt.encode(claims, secrets.token_bytes(32), algorithm="HS256")
    relative = f"/object/upload/sign/{path}?token={token}"
    if problem == "external":
        relative = "https://external.example" + relative
    elif problem == "duplicate-token":
        relative += "&token=second"

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer " + config.service_key.get_secret_value()
        if request.method == "GET":
            return httpx.Response(200, json=bucket(config))
        assert request.headers.get("x-upsert") is None
        return httpx.Response(200, json={"url": relative})

    storage = Storage(config, transport=httpx.MockTransport(respond))
    try:
        if problem:
            with pytest.raises(StorageError) as exc:
                storage.sign_upload(key)
            assert token not in str(exc.value)
        else:
            capability = storage.sign_upload(key)
            assert token not in repr(capability)
            assert capability.url.get_secret_value().startswith(config.url + "/object/upload/sign/")
    finally:
        storage.close()


@pytest.mark.parametrize(
    "problem",
    [None, "wrong-key", "string-size", "missing", "oversize-response", "redirect", "timeout"],
)
def test_object_info_and_provider_failures_are_validated(problem: str | None) -> None:
    config = settings()
    key = new_staging_key(uuid4())
    private = secrets.token_urlsafe(32)
    info: dict[str, object] = {
        "id": str(uuid4()),
        "name": key,
        "size": 12,
        "contentType": "image/jpeg",
        "etag": "v1",
    }
    if problem == "wrong-key":
        info["name"] = new_staging_key(uuid4())
    elif problem == "string-size":
        info["size"] = "12"

    def respond(request: httpx.Request) -> httpx.Response:
        if problem == "missing":
            return httpx.Response(400, json={"code": "NoSuchKey", "message": private})
        if problem == "oversize-response":
            return httpx.Response(200, content=b"x" * 17000)
        if problem == "redirect":
            return httpx.Response(
                302, json={"message": private}, headers={"Location": "https://external.example"}
            )
        if problem == "timeout":
            raise httpx.ReadTimeout(private, request=request)
        return httpx.Response(200, json=info)

    storage = Storage(config, transport=httpx.MockTransport(respond))
    try:
        if problem:
            with pytest.raises(ObjectMissing if problem == "missing" else StorageError) as exc:
                storage.info(key)
            assert private not in str(exc.value)
        else:
            assert storage.info(key).size == 12
        with pytest.raises(ValueError, match="Invalid staging key"):
            storage.info("../other-user/file.jpg")
    finally:
        storage.close()
