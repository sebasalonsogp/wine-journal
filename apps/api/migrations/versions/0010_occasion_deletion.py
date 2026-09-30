"""Allow explicit occasion removal without cascading entry deletion."""

from alembic import op

revision = "0010_occasion_deletion"
down_revision = "0009_entry_association"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT DELETE ON app.occasions TO wine_api")


def downgrade() -> None:
    op.execute("REVOKE DELETE ON app.occasions FROM wine_api")
