"""Release logical reservations after verified deletion, retaining cleanup tombstones."""

import sqlalchemy as sa
from alembic import op

revision = "0020_media_quota_release"
down_revision = "0019_media_sweep"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "upload_assets", sa.Column("quota_released_at", sa.DateTime(timezone=True)), schema="app"
    )
    op.create_check_constraint(
        "ck_upload_quota_release",
        "upload_assets",
        "quota_released_at IS NULL OR "
        "(retired_at IS NOT NULL AND cleanup_attempted_at IS NOT NULL)",
        schema="app",
    )
    op.execute("GRANT UPDATE (quota_released_at) ON app.upload_assets TO wine_api")
    op.execute("""
        CREATE FUNCTION app.keep_quota_release() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        BEGIN
            IF OLD.quota_released_at IS NOT NULL
               AND NEW.quota_released_at IS DISTINCT FROM OLD.quota_released_at THEN
                RAISE EXCEPTION 'Quota release is immutable' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER keep_quota_release BEFORE UPDATE OF quota_released_at
        ON app.upload_assets FOR EACH ROW EXECUTE FUNCTION app.keep_quota_release()
    """)
    op.execute("REVOKE ALL ON FUNCTION app.keep_quota_release() FROM PUBLIC")


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM app.upload_assets WHERE quota_released_at IS NOT NULL) THEN
                RAISE EXCEPTION 'Released quota exists; retain quota accounting';
            END IF;
        END $$
    """)
    op.execute("DROP TRIGGER keep_quota_release ON app.upload_assets")
    op.execute("DROP FUNCTION app.keep_quota_release()")
    op.drop_constraint("ck_upload_quota_release", "upload_assets", schema="app")
    op.drop_column("upload_assets", "quota_released_at", schema="app")
