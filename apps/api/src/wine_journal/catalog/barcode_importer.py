"""Offline curator import. Package evidence never selects or creates a vintage."""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from wine_journal.catalog.models import CatalogBarcodeObservation, CatalogDefinition
from wine_journal.catalog.references import safe_reference
from wine_journal.identification.gtin import canonical_gtin


class BarcodeRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    gtin: str = Field(strict=True, max_length=14)
    definition_key: str = Field(max_length=120, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    producer: str = Field(min_length=1, max_length=200)
    wine_name: str = Field(min_length=1, max_length=200)
    bottle_ml: int = Field(strict=True, gt=0, le=30000)
    source_url: str = Field(max_length=500)
    retrieved_on: date
    market: Literal["UNVERIFIED"]
    evidence_status: Literal["WEB_TEXT", "PRODUCER_WEB_IMAGE"]
    source_sha256: str | None = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("gtin")
    @classmethod
    def retail_gtin(cls, value: str) -> str:
        code = canonical_gtin(value)
        if not code.startswith("0"):
            raise ValueError("Case-level package indicators are outside this import.")
        return code

    @field_validator("source_url")
    @classmethod
    def source_reference(cls, value: str) -> str:
        return safe_reference(value)

    @field_validator("retrieved_on")
    @classmethod
    def observed_date(cls, value: date) -> date:
        if value > datetime.now(UTC).date():
            raise ValueError("Retrieval cannot be in the future.")
        return value

    @model_validator(mode="after")
    def image_provenance(self) -> Self:
        if (self.evidence_status == "PRODUCER_WEB_IMAGE") != (self.source_sha256 is not None):
            raise ValueError("Only image evidence requires an original source hash.")
        return self


def load_barcode_manifest(path: Path) -> tuple[BarcodeRow, ...]:
    with path.open("rb") as source:
        raw = source.read(65537)
    if len(raw) > 65536:
        raise ValueError("Barcode input exceeds 64 KiB.")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, list) or not 1 <= len(data) <= 100:
        raise ValueError("Provide one to 100 reviewed observations.")
    rows = tuple(BarcodeRow.model_validate(item) for item in data)
    keys = {(r.gtin, r.definition_key, r.source_url, r.retrieved_on) for r in rows}
    if len(keys) != len(rows):
        raise ValueError("Duplicate evidence after GTIN normalization.")
    return rows


@dataclass(frozen=True)
class BarcodeImportResult:
    observations: int
    package_codes: int
    applied: bool


def import_barcodes(engine: Engine, path: Path, *, apply: bool = False) -> BarcodeImportResult:
    rows = load_barcode_manifest(path)
    with Session(engine) as session, session.begin():
        session.execute(text("SET LOCAL lock_timeout = '5s'"))
        session.execute(text("SET LOCAL statement_timeout = '10s'"))
        session.execute(
            text(
                "LOCK TABLE app.catalog_definitions, app.catalog_barcode_observations "
                "IN SHARE ROW EXCLUSIVE MODE"
            )
        )
        definitions = {
            d.key: d
            for d in session.scalars(
                select(CatalogDefinition).where(
                    CatalogDefinition.key.in_({row.definition_key for row in rows})
                )
            )
        }
        existing = {
            (s.gtin, s.definition_id, s.url, s.retrieved_on): s
            for s in session.scalars(
                select(CatalogBarcodeObservation).where(
                    CatalogBarcodeObservation.gtin.in_({row.gtin for row in rows})
                )
            )
        }
        new: list[CatalogBarcodeObservation] = []
        for row in rows:
            definition = definitions.get(row.definition_key)
            if definition is None or (definition.producer, definition.name) != (
                row.producer,
                row.wine_name,
            ):
                raise ValueError("Unknown or conflicting catalog definition; review required.")
            previous = existing.get((row.gtin, definition.id, row.source_url, row.retrieved_on))
            if previous is not None:
                if (previous.bottle_ml, previous.evidence_status, previous.source_sha256) != (
                    row.bottle_ml,
                    row.evidence_status,
                    row.source_sha256,
                ):
                    raise ValueError("Stored evidence conflicts; explicit curator review required.")
                continue
            new.append(
                CatalogBarcodeObservation(
                    gtin=row.gtin,
                    definition_id=definition.id,
                    bottle_ml=row.bottle_ml,
                    url=row.source_url,
                    retrieved_on=row.retrieved_on,
                    market=row.market,
                    evidence_status=row.evidence_status,
                    source_sha256=row.source_sha256,
                )
            )
        if apply:
            # Nothing is inserted until every definition and prior source has been checked.
            session.add_all(new)
            session.flush()
        return BarcodeImportResult(
            len(new), len({row.gtin for row in new} - {key[0] for key in existing}), apply
        )
