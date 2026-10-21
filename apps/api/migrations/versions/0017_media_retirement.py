"""Fence retired uploads without deleting files, identity claims or quota."""

import sqlalchemy as sa
from alembic import op

revision = "0017_media_retirement"
down_revision = "0016_occasion_photos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "upload_assets", sa.Column("retired_at", sa.DateTime(timezone=True)), schema="app"
    )
    op.create_index(
        "ix_upload_retirement_candidates",
        "upload_assets",
        ["created_at", "id"],
        schema="app",
        postgresql_where=sa.text("retired_at IS NULL"),
    )
    op.execute("GRANT UPDATE (retired_at) ON app.upload_assets TO wine_api")
    # A durable retirement cannot be undone by a delayed writer or operation replay.
    op.execute("""
        CREATE FUNCTION app.keep_upload_retirement() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        BEGIN
            IF OLD.retired_at IS NOT NULL AND NEW.retired_at IS DISTINCT FROM OLD.retired_at THEN
                RAISE EXCEPTION 'Upload retirement is immutable' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER keep_upload_retirement BEFORE UPDATE OF retired_at
        ON app.upload_assets FOR EACH ROW EXECUTE FUNCTION app.keep_upload_retirement()
    """)
    op.execute("REVOKE ALL ON FUNCTION app.keep_upload_retirement() FROM PUBLIC")


def downgrade() -> None:
    # Dropping a fence after use could resurrect previously retired operation keys.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM app.upload_assets WHERE retired_at IS NOT NULL) THEN
                RAISE EXCEPTION 'Retired media exists; retain the retirement migration';
            END IF;
        END $$
    """)
    op.execute("DROP TRIGGER keep_upload_retirement ON app.upload_assets")
    op.execute("DROP FUNCTION app.keep_upload_retirement()")
    op.drop_index("ix_upload_retirement_candidates", table_name="upload_assets", schema="app")
    op.drop_column("upload_assets", "retired_at", schema="app")
