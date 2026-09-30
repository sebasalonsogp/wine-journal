from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.edits import read_entry
from wine_journal.journal.models import DrinkingEntry
from wine_journal.journal.occasions import read_occasion
from wine_journal.journal.schemas import EntryResponse


class LinkEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(gt=0, strict=True)
    previous_occasion_id: UUID | None = Field(alias="previousOccasionId")


def set_occasion(
    session: Session,
    principal: Principal,
    entry_id: UUID,
    occasion_id: UUID,
    version: int,
    previous: UUID | None,
    *,
    unlink: bool = False,
) -> EntryResponse:
    try:
        with session.begin():
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            owner = read_account(session, principal).id
            read_occasion(session, owner, occasion_id)
            entry = read_entry(session, owner, entry_id)
            expected = occasion_id if unlink else previous
            if entry.version != version or entry.occasion_id != expected:
                raise ApiError(
                    409,
                    "LINK_CONFLICT",
                    "This entry changed. Review its current occasion before changing the link.",
                )
            target = None if unlink else occasion_id
            if entry.occasion_id == target:
                return EntryResponse.model_validate(entry)
            saved = session.scalar(
                update(DrinkingEntry)
                .where(
                    DrinkingEntry.id == entry_id,
                    DrinkingEntry.owner_id == owner,
                    DrinkingEntry.version == version,
                    DrinkingEntry.occasion_id == expected,
                )
                .values(occasion_id=target, version=version + 1)
                .returning(DrinkingEntry),
                execution_options={"populate_existing": True},
            )
            if saved is None:
                raise ApiError(
                    409, "LINK_CONFLICT", "This entry changed. Review it before changing the link."
                )
            return EntryResponse.model_validate(saved)
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) == "55P03":
            raise ApiError(
                409, "LINK_BUSY", "Another change is saving. Review and retry."
            ) from None
        raise
