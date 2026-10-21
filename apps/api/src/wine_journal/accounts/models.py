from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from wine_journal.core.database import Base


class AppUser(Base):
    __tablename__ = "app_users"
    __table_args__ = (
        UniqueConstraint("auth_issuer", "auth_subject", name="uq_app_users_identity"),
        CheckConstraint("state IN ('ACTIVE', 'DISABLED')", name="ck_app_users_state"),
        {"schema": "app"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    auth_issuer: Mapped[str] = mapped_column(String(512))
    auth_subject: Mapped[UUID] = mapped_column()
    state: Mapped[str] = mapped_column(String(16), server_default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
