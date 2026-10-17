"""Private entries and transactional save intents."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_entries"
down_revision = "0002_private_wines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_wines",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("release_id", sa.Uuid(), nullable=False),
        sa.UniqueConstraint("owner_id", "id", name="uq_user_wines_owner"),
        sa.UniqueConstraint("owner_id", "release_id", name="uq_user_wines_release"),
        sa.ForeignKeyConstraint(
            ["owner_id", "release_id"], ["app.wine_releases.owner_id", "app.wine_releases.id"]
        ),
        schema="app",
    )
    op.create_table(
        "drinking_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("user_wine_id", sa.Uuid(), nullable=False),
        sa.Column("consumed_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "user_wine_id"], ["app.user_wines.owner_id", "app.user_wines.id"]
        ),
        schema="app",
    )
    op.create_index(
        "ix_entries_wine_date",
        "drinking_entries",
        ["owner_id", "user_wine_id", "consumed_date", "id"],
        schema="app",
    )
    op.create_table(
        "entry_saves",
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("app.app_users.id"), primary_key=True),
        sa.Column("key", sa.Uuid(), primary_key=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response", JSONB()),
        schema="app",
    )
    op.execute("REVOKE ALL ON app.user_wines, app.drinking_entries, app.entry_saves FROM PUBLIC")
    op.execute("GRANT SELECT, INSERT ON app.user_wines, app.drinking_entries TO wine_api")
    op.execute("GRANT SELECT, INSERT, UPDATE ON app.entry_saves TO wine_api")


def downgrade() -> None:
    op.drop_table("entry_saves", schema="app")
    op.drop_table("drinking_entries", schema="app")
    op.drop_table("user_wines", schema="app")
