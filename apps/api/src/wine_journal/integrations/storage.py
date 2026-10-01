"""Concrete Supabase Storage boundary. Ownership and quota decisions belong to media."""

import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import httpx
import jwt
from pydantic import AliasChoices, BaseModel, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from wine_journal.core.config import API_DIRECTORY

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
UPLOAD_TYPES = ("image/jpeg", "image/png", "image/webp", "image/heic", "image/heif")
KEY_PATTERN = re.compile(r"staging/[0-9a-f]{32}/[0-9a-f]{32}")
DERIVATIVE_PATTERN = re.compile(r"photos/[0-9a-f]{32}/v1/(display\.jpg|thumbnail\.webp)")
VIEW_SECONDS = 120


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WINE_JOURNAL_STORAGE_",
        env_file=API_DIRECTORY / ".env.storage",
        extra="ignore",
        hide_input_in_errors=True,
    )
    url: str
    service_key: SecretStr = Field(min_length=20)
    bucket: str = Field(default="wine-journal-staging", pattern=r"^[a-z][a-z0-9-]{2,62}$")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path != "/storage/v1"
            or (parsed.scheme != "https" and not (local and parsed.scheme == "http"))
        ):
            raise ValueError("Use the HTTPS Storage endpoint; HTTP is local-only.")
        return value


class StorageError(Exception):
    """Fixed errors only: never expose provider bodies, credentials or signed URLs."""


class ObjectMissing(StorageError):
    pass


class ObjectChanged(StorageError):
    pass


class OutputConflict(StorageError):
    pass


@dataclass(frozen=True)
class UploadCapability:
    url: SecretStr
    expires_at: datetime


@dataclass(frozen=True)
class ViewCapability:
    url: SecretStr
    expires_at: datetime


class ObjectInfo(BaseModel):
    model_config = {"extra": "ignore", "frozen": True, "hide_input_in_errors": True}
    id: UUID
    name: str = Field(max_length=128)
    size: int = Field(strict=True, ge=0)
    content_type: str = Field(
        validation_alias=AliasChoices("contentType", "content_type"), max_length=128
    )
    etag: str = Field(min_length=1, max_length=256)


def new_staging_key(asset_id: UUID) -> str:
    return f"staging/{asset_id.hex}/{uuid4().hex}"


