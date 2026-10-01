"""Owned entry photos with independent revisions and retry-safe removal."""

import sqlalchemy as sa
from alembic import op

revision = "0014_entry_photos"
down_revision = "0013_photo_publication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("drinking_entries", "upload_assets"):
        op.create_unique_constraint(f"uq_{table}_owner", table, ["owner_id", "id"], schema="app")
    op.create_table(
        "entry_photos",
        sa.Column("entry_id", sa.Uuid(), primary_key=True),
        sa.Column("asset_id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("caption", sa.String(500)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("removed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "entry_id"],
            ["app.drinking_entries.owner_id", "app.drinking_entries.id"],
            name="fk_entry_photo_entry_owner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "asset_id"],
            ["app.upload_assets.owner_id", "app.upload_assets.id"],
            name="fk_entry_photo_asset_owner",
        ),
        sa.CheckConstraint("version > 0", name="ck_entry_photo_version"),
        schema="app",
    )
    op.create_index("ix_entry_photos_asset", "entry_photos", ["owner_id", "asset_id"], schema="app")
    op.execute("GRANT SELECT, INSERT ON app.entry_photos TO wine_api")
    op.execute("GRANT UPDATE (caption, version, removed) ON app.entry_photos TO wine_api")


def downgrade() -> None:
    op.drop_table("entry_photos", schema="app")
    for table in ("drinking_entries", "upload_assets"):
        op.drop_constraint(f"uq_{table}_owner", table, type_="unique", schema="app")
