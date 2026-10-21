"""Allow the application to delete drinking entries, not wine identities."""

from alembic import op

revision = "0005_entry_deletion"
down_revision = "0004_entry_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT DELETE ON app.drinking_entries TO wine_api")


def downgrade() -> None:
    op.execute("REVOKE DELETE ON app.drinking_entries FROM wine_api")
