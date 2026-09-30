"""Associate entries with an optional same-owner occasion."""

import sqlalchemy as sa
from alembic import op

revision = "0008_entry_occasion"
down_revision = "0007_occasions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("drinking_entries", sa.Column("occasion_id", sa.Uuid()), schema="app")
    op.create_foreign_key(
        "fk_entry_occasion_owner",
        "drinking_entries",
        "occasions",
        ["owner_id", "occasion_id"],
        ["owner_id", "id"],
        source_schema="app",
        referent_schema="app",
    )
    op.create_index(
        "ix_entries_occasion", "drinking_entries", ["owner_id", "occasion_id"], schema="app"
    )


def downgrade() -> None:
    op.drop_index("ix_entries_occasion", table_name="drinking_entries", schema="app")
    op.drop_constraint(
        "fk_entry_occasion_owner", "drinking_entries", schema="app", type_="foreignkey"
    )
    op.drop_column("drinking_entries", "occasion_id", schema="app")
