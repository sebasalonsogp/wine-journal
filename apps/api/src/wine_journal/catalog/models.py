from datetime import date
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
        UniqueConstraint("owner_id", "catalog_release_id", name="uq_owned_catalog_release"),
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
    catalog_release_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.catalog_releases.id", name="fk_wine_release_catalog")
    )
    vintage_status: Mapped[str] = mapped_column(String(16))
    year: Mapped[int | None] = mapped_column()
    edition: Mapped[str | None] = mapped_column(String(120))


class CatalogDefinition(Base):
    """Reviewed public knowledge, separate from owner-scoped manual identities."""

    __tablename__ = "catalog_definitions"
    __table_args__ = (
        UniqueConstraint("key", name="uq_catalog_definition_key"),
        CheckConstraint("key ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="ck_catalog_definition_key"),
        CheckConstraint("length(trim(name)) > 0", name="ck_catalog_definition_name"),
        CheckConstraint("length(trim(producer)) > 0", name="ck_catalog_definition_producer"),
        {"schema": "app"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(200))
    producer: Mapped[str] = mapped_column(String(200))


class CatalogRelease(Base):
    __tablename__ = "catalog_releases"
    __table_args__ = (
        UniqueConstraint(
            "definition_id",
            "vintage_status",
            "year",
            "edition",
            name="uq_catalog_release_identity",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "(vintage_status = 'YEAR' AND year IS NOT NULL AND year BETWEEN 1000 AND 9999)"
            " OR (vintage_status IN ('NON_VINTAGE', 'MULTI_VINTAGE') AND year IS NULL)",
            name="ck_catalog_release_vintage",
        ),
        CheckConstraint("edition IS NULL OR length(trim(edition)) > 0", name="ck_catalog_edition"),
        {"schema": "app"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    definition_id: Mapped[UUID] = mapped_column(ForeignKey("app.catalog_definitions.id"))
    vintage_status: Mapped[str] = mapped_column(String(16))
    year: Mapped[int | None] = mapped_column()
    edition: Mapped[str | None] = mapped_column(String(120))


class CatalogSource(Base):
    """Identity-level provenance; does not claim sourced prices/specifications."""

    __tablename__ = "catalog_sources"
    __table_args__ = (
        UniqueConstraint("release_id", "url", "retrieved_on", name="uq_catalog_source"),
        CheckConstraint("url LIKE 'https://%'", name="ck_catalog_source_https"),
        CheckConstraint("market = 'UNVERIFIED'", name="ck_catalog_source_market"),
        CheckConstraint("evidence_status = 'SOURCE_ONLY'", name="ck_catalog_source_evidence"),
        {"schema": "app"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    release_id: Mapped[UUID] = mapped_column(ForeignKey("app.catalog_releases.id"))
    url: Mapped[str] = mapped_column(String(500))
    retrieved_on: Mapped[date] = mapped_column()
    market: Mapped[str] = mapped_column(String(16))
    evidence_status: Mapped[str] = mapped_column(String(16))
