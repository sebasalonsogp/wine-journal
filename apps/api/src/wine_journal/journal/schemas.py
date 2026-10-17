from datetime import date, datetime, time
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from wine_journal.catalog.schemas import ManualWine
from wine_journal.journal import validation
from wine_journal.journal.occasion_schemas import OccasionFields


class SaveEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel)

    consumed_date: date
    manual_wine: ManualWine | None = None
    release_id: UUID | None = None
    occasion_id: UUID | None = None
    new_occasion: OccasionFields | None = None
    notes: str | None = Field(default=None, max_length=10000, pattern=r"^[^\x00]*$")

    @model_validator(mode="after")
    def exactly_one_wine(self) -> Self:
        if (self.manual_wine is None) == (self.release_id is None):
            raise ValueError("Choose an existing wine or enter a manual wine.")
        if self.occasion_id is not None and self.new_occasion is not None:
            raise ValueError("Choose an existing occasion or enter a new occasion, not both.")
        return self


class EntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: UUID
    user_wine_id: UUID
    consumed_date: date
    created_at: datetime
    local_time: time | None = None
    timezone: str | None = None
    location_label: str | None = None
    notes: str | None = None
    version: int = 1
    occasion_id: UUID | None = None


class EditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel)

    version: int = Field(gt=0, strict=True)
    consumed_date: date | None = None
    local_time: time | None = None
    timezone: str | None = Field(default=None, max_length=100)
    location_label: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("local_time")
    @classmethod
    def local_minute(cls, value: time | None) -> time | None:
        return validation.local_minute(value)

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str | None) -> str | None:
        return validation.known_timezone(value)

    @model_validator(mode="after")
    def valid_patch(self) -> Self:
        if self.model_fields_set == {"version"}:
            raise ValueError("Provide a field to edit.")
        if "consumed_date" in self.model_fields_set and self.consumed_date is None:
            raise ValueError("The drinking date cannot be cleared.")
        return self


class WineResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    release_id: UUID
    name: str
    producer: str | None
    vintage_status: str
    year: int | None
    edition: str | None
    last_consumed_date: date | None
    entry_count: int
    current_rating: float | None
    rating_version: int
    cover_asset_id: UUID | None = None
    cover_version: int = 0


class WinePage(BaseModel):
    items: list[WineResponse]
    nextCursor: str | None


class DeletedEntry(BaseModel):
    id: UUID


class EntryPage(BaseModel):
    items: list[EntryResponse]
    nextCursor: str | None
