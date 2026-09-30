from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from wine_journal.core.errors import ApiError
from wine_journal.journal.models import UserWine
from wine_journal.journal.occasions import read_occasion
from wine_journal.journal.queries import decode_cursor, encode_cursor, wine_query
from wine_journal.journal.schemas import WinePage, WineResponse


def list_occasion_wines(
    session: Session, owner: UUID, occasion_id: UUID, limit: int, cursor: str | None
) -> WinePage:
    read_occasion(session, owner, occasion_id)
    scope = f"occasion-wines:{occasion_id}"
    query = wine_query(owner, occasion_id)
    day = query.selected_columns.last_consumed_date
    query = query.where(query.selected_columns.entry_count > 0)
    if cursor:
        consumed, identifier = decode_cursor(cursor, scope, owner)
        if consumed is None:
            raise ApiError(422, "INVALID_CURSOR", "Reload this list to continue.")
        query = query.where(or_(day < consumed, and_(day == consumed, UserWine.id > identifier)))
    rows = (
        session.execute(query.order_by(day.desc(), UserWine.id).limit(limit + 1)).mappings().all()
    )
    items = [WineResponse.model_validate(row) for row in rows[:limit]]
    return WinePage(
        items=items,
        nextCursor=encode_cursor(scope, owner, items[-1].last_consumed_date, items[-1].id)
        if len(rows) > limit
        else None,
    )
