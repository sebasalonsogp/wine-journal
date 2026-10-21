"""Version private wine identity corrections and grant only editable columns."""

import sqlalchemy as sa
from alembic import op

revision = "0025_wine_identity"
down_revision = "0024_entry_wine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wine_releases",
        sa.Column("identity_version", sa.Integer(), nullable=False, server_default="0"),
        schema="app",
    )
    op.create_check_constraint(
        "ck_wine_identity_version", "wine_releases", "identity_version >= 0", schema="app"
    )
    op.execute("GRANT UPDATE (name, producer) ON app.wine_definitions TO wine_api")
    op.execute(
        "GRANT UPDATE (vintage_status, year, edition, identity_version)"
        " ON app.wine_releases TO wine_api"
    )


def downgrade() -> None:
    op.execute("REVOKE UPDATE (name, producer) ON app.wine_definitions FROM wine_api")
    op.execute(
        "REVOKE UPDATE (vintage_status, year, edition, identity_version)"
        " ON app.wine_releases FROM wine_api"
    )
    op.drop_constraint("ck_wine_identity_version", "wine_releases", schema="app")
    op.drop_column("wine_releases", "identity_version", schema="app")
