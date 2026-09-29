from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from wine_journal.core.database import Base


class UserWine(Base):
    __tablename__ = "user_wines"
    __table_args__ = (
        UniqueConstraint("owner_id", "id", name="uq_user_wines_owner"),
        UniqueConstraint("owner_id", "release_id", name="uq_user_wines_release"),
        ForeignKeyConstraint(
            ["owner_id", "release_id"], ["app.wine_releases.owner_id", "app.wine_releases.id"]
        ),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column()
    release_id: Mapped[UUID] = mapped_column()


class DrinkingEntry(Base):
    __tablename__ = "drinking_entries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "user_wine_id"], ["app.user_wines.owner_id", "app.user_wines.id"]
        ),
        Index("ix_entries_wine_date", "owner_id", "user_wine_id", "consumed_date", "id"),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column()
    user_wine_id: Mapped[UUID] = mapped_column()
    consumed_date: Mapped[date] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EntrySave(Base):
    """One intent per owner/key; inserted and completed in the entry transaction."""

    __tablename__ = "entry_saves"
    __table_args__ = ({"schema": "app"},)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("app.app_users.id"), primary_key=True)
    key: Mapped[UUID] = mapped_column(primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict[str, object] | None] = mapped_column(JSONB)
