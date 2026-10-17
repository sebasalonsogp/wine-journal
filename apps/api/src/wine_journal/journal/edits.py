from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.models import DrinkingEntry
from wine_journal.journal.schemas import EditEntry, EntryResponse


def read_entry(session: Session, owner: UUID, entry_id: UUID) -> DrinkingEntry:
    entry = session.scalar(
        select(DrinkingEntry).where(
            DrinkingEntry.id == entry_id,
            DrinkingEntry.owner_id == owner,
        )
    )
    if entry is None:
        raise ApiError(404, "ENTRY_NOT_FOUND", "This entry is unavailable.")
    return entry


def edit_entry(
    session: Session,
    principal: Principal,
    entry_id: UUID,
    body: EditEntry,
) -> EntryResponse:
    try:
        with session.begin():
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            owner = read_account(session, principal).id
            entry = read_entry(session, owner, entry_id)
            if entry.version != body.version:
                raise ApiError(
                    409, "EDIT_CONFLICT", "This entry changed. Review the latest version."
                )
            values = body.model_dump(exclude_unset=True, exclude={"version"})
            if (values.get("local_time", entry.local_time) is None) != (
                values.get("timezone", entry.timezone) is None
            ):
                raise ApiError(
                    422, "INVALID_TIME", "Set or clear local time and timezone together."
                )
            # The compare-and-swap predicate protects the interval after the initial read.
            saved = session.scalar(
                update(DrinkingEntry)
                .where(
                    DrinkingEntry.id == entry_id,
                    DrinkingEntry.owner_id == owner,
                    DrinkingEntry.version == body.version,
                )
                .values(**values, version=body.version + 1)
                .returning(DrinkingEntry),
                execution_options={"populate_existing": True},
            )
            if saved is None:
                raise ApiError(
                    409, "EDIT_CONFLICT", "This entry changed. Review the latest version."
                )
            return EntryResponse.model_validate(saved)
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) == "55P03":
            raise ApiError(409, "EDIT_BUSY", "Another edit is saving. Review and retry.") from None
        raise
