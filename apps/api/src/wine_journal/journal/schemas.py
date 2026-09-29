from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel

from wine_journal.catalog.schemas import ManualWine


class SaveEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel)

    consumed_date: date
    manual_wine: ManualWine | None = None
    release_id: UUID | None = None

    @model_validator(mode="after")
    def exactly_one_wine(self) -> Self:
        if (self.manual_wine is None) == (self.release_id is None):
            raise ValueError("Choose an existing wine or enter a manual wine.")
        return self


class EntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: UUID
    user_wine_id: UUID
    consumed_date: date
    created_at: datetime


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


class WinePage(BaseModel):
    items: list[WineResponse]
    nextCursor: str | None


class EntryPage(BaseModel):
    items: list[EntryResponse]
    nextCursor: str | None
