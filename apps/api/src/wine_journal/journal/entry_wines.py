"""Move one entry without merging wine identities, ratings or media."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.catalog.schemas import ManualWine
from wine_journal.catalog.service import create_manual_release
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.edits import read_entry
from wine_journal.journal.models import DrinkingEntry, EntrySave, UserWine
from wine_journal.journal.ratings import owned_wine
from wine_journal.journal.schemas import EntryResponse


class MoveEntryWine(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel)

    version: int = Field(gt=0, strict=True)
    previous_wine_id: UUID
    wine_id: UUID | None = None
    manual_wine: ManualWine | None = None

    @model_validator(mode="after")
    def one_destination(self) -> Self:
        if (self.wine_id is None) == (self.manual_wine is None):
            raise ValueError("Choose an existing wine or enter a new wine.")
        return self


def move_entry_wine(
    session: Session, principal: Principal, entry_id: UUID, body: MoveEntryWine
) -> EntryResponse:
    try:
        with session.begin():
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            owner = read_account(session, principal).id
            entry = read_entry(session, owner, entry_id)
            if entry.version != body.version or entry.user_wine_id != body.previous_wine_id:
                raise ApiError(409, "MOVE_CONFLICT", "This entry changed. Review it before moving.")
            if body.wine_id is not None:
                target = owned_wine(session, owner, body.wine_id)
                if target.id == entry.user_wine_id:
                    return EntryResponse.model_validate(entry)
            else:
                assert body.manual_wine is not None
                release = create_manual_release(session, owner, body.manual_wine)
                target = UserWine(owner_id=owner, release_id=release.id)
                session.add(target)
                session.flush()
            # CAS also protects a concurrent edit, deletion or occasion change.
            # Losing the race rolls back any new definition/release/wine together.
            saved = session.scalar(
                update(DrinkingEntry)
                .where(
                    DrinkingEntry.owner_id == owner,
                    DrinkingEntry.id == entry_id,
                    DrinkingEntry.version == body.version,
                    DrinkingEntry.user_wine_id == body.previous_wine_id,
                )
                .values(user_wine_id=target.id, version=body.version + 1)
                .returning(DrinkingEntry),
                execution_options={"populate_existing": True},
            )
            if saved is None:
                raise ApiError(409, "MOVE_CONFLICT", "This entry changed. Review it before moving.")
            result = EntryResponse.model_validate(saved)
            # An old capture retry must navigate to the corrected wine, not the
            # original record. Keep its request hash/key; never create another entry.
            session.execute(
                update(EntrySave)
                .where(
                    EntrySave.owner_id == owner,
                    EntrySave.response["id"].astext == str(entry_id),
                )
                .values(response=result.model_dump(mode="json", by_alias=True))
            )
            return result
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) == "55P03":
            raise ApiError(
                409, "MOVE_BUSY", "Another change is saving. Review and retry."
            ) from None
        raise
