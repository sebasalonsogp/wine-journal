"""Entry insertion inside the caller's transaction; no commits or save receipts."""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from wine_journal.journal.models import DrinkingEntry, UserWine


def insert_entry(
    session: Session,
    owner: UUID,
    release_id: UUID,
    consumed_date: date,
    occasion_id: UUID | None = None,
    notes: str | None = None,
) -> DrinkingEntry:
    session.execute(
        insert(UserWine)
        .values(owner_id=owner, release_id=release_id)
        .on_conflict_do_nothing(constraint="uq_user_wines_release")
    )
    wine = session.scalar(
        select(UserWine).where(UserWine.owner_id == owner, UserWine.release_id == release_id)
    )
    assert wine is not None
    entry = DrinkingEntry(
        owner_id=owner,
        user_wine_id=wine.id,
        consumed_date=consumed_date,
        occasion_id=occasion_id,
        notes=notes,
    )
    session.add(entry)
    session.flush()
    return entry
