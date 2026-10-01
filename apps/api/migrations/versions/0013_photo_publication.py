"""Versioned, bounded photo publication with fixed failure outcomes."""

import sqlalchemy as sa
from alembic import op

revision = "0013_photo_publication"
down_revision = "0012_media_uploads"
branch_labels = None
depends_on = None

INTEGERS = (
    "display_bytes",
    "thumbnail_bytes",
    "width",
    "height",
    "thumbnail_width",
    "thumbnail_height",
)
OUTPUTS = (*INTEGERS, "display_sha256", "thumbnail_sha256", "processing_error")
CHECKS = {
    "ck_photo_version": "processing_version = 1",
    "ck_photo_bytes": (
        "display_bytes BETWEEN 1 AND 5242880 AND thumbnail_bytes BETWEEN 1 AND 524288"
    ),
    "ck_photo_dimensions": (
        "width BETWEEN 1 AND 2048 AND height BETWEEN 1 AND 2048 "
        "AND thumbnail_width BETWEEN 1 AND 480 AND thumbnail_height BETWEEN 1 AND 480"
    ),
    "ck_photo_hashes": "display_sha256 ~ '^[0-9a-f]{64}$' AND thumbnail_sha256 ~ '^[0-9a-f]{64}$'",
    "ck_photo_ready": (
        "state != 'READY' OR (display_bytes IS NOT NULL AND thumbnail_bytes IS NOT NULL "
        "AND width IS NOT NULL AND height IS NOT NULL AND thumbnail_width IS NOT NULL "
        "AND thumbnail_height IS NOT NULL AND display_sha256 IS NOT NULL "
        "AND thumbnail_sha256 IS NOT NULL AND object_id IS NOT NULL AND object_etag IS NOT NULL)"
    ),
    "ck_photo_error": (
        "processing_error IN ('INPUT_BYTES', 'PIXEL_LIMIT', 'INVALID_IMAGE', 'COLOR_PROFILE', "
        "'OUTPUT_BYTES', 'RESOURCE_LIMIT', 'DECODER_PROTOCOL', 'SOURCE_CHANGED', "
        "'SOURCE_TYPE_MISMATCH', 'OUTPUT_CONFLICT', 'ACCOUNT_UNAVAILABLE', 'PROCESSING_FAILED')"
    ),
    "ck_photo_failed": "(state = 'FAILED') = (processing_error IS NOT NULL)",
}


def upgrade() -> None:
    op.add_column(
        "upload_assets",
        sa.Column("processing_version", sa.Integer(), nullable=False, server_default="1"),
        schema="app",
    )
    for name in INTEGERS:
        op.add_column("upload_assets", sa.Column(name, sa.Integer()), schema="app")
    for name, size in (("display_sha256", 64), ("thumbnail_sha256", 64), ("processing_error", 32)):
        op.add_column("upload_assets", sa.Column(name, sa.String(size)), schema="app")
    op.execute(
        "UPDATE app.upload_assets SET processing_error = 'PROCESSING_FAILED' WHERE state = 'FAILED'"
    )
    for name, condition in CHECKS.items():
        op.create_check_constraint(name, "upload_assets", condition, schema="app")
    # Only lifecycle outputs are writable. Keys, ownership, version and quota stay immutable.
    op.execute(f"GRANT UPDATE ({', '.join(OUTPUTS)}) ON app.upload_assets TO wine_api")


def downgrade() -> None:
    op.execute(f"REVOKE UPDATE ({', '.join(OUTPUTS)}) ON app.upload_assets FROM wine_api")
    for name in CHECKS:
        op.drop_constraint(name, "upload_assets", schema="app", type_="check")
    for name in (*OUTPUTS, "processing_version"):
        op.drop_column("upload_assets", name, schema="app")
