"""At-least-once queue. No files, URLs, credentials or user text in job payloads."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import Engine, and_, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from wine_journal.media.models import Job


@dataclass(frozen=True)
class Claim:
    id: UUID
    owner_id: UUID
    operation_key: UUID
    kind: str
    reference_id: UUID
    token: UUID
    attempt: int
    max_attempts: int


def enqueue(
    session: Session,
    *,
    owner_id: UUID,
    operation_key: UUID,
    kind: str,
    reference_id: UUID,
    max_attempts: int = 5,
) -> UUID:
    """Caller owns the transaction, including the domain change that requires work."""
    if (
        not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", kind)
        or type(max_attempts) is not int
        or not 1 <= max_attempts <= 10
    ):
        raise ValueError("Invalid job kind or attempt limit.")
    session.execute(
        insert(Job)
        .values(
            owner_id=owner_id,
            operation_key=operation_key,
            kind=kind,
            reference_id=reference_id,
            max_attempts=max_attempts,
        )
        .on_conflict_do_nothing(constraint="uq_jobs_operation")
    )
    job = session.scalar(
        select(Job).where(Job.owner_id == owner_id, Job.operation_key == operation_key)
    )
    assert job is not None
    if (job.kind, job.reference_id, job.max_attempts) != (kind, reference_id, max_attempts):
        raise ValueError("Job operation key already belongs to different work.")
    return job.id


def claim(engine: Engine, *, lease_seconds: int = 60) -> Claim | None:
    if not 1 <= lease_seconds <= 3600:
        raise ValueError("Lease must be between 1 and 3600 seconds.")
    with Session(engine) as session, session.begin():
        session.execute(text("SET LOCAL lock_timeout = '3s'"))
        job = session.scalar(
            select(Job)
            .where(
                or_(
                    and_(Job.state == "PENDING", Job.run_after <= func.now()),
                    and_(Job.state == "RUNNING", Job.lease_until <= func.now()),
                )
            )
            .order_by(Job.run_after, Job.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        if job.attempts >= job.max_attempts:
            job.state, job.error_code = "FAILED", "LEASE_EXPIRED"
            job.lease_token = job.lease_until = None
            return None
        now = session.scalar(select(func.clock_timestamp()))
        assert isinstance(now, datetime)
        job.state = "RUNNING"
        job.attempts += 1
        job.lease_token = uuid4()
        job.lease_until = now + timedelta(seconds=lease_seconds)
        return Claim(
            job.id,
            job.owner_id,
            job.operation_key,
            job.kind,
            job.reference_id,
            job.lease_token,
            job.attempts,
            job.max_attempts,
        )


def finish(
    engine: Engine,
    job: Claim,
    *,
    error: Literal["HANDLER_FAILED", "UNSUPPORTED_KIND"] | None = None,
) -> bool:
    """Only the current, unexpired claimant may acknowledge or schedule another attempt."""
    retry = error == "HANDLER_FAILED" and job.attempt < job.max_attempts
    with Session(engine) as session, session.begin():
        session.execute(text("SET LOCAL lock_timeout = '3s'"))
        saved = session.scalar(
            update(Job)
            .where(
                Job.id == job.id,
                Job.state == "RUNNING",
                Job.lease_token == job.token,
                Job.lease_until > func.clock_timestamp(),
            )
            .values(
                state="PENDING" if retry else "FAILED" if error else "SUCCEEDED",
                lease_token=None,
                lease_until=None,
                error_code=error,
                run_after=func.clock_timestamp() + timedelta(seconds=min(300, 2**job.attempt))
                if retry
                else Job.run_after,
            )
            .returning(Job.id)
        )
        return saved is not None


def renew(engine: Engine, job: Claim, *, lease_seconds: int = 60) -> bool:
    """Handlers may renew between bounded chunks; an expired lease cannot be revived."""
    if not 1 <= lease_seconds <= 3600:
        raise ValueError("Lease must be between 1 and 3600 seconds.")
    with Session(engine) as session, session.begin():
        session.execute(text("SET LOCAL lock_timeout = '3s'"))
        return (
            session.scalar(
                update(Job)
                .where(
                    Job.id == job.id,
                    Job.state == "RUNNING",
                    Job.lease_token == job.token,
                    Job.lease_until > func.clock_timestamp(),
                )
                .values(lease_until=func.clock_timestamp() + timedelta(seconds=lease_seconds))
                .returning(Job.id)
            )
            is not None
        )
