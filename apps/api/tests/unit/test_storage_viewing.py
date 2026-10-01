import json
import secrets
import time
from uuid import uuid4

import httpx
import jwt
import pytest
from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from wine_journal.integrations.storage import (
    MAX_UPLOAD_BYTES,
    UPLOAD_TYPES,
    VIEW_SECONDS,
    Storage,
    StorageError,
    StorageSettings,
    new_staging_key,
)


class IsolatedSettings(StorageSettings):
    model_config = SettingsConfigDict(env_file=None)


@pytest.mark.parametrize(
    "problem",
    [
        None,
        "external",
        "fragment",
        "path",
        "claims",
        "expired",
        "long",
        "duplicate",
        "extra",
        "missing",
        "provider",
        "public",
    ],
)
def test_view_capability_is_private_bounded_and_exact(problem: str | None) -> None:
    config = IsolatedSettings(
        url="https://storage.example/storage/v1", service_key=SecretStr(secrets.token_urlsafe(32))
    )
    key = f"photos/{uuid4().hex}/v1/display.jpg"
    path = f"{config.bucket}/{key}"
    expiry = int(time.time()) + VIEW_SECONDS
    if problem == "expired":
        expiry = 1
    elif problem == "long":
        expiry += 3600
    token = jwt.encode(
        {"url": path + ("other" if problem == "claims" else ""), "exp": expiry},
        secrets.token_bytes(32),
        algorithm="HS256",
    )
    relative = f"/object/sign/{path}?token={token}"
    if problem == "external":
        relative = "https://external.example" + relative
    elif problem == "fragment":
        relative += "#fragment"
    elif problem == "path":
        relative = relative.replace("display.jpg", "thumbnail.webp")
    elif problem == "duplicate":
        relative += "&token=other"
    elif problem == "extra":
        relative += "&download=1"
    writes = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal writes
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": config.bucket,
                    "public": problem == "public",
                    "file_size_limit": MAX_UPLOAD_BYTES,
                    "allowed_mime_types": list(UPLOAD_TYPES),
                },
            )
        writes += 1
        assert request.url.path.endswith("object/sign/" + path)
        assert json.loads(request.content) == {"expiresIn": VIEW_SECONDS}
        return httpx.Response(
            503 if problem == "provider" else 200,
            json={} if problem == "missing" else {"signedURL": relative},
        )

    storage = Storage(config, transport=httpx.MockTransport(respond))
    try:
        if problem:
            with pytest.raises(StorageError) as exc:
                storage.sign_view(key)
            assert token not in str(exc.value)
        else:
            result = storage.sign_view(key)
            assert result.expires_at.timestamp() == expiry and token not in repr(result)
            assert result.url.get_secret_value() == config.url + relative
        assert writes == (0 if problem == "public" else 1)
        for bad_key in (new_staging_key(uuid4()), "../source", key.replace("v1", "v2")):
            with pytest.raises(ValueError):
                storage.sign_view(bad_key)
        for seconds in (0, 121, True):
            with pytest.raises(ValueError):
                storage.sign_view(key, seconds=seconds)
    finally:
        storage.close()
