from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from wine_journal.accounts.models import AppUser
from wine_journal.core.auth import Principal
from wine_journal.core.errors import ApiError


def read_account(session: Session, principal: Principal) -> AppUser:
    account = session.scalar(
        select(AppUser).where(
            AppUser.auth_issuer == principal.issuer, AppUser.auth_subject == principal.subject
        )
    )
    if account is None:
        raise ApiError(404, "ACCOUNT_NOT_FOUND", "Finish signing in to create your journal.")
    if account.state != "ACTIVE":
        raise ApiError(403, "ACCOUNT_DISABLED", "This account is unavailable.")
    return account


def bootstrap_account(session: Session, principal: Principal) -> AppUser:
    # The unique constraint serializes concurrent creation. At READ COMMITTED,
    # the following SELECT sees the winner after ON CONFLICT finishes waiting.
    with session.begin():
        session.execute(
            insert(AppUser)
            .values(auth_issuer=principal.issuer, auth_subject=principal.subject)
            .on_conflict_do_nothing(constraint="uq_app_users_identity")
        )
        return read_account(session, principal)
