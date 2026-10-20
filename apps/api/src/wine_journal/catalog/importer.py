"""Offline, bounded import of operator-reviewed public wine facts. No URL fetching."""

import csv
import io
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from wine_journal.catalog.models import CatalogDefinition, CatalogRelease, CatalogSource

MAX_BYTES = 1_048_576
MAX_ROWS = 1_000


class CatalogRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    fixture_id: str = Field(pattern=r"^W[0-9]{3}$")
    definition_key: str = Field(max_length=120, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    producer: str = Field(min_length=1, max_length=200)
    wine_name: str = Field(min_length=1, max_length=200)
    vintage_status: Literal["YEAR", "NON_VINTAGE", "MULTI_VINTAGE"]
    year: int | None = Field(ge=1000, le=9999, strict=True)
    edition: str | None = Field(min_length=1, max_length=120)
    source_url: str = Field(max_length=500)
    retrieved_on: date
    market: Literal["UNVERIFIED"]
    evidence_status: Literal["SOURCE_ONLY"]

    @field_validator("year", "edition", mode="before")
    @classmethod
    def optional_cells(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("year", mode="before")
    @classmethod
    def parse_year(cls, value: object) -> object:
        if isinstance(value, str) and len(value) == 4 and value.isascii() and value.isdigit():
            return int(value)
        return value

    @field_validator("source_url")
    @classmethod
    def safe_reference(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or "." not in parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.port not in (None, 443)
            or any(char.isspace() for char in value)
        ):
            raise ValueError("Use a plain HTTPS source URL without credentials or query strings.")
        return value

    @field_validator("retrieved_on")
    @classmethod
    def observed_date(cls, value: date) -> date:
        if value > datetime.now(UTC).date():
            raise ValueError("Retrieval cannot be in the future.")
        return value

    @model_validator(mode="after")
    def valid_vintage(self) -> Self:
        if (self.vintage_status == "YEAR") != (self.year is not None):
            raise ValueError("Only YEAR identities require a year.")
        return self


def load_manifest(path: Path) -> tuple[CatalogRow, ...]:
    with path.open("rb") as source:
        raw = source.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Catalog input exceeds 1 MiB.")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        if reader.fieldnames != list(CatalogRow.model_fields):
            raise ValueError("Catalog headers do not match the reviewed manifest format.")
        rows: list[CatalogRow] = []
        ids: set[str] = set()
        identities: set[tuple[str, str, int | None, str | None]] = set()
        definitions: dict[str, tuple[str, str]] = {}
        for number, cells in enumerate(reader, 2):
            if len(rows) == MAX_ROWS:
                raise ValueError("Catalog input exceeds 1000 rows.")
            try:
                row = CatalogRow.model_validate(cells)
            except ValidationError:
                raise ValueError(f"Invalid catalog row {number}; no values were logged.") from None
            identity = (row.definition_key, row.vintage_status, row.year, row.edition)
            if row.fixture_id in ids or identity in identities:
                raise ValueError(f"Duplicate catalog identity at row {number}.")
            definition = (row.producer, row.wine_name)
            if definitions.setdefault(row.definition_key, definition) != definition:
                raise ValueError(f"Inconsistent catalog definition at row {number}.")
            ids.add(row.fixture_id)
            identities.add(identity)
            rows.append(row)
        if not rows:
            raise ValueError("Catalog input is empty.")
        return tuple(rows)
    except (csv.Error, UnicodeError):
        raise ValueError("Invalid UTF-8 CSV input.") from None


@dataclass(frozen=True)
class ImportResult:
    definitions: int
    releases: int
    sources: int
    applied: bool


def import_catalog(engine: Engine, path: Path, *, apply: bool = False) -> ImportResult:
    rows = load_manifest(path)
    with Session(engine) as session, session.begin():
        # Rare operator imports serialize; ordinary catalog SELECTs remain available.
        session.execute(text("SET LOCAL lock_timeout = '5s'"))
        session.execute(text("SET LOCAL statement_timeout = '10s'"))
        session.execute(
            text(
                "LOCK TABLE app.catalog_definitions, app.catalog_releases, app.catalog_sources "
                "IN SHARE ROW EXCLUSIVE MODE"
            )
        )
        definitions = {
            definition.key: definition
            for definition in session.scalars(
                select(CatalogDefinition).where(
                    CatalogDefinition.key.in_({row.definition_key for row in rows})
                )
            )
        }
        releases = {
            (release.definition_id, release.vintage_status, release.year, release.edition): release
            for release in session.scalars(
                select(CatalogRelease).where(
                    CatalogRelease.definition_id.in_([d.id for d in definitions.values()])
                )
            )
        }
        sources = {
            (source.release_id, source.url, source.retrieved_on)
            for source in session.scalars(
                select(CatalogSource).where(
                    CatalogSource.release_id.in_([r.id for r in releases.values()])
                )
            )
        }
        new_definitions: list[CatalogDefinition] = []
        new_releases: list[CatalogRelease] = []
        new_sources: list[CatalogSource] = []
        for row in rows:
            definition = definitions.get(row.definition_key)
            if definition is None:
                definition = CatalogDefinition(
                    id=uuid4(), key=row.definition_key, name=row.wine_name, producer=row.producer
                )
                definitions[row.definition_key] = definition
                new_definitions.append(definition)
            elif (definition.name, definition.producer) != (row.wine_name, row.producer):
                raise ValueError(
                    "Catalog definition conflicts with stored identity; review required."
                )
            identity: tuple[UUID, str, int | None, str | None] = (
                definition.id,
                row.vintage_status,
                row.year,
                row.edition,
            )
            release = releases.get(identity)
            if release is None:
                release = CatalogRelease(
                    id=uuid4(),
                    definition_id=definition.id,
                    vintage_status=row.vintage_status,
                    year=row.year,
                    edition=row.edition,
                )
                releases[identity] = release
                new_releases.append(release)
            source_key = (release.id, row.source_url, row.retrieved_on)
            if source_key not in sources:
                new_sources.append(
                    CatalogSource(
                        id=uuid4(),
                        release_id=release.id,
                        url=row.source_url,
                        retrieved_on=row.retrieved_on,
                        market=row.market,
                        evidence_status=row.evidence_status,
                    )
                )
                sources.add(source_key)
        if apply:
            # Validate the entire batch against existing identities before any inserts.
            for batch in (new_definitions, new_releases, new_sources):
                session.add_all(batch)
                session.flush()
        return ImportResult(len(new_definitions), len(new_releases), len(new_sources), apply)
