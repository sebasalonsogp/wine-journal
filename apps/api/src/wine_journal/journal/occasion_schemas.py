from datetime import date, datetime, time
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from wine_journal.journal import validation


class OccasionFields(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)

    occasion_date: date
    title: str | None = Field(default=None, max_length=200, pattern=r"^[^\x00]*$")
    local_time: time | None = None
    timezone: str | None = Field(default=None, max_length=100)
    location_label: str | None = Field(default=None, max_length=200, pattern=r"^[^\x00]*$")
    notes: str | None = Field(default=None, max_length=10000, pattern=r"^[^\x00]*$")

    @field_validator("title", "location_label")
    @classmethod
    def optional_label(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("local_time")
    @classmethod
    def local_minute(cls, value: time | None) -> time | None:
        return validation.local_minute(value)

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str | None) -> str | None:
        return validation.known_timezone(value)

    @model_validator(mode="after")
    def time_and_zone(self) -> Self:
        if (self.local_time is None) != (self.timezone is None):
            raise ValueError("Set or clear local time and timezone together.")
        return self


class EditOccasion(OccasionFields):
    version: int = Field(gt=0, strict=True)


class OccasionResponse(OccasionFields):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: UUID
    version: int
    created_at: datetime


class OccasionPage(BaseModel):
    items: list[OccasionResponse]
    nextCursor: str | None
