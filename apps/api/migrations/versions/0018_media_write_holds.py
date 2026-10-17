"""Retain cleanup holds for derivative requests without a durable acknowledgement."""

import sqlalchemy as sa
from alembic import op

revision = "0018_media_write_holds"
down_revision = "0017_media_retirement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing assets and inserts from old workers lack complete write accounting.
    # New application inserts explicitly start at zero; never infer safety from age.
    op.add_column(
        "upload_assets",
        sa.Column("unsettled_writes", sa.Integer(), nullable=False, server_default="1"),
        schema="app",
    )
    op.create_check_constraint(
        "ck_upload_writes", "upload_assets", "unsettled_writes >= 0", schema="app"
    )
    op.execute("GRANT UPDATE (unsettled_writes) ON app.upload_assets TO wine_api")


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM app.upload_assets WHERE unsettled_writes > 0) THEN
                RAISE EXCEPTION 'Unresolved media writes exist; retain the write holds';
            END IF;
        END $$
    """)
    op.drop_constraint("ck_upload_writes", "upload_assets", schema="app")
    op.drop_column("upload_assets", "unsettled_writes", schema="app")
