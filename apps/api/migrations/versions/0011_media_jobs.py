"""Durable job claims, bounded attempts and fenced leases."""

import sqlalchemy as sa
from alembic import op

revision = "0011_media_jobs"
down_revision = "0010_occasion_deletion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("app.app_users.id"), nullable=False),
        sa.Column("operation_key", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(16), server_default="PENDING", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column(
            "run_after", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("error_code", sa.String(32)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("owner_id", "operation_key", name="uq_jobs_operation"),
        sa.CheckConstraint(
            "state IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')", name="ck_job_state"
        ),
        sa.CheckConstraint(
            "max_attempts BETWEEN 1 AND 10 AND attempts BETWEEN 0 AND max_attempts",
            name="ck_job_attempts",
        ),
        sa.CheckConstraint(
            "(state = 'RUNNING') = (lease_token IS NOT NULL AND lease_until IS NOT NULL) "
            "AND ((lease_token IS NULL) = (lease_until IS NULL))",
            name="ck_job_lease",
        ),
        sa.CheckConstraint("kind ~ '^[a-z][a-z0-9_]{0,63}$'", name="ck_job_kind"),
        sa.CheckConstraint(
            "error_code IN ('HANDLER_FAILED', 'UNSUPPORTED_KIND', 'LEASE_EXPIRED')",
            name="ck_job_error",
        ),
        schema="app",
    )
    op.create_index(
        "ix_jobs_pending",
        "jobs",
        ["run_after", "id"],
        schema="app",
        postgresql_where=sa.text("state = 'PENDING'"),
    )
    op.create_index(
        "ix_jobs_expired",
        "jobs",
        ["lease_until", "id"],
        schema="app",
        postgresql_where=sa.text("state = 'RUNNING'"),
    )
    op.execute("REVOKE ALL ON app.jobs FROM PUBLIC")
    op.execute("GRANT SELECT, INSERT ON app.jobs TO wine_api")
    op.execute(
        "GRANT UPDATE (state, attempts, run_after, lease_until, lease_token, error_code) "
        "ON app.jobs TO wine_api"
    )


def downgrade() -> None:
    op.drop_table("jobs", schema="app")
