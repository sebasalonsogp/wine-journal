"""Persist bounded cleanup retries and revisit tombstones for late objects."""

import sqlalchemy as sa
from alembic import op

revision = "0019_media_sweep"
down_revision = "0018_media_write_holds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "upload_assets", sa.Column("cleanup_attempted_at", sa.DateTime(timezone=True)), schema="app"
    )
    op.create_index(
        "ix_upload_cleanup_due",
        "upload_assets",
        [sa.text("coalesce(cleanup_attempted_at, retired_at)"), "id"],
        schema="app",
        postgresql_where=sa.text("retired_at IS NOT NULL"),
    )
    op.execute("GRANT UPDATE (cleanup_attempted_at) ON app.upload_assets TO wine_api")


def downgrade() -> None:
    op.drop_index("ix_upload_cleanup_due", table_name="upload_assets", schema="app")
    op.drop_column("upload_assets", "cleanup_attempted_at", schema="app")
