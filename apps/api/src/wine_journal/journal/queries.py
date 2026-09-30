from __future__ import annotations

import base64
import json
from datetime import date
from uuid import UUID

from sqlalchemy import Select, String, and_, cast, func, or_, select
from sqlalchemy.orm import Session

from wine_journal.catalog.models import WineDefinition, WineRelease
from wine_journal.core.errors import ApiError
from wine_journal.journal.models import DrinkingEntry, UserWine
from wine_journal.journal.schemas import EntryPage, EntryResponse, WinePage, WineResponse
from wine_journal.journal.wine_filters import (
    SortValue,
    WineFilters,
    decode_wine_cursor,
    encode_wine_cursor,
)

type WineRow = tuple[
    UUID,
    UUID,
    str,
    str | None,
    str,
    int | None,
    str | None,
    date | None,
    int,
    float | None,
    int,
]


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


def wine_query(owner: UUID, occasion_id: UUID | None = None) -> Select[WineRow]:
    history = (
        select(
            DrinkingEntry.user_wine_id,
            func.max(DrinkingEntry.consumed_date).label("last_date"),
            func.count().label("entry_count"),
        )
        .where(
            DrinkingEntry.owner_id == owner,
            *([DrinkingEntry.occasion_id == occasion_id] if occasion_id else []),
        )
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
            (UserWine.rating_units / 2.0).label("current_rating"),
            UserWine.rating_version,
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


def filtered_wine_query(owner: UUID, filters: WineFilters) -> Select[tuple[*WineRow, SortValue]]:
    query = wine_query(owner)
    if filters.q:
        searchable = func.concat_ws(
            " ",
            WineDefinition.name,
            WineDefinition.producer,
            WineRelease.edition,
            cast(WineRelease.year, String),
        )
        query = query.where(
            *(searchable.icontains(word, autoescape=True) for word in filters.q.split())
        )
    if filters.rating == "RATED":
        query = query.where(UserWine.rating_units.is_not(None))
    elif filters.rating == "UNRATED":
        query = query.where(UserWine.rating_units.is_(None))
    if filters.vintage != "ALL":
        query = query.where(WineRelease.vintage_status == filters.vintage)
    sort_key = query.selected_columns.last_consumed_date
    if filters.sort == "NAME":
        sort_key = func.lower(WineDefinition.name)
    elif filters.sort == "RATING":
        sort_key = UserWine.rating_units.expression
    return query.add_columns(sort_key.label("sort_value"))


def list_wines(
    session: Session,
    owner: UUID,
    limit: int,
    cursor: str | None,
    filters: WineFilters | None = None,
) -> WinePage:
    filters = filters or WineFilters()
    query = filtered_wine_query(owner, filters)
    sort_key = query.selected_columns.sort_value
    if cursor:
        value, identifier = decode_wine_cursor(cursor, filters, owner)
        if value is None:
            query = query.where(sort_key.is_(None), UserWine.id > identifier)
        else:
            query = query.where(
                or_(
                    sort_key.is_(None),
                    sort_key > value if filters.sort == "NAME" else sort_key < value,
                    and_(sort_key == value, UserWine.id > identifier),
                )
            )
    order = sort_key.asc() if filters.sort == "NAME" else sort_key.desc()
    rows = (
        session.execute(query.order_by(order.nulls_last(), UserWine.id).limit(limit + 1))
        .mappings()
        .all()
    )
    items = [WineResponse.model_validate(row) for row in rows[:limit]]
    return WinePage(
        items=items,
        nextCursor=encode_wine_cursor(filters, owner, rows[limit - 1]["sort_value"], items[-1].id)
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
