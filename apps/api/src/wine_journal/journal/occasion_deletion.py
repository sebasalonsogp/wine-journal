from uuid import UUID

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.models import DrinkingEntry, EntrySave, Occasion, OccasionSave


def delete_occasion(
    session: Session, principal: Principal, occasion_id: UUID, version: int
) -> UUID:
    try:
        with session.begin():
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            owner = read_account(session, principal).id
            # Writers hold KEY SHARE on the target occasion before touching entries.
            # Lock first so no new links appear between detach and delete.
            occasion = session.scalar(
                select(Occasion)
                .where(Occasion.owner_id == owner, Occasion.id == occasion_id)
                .with_for_update()
            )
            if occasion is None:
                raise ApiError(404, "OCCASION_NOT_FOUND", "This occasion is unavailable.")
            if occasion.version != version:
                raise ApiError(
                    409, "DELETE_CONFLICT", "This occasion changed. Review it before deleting."
                )
            session.execute(
                update(DrinkingEntry)
                .where(DrinkingEntry.owner_id == owner, DrinkingEntry.occasion_id == occasion_id)
                .values(occasion_id=None, version=DrinkingEntry.version + 1)
            )
            # Retain key/hash claims but erase deleted occasion context from every
            # creation/addition receipt. Entry receipts retain their surviving entry.
            session.execute(
                update(OccasionSave)
                .where(
                    OccasionSave.owner_id == owner,
                    OccasionSave.response["id"].astext == str(occasion_id),
                )
                .values(response={"deleted": True})
            )
            session.execute(
                update(EntrySave)
                .where(
                    EntrySave.owner_id == owner,
                    EntrySave.response["occasionId"].astext == str(occasion_id),
                )
                .values(
                    response=func.jsonb_set(
                        EntrySave.response, text("'{occasionId}'"), text("'null'::jsonb")
                    )
                )
            )
            # Future occasion-owned media cleanup jobs belong in this transaction.
            session.execute(
                delete(Occasion).where(Occasion.owner_id == owner, Occasion.id == occasion_id)
            )
            return occasion_id
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) == "55P03":
            raise ApiError(
                409, "DELETE_BUSY", "Another change is saving. Review and retry."
            ) from None
        raise
