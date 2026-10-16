"""Ready memories for one wine, ranked by their latest eligible journal source."""

import base64
import json
from datetime import date
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.ratings import owned_wine
from wine_journal.media.album import AlbumPhoto, AlbumSource


class MomentSource(AlbumSource):
    source_date: date


class WineMoment(AlbumPhoto):
    source: MomentSource


class WineMoments(BaseModel):
    items: list[WineMoment]
    nextCursor: str | None


SOURCES = """
WITH sources AS (
    SELECT p.asset_id, 'ENTRY' AS kind, e.id AS parent_id, e.user_wine_id,
           p.caption, p.version, e.consumed_date AS source_date, 0 AS priority
    FROM app.entry_photos p JOIN app.drinking_entries e
      ON e.id = p.entry_id AND e.owner_id = p.owner_id
    WHERE p.owner_id = :owner AND e.user_wine_id = :wine AND NOT p.removed
    UNION ALL
    SELECT p.asset_id, 'OCCASION', o.id, NULL::uuid,
           p.caption, p.version, o.occasion_date, 1
    FROM app.occasion_photos p JOIN app.occasions o
      ON o.id = p.occasion_id AND o.owner_id = p.owner_id
    WHERE p.owner_id = :owner AND NOT p.removed AND EXISTS (
        SELECT 1 FROM app.drinking_entries e
        WHERE e.owner_id = :owner AND e.user_wine_id = :wine AND e.occasion_id = o.id
    )
), ranked AS (
    SELECT sources.*, row_number() OVER (
        PARTITION BY asset_id ORDER BY source_date DESC, priority, parent_id
    ) AS rank, count(*) OVER (PARTITION BY asset_id) AS source_count FROM sources
)
SELECT a.id AS asset_id, a.state, a.width, a.height,
       r.kind, r.parent_id, r.user_wine_id, r.caption, r.version, r.source_date, r.source_count
FROM ranked r JOIN app.upload_assets a ON a.id = r.asset_id AND a.owner_id = :owner
WHERE r.rank = 1 AND a.state = 'READY' AND NOT EXISTS (
    SELECT 1 FROM app.user_wines w WHERE w.owner_id = :owner AND w.cover_asset_id = a.id
)
"""


def wine_moments(
    session: Session, principal: Principal, wine_id: UUID, limit: int, cursor: str | None
) -> WineMoments:
    with session.begin():
        owner = read_account(session, principal).id
        owned_wine(session, owner, wine_id)
        before, after = None, None
        if cursor:
            try:
                fields = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
                if not isinstance(fields, list) or len(fields) != 4:
                    raise ValueError
                if fields[:2] != [str(owner), str(wine_id)]:
                    raise ValueError
                before, after = date.fromisoformat(fields[2]), UUID(fields[3])
            except (ValueError, TypeError, AttributeError):
                raise ApiError(
                    422, "INVALID_CURSOR", "Reload these memories to continue."
                ) from None
        query = SOURCES
        if before is not None:
            query += " AND (r.source_date < :before OR (r.source_date = :before AND a.id > :after))"
        query += " ORDER BY r.source_date DESC, a.id LIMIT :limit"
        rows = (
            session.execute(
                text(query),
                {
                    "owner": owner,
                    "wine": wine_id,
                    "before": before,
                    "after": after,
                    "limit": limit + 1,
                },
            )
            .mappings()
            .all()
        )
        items = [
            WineMoment(
                asset_id=row["asset_id"],
                state=row["state"],
                width=row["width"],
                height=row["height"],
                error_code=None,
                source=MomentSource.model_validate(row),
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
                        str(wine_id),
                        last["source_date"].isoformat(),
                        str(last["asset_id"]),
                    ]
                ).encode()
            ).decode()
        return WineMoments(items=items, nextCursor=next_cursor)
