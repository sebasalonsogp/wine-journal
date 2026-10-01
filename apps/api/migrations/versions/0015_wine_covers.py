"""Personal cover references with independent optimistic revisions."""

import sqlalchemy as sa
from alembic import op

revision = "0015_wine_covers"
down_revision = "0014_entry_photos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_wines", sa.Column("cover_asset_id", sa.Uuid()), schema="app")
    op.add_column(
        "user_wines",
        sa.Column("cover_version", sa.Integer(), nullable=False, server_default="0"),
        schema="app",
    )
    op.create_check_constraint(
        "ck_wine_cover_version", "user_wines", "cover_version >= 0", schema="app"
    )
    op.create_foreign_key(
        "fk_wine_cover_owner",
        "user_wines",
        "upload_assets",
        ["owner_id", "cover_asset_id"],
        ["owner_id", "id"],
        source_schema="app",
        referent_schema="app",
    )
    op.execute("GRANT UPDATE (cover_asset_id, cover_version) ON app.user_wines TO wine_api")


def downgrade() -> None:
    op.drop_constraint("fk_wine_cover_owner", "user_wines", schema="app", type_="foreignkey")
    op.drop_constraint("ck_wine_cover_version", "user_wines", schema="app", type_="check")
    op.drop_column("user_wines", "cover_version", schema="app")
    op.drop_column("user_wines", "cover_asset_id", schema="app")
