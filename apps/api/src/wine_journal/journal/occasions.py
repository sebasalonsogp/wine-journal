import hashlib
from uuid import UUID

from sqlalchemy import and_, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import read_account
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError
from wine_journal.journal.models import Occasion, OccasionSave
from wine_journal.journal.occasion_batch import CreateOccasion, OccasionWines, insert_wines
from wine_journal.journal.occasion_schemas import (
    EditOccasion,
    OccasionFields,
    OccasionPage,
    OccasionResponse,
)
from wine_journal.journal.queries import decode_cursor, encode_cursor


def read_occasion(
    session: Session, owner: UUID, occasion_id: UUID, *, lock: bool = False
) -> Occasion:
    query = select(Occasion).where(Occasion.owner_id == owner, Occasion.id == occasion_id)
    if lock:
        query = query.with_for_update(read=True, key_share=True)
    row = session.scalar(query)
    if row is None:
        raise ApiError(404, "OCCASION_NOT_FOUND", "This occasion is unavailable.")
    return row


def list_occasions(session: Session, owner: UUID, limit: int, cursor: str | None) -> OccasionPage:
    query = select(Occasion).where(Occasion.owner_id == owner)
    if cursor:
        day, identifier = decode_cursor(cursor, "occasions", owner)
        if day is None:
            raise ApiError(422, "INVALID_CURSOR", "Reload this list to continue.")
        query = query.where(
            or_(
                Occasion.occasion_date < day,
                and_(Occasion.occasion_date == day, Occasion.id > identifier),
            )
        )
    rows = session.scalars(
        query.order_by(Occasion.occasion_date.desc(), Occasion.id).limit(limit + 1)
    ).all()
    items = [OccasionResponse.model_validate(row) for row in rows[:limit]]
    return OccasionPage(
        items=items,
        nextCursor=encode_cursor("occasions", owner, items[-1].occasion_date, items[-1].id)
        if len(rows) > limit
        else None,
    )


def create_occasion(
    session: Session, principal: Principal, key: UUID, body: OccasionFields
) -> OccasionResponse:
    creation = CreateOccasion.model_validate(body.model_dump(by_alias=True))
    return save_occasion_wines(session, principal, key, creation)


def save_occasion_wines(
    session: Session,
    principal: Principal,
    key: UUID,
    body: CreateOccasion | OccasionWines,
    occasion_id: UUID | None = None,
) -> OccasionResponse:
    # Empty batches preserve standalone creation hashes issued before O03.
    payload = body.model_dump_json(exclude={"wines"} if not body.wines else set())
    digest = hashlib.sha256(
        (f"add:{occasion_id}:" + payload if occasion_id else payload).encode()
    ).hexdigest()
    try:
        with session.begin():
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            owner = read_account(session, principal).id
            claimed = session.scalar(
                insert(OccasionSave)
                .values(owner_id=owner, key=key, request_hash=digest)
                .on_conflict_do_nothing()
                .returning(OccasionSave.key)
            )
            intent = session.get(OccasionSave, (owner, key))
            assert intent is not None
            if claimed is None:
                if intent.request_hash != digest:
                    raise ApiError(
                        409, "SAVE_CONFLICT", "This save key belongs to different input."
                    )
                assert intent.response is not None
                if intent.response.get("deleted") is True:
                    raise ApiError(409, "OCCASION_REMOVED", "This saved occasion has been deleted.")
                return OccasionResponse.model_validate(intent.response)
            if occasion_id is not None:
                occasion = read_occasion(session, owner, occasion_id, lock=True)
            else:
                assert isinstance(body, CreateOccasion)
                occasion = Occasion(owner_id=owner, **body.model_dump(exclude={"wines"}))
                session.add(occasion)
                session.flush()
            insert_wines(session, owner, occasion.id, body.wines)
            result = OccasionResponse.model_validate(occasion)
            intent.response = result.model_dump(mode="json", by_alias=True)
            return result
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) == "55P03":
            raise ApiError(
                409, "SAVE_BUSY", "A save is in progress. Retry with the same key.", retry_after=3
            ) from None
        raise


def edit_occasion(
    session: Session, principal: Principal, occasion_id: UUID, body: EditOccasion
) -> OccasionResponse:
    try:
        with session.begin():
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            owner = read_account(session, principal).id
            read_occasion(session, owner, occasion_id)
            saved = session.scalar(
                update(Occasion)
                .where(
                    Occasion.owner_id == owner,
                    Occasion.id == occasion_id,
                    Occasion.version == body.version,
                )
                .values(**body.model_dump(exclude={"version"}), version=body.version + 1)
                .returning(Occasion),
                execution_options={"populate_existing": True},
            )
            if saved is None:
                raise ApiError(
                    409, "EDIT_CONFLICT", "This occasion changed. Review the latest version."
                )
            return OccasionResponse.model_validate(saved)
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) == "55P03":
            raise ApiError(409, "EDIT_BUSY", "Another edit is saving. Review and retry.") from None
        raise
