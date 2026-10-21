"""Bounded recurring cleanup, preview by default; run under a process supervisor."""

import argparse
import json
import logging
import signal
import time
from datetime import UTC, datetime
from threading import Event
from uuid import uuid4

from sqlalchemy import Engine

from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.integrations.storage import Storage, StorageSettings
from wine_journal.media import cleanup, sweep
from wine_journal.media.maintenance_status import hold_summary


def run_cycle(
    engine: Engine, storage: Storage | None, stop: Event, *, apply: bool = False, limit: int = 50
) -> dict[str, int | bool]:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Batch size must be between 1 and 100.")
    if apply and storage is None:
        raise ValueError("Apply requires configured private storage.")
    result: dict[str, int | bool] = {
        "retirementCandidates": 0,
        "retired": 0,
        "deletionCandidates": 0,
        "assetsConfirmedAbsent": 0,
        "retirementFailures": 0,
        "deletionFailures": 0,
        "batchFull": False,
        "interrupted": False,
    }
    result.update(hold_summary(engine))
    if result.get("writeAccountingMismatchAssets", 0):
        # A ledger entry without its counter hold invalidates cleanup assumptions.
        # Report only; do not select candidates, repair counters or touch Storage.
        return result
    retirements = cleanup.candidates(engine, limit=limit)
    result["retirementCandidates"] = len(retirements)
    for owner, asset in retirements if apply else ():
        if stop.is_set():
            break
        try:
            result["retired"] += cleanup.retire(engine, owner, asset)
        except Exception:
            result["retirementFailures"] += 1
    # Query after retirement so newly retired objects can be swept in this cycle.
    deletions = [] if stop.is_set() else sweep.candidates(engine, limit=limit)
    result["deletionCandidates"] = len(deletions)
    for owner, asset in deletions if apply else ():
        if stop.is_set():
            break
        assert storage is not None
        try:
            result["assetsConfirmedAbsent"] += sweep.sweep(engine, storage, owner, asset)
        except Exception:
            result["deletionFailures"] += 1
    result["batchFull"] = len(retirements) == limit or len(deletions) == limit
    result["interrupted"] = stop.is_set()
    return result


def emit(event: str, run_id: str, entry_point: str, **fields: object) -> None:
    print(
        json.dumps(
            {
                "event": event,
                "runId": run_id,
                "entryPoint": entry_point,
                "timestamp": datetime.now(UTC).isoformat(),
                **fields,
            }
        ),
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or run bounded recurring media cleanup.")
    parser.add_argument("--apply", action="store_true", help="Retire, delete and reclaim quota.")
    parser.add_argument("--watch", action="store_true", help="Repeat until SIGINT/SIGTERM.")
    parser.add_argument("--limit", type=int, choices=range(1, 101), default=50, metavar="1..100")
    parser.add_argument(
        "--interval-seconds", type=int, choices=range(300, 3601), default=300, metavar="300..3600"
    )
    args = parser.parse_args()
    # Emit our allowlisted events only, not provider URLs or SQL diagnostics.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    entry_point = "maintenance_watch" if args.watch else "maintenance_cli"
    run_id = uuid4().hex
    engine = storage = None
    stop = Event()
    previous = {
        sig: signal.signal(sig, lambda *_: stop.set()) for sig in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        settings = Settings()
        if settings.database_url is None:
            raise ValueError("Database configuration is required.")
        engine = database_engine(settings.database_url)
        if args.apply:
            storage = Storage(StorageSettings.model_validate({}))
            storage.check_private_bucket()  # Validate before any irreversible retirement.
        emit("maintenance_started", run_id, entry_point, mode="apply" if args.apply else "preview")
        while not stop.is_set():
            run_id = uuid4().hex
            started = time.monotonic()
            failed = False
            emit("maintenance_cycle_started", run_id, entry_point)
            try:
                result = run_cycle(engine, storage, stop, apply=args.apply, limit=args.limit)
                cleanup_failed = bool(result["retirementFailures"] or result["deletionFailures"])
                mismatch = bool(result.get("writeAccountingMismatchAssets", 0))
                failed = cleanup_failed or mismatch
                alerts = []
                if cleanup_failed:
                    alerts.append("CLEANUP_FAILED")
                if mismatch:
                    alerts.append("WRITE_ACCOUNTING_MISMATCH")
                if result["heldAssets"]:
                    alerts.append("HELD_ASSETS")
                if result["batchFull"]:
                    alerts.append("BATCH_FULL")
                emit(
                    "maintenance_cycle_finished",
                    run_id,
                    entry_point,
                    level="warning" if failed else "info",
                    alerts=alerts,
                    durationMs=round((time.monotonic() - started) * 1000),
                    **result,
                )
            except Exception:
                failed = True
                emit(
                    "maintenance_cycle_failed",
                    run_id,
                    entry_point,
                    level="error",
                    code="CYCLE_UNAVAILABLE",
                )
            if not args.watch:
                return int(failed)
            stop.wait(args.interval_seconds)
        return 0
    except Exception:
        emit(
            "maintenance_startup_failed",
            run_id,
            entry_point,
            level="error",
            code="CONFIGURATION_UNAVAILABLE",
        )
        return 1
    finally:
        if storage is not None:
            storage.close()
        if engine is not None:
            engine.dispose()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        emit("maintenance_stopped", run_id, entry_point)


if __name__ == "__main__":
    raise SystemExit(main())
