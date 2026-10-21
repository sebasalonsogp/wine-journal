"""Permit owner-constrained entry retargeting without identity updates."""

from alembic import op

revision = "0024_entry_wine"
down_revision = "0023_catalog_capture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT UPDATE (user_wine_id) ON app.drinking_entries TO wine_api")


def downgrade() -> None:
    # Revoke the capability; never undo a user's correction or delete their wine.
    op.execute("REVOKE UPDATE (user_wine_id) ON app.drinking_entries FROM wine_api")
