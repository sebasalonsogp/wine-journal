from datetime import date
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class ManualWine(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    producer: str | None = Field(default=None, min_length=1, max_length=200)
    vintage_status: Literal["YEAR", "NON_VINTAGE", "MULTI_VINTAGE", "UNKNOWN"] = "UNKNOWN"
    year: int | None = Field(default=None, ge=1000, le=9999, strict=True)
    edition: str | None = Field(default=None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def valid_vintage(self) -> Self:
        if (self.vintage_status == "YEAR") != (self.year is not None):
            raise ValueError("A year is required only when vintage status is YEAR.")
        return self


class CatalogWine(BaseModel):
    """Explicit public allowlist; never serialize a private wine/journal model."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    name: str
    producer: str
    vintage_status: Literal["YEAR", "NON_VINTAGE", "MULTI_VINTAGE"]
    year: int | None
    edition: str | None


class CatalogPage(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[CatalogWine]
    next_offset: int | None


class CatalogReference(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    url: str
    retrieved_on: date


class CatalogDetails(CatalogWine):
    sources: list[CatalogReference]
