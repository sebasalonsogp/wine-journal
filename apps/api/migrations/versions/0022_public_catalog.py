"""Separate reviewed public wine identities from private journal identities."""

import sqlalchemy as sa
from alembic import op

revision = "0022_public_catalog"
down_revision = "0021_photo_write_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("producer", sa.String(200), nullable=False),
        sa.UniqueConstraint("key", name="uq_catalog_definition_key"),
        sa.CheckConstraint("key ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="ck_catalog_definition_key"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_catalog_definition_name"),
        sa.CheckConstraint("length(trim(producer)) > 0", name="ck_catalog_definition_producer"),
        schema="app",
    )
    op.create_table(
        "catalog_releases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "definition_id", sa.Uuid(), sa.ForeignKey("app.catalog_definitions.id"), nullable=False
        ),
        sa.Column("vintage_status", sa.String(16), nullable=False),
        sa.Column("year", sa.Integer()),
        sa.Column("edition", sa.String(120)),
        sa.UniqueConstraint(
            "definition_id",
            "vintage_status",
            "year",
            "edition",
            name="uq_catalog_release_identity",
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint(
            "(vintage_status = 'YEAR' AND year IS NOT NULL AND year BETWEEN 1000 AND 9999)"
            " OR (vintage_status IN ('NON_VINTAGE', 'MULTI_VINTAGE') AND year IS NULL)",
            name="ck_catalog_release_vintage",
        ),
        sa.CheckConstraint(
            "edition IS NULL OR length(trim(edition)) > 0", name="ck_catalog_edition"
        ),
        schema="app",
    )
    op.create_table(
        "catalog_sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "release_id", sa.Uuid(), sa.ForeignKey("app.catalog_releases.id"), nullable=False
        ),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("retrieved_on", sa.Date(), nullable=False),
        sa.Column("market", sa.String(16), nullable=False),
        sa.Column("evidence_status", sa.String(16), nullable=False),
        sa.UniqueConstraint("release_id", "url", "retrieved_on", name="uq_catalog_source"),
        sa.CheckConstraint("url LIKE 'https://%'", name="ck_catalog_source_https"),
        sa.CheckConstraint("market = 'UNVERIFIED'", name="ck_catalog_source_market"),
        sa.CheckConstraint("evidence_status = 'SOURCE_ONLY'", name="ck_catalog_source_evidence"),
        schema="app",
    )
    for table in ("catalog_definitions", "catalog_releases", "catalog_sources"):
        op.execute(f"REVOKE ALL ON app.{table} FROM PUBLIC, wine_api")
        op.execute(f"GRANT SELECT ON app.{table} TO wine_api")


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM app.catalog_definitions) THEN
                RAISE EXCEPTION 'Catalog data exists; retain the additive schema';
            END IF;
        END $$
    """)
    op.drop_table("catalog_sources", schema="app")
    op.drop_table("catalog_releases", schema="app")
    op.drop_table("catalog_definitions", schema="app")
