import json
import signal
import sys
from threading import Event
from unittest.mock import Mock
from uuid import uuid4

import pytest

from wine_journal.core.config import Settings
from wine_journal.media import cleanup, maintenance, sweep


@pytest.mark.parametrize("apply", [False, True])
def test_cycle_preview_is_read_only_and_apply_isolates_failures(
    apply: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = (uuid4(), uuid4())
    monkeypatch.setattr(maintenance, "hold_summary", Mock(return_value={"heldAssets": 2}))
    retire_candidates = Mock(return_value=[pair, pair])
    delete_candidates = Mock(return_value=[pair, pair])
    retire = Mock(side_effect=[RuntimeError("private"), True])
    delete = Mock(side_effect=[RuntimeError("private"), True])
    monkeypatch.setattr(cleanup, "candidates", retire_candidates)
    monkeypatch.setattr(cleanup, "retire", retire)
    monkeypatch.setattr(sweep, "candidates", delete_candidates)
    monkeypatch.setattr(sweep, "sweep", delete)
    result = maintenance.run_cycle(Mock(), Mock() if apply else None, Event(), apply=apply, limit=2)
    assert result["heldAssets"] == 2 and result["batchFull"] is True
    assert result["retired"] == result["assetsConfirmedAbsent"] == int(apply)
    assert result["retirementFailures"] == result["deletionFailures"] == int(apply)
    assert retire.call_count == delete.call_count == (2 if apply else 0)
    assert "private" not in str(result)


def test_cycle_rejects_apply_without_storage_before_any_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = Mock()
    monkeypatch.setattr(maintenance, "hold_summary", summary)
    with pytest.raises(ValueError):
        maintenance.run_cycle(Mock(), None, Event(), apply=True)
    for limit in (True, 0, 101):
        with pytest.raises(ValueError):
            maintenance.run_cycle(Mock(), None, Event(), limit=limit)
    summary.assert_not_called()


@pytest.mark.parametrize("problem", [None, "settings", "bucket", "cycle", "partial"])
@pytest.mark.parametrize("apply", [False, True])
def test_cli_defaults_validates_before_mutation_and_redacts_failures(
    problem: str | None,
    apply: bool,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["maintenance", *(["--apply"] if apply else [])])
    monkeypatch.setattr(signal, "signal", Mock())
    config = Mock(return_value=Settings.model_construct(database_url="unused-synthetic"))
    if problem == "settings":
        config.side_effect = ValueError("SYNTHETIC_PRIVATE")
    monkeypatch.setattr(maintenance, "Settings", config)
    engine, storage = Mock(), Mock()
    monkeypatch.setattr(maintenance, "database_engine", Mock(return_value=engine))
    factory = Mock(return_value=storage)
    monkeypatch.setattr(maintenance, "Storage", factory)
    monkeypatch.setattr(maintenance, "StorageSettings", Mock())
    if problem == "bucket":
        storage.check_private_bucket.side_effect = RuntimeError("SYNTHETIC_PRIVATE")
    run = Mock(
        return_value={
            "retirementFailures": int(problem == "partial"),
            "deletionFailures": 0,
            "heldAssets": 1,
            "batchFull": True,
        }
    )
    if problem == "cycle":
        run.side_effect = RuntimeError("SYNTHETIC_PRIVATE")
    monkeypatch.setattr(maintenance, "run_cycle", run)
    fails = problem in {"settings", "cycle", "partial"} or (apply and problem == "bucket")
    assert maintenance.main() == int(fails)
    output = capsys.readouterr().out
    assert "SYNTHETIC_PRIVATE" not in output
    rows = [json.loads(line) for line in output.splitlines()]
    assert all(row["runId"] and row["entryPoint"] == "maintenance_cli" for row in rows)
    if not apply:
        factory.assert_not_called()
    if problem == "settings":
        run.assert_not_called()
        engine.dispose.assert_not_called()
    else:
        engine.dispose.assert_called_once()
        if apply:
            storage.close.assert_called_once()
        if apply and problem == "bucket":
            run.assert_not_called()
        else:
            assert run.call_args.kwargs == {"apply": apply, "limit": 50}


def test_watch_retries_failed_cycle_and_stops_during_wait(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["maintenance", "--watch"])
    monkeypatch.setattr(signal, "signal", Mock())
    monkeypatch.setattr(
        maintenance,
        "Settings",
        Mock(return_value=Settings.model_construct(database_url="unused-synthetic")),
    )
    engine, stop = Mock(), Event()
    monkeypatch.setattr(maintenance, "database_engine", Mock(return_value=engine))
    monkeypatch.setattr(maintenance, "Event", lambda: stop)
    run = Mock(
        side_effect=[
            RuntimeError("private"),
            {"retirementFailures": 0, "deletionFailures": 0, "heldAssets": 0, "batchFull": False},
        ]
    )
    monkeypatch.setattr(maintenance, "run_cycle", run)
    waits = []

    def wait(seconds: float | None = None) -> bool:
        waits.append(seconds)
        if len(waits) == 2:
            stop.set()
        return stop.is_set()

    monkeypatch.setattr(stop, "wait", wait)
    assert maintenance.main() == 0
    assert run.call_count == 2 and waits == [300, 300]
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    starts = [row["runId"] for row in rows if row["event"] == "maintenance_cycle_started"]
    assert len(set(starts)) == 2
    assert rows[-1]["event"] == "maintenance_stopped"
    engine.dispose.assert_called_once()


def test_stop_between_assets_does_not_start_deletion(monkeypatch: pytest.MonkeyPatch) -> None:
    stop = Event()
    monkeypatch.setattr(maintenance, "hold_summary", Mock(return_value={}))
    monkeypatch.setattr(cleanup, "candidates", Mock(return_value=[(uuid4(), uuid4())] * 2))

    def retire(*_: object) -> bool:
        stop.set()
        return True

    action, deletions = Mock(side_effect=retire), Mock()
    monkeypatch.setattr(cleanup, "retire", action)
    monkeypatch.setattr(sweep, "candidates", deletions)
    report = maintenance.run_cycle(Mock(), Mock(), stop, apply=True)
    assert report["interrupted"] is True and report["retired"] == 1
    action.assert_called_once()
    deletions.assert_not_called()
