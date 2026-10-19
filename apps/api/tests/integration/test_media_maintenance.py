import json
import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Event
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.core.auth import Principal
from wine_journal.core.database import database_engine
from wine_journal.integrations.storage import Storage, new_staging_key
from wine_journal.media.maintenance import run_cycle
from wine_journal.media.maintenance_status import hold_summary
from wine_journal.media.models import UploadAsset
from wine_journal.media.uploads import RESERVATION_BYTES


@dataclass
class MaintenanceFixture:
    engine: Engine
    owner: UUID
    assets: list[UUID]


@pytest.fixture
def media(database_urls: dict[str, SecretStr]) -> Iterator[MaintenanceFixture]:
    engine = database_engine(database_urls["runtime"])
    admin = database_engine(database_urls["migration"], role="wine_migrator")
    with Session(engine) as session:
        owner = bootstrap_account(session, Principal("https://maintenance.test", uuid4())).id
    assets = [uuid4() for _ in range(5)]
    with Session(engine) as session, session.begin():
        for index, identifier in enumerate(assets):
            session.add(
                UploadAsset(
                    id=identifier,
                    owner_id=owner,
                    operation_key=uuid4(),
                    object_key=new_staging_key(identifier),
                    declared_bytes=12,
                    declared_type="image/jpeg",
                    reserved_bytes=RESERVATION_BYTES,
                    unsettled_grants=int(index in (2, 3)),
                    unsettled_writes=int(index in (1, 3)),
                    created_at=datetime.now(UTC) - timedelta(days=0 if index == 4 else 2),
                )
            )
    try:
        yield MaintenanceFixture(engine, owner, assets)
    finally:
        with admin.begin() as connection:
            connection.execute(
                text("DELETE FROM app.upload_assets WHERE owner_id = :owner"), {"owner": owner}
            )
        engine.dispose()
        admin.dispose()


def test_cycle_uses_real_eligibility_and_preserves_holds(media: MaintenanceFixture) -> None:
    p, storage = media, Mock(spec=Storage)
    preview = run_cycle(p.engine, None, Event())
    assert preview["heldAssets"] == 3
    assert preview["signingHeldAssets"] == preview["writeHeldAssets"] == 2
    assert preview["heldReservedBytes"] == 3 * RESERVATION_BYTES
    assert preview["retirementCandidates"] == 1 and preview["retired"] == 0
    with Session(p.engine) as session:
        row = session.get(UploadAsset, p.assets[0])
        assert row is not None and row.retired_at is None

    def remove(keys: tuple[str, ...]) -> None:
        assert p.engine.pool.checkedout() == 0  # type: ignore[attr-defined]
        assert len(keys) == 3 and all(p.assets[0].hex in key for key in keys)

    storage.remove.side_effect = remove
    applied = run_cycle(p.engine, storage, Event(), apply=True)
    assert applied["retired"] == applied["assetsConfirmedAbsent"] == 1
    storage.remove.assert_called_once()
    with Session(p.engine) as session:
        for index, identifier in enumerate(p.assets):
            row = session.get(UploadAsset, identifier)
            assert row is not None
            assert (
                (row.retired_at is not None) == (row.quota_released_at is not None) == (index == 0)
            )
    replay = run_cycle(p.engine, storage, Event(), apply=True)
    assert replay["retired"] == replay["assetsConfirmedAbsent"] == 0
    assert hold_summary(p.engine)["heldAssets"] == 3
    storage.remove.assert_called_once()


def test_preview_subprocess_restarts_without_mutation_or_private_output(
    media: MaintenanceFixture, database_urls: dict[str, SecretStr]
) -> None:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("WINE_JOURNAL_")
    }
    environment["WINE_JOURNAL_DATABASE_URL"] = database_urls["runtime"].get_secret_value()
    # Missing Storage configuration is deliberate: preview does not instantiate it.
    environment["WINE_JOURNAL_STORAGE_URL"] = "invalid-preview-must-ignore-this"
    for _ in range(2):
        process = subprocess.run(
            [sys.executable, "-m", "wine_journal.media.maintenance"],
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert process.returncode == 0, "Maintenance preview failed; private output withheld."
        events = [json.loads(line) for line in process.stdout.splitlines()]
        result = next(row for row in events if row["event"] == "maintenance_cycle_finished")
        assert result["retired"] == result["assetsConfirmedAbsent"] == 0
        assert result["heldAssets"] == 3 and result["retirementCandidates"] == 1
        for identifier in (media.owner, *media.assets):
            assert str(identifier) not in process.stdout and identifier.hex not in process.stdout
        assert database_urls["runtime"].get_secret_value() not in process.stdout + process.stderr
        assert "invalid-preview" not in process.stdout + process.stderr
