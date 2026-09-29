import hashlib
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.catalog.service import create_manual_release, read_owned_release
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.models import DrinkingEntry, EntrySave, UserWine
from wine_journal.journal.schemas import EntryResponse, SaveEntry


def save_entry(session: Session, principal: Principal, key: UUID, body: SaveEntry) -> EntryResponse:
    digest = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    try:
        with session.begin():
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            owner = read_account(session, principal)
            claimed = session.scalar(
                insert(EntrySave)
                .values(owner_id=owner.id, key=key, request_hash=digest)
                .on_conflict_do_nothing()
                .returning(EntrySave.key)
            )
            intent = session.get(EntrySave, (owner.id, key))
            assert intent is not None
            if claimed is None:
                if intent.request_hash != digest:
                    raise ApiError(
                        409, "SAVE_CONFLICT", "This save key belongs to different input."
                    )
                assert intent.response is not None
                return EntryResponse.model_validate(intent.response)
            if body.manual_wine is not None:
                release = create_manual_release(session, owner.id, body.manual_wine)
            else:
                assert body.release_id is not None
                release = read_owned_release(session, owner.id, body.release_id)
            session.execute(
                insert(UserWine)
                .values(owner_id=owner.id, release_id=release.id)
                .on_conflict_do_nothing(constraint="uq_user_wines_release")
            )
            user_wine = session.scalar(
                select(UserWine).where(
                    UserWine.owner_id == owner.id, UserWine.release_id == release.id
                )
            )
            assert user_wine is not None
            entry = DrinkingEntry(
                owner_id=owner.id, user_wine_id=user_wine.id, consumed_date=body.consumed_date
            )
            session.add(entry)
            session.flush()
            result = EntryResponse.model_validate(entry)
            intent.response = result.model_dump(mode="json", by_alias=True)
            return result
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) == "55P03":
            raise ApiError(
                409, "SAVE_BUSY", "A save is in progress. Retry with the same key."
            ) from None
        raise
