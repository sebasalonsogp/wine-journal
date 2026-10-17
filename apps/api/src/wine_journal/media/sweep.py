"""Retry exact-key deletion and release logical quota while retaining tombstones."""

import argparse
import json
from uuid import UUID

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from wine_journal.accounts.models import AppUser
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.integrations.storage import Storage, StorageSettings
from wine_journal.media.cleanup import SAFE_UNUSED
from wine_journal.media.photo_processing import derivative_keys

DUE = (
    """a.retired_at IS NOT NULL
    AND (a.cleanup_attempted_at IS NULL
         OR a.cleanup_attempted_at <= clock_timestamp() - interval '5 minutes')
    AND """
    + SAFE_UNUSED
)


def candidates(engine: Engine, *, limit: int = 50) -> list[tuple[UUID, UUID]]:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Batch size must be between 1 and 100.")
    with Session(engine) as session:
        rows = session.execute(
            text(
                "SELECT a.owner_id, a.id FROM app.upload_assets a WHERE "
                + DUE
                + " ORDER BY coalesce(a.cleanup_attempted_at, a.retired_at), a.id LIMIT :limit"
            ),
            {"limit": limit},
        ).all()
        return [(row.owner_id, row.id) for row in rows]


def sweep(engine: Engine, storage: Storage, owner_id: UUID, asset_id: UUID) -> bool:
    """Claim under the account lock, release DB resources, then perform bounded I/O."""
    with Session(engine) as session, session.begin():
        session.execute(text("SET LOCAL lock_timeout = '3s'"))
        if (
            session.scalar(select(AppUser.id).where(AppUser.id == owner_id).with_for_update())
            is None
        ):
            return False
        key = session.scalar(
            text(
                "UPDATE app.upload_assets a SET cleanup_attempted_at = clock_timestamp() "
                "WHERE a.owner_id = :owner AND a.id = :asset AND " + DUE + " RETURNING a.object_key"
            ),
            {"owner": owner_id, "asset": asset_id},
        )
        if key is None:
            return False
        if not key.startswith(f"staging/{asset_id.hex}/"):
            raise ValueError("Storage identity does not match the retired asset.")
    # Immutable retirement prohibits new references/grants/work. A crash or failed
    # delete leaves a due timestamp; the next run can repeat the same exact keys.
    storage.remove((key, *derivative_keys(asset_id)))
    with Session(engine) as session, session.begin():
        session.execute(text("SET LOCAL lock_timeout = '3s'"))
        session.scalar(select(AppUser.id).where(AppUser.id == owner_id).with_for_update())
        # A provider failure or crash before this commit keeps the reservation. An
        # eventual retry verifies absence again; logical quota is released once.
        session.execute(
            text(
                "UPDATE app.upload_assets a SET quota_released_at = clock_timestamp() "
                "WHERE a.owner_id = :owner AND a.id = :asset "
                "AND a.retired_at IS NOT NULL AND a.quota_released_at IS NULL AND " + SAFE_UNUSED
            ),
            {"owner": owner_id, "asset": asset_id},
        )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or delete retired media objects.")
    parser.add_argument(
        "--apply", action="store_true", help="Delete objects and reclaim quota; retain tombstones."
    )
    parser.add_argument("--limit", type=int, choices=range(1, 101), default=50, metavar="1..100")
    args = parser.parse_args()
    engine = None
    storage = None
    try:
        settings = Settings()
        if settings.database_url is None:
            raise ValueError("Database configuration is required.")
        engine = database_engine(settings.database_url)
        batch = candidates(engine, limit=args.limit)
        cleaned = failed = 0
        if args.apply and batch:
            storage = Storage(StorageSettings.model_validate({}))
            for owner, asset in batch:
                try:
                    cleaned += sweep(engine, storage, owner, asset)
                except Exception:
                    # One failing asset must not starve the rest of a bounded batch.
                    failed += 1
        print(
            json.dumps(
                {
                    "mode": "delete" if args.apply else "preview",
                    "candidates": len(batch),
                    "assetsConfirmedAbsent": cleaned,
                    "failed": failed,
                }
            )
        )
        return 1 if failed else 0
    except Exception:
        print("Media deletion failed; retry the bounded batch. Details withheld.")
        return 1
    finally:
        if storage is not None:
            storage.close()
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
