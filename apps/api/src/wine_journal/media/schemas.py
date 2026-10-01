from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from wine_journal.integrations.storage import MAX_UPLOAD_BYTES


class UploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel)
    size_bytes: int = Field(strict=True, ge=1, le=MAX_UPLOAD_BYTES)
    content_type: Literal["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"]


class UploadGrant(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    asset_id: UUID
    upload_url: str = Field(repr=False)
    expires_at: datetime
    method: Literal["PUT"] = "PUT"
    content_type: str


class UploadCompletion(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    asset_id: UUID
    state: Literal["PROCESSING", "READY", "FAILED"]


class CompleteUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PhotoStatus(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    asset_id: UUID
    state: Literal["PENDING", "PROCESSING", "READY", "FAILED"]
    error_code: Literal["PHOTO_PROCESSING_FAILED"] | None = None
    width: int | None = None
    height: int | None = None


class PhotoViewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variant: Literal["display", "thumbnail"]


class PhotoView(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    asset_id: UUID
    variant: Literal["display", "thumbnail"]
    view_url: str = Field(repr=False)
    expires_at: datetime
