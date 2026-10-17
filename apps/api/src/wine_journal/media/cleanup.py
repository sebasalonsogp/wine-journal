"""Bounded retirement; physical deletion and quota release are a separate step."""

import argparse
import json
from uuid import UUID

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from wine_journal.accounts.models import AppUser
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine

# Do not replace unresolved grants or jobs with a guessed timeout. The draft age
# is only a retention policy; these guards are independently required.
ELIGIBLE = """
    a.retired_at IS NULL
    AND a.created_at <= clock_timestamp() - interval '24 hours'
    AND a.state IN ('PENDING', 'READY', 'FAILED')
    AND a.unsettled_grants = 0
    AND (a.grant_expires_at IS NULL OR a.grant_expires_at <= clock_timestamp())
    AND NOT EXISTS (
        SELECT 1 FROM app.entry_photos p
        WHERE p.owner_id = a.owner_id AND p.asset_id = a.id AND NOT p.removed)
    AND NOT EXISTS (
        SELECT 1 FROM app.occasion_photos p
        WHERE p.owner_id = a.owner_id AND p.asset_id = a.id AND NOT p.removed)
    AND NOT EXISTS (
        SELECT 1 FROM app.user_wines w
        WHERE w.owner_id = a.owner_id AND w.cover_asset_id = a.id)
    AND NOT EXISTS (
        SELECT 1 FROM app.jobs j
        WHERE j.owner_id = a.owner_id AND j.reference_id = a.id
        AND j.state IN ('PENDING', 'RUNNING'))
"""


def candidates(engine: Engine, *, limit: int = 50) -> list[tuple[UUID, UUID]]:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Batch size must be between 1 and 100.")
    with Session(engine) as session:
        rows = session.execute(
            text(
                "SELECT a.owner_id, a.id FROM app.upload_assets a WHERE "
                + ELIGIBLE
                + " ORDER BY a.created_at, a.id LIMIT :limit"
            ),
            {"limit": limit},
        ).all()
        return [(row.owner_id, row.id) for row in rows]


def retire(engine: Engine, owner_id: UUID, asset_id: UUID) -> bool:
    """The account lock orders this claim against attachments, grants and covers."""
    with Session(engine) as session, session.begin():
        session.execute(text("SET LOCAL lock_timeout = '3s'"))
        account = session.scalar(select(AppUser.id).where(AppUser.id == owner_id).with_for_update())
        if account is None:
            return False
        return (
            session.scalar(
                text(
                    "UPDATE app.upload_assets a SET retired_at = clock_timestamp() "
                    "WHERE a.owner_id = :owner AND a.id = :asset AND "
                    + ELIGIBLE
                    + " RETURNING a.id"
                ),
                {"owner": owner_id, "asset": asset_id},
            )
            is not None
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or retire unused journal uploads.")
    parser.add_argument(
        "--apply", action="store_true", help="Record retirement; never delete files."
    )
    parser.add_argument("--limit", type=int, choices=range(1, 101), default=50, metavar="1..100")
    args = parser.parse_args()
    engine = None
    try:
        settings = Settings()
        if settings.database_url is None:
            raise ValueError("Database configuration is required.")
        engine = database_engine(settings.database_url)
        batch = candidates(engine, limit=args.limit)
        retired = sum(retire(engine, owner, asset) for owner, asset in batch) if args.apply else 0
        print(
            json.dumps(
                {
                    "mode": "retire" if args.apply else "preview",
                    "candidates": len(batch),
                    "retired": retired,
                    "filesDeleted": 0,
                    "quotaReleased": 0,
                }
            )
        )
        return 0
    except Exception:
        # Driver errors can contain credentials or private IDs. A partial batch is
        # safe to retry: each successful retirement was committed independently.
        print("Media retirement failed; retry the bounded batch. Details withheld.")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
