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


@dataclass(frozen=True)
class UploadCapability:
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
        self, method: str, path: str, body: object = None
    ) -> tuple[int, dict[str, object]]:
        started = time.monotonic()
        try:
            with self._http.stream(method, path, json=body) as response:
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
        if not KEY_PATTERN.fullmatch(key):
            raise ValueError("Invalid staging key.")
        return f"{self.settings.bucket}/{key}"

    def sign_upload(self, key: str) -> UploadCapability:
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
