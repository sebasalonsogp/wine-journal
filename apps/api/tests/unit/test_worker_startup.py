import signal
import sys
from unittest.mock import Mock

import pytest

from wine_journal import worker
from wine_journal.core.config import Settings
from wine_journal.integrations.storage import StorageSettings
from wine_journal.media.photo_processing import PhotoPublisher


@pytest.mark.parametrize("problem", [None, "disabled", "settings", "bucket", "decoder", "database"])
def test_worker_checks_infrastructure_before_claiming_and_closes_resources(
    problem: str | None, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(sys, "argv", ["worker", "--once"])
    monkeypatch.setattr(signal, "signal", Mock())
    config = Mock(
        return_value=Settings.model_construct(
            database_url="unused-synthetic", media_uploads_enabled=problem != "disabled"
        )
    )
    if problem == "settings":
        config.side_effect = ValueError("SYNTHETIC_PRIVATE_CONFIGURATION")
    monkeypatch.setattr(worker, "Settings", config)
    engine, storage, decoder = Mock(), Mock(), Mock()
    make_engine = Mock(return_value=engine)
    monkeypatch.setattr(worker, "database_engine", make_engine)
    monkeypatch.setattr(StorageSettings, "model_validate", Mock(return_value=Mock()))
    monkeypatch.setattr(worker, "Storage", Mock(return_value=storage))
    make_decoder = Mock(return_value=decoder)
    monkeypatch.setattr(worker, "PhotoSandbox", make_decoder)
    run = Mock(return_value=False)
    monkeypatch.setattr(worker, "run_once", run)
    if problem == "bucket":
        storage.check_private_bucket.side_effect = RuntimeError("SYNTHETIC_PRIVATE_STORAGE")
    elif problem == "decoder":
        make_decoder.side_effect = RuntimeError("SYNTHETIC_PRIVATE_DOCKER")
    elif problem == "database":
        run.side_effect = RuntimeError("SYNTHETIC_PRIVATE_DATABASE")
    assert worker.main() == (0 if problem in (None, "disabled") else 1)
    if problem in ("disabled", "settings"):
        assert not make_engine.called and not run.called and not storage.close.called
    else:
        storage.close.assert_called_once()
        engine.dispose.assert_called_once()
        if problem in ("bucket", "decoder"):
            assert not run.called
        else:
            run.assert_called_once()
            assert set(run.call_args.args[1]) == {"process_photo"}
            assert isinstance(run.call_args.args[1]["process_photo"], PhotoPublisher)
    assert "SYNTHETIC_PRIVATE" not in caplog.text
