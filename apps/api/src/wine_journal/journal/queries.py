import base64
import json
from datetime import date
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from wine_journal.catalog.models import WineDefinition, WineRelease
from wine_journal.core.errors import ApiError
from wine_journal.journal.models import DrinkingEntry, UserWine
from wine_journal.journal.schemas import EntryPage, EntryResponse, WinePage, WineResponse


def encode_cursor(scope: str, owner: UUID, consumed: date | None, identifier: UUID) -> str:
    data = [scope, str(owner), consumed.isoformat() if consumed else None, str(identifier)]
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def decode_cursor(value: str, scope: str, owner: UUID) -> tuple[date | None, UUID]:
    try:
        if len(value) > 512:
            raise ValueError
        fields = json.loads(base64.b64decode(value, altchars=b"-_", validate=True))
        if not isinstance(fields, list) or len(fields) != 4 or fields[:2] != [scope, str(owner)]:
            raise ValueError
        return date.fromisoformat(fields[2]) if fields[2] is not None else None, UUID(fields[3])
    except (ValueError, TypeError, AttributeError):
        raise ApiError(422, "INVALID_CURSOR", "Reload this list to continue.") from None


def wine_query(
    owner: UUID,
) -> Select[tuple[UUID, UUID, str, str | None, str, int | None, str | None, date | None, int]]:
    history = (
        select(
            DrinkingEntry.user_wine_id,
            func.max(DrinkingEntry.consumed_date).label("last_date"),
            func.count().label("entry_count"),
        )
        .where(DrinkingEntry.owner_id == owner)
        .group_by(DrinkingEntry.user_wine_id)
        .subquery()
    )
    return (
        select(
            UserWine.id,
            UserWine.release_id,
            WineDefinition.name,
            WineDefinition.producer,
            WineRelease.vintage_status,
            WineRelease.year,
            WineRelease.edition,
            history.c.last_date.label("last_consumed_date"),
            func.coalesce(history.c.entry_count, 0).label("entry_count"),
        )
        .join(WineRelease, UserWine.release_id == WineRelease.id)
        .join(WineDefinition, WineRelease.definition_id == WineDefinition.id)
        .outerjoin(history, history.c.user_wine_id == UserWine.id)
        .where(UserWine.owner_id == owner)
    )


def read_wine(session: Session, owner: UUID, wine_id: UUID) -> WineResponse:
    row = session.execute(wine_query(owner).where(UserWine.id == wine_id)).mappings().first()
    if row is None:
        raise ApiError(404, "WINE_NOT_FOUND", "This wine is unavailable.")
    return WineResponse.model_validate(row)


def list_wines(session: Session, owner: UUID, limit: int, cursor: str | None) -> WinePage:
    query = wine_query(owner)
    last_date = query.selected_columns.last_consumed_date
    if cursor:
        consumed, identifier = decode_cursor(cursor, "wines", owner)
        if consumed is None:
            query = query.where(last_date.is_(None), UserWine.id > identifier)
        else:
            query = query.where(
                or_(
                    last_date.is_(None),
                    last_date < consumed,
                    and_(last_date == consumed, UserWine.id > identifier),
                )
            )
    rows = (
        session.execute(query.order_by(last_date.desc().nulls_last(), UserWine.id).limit(limit + 1))
        .mappings()
        .all()
    )
    items = [WineResponse.model_validate(row) for row in rows[:limit]]
    return WinePage(
        items=items,
        nextCursor=encode_cursor("wines", owner, items[-1].last_consumed_date, items[-1].id)
        if len(rows) > limit
        else None,
    )


def list_entries(
    session: Session, owner: UUID, wine_id: UUID, limit: int, cursor: str | None
) -> EntryPage:
    read_wine(session, owner, wine_id)
    scope = f"entries:{wine_id}"
    query = select(DrinkingEntry).where(
        DrinkingEntry.owner_id == owner, DrinkingEntry.user_wine_id == wine_id
    )
    if cursor:
        consumed, identifier = decode_cursor(cursor, scope, owner)
        if consumed is None:
            raise ApiError(422, "INVALID_CURSOR", "Reload this list to continue.")
        query = query.where(
            or_(
                DrinkingEntry.consumed_date < consumed,
                and_(DrinkingEntry.consumed_date == consumed, DrinkingEntry.id > identifier),
            )
        )
    rows = session.scalars(
        query.order_by(DrinkingEntry.consumed_date.desc(), DrinkingEntry.id).limit(limit + 1)
    ).all()
    items = [EntryResponse.model_validate(row) for row in rows[:limit]]
    return EntryPage(
        items=items,
        nextCursor=encode_cursor(scope, owner, items[-1].consumed_date, items[-1].id)
        if len(rows) > limit
        else None,
    )
