from datetime import date
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel
from sqlalchemy.orm import Session

from wine_journal.catalog.schemas import ManualWine
from wine_journal.catalog.service import create_manual_release, read_owned_release
from wine_journal.journal.entry_creation import insert_entry
from wine_journal.journal.occasion_schemas import OccasionFields


class StagedEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel)
    consumed_date: date
    notes: str | None = Field(default=None, max_length=10000, pattern=r"^[^\x00]*$")


class StagedWine(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel)
    manual_wine: ManualWine | None = None
    release_id: UUID | None = None
    entries: list[StagedEntry] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def one_wine(self) -> Self:
        if (self.manual_wine is None) == (self.release_id is None):
            raise ValueError("Choose a known release or enter a manual wine.")
        return self


class OccasionWines(BaseModel):
    model_config = ConfigDict(extra="forbid")
    wines: list[StagedWine] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def bounded_entries(self) -> Self:
        if sum(len(wine.entries) for wine in self.wines) > 20:
            raise ValueError("Save at most 20 drinking entries at once.")
        return self


class CreateOccasion(OccasionFields):
    wines: list[StagedWine] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def bounded_entries(self) -> Self:
        if sum(len(wine.entries) for wine in self.wines) > 20:
            raise ValueError("Save at most 20 drinking entries at once.")
        return self


def insert_wines(session: Session, owner: UUID, occasion_id: UUID, wines: list[StagedWine]) -> None:
    for wine in wines:
        if wine.manual_wine is not None:
            release = create_manual_release(session, owner, wine.manual_wine)
        else:
            assert wine.release_id is not None
            release = read_owned_release(session, owner, wine.release_id)
        for entry in wine.entries:
            insert_entry(session, owner, release.id, entry.consumed_date, occasion_id, entry.notes)
