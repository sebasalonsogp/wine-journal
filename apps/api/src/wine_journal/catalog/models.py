from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from wine_journal.core.database import Base


class WineDefinition(Base):
    __tablename__ = "wine_definitions"
    __table_args__ = (
        UniqueConstraint("owner_id", "id", name="uq_wine_definitions_owner"),
        CheckConstraint("length(trim(name)) > 0", name="ck_wine_definitions_name"),
        {"schema": "app"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("app.app_users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    producer: Mapped[str | None] = mapped_column(String(200))


class WineRelease(Base):
    __tablename__ = "wine_releases"
    __table_args__ = (
        UniqueConstraint("owner_id", "id", name="uq_wine_releases_owner"),
        ForeignKeyConstraint(
            ["owner_id", "definition_id"],
            ["app.wine_definitions.owner_id", "app.wine_definitions.id"],
        ),
        CheckConstraint(
            "(vintage_status = 'YEAR' AND year IS NOT NULL AND year BETWEEN 1000 AND 9999)"
            " OR (vintage_status IN ('UNKNOWN', 'NON_VINTAGE', 'MULTI_VINTAGE') AND year IS NULL)",
            name="ck_wine_releases_vintage",
        ),
        {"schema": "app"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column()
    definition_id: Mapped[UUID] = mapped_column(index=True)
    vintage_status: Mapped[str] = mapped_column(String(16))
    year: Mapped[int | None] = mapped_column()
    edition: Mapped[str | None] = mapped_column(String(120))
