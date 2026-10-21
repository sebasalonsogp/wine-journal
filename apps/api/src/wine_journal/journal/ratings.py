from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.models import RatingRevision, UserWine
from wine_journal.journal.rating_schemas import RatingHistory, RatingHistoryItem, RatingState


def owned_wine(session: Session, owner: UUID, wine_id: UUID, *, lock: bool = False) -> UserWine:
    query = select(UserWine).where(UserWine.owner_id == owner, UserWine.id == wine_id)
    wine = session.scalar(query.with_for_update() if lock else query)
    if wine is None:
        raise ApiError(404, "WINE_NOT_FOUND", "This wine is unavailable.")
    return wine


def change_rating(
    session: Session,
    principal: Principal,
    wine_id: UUID,
    version: int,
    score: float | None,
    *,
    erase_history: bool = False,
) -> RatingState:
    try:
        with session.begin():
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            owner = read_account(session, principal).id
            wine = owned_wine(session, owner, wine_id, lock=True)
            if wine.rating_version != version:
                raise ApiError(
                    409, "RATING_CONFLICT", "Your rating changed. Review it and try again."
                )
            units = int(score * 2) if score is not None else None
            if erase_history:
                session.execute(
                    delete(RatingRevision).where(
                        RatingRevision.owner_id == owner, RatingRevision.user_wine_id == wine_id
                    )
                )
                units = None
            elif wine.rating_units == units:
                return RatingState(score=score, version=version)
            # Never reset this counter: an old browser must not overwrite a later erasure.
            wine.rating_version += 1
            wine.rating_units = units
            if not erase_history:
                session.add(
                    RatingRevision(
                        owner_id=owner,
                        user_wine_id=wine_id,
                        version=wine.rating_version,
                        rating_units=units,
                    )
                )
            return RatingState(
                score=None if units is None else units / 2, version=wine.rating_version
            )
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) == "55P03":
            raise ApiError(
                409, "RATING_BUSY", "Another change is saving. Review and retry."
            ) from None
        raise


def rating_history(
    session: Session, owner: UUID, wine_id: UUID, limit: int, before_version: int | None
) -> RatingHistory:
    owned_wine(session, owner, wine_id)
    query = select(RatingRevision).where(
        RatingRevision.owner_id == owner, RatingRevision.user_wine_id == wine_id
    )
    if before_version is not None:
        query = query.where(RatingRevision.version < before_version)
    rows = session.scalars(query.order_by(RatingRevision.version.desc()).limit(limit + 1)).all()
    items = [
        RatingHistoryItem(
            score=None if row.rating_units is None else row.rating_units / 2,
            version=row.version,
            changed_at=row.changed_at,
        )
        for row in rows[:limit]
    ]
    return RatingHistory(
        items=items, nextBeforeVersion=items[-1].version if len(rows) > limit else None
    )
