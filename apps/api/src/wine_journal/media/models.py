from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from wine_journal.accounts.models import AppUser
from wine_journal.core.database import Base


class UploadAsset(Base):
    __tablename__ = "upload_assets"
    __table_args__ = (
        UniqueConstraint("owner_id", "operation_key", name="uq_upload_operation"),
        UniqueConstraint("object_key", name="uq_upload_object"),
        CheckConstraint("declared_bytes BETWEEN 1 AND 20971520", name="ck_upload_size"),
        CheckConstraint("reserved_bytes >= 26738688", name="ck_upload_reservation"),
        CheckConstraint("unsettled_grants >= 0", name="ck_upload_grants"),
        CheckConstraint(
            "declared_type IN ('image/jpeg', 'image/png', 'image/webp', "
            "'image/heic', 'image/heif')",
            name="ck_upload_type",
        ),
        CheckConstraint(
            "state IN ('PENDING', 'PROCESSING', 'READY', 'FAILED')", name="ck_upload_state"
        ),
        CheckConstraint("object_key ~ '^staging/[0-9a-f]{32}/[0-9a-f]{32}$'", name="ck_upload_key"),
        CheckConstraint(
            "state != 'PROCESSING' OR (object_id IS NOT NULL AND object_etag IS NOT NULL)",
            name="ck_upload_verified",
        ),
        CheckConstraint("processing_version = 1", name="ck_photo_version"),
        CheckConstraint(
            "display_bytes BETWEEN 1 AND 5242880 AND thumbnail_bytes BETWEEN 1 AND 524288",
            name="ck_photo_bytes",
        ),
        CheckConstraint(
            "width BETWEEN 1 AND 2048 AND height BETWEEN 1 AND 2048 "
            "AND thumbnail_width BETWEEN 1 AND 480 AND thumbnail_height BETWEEN 1 AND 480",
            name="ck_photo_dimensions",
        ),
        CheckConstraint(
            "display_sha256 ~ '^[0-9a-f]{64}$' AND thumbnail_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_photo_hashes",
        ),
        CheckConstraint(
            "state != 'READY' OR (display_bytes IS NOT NULL AND thumbnail_bytes IS NOT NULL "
            "AND width IS NOT NULL AND height IS NOT NULL AND thumbnail_width IS NOT NULL "
            "AND thumbnail_height IS NOT NULL AND display_sha256 IS NOT NULL "
            "AND thumbnail_sha256 IS NOT NULL AND object_id IS NOT NULL "
            "AND object_etag IS NOT NULL)",
            name="ck_photo_ready",
        ),
        CheckConstraint(
            "processing_error IN ('INPUT_BYTES', 'PIXEL_LIMIT', 'INVALID_IMAGE', 'COLOR_PROFILE', "
            "'OUTPUT_BYTES', 'RESOURCE_LIMIT', 'DECODER_PROTOCOL', 'SOURCE_CHANGED', "
            "'SOURCE_TYPE_MISMATCH', 'OUTPUT_CONFLICT', 'ACCOUNT_UNAVAILABLE', "
            "'PROCESSING_FAILED')",
            name="ck_photo_error",
        ),
        CheckConstraint(
            "(state = 'FAILED') = (processing_error IS NOT NULL)", name="ck_photo_failed"
        ),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey(AppUser.id))
    operation_key: Mapped[UUID] = mapped_column()
    object_key: Mapped[str] = mapped_column(String(128))
    declared_bytes: Mapped[int] = mapped_column()
    declared_type: Mapped[str] = mapped_column(String(32))
    reserved_bytes: Mapped[int] = mapped_column()
    state: Mapped[str] = mapped_column(String(16), server_default="PENDING")
    grant_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # A crash/timeout may leave a live capability. Cleanup must retain this reservation
    # until every signing attempt is accounted for, even after known grants expire.
    unsettled_grants: Mapped[int] = mapped_column(server_default="0")
    object_id: Mapped[UUID | None] = mapped_column()
    object_etag: Mapped[str | None] = mapped_column(String(256))
    processing_version: Mapped[int] = mapped_column(server_default="1")
    display_bytes: Mapped[int | None] = mapped_column()
    thumbnail_bytes: Mapped[int | None] = mapped_column()
    width: Mapped[int | None] = mapped_column()
    height: Mapped[int | None] = mapped_column()
    thumbnail_width: Mapped[int | None] = mapped_column()
    thumbnail_height: Mapped[int | None] = mapped_column()
    display_sha256: Mapped[str | None] = mapped_column(String(64))
    thumbnail_sha256: Mapped[str | None] = mapped_column(String(64))
    processing_error: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("owner_id", "operation_key", name="uq_jobs_operation"),
        CheckConstraint(
            "state IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')", name="ck_job_state"
        ),
        CheckConstraint(
            "max_attempts BETWEEN 1 AND 10 AND attempts BETWEEN 0 AND max_attempts",
            name="ck_job_attempts",
        ),
        CheckConstraint(
            "(state = 'RUNNING') = (lease_token IS NOT NULL AND lease_until IS NOT NULL) "
            "AND ((lease_token IS NULL) = (lease_until IS NULL))",
            name="ck_job_lease",
        ),
        CheckConstraint("kind ~ '^[a-z][a-z0-9_]{0,63}$'", name="ck_job_kind"),
        CheckConstraint(
            "error_code IN ('HANDLER_FAILED', 'UNSUPPORTED_KIND', 'LEASE_EXPIRED')",
            name="ck_job_error",
        ),
        Index("ix_jobs_pending", "run_after", "id", postgresql_where=text("state = 'PENDING'")),
        Index("ix_jobs_expired", "lease_until", "id", postgresql_where=text("state = 'RUNNING'")),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey(AppUser.id))
    operation_key: Mapped[UUID] = mapped_column()
    kind: Mapped[str] = mapped_column(String(64))
    reference_id: Mapped[UUID] = mapped_column()
    state: Mapped[str] = mapped_column(String(16), server_default="PENDING")
    attempts: Mapped[int] = mapped_column(server_default="0")
    max_attempts: Mapped[int] = mapped_column(server_default="5")
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None] = mapped_column()
    error_code: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
