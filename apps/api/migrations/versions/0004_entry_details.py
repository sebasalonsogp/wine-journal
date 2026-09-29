"""Optional private entry details and optimistic edit versions."""

import sqlalchemy as sa
from alembic import op

revision = "0004_entry_details"
down_revision = "0003_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in [
        sa.Column("local_time", sa.Time(), nullable=True),
        sa.Column("timezone", sa.String(100), nullable=True),
        sa.Column("location_label", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    ]:
        op.add_column("drinking_entries", column, schema="app")
    op.create_check_constraint("ck_entry_version", "drinking_entries", "version > 0", schema="app")
    op.create_check_constraint(
        "ck_entry_time_zone",
        "drinking_entries",
        "(local_time IS NULL) = (timezone IS NULL)",
        schema="app",
    )
    op.execute(
        "GRANT UPDATE (consumed_date, local_time, timezone, location_label, notes, version) "
        "ON app.drinking_entries TO wine_api"
    )


def downgrade() -> None:
    op.execute(
        "REVOKE UPDATE (consumed_date, local_time, timezone, location_label, notes, version) "
        "ON app.drinking_entries FROM wine_api"
    )
    op.drop_constraint("ck_entry_time_zone", "drinking_entries", schema="app")
    op.drop_constraint("ck_entry_version", "drinking_entries", schema="app")
    for column in ["version", "notes", "location_label", "timezone", "local_time"]:
        op.drop_column("drinking_entries", column, schema="app")
