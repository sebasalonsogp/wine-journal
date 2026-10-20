"""Add reviewed barcode evidence without binding package codes to vintages."""

import sqlalchemy as sa
from alembic import op

revision = "0026_catalog_barcodes"
down_revision = "0025_wine_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "catalog_barcode_observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("gtin", sa.String(14), nullable=False),
        sa.Column(
            "definition_id", sa.Uuid(), sa.ForeignKey("app.catalog_definitions.id"), nullable=False
        ),
        sa.Column("bottle_ml", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("retrieved_on", sa.Date(), nullable=False),
        sa.Column("market", sa.String(16), nullable=False),
        sa.Column("evidence_status", sa.String(24), nullable=False),
        sa.Column("source_sha256", sa.String(64)),
        sa.UniqueConstraint(
            "gtin", "definition_id", "url", "retrieved_on", name="uq_catalog_barcode_evidence"
        ),
        sa.CheckConstraint(
            "gtin ~ '^0[0-9]{13}$' AND gtin <> '00000000000000'", name="ck_catalog_barcode_gtin"
        ),
        sa.CheckConstraint("bottle_ml BETWEEN 1 AND 30000", name="ck_catalog_barcode_size"),
        sa.CheckConstraint("url LIKE 'https://%'", name="ck_catalog_barcode_https"),
        sa.CheckConstraint("market = 'UNVERIFIED'", name="ck_catalog_barcode_market"),
        sa.CheckConstraint(
            "(evidence_status = 'WEB_TEXT' AND source_sha256 IS NULL) OR "
            "(evidence_status = 'PRODUCER_WEB_IMAGE' AND source_sha256 IS NOT NULL "
            "AND source_sha256 ~ '^[a-f0-9]{64}$')",
            name="ck_catalog_barcode_evidence",
        ),
        schema="app",
    )
    op.execute("REVOKE ALL ON app.catalog_barcode_observations FROM PUBLIC, wine_api")
    op.execute("GRANT SELECT ON app.catalog_barcode_observations TO wine_api")


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM app.catalog_barcode_observations) THEN
                RAISE EXCEPTION 'Barcode evidence exists; retain the additive schema';
            END IF;
        END $$
    """)
    op.drop_table("catalog_barcode_observations", schema="app")
