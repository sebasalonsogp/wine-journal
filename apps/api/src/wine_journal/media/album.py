"""One asset per album card, with bounded, independently pageable provenance."""

import base64
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import text
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.media.occasion_attachments import require_occasion
from wine_journal.media.schemas import PhotoStatus


class AlbumSource(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    kind: Literal["OCCASION", "ENTRY"]
    parent_id: UUID
    user_wine_id: UUID | None
    caption: str | None
    version: int


class AlbumPhoto(PhotoStatus):
    source: AlbumSource
    source_count: int


class AlbumPage(BaseModel):
    items: list[AlbumPhoto]
    nextCursor: str | None


class AlbumSources(BaseModel):
    items: list[AlbumSource]
    nextOffset: int | None


# All references are owner-scoped. Cover references are deliberately absent.
SOURCES = """
WITH sources AS (
    SELECT p.asset_id, 'OCCASION' AS kind, p.occasion_id AS parent_id,
           NULL::uuid AS user_wine_id, p.caption, p.version, 0 AS priority
    FROM app.occasion_photos p
    WHERE p.owner_id = :owner AND p.occasion_id = :occasion AND NOT p.removed
    UNION ALL
    SELECT p.asset_id, 'ENTRY', e.id, e.user_wine_id, p.caption, p.version, 1
    FROM app.entry_photos p
    JOIN app.drinking_entries e ON e.id = p.entry_id AND e.owner_id = p.owner_id
    WHERE p.owner_id = :owner AND e.occasion_id = :occasion AND NOT p.removed
)
"""


def album_page(
    session: Session, principal: Principal, occasion_id: UUID, limit: int, cursor: str | None
) -> AlbumPage:
    with session.begin():
        owner = read_account(session, principal).id
        require_occasion(session, owner, occasion_id)
        before, after = None, None
        if cursor:
            try:
                fields = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
                if not isinstance(fields, list) or len(fields) != 4:
                    raise ValueError
                if fields[:2] != [str(owner), str(occasion_id)]:
                    raise ValueError
                before, after = datetime.fromisoformat(fields[2]), UUID(fields[3])
                if before.tzinfo is None:
                    raise ValueError
            except (ValueError, TypeError, AttributeError):
                raise ApiError(422, "INVALID_CURSOR", "Reload this album to continue.") from None
        query = (
            SOURCES
            + """
        , ranked AS (
            SELECT sources.*, row_number() OVER (
                PARTITION BY asset_id ORDER BY priority, parent_id
            ) AS rank, count(*) OVER (PARTITION BY asset_id) AS source_count FROM sources
        )
        SELECT a.id AS asset_id, a.state, a.width, a.height, a.created_at,
               r.kind, r.parent_id, r.user_wine_id, r.caption, r.version, r.source_count
        FROM ranked r JOIN app.upload_assets a ON a.id = r.asset_id AND a.owner_id = :owner
        WHERE r.rank = 1
        """
        )
        if before is not None:
            query += " AND (a.created_at < :before OR (a.created_at = :before AND a.id > :after))"
        query += " ORDER BY a.created_at DESC, a.id LIMIT :limit"
        rows = (
            session.execute(
                text(query),
                {
                    "owner": owner,
                    "occasion": occasion_id,
                    "before": before,
                    "after": after,
                    "limit": limit + 1,
                },
            )
            .mappings()
            .all()
        )
        items = [
            AlbumPhoto(
                asset_id=row["asset_id"],
                state=row["state"],
                width=row["width"] if row["state"] == "READY" else None,
                height=row["height"] if row["state"] == "READY" else None,
                error_code="PHOTO_PROCESSING_FAILED" if row["state"] == "FAILED" else None,
                source=AlbumSource.model_validate(row),
                source_count=row["source_count"],
            )
            for row in rows[:limit]
        ]
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = base64.urlsafe_b64encode(
                json.dumps(
                    [
                        str(owner),
                        str(occasion_id),
                        last["created_at"].isoformat(),
                        str(last["asset_id"]),
                    ]
                ).encode()
            ).decode()
        return AlbumPage(items=items, nextCursor=next_cursor)


def album_sources(
    session: Session,
    principal: Principal,
    occasion_id: UUID,
    asset_id: UUID,
    limit: int,
    offset: int,
) -> AlbumSources:
    with session.begin():
        owner = read_account(session, principal).id
        require_occasion(session, owner, occasion_id)
        parameters = {
            "owner": owner,
            "occasion": occasion_id,
            "asset": asset_id,
            "limit": limit + 1,
            "offset": offset,
        }
        if not session.scalar(
            text(SOURCES + " SELECT count(*) FROM sources WHERE asset_id = :asset"), parameters
        ):
            raise ApiError(404, "PHOTO_NOT_FOUND", "This photo is unavailable in this album.")
        rows = (
            session.execute(
                text(
                    SOURCES
                    + """
            SELECT * FROM sources WHERE asset_id = :asset
            ORDER BY priority, parent_id LIMIT :limit OFFSET :offset
        """
                ),
                parameters,
            )
            .mappings()
            .all()
        )
        return AlbumSources(
            items=[AlbumSource.model_validate(row) for row in rows[:limit]],
            nextOffset=offset + limit if len(rows) > limit else None,
        )