class Storage:
    def __init__(
        self, settings: StorageSettings, *, transport: httpx.BaseTransport | None = None
    ) -> None:
        self.settings = settings
        key = settings.service_key.get_secret_value()
        self._http = httpx.Client(
            base_url=settings.url + "/",
            headers={"Authorization": f"Bearer {key}", "apikey": key},
            timeout=httpx.Timeout(5, connect=3, pool=3),
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def _request(
        self,
        method: str,
        path: str,
        body: object = None,
        *,
        contents: bytes | None = None,
        content_type: str | None = None,
    ) -> tuple[int, dict[str, object]]:
        started = time.monotonic()
        try:
            headers = (
                {"Content-Type": content_type, "x-upsert": "false", "Cache-Control": "no-store"}
                if content_type
                else {}
            )
            with self._http.stream(
                method, path, json=body, content=contents, headers=headers
            ) as response:
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 16 * 1024 or time.monotonic() - started > 15:
                        raise StorageError("Invalid storage response.")
                parsed = json.loads(data)
                if not isinstance(parsed, dict):
                    raise StorageError("Invalid storage response.")
                return response.status_code, parsed
        except (httpx.HTTPError, ValueError):
            raise StorageError("Storage is temporarily unavailable.") from None

    def ensure_private_bucket(self) -> None:
        """Provision through the provider API; never rewrite a pre-existing bucket's policy."""
        status, response = self._request("GET", f"bucket/{self.settings.bucket}")
        if status == 404 or (status == 400 and response.get("code") == "NoSuchBucket"):
            status, _ = self._request(
                "POST",
                "bucket",
                {
                    "id": self.settings.bucket,
                    "name": self.settings.bucket,
                    "public": False,
                    "file_size_limit": MAX_UPLOAD_BYTES,
                    "allowed_mime_types": list(UPLOAD_TYPES),
                },
            )
            if status not in {200, 201, 409}:
                raise StorageError("Private storage provisioning failed.")
        elif status != 200:
            raise StorageError("Private storage provisioning failed.")
        self.check_private_bucket()

    def check_private_bucket(self) -> None:
        status, bucket = self._request("GET", f"bucket/{self.settings.bucket}")
        if (
            status != 200
            or bucket.get("id") != self.settings.bucket
            or bucket.get("public") is not False
            or type(bucket.get("file_size_limit")) is not int
            or bucket.get("file_size_limit") != MAX_UPLOAD_BYTES
            or bucket.get("allowed_mime_types") != list(UPLOAD_TYPES)
        ):
            raise StorageError("Private storage configuration does not match the upload contract.")

    def _object_path(self, key: str) -> str:
        if not KEY_PATTERN.fullmatch(key) and not DERIVATIVE_PATTERN.fullmatch(key):
            raise ValueError("Invalid staging key.")
        return f"{self.settings.bucket}/{key}"

    def sign_upload(self, key: str) -> UploadCapability:
        if not KEY_PATTERN.fullmatch(key):
            raise ValueError("Invalid staging key.")
        path = self._object_path(key)
        # Check configuration before issuing a capability. Provider limits are essential:
        # clients can bypass the future app completion route after obtaining a token.
        self.check_private_bucket()
        status, body = self._request("POST", f"object/upload/sign/{path}", {})
        if status != 200:
            raise StorageError("Upload authorization is temporarily unavailable.")
        try:
            relative = body["url"]
            if not isinstance(relative, str) or len(relative) > 8192:
                raise ValueError()
            parsed = urlsplit(relative)
            query = parse_qs(parsed.query, strict_parsing=True)
            if (
                parsed.scheme
                or parsed.netloc
                or parsed.fragment
                or parsed.path != f"/object/upload/sign/{path}"
                or set(query) != {"token"}
                or len(query["token"]) != 1
            ):
                raise ValueError()
            # This is provider-response validation, not authentication of user JWTs.
            claims = jwt.decode(query["token"][0], options={"verify_signature": False})
            expiry = claims.get("exp")
            now = datetime.now(UTC).timestamp()
            if (
                type(expiry) is not int
                or not now < expiry <= now + 7260
                or claims.get("url") != path
                or claims.get("upsert", False) is not False
            ):
                raise ValueError()
            return UploadCapability(
                SecretStr(self.settings.url + relative), datetime.fromtimestamp(expiry, UTC)
            )
        except (ValueError, KeyError, jwt.InvalidTokenError):
            raise StorageError("Invalid upload authorization response.") from None

    def info(self, key: str) -> ObjectInfo:
        status, body = self._request("GET", f"object/info/{self._object_path(key)}")
        if body.get("code") == "NoSuchKey" or status == 404:
            raise ObjectMissing("Uploaded object is not available.")
        if status != 200:
            raise StorageError("Storage verification is temporarily unavailable.")
        try:
            info = ObjectInfo.model_validate(body)
            if info.name != key:
                raise ValueError()
            return info
        except (ValueError, ValidationError):
            raise StorageError("Invalid object verification response.") from None

    def download(self, expected: ObjectInfo, *, limit: int = MAX_UPLOAD_BYTES) -> bytes:
        """Read exactly the verified object; cap raw bytes and never follow redirects."""
        path = self._object_path(expected.name)
        if not 0 < expected.size <= limit <= MAX_UPLOAD_BYTES:
            raise ObjectChanged("Object exceeds its download limit.")
        if self.info(expected.name) != expected:
            raise ObjectChanged("Object identity changed.")
        started = time.monotonic()
        try:
            with self._http.stream(
                "GET", f"object/authenticated/{path}", headers={"Accept-Encoding": "identity"}
            ) as response:
                if response.status_code != 200:
                    raise StorageError("Private download is temporarily unavailable.")
                if (
                    response.headers.get("content-encoding", "identity") != "identity"
                    or response.headers.get("content-type") != expected.content_type
                    or response.headers.get("etag", "").strip('"') != expected.etag.strip('"')
                    or response.headers.get("content-length") != str(expected.size)
                ):
                    raise ObjectChanged("Object headers changed.")
                data = bytearray()
                # No chunk aggregation: check the deadline after every transport read.
                for chunk in response.iter_raw():
                    if len(data) + len(chunk) > expected.size:
                        raise ObjectChanged("Object size changed.")
                    if time.monotonic() - started > 15:
                        raise StorageError("Private download timed out.")
                    data.extend(chunk)
                if len(data) != expected.size:
                    raise ObjectChanged("Object size changed.")
        except httpx.HTTPError:
            raise StorageError("Private download is temporarily unavailable.") from None
        if self.info(expected.name) != expected:
            raise ObjectChanged("Object identity changed.")
        return bytes(data)

    def put_derivative(self, key: str, contents: bytes) -> None:
        """Never overwrite. A matching existing object also completes an uncertain write."""
        if not DERIVATIVE_PATTERN.fullmatch(key):
            raise ValueError("Invalid derivative key.")
        display = key.endswith("display.jpg")
        limit = 5 * 1024 * 1024 if display else 512 * 1024
        content_type = "image/jpeg" if display else "image/webp"
        if not 0 < len(contents) <= limit:
            raise ValueError("Invalid derivative size.")
        try:
            # Readback, rather than provider-specific conflict responses, determines success.
            self._request(
                "POST",
                f"object/{self._object_path(key)}",
                contents=contents,
                content_type=content_type,
            )
        except StorageError:
            pass
        info = self.info(key)
        if (info.size, info.content_type) != (len(contents), content_type):
            raise OutputConflict("Existing derivative differs.")
        if self.download(info, limit=limit) != contents:
            raise OutputConflict("Existing derivative differs.")

    def sign_view(self, key: str, *, seconds: int = VIEW_SECONDS) -> ViewCapability:
        """Issue a bounded read capability only for server-generated derivative paths."""
        if (
            not DERIVATIVE_PATTERN.fullmatch(key)
            or type(seconds) is not int
            or not 1 <= seconds <= VIEW_SECONDS
        ):
            raise ValueError("Invalid photo viewing request.")
        path = self._object_path(key)
        self.check_private_bucket()
        status, body = self._request("POST", f"object/sign/{path}", {"expiresIn": seconds})
        if status != 200:
            raise StorageError("Photo viewing is temporarily unavailable.")
        try:
            relative = body["signedURL"]
            if not isinstance(relative, str) or len(relative) > 8192:
                raise ValueError()
            parsed = urlsplit(relative)
            query = parse_qs(parsed.query, strict_parsing=True)
            if (
                parsed.scheme
                or parsed.netloc
                or parsed.fragment
                or parsed.path != f"/object/sign/{path}"
                or set(query) != {"token"}
                or len(query["token"]) != 1
            ):
                raise ValueError()
            # Trusted-provider response validation only, never user authentication.
            claims = jwt.decode(query["token"][0], options={"verify_signature": False})
            expiry = claims.get("exp")
            now = datetime.now(UTC).timestamp()
            if (
                type(expiry) is not int
                or not now < expiry <= now + seconds + 5
                or claims.get("url") != path
            ):
                raise ValueError()
            return ViewCapability(
                SecretStr(self.settings.url + relative), datetime.fromtimestamp(expiry, UTC)
            )
        except (ValueError, KeyError, jwt.InvalidTokenError):
            raise StorageError("Invalid photo viewing response.") from None
