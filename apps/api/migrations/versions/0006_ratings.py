"""Private wine ratings and ordered revision history."""

import sqlalchemy as sa
from alembic import op

revision = "0006_ratings"
down_revision = "0005_entry_deletion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_wines", sa.Column("rating_units", sa.Integer()), schema="app")
    op.add_column(
        "user_wines",
        sa.Column("rating_version", sa.Integer(), server_default="0", nullable=False),
        schema="app",
    )
    op.create_check_constraint(
        "ck_wine_rating", "user_wines", "rating_units BETWEEN 2 AND 10", schema="app"
    )
    op.create_check_constraint(
        "ck_wine_rating_version", "user_wines", "rating_version >= 0", schema="app"
    )
    op.create_table(
        "rating_revisions",
        sa.Column("user_wine_id", sa.Uuid(), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("rating_units", sa.Integer()),
        sa.Column(
            "changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "user_wine_id"], ["app.user_wines.owner_id", "app.user_wines.id"]
        ),
        sa.CheckConstraint("rating_units BETWEEN 2 AND 10", name="ck_revision_rating"),
        sa.CheckConstraint("version > 0", name="ck_revision_version"),
        schema="app",
    )
    op.execute("REVOKE ALL ON app.rating_revisions FROM PUBLIC")
    op.execute("GRANT SELECT, INSERT, DELETE ON app.rating_revisions TO wine_api")
    op.execute("GRANT UPDATE (rating_units, rating_version) ON app.user_wines TO wine_api")


def downgrade() -> None:
    op.execute("REVOKE UPDATE (rating_units, rating_version) ON app.user_wines FROM wine_api")
    op.drop_table("rating_revisions", schema="app")
    op.drop_constraint("ck_wine_rating", "user_wines", schema="app")
    op.drop_constraint("ck_wine_rating_version", "user_wines", schema="app")
    op.drop_column("user_wines", "rating_units", schema="app")
    op.drop_column("user_wines", "rating_version", schema="app")
