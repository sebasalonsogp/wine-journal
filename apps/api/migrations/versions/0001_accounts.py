"""Application identity and its least-privilege runtime grants."""

import sqlalchemy as sa
from alembic import op

revision = "0001_accounts"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("auth_issuer", sa.String(512), nullable=False),
        sa.Column("auth_subject", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("auth_issuer", "auth_subject", name="uq_app_users_identity"),
        sa.CheckConstraint("state IN ('ACTIVE', 'DISABLED')", name="ck_app_users_state"),
        schema="app",
    )
    op.execute("REVOKE ALL ON app.app_users FROM PUBLIC")
    op.execute("GRANT SELECT, INSERT, UPDATE ON app.app_users TO wine_api")


def downgrade() -> None:
    op.drop_table("app_users", schema="app")
