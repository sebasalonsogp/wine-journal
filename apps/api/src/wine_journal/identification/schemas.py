"""Barcode evidence proposes offerings; only an explicit choice selects a release."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from wine_journal.catalog.schemas import CatalogReference, CatalogWine
from wine_journal.identification.gtin import canonical_gtin


class BarcodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)

    gtin: str = Field(strict=True, max_length=14)

    @field_validator("gtin")
    @classmethod
    def retail_code(cls, value: str) -> str:
        code = canonical_gtin(value)
        if not code.startswith("0"):
            raise ValueError("Case-level codes are unsupported.")
        return code


class BarcodeConfirmation(BarcodeRequest):
    catalog_release_id: UUID
    vintage_status: Literal["YEAR", "NON_VINTAGE", "MULTI_VINTAGE"]
    year: int | None = Field(ge=1000, le=9999, strict=True)
    edition: str | None = Field(max_length=120)


class BarcodeCandidate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    definition_id: UUID
    name: str
    producer: str
    bottle_sizes_ml: list[int]
    sources: list[CatalogReference]
    releases: list[CatalogWine]


class BarcodeLookup(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    gtin: str
    status: Literal["NEEDS_CONFIRMATION", "NOT_FOUND", "TOO_MANY_MATCHES"]
    candidates: list[BarcodeCandidate]
