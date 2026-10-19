"""Retain exact derivative write identities and immutable acknowledgements."""

import sqlalchemy as sa
from alembic import op

revision = "0021_photo_write_attempts"
down_revision = "0020_media_quota_release"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Never backfill identities or clear counters: historical requests are unknown.
    op.create_table(
        "photo_write_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("lease_token", sa.Uuid(), nullable=False),
        sa.Column("derivative", sa.String(16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["owner_id", "asset_id"],
            ["app.upload_assets.owner_id", "app.upload_assets.id"],
            name="fk_photo_write_asset_owner",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("derivative IN ('display', 'thumbnail')", name="ck_photo_write_kind"),
        schema="app",
    )
    op.create_index(
        "ix_photo_write_asset", "photo_write_attempts", ["owner_id", "asset_id"], schema="app"
    )
    op.execute("REVOKE ALL ON app.photo_write_attempts FROM PUBLIC")
    op.execute("GRANT SELECT, INSERT ON app.photo_write_attempts TO wine_api")
    op.execute("GRANT UPDATE (acknowledged_at) ON app.photo_write_attempts TO wine_api")
    op.execute("""
        CREATE FUNCTION app.keep_photo_write_ack() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        BEGIN
            IF OLD.acknowledged_at IS NOT NULL
               AND NEW.acknowledged_at IS DISTINCT FROM OLD.acknowledged_at THEN
                RAISE EXCEPTION 'Write acknowledgement is immutable' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER keep_photo_write_ack BEFORE UPDATE OF acknowledged_at
        ON app.photo_write_attempts FOR EACH ROW EXECUTE FUNCTION app.keep_photo_write_ack()
    """)
    op.execute("REVOKE ALL ON FUNCTION app.keep_photo_write_ack() FROM PUBLIC")


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM app.photo_write_attempts) THEN
                RAISE EXCEPTION 'Write attempt evidence exists; retain the ledger';
            END IF;
        END $$
    """)
    op.drop_table("photo_write_attempts", schema="app")
    op.execute("DROP FUNCTION app.keep_photo_write_ack()")
