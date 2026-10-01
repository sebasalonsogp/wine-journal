"""Run separately: python -m wine_journal.worker [--once]."""

import argparse
import logging
import signal
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from threading import Event

from sqlalchemy import Engine

from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.integrations.storage import Storage, StorageSettings
from wine_journal.media.jobs import Claim, claim, finish
from wine_journal.media.photo_processing import PhotoPublisher
from wine_journal.media.photo_sandbox import PhotoSandbox

Handler = Callable[[Claim], None]
logger = logging.getLogger("wine_journal.worker")


@contextmanager
def photo_handlers(engine: Engine) -> Iterator[Mapping[str, Handler]]:
    """Validate infrastructure before claiming; never load modules from a job kind."""
    storage = Storage(StorageSettings.model_validate({}))
    try:
        storage.check_private_bucket()
        decoder = PhotoSandbox()
        yield {"process_photo": PhotoPublisher(engine, storage, decoder)}
    finally:
        storage.close()


def run_once(engine: Engine, handlers: Mapping[str, Handler], *, lease_seconds: int = 60) -> bool:
    job = claim(engine, lease_seconds=lease_seconds)
    if job is None:
        return False
    handler = handlers.get(job.kind)
    if handler is None:
        accepted = finish(engine, job, error="UNSUPPORTED_KIND")
        logger.warning("job_unsupported id=%s acknowledged=%s", job.id, accepted)
        return True
    try:
        # No queue transaction/connection is held while executing the handler.
        handler(job)
    except Exception:
        accepted = finish(engine, job, error="HANDLER_FAILED")
        logger.warning("job_failed id=%s attempt=%s acknowledged=%s", job.id, job.attempt, accepted)
    else:
        accepted = finish(engine, job)
        logger.info("job_finished id=%s attempt=%s acknowledged=%s", job.id, job.attempt, accepted)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Run durable Wine Journal media jobs.")
    parser.add_argument("--once", action="store_true", help="Process at most one job and exit.")
    parser.add_argument(
        "--lease-seconds", type=int, default=60, choices=range(1, 3601), metavar="1..3600"
    )
    parser.add_argument(
        "--poll-seconds", type=int, default=2, choices=range(1, 61), metavar="1..60"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        settings = Settings()
        if not settings.media_uploads_enabled:
            logger.info("worker_media_disabled")
            return 0  # Never claim and fail photo jobs against an empty registry.
        if settings.database_url is None:
            raise ValueError("Missing database configuration")
        engine = database_engine(settings.database_url)
    except Exception:
        logger.error("worker_configuration_invalid")
        return 1
    stop = Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    try:
        with photo_handlers(engine) as handlers:
            logger.info("worker_started registered_handlers=%s", len(handlers))
            while not stop.is_set():
                try:
                    worked = run_once(engine, handlers, lease_seconds=args.lease_seconds)
                except Exception:
                    # Driver exceptions may contain private connection or payload details.
                    logger.error("worker_database_unavailable")
                    if args.once:
                        return 1
                    worked = False
                if args.once:
                    break
                if not worked:
                    stop.wait(args.poll_seconds)
        return 0
    except Exception:
        logger.error("worker_startup_failed")
        return 1
    finally:
        engine.dispose()
        logger.info("worker_stopped")


if __name__ == "__main__":
    raise SystemExit(main())
