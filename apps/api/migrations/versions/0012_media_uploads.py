"""Private upload reservations and immutable source object identities."""

import sqlalchemy as sa
from alembic import op

revision = "0012_media_uploads"
down_revision = "0011_media_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "upload_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("app.app_users.id"), nullable=False),
        sa.Column("operation_key", sa.Uuid(), nullable=False),
        sa.Column("object_key", sa.String(128), nullable=False),
        sa.Column("declared_bytes", sa.Integer(), nullable=False),
        sa.Column("declared_type", sa.String(32), nullable=False),
        sa.Column("reserved_bytes", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(16), server_default="PENDING", nullable=False),
        sa.Column("grant_expires_at", sa.DateTime(timezone=True)),
        sa.Column("unsettled_grants", sa.Integer(), server_default="0", nullable=False),
        sa.Column("object_id", sa.Uuid()),
        sa.Column("object_etag", sa.String(256)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("owner_id", "operation_key", name="uq_upload_operation"),
        sa.UniqueConstraint("object_key", name="uq_upload_object"),
        sa.CheckConstraint("declared_bytes BETWEEN 1 AND 20971520", name="ck_upload_size"),
        sa.CheckConstraint("reserved_bytes >= 26738688", name="ck_upload_reservation"),
        sa.CheckConstraint("unsettled_grants >= 0", name="ck_upload_grants"),
        sa.CheckConstraint(
            "declared_type IN ('image/jpeg', 'image/png', 'image/webp', "
            "'image/heic', 'image/heif')",
            name="ck_upload_type",
        ),
        sa.CheckConstraint(
            "state IN ('PENDING', 'PROCESSING', 'READY', 'FAILED')", name="ck_upload_state"
        ),
        sa.CheckConstraint(
            "object_key ~ '^staging/[0-9a-f]{32}/[0-9a-f]{32}$'", name="ck_upload_key"
        ),
        sa.CheckConstraint(
            "state != 'PROCESSING' OR (object_id IS NOT NULL AND object_etag IS NOT NULL)",
            name="ck_upload_verified",
        ),
        schema="app",
    )
    op.execute("REVOKE ALL ON app.upload_assets FROM PUBLIC")
    op.execute("GRANT SELECT, INSERT ON app.upload_assets TO wine_api")
    op.execute(
        "GRANT UPDATE (state, grant_expires_at, unsettled_grants, object_id, object_etag) "
        "ON app.upload_assets TO wine_api"
    )


def downgrade() -> None:
    op.drop_table("upload_assets", schema="app")
