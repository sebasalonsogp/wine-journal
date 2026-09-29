from datetime import date, datetime, time
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
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
        CheckConstraint("rating_units BETWEEN 2 AND 10", name="ck_wine_rating"),
        CheckConstraint("rating_version >= 0", name="ck_wine_rating_version"),
        ForeignKeyConstraint(
            ["owner_id", "release_id"], ["app.wine_releases.owner_id", "app.wine_releases.id"]
        ),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column()
    release_id: Mapped[UUID] = mapped_column()
    rating_units: Mapped[int | None] = mapped_column()
    rating_version: Mapped[int] = mapped_column(server_default="0")


class RatingRevision(Base):
    __tablename__ = "rating_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "user_wine_id"], ["app.user_wines.owner_id", "app.user_wines.id"]
        ),
        CheckConstraint("rating_units BETWEEN 2 AND 10", name="ck_revision_rating"),
        CheckConstraint("version > 0", name="ck_revision_version"),
        {"schema": "app"},
    )
    user_wine_id: Mapped[UUID] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[UUID] = mapped_column()
    rating_units: Mapped[int | None] = mapped_column()
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DrinkingEntry(Base):
    __tablename__ = "drinking_entries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "user_wine_id"], ["app.user_wines.owner_id", "app.user_wines.id"]
        ),
        Index("ix_entries_wine_date", "owner_id", "user_wine_id", "consumed_date", "id"),
        CheckConstraint("version > 0", name="ck_entry_version"),
        CheckConstraint("(local_time IS NULL) = (timezone IS NULL)", name="ck_entry_time_zone"),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column()
    user_wine_id: Mapped[UUID] = mapped_column()
    consumed_date: Mapped[date] = mapped_column()
    local_time: Mapped[time | None] = mapped_column()
    timezone: Mapped[str | None] = mapped_column(String(100))
    location_label: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text())
    version: Mapped[int] = mapped_column(server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EntrySave(Base):
    """One intent per owner/key; inserted and completed in the entry transaction."""

    __tablename__ = "entry_saves"
    __table_args__ = ({"schema": "app"},)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("app.app_users.id"), primary_key=True)
    key: Mapped[UUID] = mapped_column(primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict[str, object] | None] = mapped_column(JSONB)
