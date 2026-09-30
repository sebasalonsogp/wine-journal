from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from wine_journal.accounts.models import AppUser
from wine_journal.core.database import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("owner_id", "operation_key", name="uq_jobs_operation"),
        CheckConstraint(
            "state IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')", name="ck_job_state"
        ),
        CheckConstraint(
            "max_attempts BETWEEN 1 AND 10 AND attempts BETWEEN 0 AND max_attempts",
            name="ck_job_attempts",
        ),
        CheckConstraint(
            "(state = 'RUNNING') = (lease_token IS NOT NULL AND lease_until IS NOT NULL) "
            "AND ((lease_token IS NULL) = (lease_until IS NULL))",
            name="ck_job_lease",
        ),
        CheckConstraint("kind ~ '^[a-z][a-z0-9_]{0,63}$'", name="ck_job_kind"),
        CheckConstraint(
            "error_code IN ('HANDLER_FAILED', 'UNSUPPORTED_KIND', 'LEASE_EXPIRED')",
            name="ck_job_error",
        ),
        Index("ix_jobs_pending", "run_after", "id", postgresql_where=text("state = 'PENDING'")),
        Index("ix_jobs_expired", "lease_until", "id", postgresql_where=text("state = 'RUNNING'")),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey(AppUser.id))
    operation_key: Mapped[UUID] = mapped_column()
    kind: Mapped[str] = mapped_column(String(64))
    reference_id: Mapped[UUID] = mapped_column()
    state: Mapped[str] = mapped_column(String(16), server_default="PENDING")
    attempts: Mapped[int] = mapped_column(server_default="0")
    max_attempts: Mapped[int] = mapped_column(server_default="5")
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None] = mapped_column()
    error_code: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
