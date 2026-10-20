"""Link an owned wine to a public release without weakening private ownership."""

import sqlalchemy as sa
from alembic import op

revision = "0023_catalog_capture"
down_revision = "0022_public_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wine_releases", sa.Column("catalog_release_id", sa.Uuid()), schema="app")
    op.create_foreign_key(
        "fk_wine_release_catalog",
        "wine_releases",
        "catalog_releases",
        ["catalog_release_id"],
        ["id"],
        source_schema="app",
        referent_schema="app",
    )
    # Ordinary NULL-distinct uniqueness preserves all existing manual identities.
    op.create_unique_constraint(
        "uq_owned_catalog_release",
        "wine_releases",
        ["owner_id", "catalog_release_id"],
        schema="app",
    )


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM app.wine_releases WHERE catalog_release_id IS NOT NULL) THEN
                RAISE EXCEPTION 'Owned catalog links exist; retain the additive schema';
            END IF;
        END $$
    """)
    op.drop_constraint("uq_owned_catalog_release", "wine_releases", schema="app", type_="unique")
    op.drop_constraint("fk_wine_release_catalog", "wine_releases", schema="app", type_="foreignkey")
    op.drop_column("wine_releases", "catalog_release_id", schema="app")
