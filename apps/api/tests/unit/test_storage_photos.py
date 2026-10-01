import secrets
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from wine_journal.integrations.storage import (
    ObjectChanged,
    ObjectInfo,
    OutputConflict,
    Storage,
    StorageError,
    StorageSettings,
    new_staging_key,
)


def info_for(key: str, contents: bytes) -> ObjectInfo:
    return ObjectInfo(
        id=uuid4(), name=key, size=len(contents), content_type="image/jpeg", etag="version-one"
    )


class IsolatedSettings(StorageSettings):
    model_config = SettingsConfigDict(env_file=None)


def configured(transport: httpx.MockTransport) -> Storage:
    return Storage(
        IsolatedSettings(
            url="https://storage.example/storage/v1",
            service_key=SecretStr(secrets.token_urlsafe(32)),
        ),
        transport=transport,
    )


def image_response(info: ObjectInfo, contents: bytes, **headers: str) -> httpx.Response:
    return httpx.Response(
        200,
        headers={
            "content-type": info.content_type,
            "content-length": str(info.size),
            "etag": f'"{info.etag}"',
            **headers,
        },
        stream=httpx.ByteStream(contents),
    )


@pytest.mark.parametrize(
    "problem",
    [
        None,
        "identity-before",
        "identity-after",
        "size",
        "type",
        "etag",
        "encoding",
        "overrun",
        "short",
        "redirect",
        "timeout",
        "limit",
        "deadline",
    ],
)
def test_bounded_private_download(problem: str | None, monkeypatch: pytest.MonkeyPatch) -> None:
    contents = b"synthetic-image"
    info = info_for(new_staging_key(uuid4()), contents)
    calls: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if "/info/" in request.url.path:
            changed = problem == "identity-before" or (
                problem == "identity-after" and len(calls) > 1
            )
            return httpx.Response(
                200,
                json=info.model_copy(update={"id": uuid4()} if changed else {}).model_dump(
                    mode="json"
                ),
            )
        assert request.headers["accept-encoding"] == "identity"
        assert "/object/authenticated/" in request.url.path
        if problem == "timeout":
            raise httpx.ReadTimeout("provider-private-body")
        if problem == "redirect":
            return httpx.Response(302, headers={"location": "https://external.example"})
        if problem == "deadline":
            monkeypatch.setattr("wine_journal.integrations.storage.time.monotonic", lambda: 100.0)
        headers = {
            "size": {"content-length": "999"},
            "type": {"content-type": "image/png"},
            "etag": {"etag": "other"},
            "encoding": {"content-encoding": "gzip"},
        }.get(problem or "", {})
        body = (
            contents + b"extra"
            if problem == "overrun"
            else contents[:-1]
            if problem == "short"
            else contents
        )
        return image_response(info, body, **headers)

    if problem == "deadline":
        monkeypatch.setattr("wine_journal.integrations.storage.time.monotonic", lambda: 1.0)
    storage = configured(httpx.MockTransport(respond))
    try:
        if problem:
            with pytest.raises(StorageError) as exc:
                storage.download(info, limit=1 if problem == "limit" else 100)
            assert "provider-private-body" not in str(exc.value)
        else:
            assert storage.download(info) == contents
            assert len(calls) == 3
    finally:
        storage.close()


@pytest.mark.parametrize(
    "outcome", ["success", "exists", "lost-response", "different", "changed", "missing"]
)
def test_immutable_write_reconciles_uncertain_results(outcome: str) -> None:
    contents = b"synthetic-image"
    key = f"photos/{uuid4().hex}/v1/display.jpg"
    info = info_for(key, contents)
    writes = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal writes
        if request.method == "POST":
            writes += 1
            assert request.headers["x-upsert"] == "false"
            assert request.headers["content-type"] == "image/jpeg"
            assert request.content == contents
            if outcome == "lost-response":
                raise httpx.ReadTimeout("private")
            return httpx.Response(200 if outcome == "success" else 400, json={})
        if "/info/" in request.url.path:
            if outcome == "missing":
                return httpx.Response(404, json={})
            return httpx.Response(200, json=info.model_dump(mode="json"))
        return image_response(
            info,
            b"different-image" if outcome == "different" else contents,
            **({"etag": "replaced"} if outcome == "changed" else {}),
        )

    storage = configured(httpx.MockTransport(respond))
    try:
        if outcome in {"different", "changed", "missing"}:
            with pytest.raises(OutputConflict if outcome == "different" else StorageError):
                storage.put_derivative(key, contents)
        else:
            storage.put_derivative(key, contents)
        assert writes == 1
        with pytest.raises(ValueError):
            storage.sign_upload(key)
        with pytest.raises(ValueError):
            storage.put_derivative(new_staging_key(uuid4()), contents)
        with pytest.raises(ValueError):
            storage.put_derivative(key, b"x" * (5 * 1024 * 1024 + 1))
        with pytest.raises(ObjectChanged):
            storage.download(info.model_copy(update={"size": 0}))
        assert writes == 1
    finally:
        storage.close()
