"""Allow the API to update only the entry occasion association."""

from alembic import op

revision = "0009_entry_association"
down_revision = "0008_entry_occasion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT UPDATE (occasion_id) ON app.drinking_entries TO wine_api")


def downgrade() -> None:
    op.execute("REVOKE UPDATE (occasion_id) ON app.drinking_entries FROM wine_api")
