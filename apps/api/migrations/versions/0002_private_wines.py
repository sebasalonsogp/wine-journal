"""Owner-only provisional wine definitions and releases."""

import sqlalchemy as sa
from alembic import op

revision = "0002_private_wines"
down_revision = "0001_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wine_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("app.app_users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("producer", sa.String(200)),
        sa.UniqueConstraint("owner_id", "id", name="uq_wine_definitions_owner"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_wine_definitions_name"),
        schema="app",
    )
    op.create_index(
        "ix_app_wine_definitions_owner_id", "wine_definitions", ["owner_id"], schema="app"
    )
    op.create_table(
        "wine_releases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("definition_id", sa.Uuid(), nullable=False),
        sa.Column("vintage_status", sa.String(16), nullable=False),
        sa.Column("year", sa.Integer()),
        sa.Column("edition", sa.String(120)),
        sa.UniqueConstraint("owner_id", "id", name="uq_wine_releases_owner"),
        sa.ForeignKeyConstraint(
            ["owner_id", "definition_id"],
            ["app.wine_definitions.owner_id", "app.wine_definitions.id"],
        ),
        sa.CheckConstraint(
            "(vintage_status = 'YEAR' AND year IS NOT NULL AND year BETWEEN 1000 AND 9999)"
            " OR (vintage_status IN ('UNKNOWN', 'NON_VINTAGE', 'MULTI_VINTAGE') AND year IS NULL)",
            name="ck_wine_releases_vintage",
        ),
        schema="app",
    )
    op.create_index(
        "ix_app_wine_releases_definition_id", "wine_releases", ["definition_id"], schema="app"
    )
    op.execute("REVOKE ALL ON app.wine_definitions, app.wine_releases FROM PUBLIC")
    op.execute("GRANT SELECT, INSERT ON app.wine_definitions, app.wine_releases TO wine_api")


def downgrade() -> None:
    op.drop_table("wine_releases", schema="app")
    op.drop_table("wine_definitions", schema="app")
