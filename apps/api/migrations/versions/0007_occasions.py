"""Private occasion context and transactional creation receipts."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007_occasions"
down_revision = "0006_ratings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "occasions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("app.app_users.id"), nullable=False),
        sa.Column("title", sa.String(200)),
        sa.Column("occasion_date", sa.Date(), nullable=False),
        sa.Column("local_time", sa.Time()),
        sa.Column("timezone", sa.String(100)),
        sa.Column("location_label", sa.String(200)),
        sa.Column("notes", sa.Text()),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("owner_id", "id", name="uq_occasions_owner"),
        sa.CheckConstraint("version > 0", name="ck_occasion_version"),
        sa.CheckConstraint(
            "(local_time IS NULL) = (timezone IS NULL)", name="ck_occasion_time_zone"
        ),
        schema="app",
    )
    op.create_index(
        "ix_occasions_owner_date", "occasions", ["owner_id", "occasion_date", "id"], schema="app"
    )
    op.create_table(
        "occasion_saves",
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("app.app_users.id"), primary_key=True),
        sa.Column("key", sa.Uuid(), primary_key=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response", JSONB()),
        schema="app",
    )
    op.execute("REVOKE ALL ON app.occasions, app.occasion_saves FROM PUBLIC")
    op.execute("GRANT SELECT, INSERT ON app.occasions TO wine_api")
    op.execute(
        "GRANT UPDATE (title, occasion_date, local_time, timezone, location_label, notes, version) "
        "ON app.occasions TO wine_api"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON app.occasion_saves TO wine_api")


def downgrade() -> None:
    op.drop_table("occasion_saves", schema="app")
    op.drop_table("occasions", schema="app")
