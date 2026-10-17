from uuid import UUID

from sqlalchemy import delete, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.edits import read_entry
from wine_journal.journal.models import DrinkingEntry, EntrySave


def delete_entry(session: Session, principal: Principal, entry_id: UUID, version: int) -> UUID:
    try:
        with session.begin():
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            owner = read_account(session, principal).id
            read_entry(session, owner, entry_id)
            removed = session.scalar(
                delete(DrinkingEntry)
                .where(
                    DrinkingEntry.owner_id == owner,
                    DrinkingEntry.id == entry_id,
                    DrinkingEntry.version == version,
                )
                .returning(DrinkingEntry.id)
            )
            if removed is None:
                raise ApiError(
                    409, "DELETE_CONFLICT", "This entry changed. Review it before deleting."
                )
            # Future media cleanup jobs must be enqueued in this same transaction.
            # Retain the request-key claim without retaining deleted entry details.
            session.execute(
                update(EntrySave)
                .where(
                    EntrySave.owner_id == owner,
                    EntrySave.response["id"].astext == str(entry_id),
                )
                .values(response={"deleted": True})
            )
            return removed
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) == "55P03":
            raise ApiError(
                409, "DELETE_BUSY", "Another change is saving. Review and retry."
            ) from None
        raise
