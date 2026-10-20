import csv
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, event, func, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.catalog.importer import import_catalog, load_manifest
from wine_journal.catalog.models import CatalogDefinition, CatalogRelease, CatalogSource
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.main import create_app

MANIFEST = Path(__file__).resolve().parents[4] / "assets/evaluation/manifest.csv"


@pytest.fixture
def catalog_db(database_urls: dict[str, SecretStr]) -> Iterator[Engine]:
    engine = database_engine(database_urls["migration"], role="wine_migrator")
    try:
        yield engine
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM app.catalog_sources"))
            connection.execute(text("DELETE FROM app.catalog_releases"))
            connection.execute(text("DELETE FROM app.catalog_definitions"))
        engine.dispose()


def counts(engine: Engine) -> tuple[int, ...]:
    with Session(engine) as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model)) or 0
            for model in (CatalogDefinition, CatalogRelease, CatalogSource)
        )


def altered_manifest(tmp_path: Path, **changes: str) -> Path:
    with MANIFEST.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    # The final row fails after many valid rows, exercising batch atomicity.
    rows[-1].update(changes)
    path = tmp_path / "catalog.csv"
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_preview_apply_and_repeat_preserve_ids_and_sources(catalog_db: Engine) -> None:
    preview = import_catalog(catalog_db, MANIFEST)
    assert (preview.definitions, preview.releases, preview.sources, preview.applied) == (
        16,
        30,
        30,
        False,
    )
    assert counts(catalog_db) == (0, 0, 0)
    applied = import_catalog(catalog_db, MANIFEST, apply=True)
    assert applied.applied and applied.releases == 30
    with Session(catalog_db) as session:
        ids = set(session.scalars(select(CatalogRelease.id)))
        editions = session.scalars(
            select(CatalogRelease).where(CatalogRelease.vintage_status == "MULTI_VINTAGE")
        ).all()
        assert {wine.edition for wine in editions} == {"171ème Édition", "172ème Édition"}
        assert all(wine.year is None for wine in editions)
        assert {s.market for s in session.scalars(select(CatalogSource))} == {"UNVERIFIED"}
    repeated = import_catalog(catalog_db, MANIFEST, apply=True)
    assert (repeated.definitions, repeated.releases, repeated.sources) == (0, 0, 0)
    assert counts(catalog_db) == (16, 30, 30)
    with Session(catalog_db) as session:
        assert set(session.scalars(select(CatalogRelease.id))) == ids


def test_parallel_imports_are_idempotent(catalog_db: Engine) -> None:
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: import_catalog(catalog_db, MANIFEST, apply=True), [1, 2])
        )
    assert sorted(result.releases for result in results) == [0, 30]
    assert counts(catalog_db) == (16, 30, 30)


@pytest.mark.parametrize(
    "changes",
    [
        {"year": "2020"},
        {"vintage_status": "UNKNOWN"},
        {"wine_name": " "},
        {"source_url": "http://example.com/wine"},
        {"source_url": "https://user:secret@example.com/wine"},
        {"source_url": "https://example.com/wine?token=secret"},
        {"retrieved_on": "2999-01-01"},
        {"market": "WORLDWIDE"},
        {"evidence_status": "VERIFIED_SCAN"},
        {"fixture_id": "W001"},
        {"definition_key": "ridge-monte-bello"},
    ],
)
def test_invalid_batch_never_partially_imports(
    catalog_db: Engine, tmp_path: Path, changes: dict[str, str]
) -> None:
    with pytest.raises(ValueError):
        import_catalog(catalog_db, altered_manifest(tmp_path, **changes), apply=True)
    assert counts(catalog_db) == (0, 0, 0)


def test_existing_definition_conflict_rolls_back_new_rows(catalog_db: Engine) -> None:
    with Session(catalog_db) as session, session.begin():
        session.add(
            CatalogDefinition(key="grahams-20-year-old-tawny", producer="Other", name="Other")
        )
    for apply in (False, True):
        with pytest.raises(ValueError, match="conflicts"):
            import_catalog(catalog_db, MANIFEST, apply=apply)
        assert counts(catalog_db) == (1, 0, 0)


def test_additional_source_preserves_identity(catalog_db: Engine, tmp_path: Path) -> None:
    import_catalog(catalog_db, MANIFEST, apply=True)
    result = import_catalog(
        catalog_db,
        altered_manifest(tmp_path, source_url="https://www.grahams-port.com/wines"),
        apply=True,
    )
    assert (result.definitions, result.releases, result.sources) == (0, 0, 1)
    assert counts(catalog_db) == (16, 30, 31)


def test_null_identity_constraints_and_orphan_sources(catalog_db: Engine) -> None:
    import_catalog(catalog_db, MANIFEST, apply=True)
    with Session(catalog_db) as session:
        rows = session.scalars(select(CatalogRelease)).all()
        # Null edition and null year must not bypass release uniqueness.
        examples = {row.vintage_status: row for row in rows}
        for row in examples.values():
            with Session(catalog_db) as write, pytest.raises(IntegrityError), write.begin():
                write.add(
                    CatalogRelease(
                        definition_id=row.definition_id,
                        vintage_status=row.vintage_status,
                        year=row.year,
                        edition=row.edition,
                    )
                )
    with Session(catalog_db) as session, pytest.raises(IntegrityError), session.begin():
        session.add(
            CatalogSource(
                release_id=uuid4(),
                url="https://example.com/wine",
                retrieved_on=load_manifest(MANIFEST)[0].retrieved_on,
                market="UNVERIFIED",
                evidence_status="SOURCE_ONLY",
            )
        )


def test_runtime_cannot_publish_and_provider_roles_have_no_access(
    catalog_db: Engine, database_urls: dict[str, SecretStr]
) -> None:
    import_catalog(catalog_db, MANIFEST, apply=True)
    runtime = database_engine(database_urls["runtime"])
    try:
        assert counts(runtime) == (16, 30, 30)
        with catalog_db.connect() as connection:
            for table in ("catalog_definitions", "catalog_releases", "catalog_sources"):
                for role in ("wine_api", "anon", "authenticated"):
                    for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                        allowed = connection.scalar(
                            text("SELECT has_table_privilege(:role, :table, :privilege)"),
                            {"role": role, "table": f"app.{table}", "privilege": privilege},
                        )
                        assert allowed == (role == "wine_api" and privilege == "SELECT")
        for statement in (
            "INSERT INTO app.catalog_definitions (id, key, name, producer) "
            "VALUES (gen_random_uuid(), 'attack', 'Private note', 'Private producer')",
            "UPDATE app.catalog_releases SET year = 2020",
            "DELETE FROM app.catalog_sources",
        ):
            with runtime.begin() as connection, pytest.raises(ProgrammingError):
                connection.execute(text(statement))
    finally:
        runtime.dispose()

    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    principal = Principal("https://catalog.test", uuid4())
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        assert client.post("/api/v1/me", json={}).status_code == 200
        for payload in (
            {"visibility": "PUBLIC"},
            {"ownerId": None},
            {"catalogReleaseId": str(uuid4())},
        ):
            response = client.post(
                "/api/v1/entries",
                headers={"Idempotency-Key": str(uuid4())},
                json={
                    "consumedDate": "2026-10-19",
                    "manualWine": {"name": "Private wine", **payload},
                },
            )
            assert response.status_code == 422
        response = client.post(
            "/api/v1/entries",
            headers={"Idempotency-Key": str(uuid4())},
            json={
                "consumedDate": "2026-10-19",
                "manualWine": {"name": "Private wine"},
            },
        )
        assert response.status_code == 200
    assert counts(catalog_db) == (16, 30, 30)


@pytest.mark.parametrize("content", ["", "fixture_id,fixture_id\nW001,W002\n", "bad\nrow\n"])
def test_invalid_csv_shape_is_rejected(tmp_path: Path, content: str) -> None:
    path = tmp_path / "invalid.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_manifest(path)


def test_cli_preview_apply_repeat_and_redacted_failure(
    catalog_db: Engine, database_urls: dict[str, SecretStr], tmp_path: Path
) -> None:
    environment = dict(os.environ)
    environment["WINE_JOURNAL_MIGRATION_DATABASE_URL"] = database_urls[
        "migration"
    ].get_secret_value()
    root = MANIFEST.parents[2]
    command = [sys.executable, str(root / "scripts/seed_catalog.py"), str(MANIFEST)]
    preview = subprocess.run(command, env=environment, capture_output=True, text=True)
    assert preview.returncode == 0, "Standalone catalog preview failed."
    assert json.loads(preview.stdout) == {
        "applied": False,
        "definitions": 16,
        "releases": 30,
        "sources": 30,
    }
    assert counts(catalog_db) == (0, 0, 0)
    first = subprocess.run([*command, "--apply"], env=environment, capture_output=True, text=True)
    assert first.returncode == 0, "Standalone catalog import failed."
    second = subprocess.run([*command, "--apply"], env=environment, capture_output=True, text=True)
    assert second.returncode == 0, "Standalone catalog repeat failed."
    assert json.loads(second.stdout)["releases"] == 0
    assert counts(catalog_db) == (16, 30, 30)
    invalid = altered_manifest(tmp_path, source_url="https://user:DO_NOT_LOG@example.com/wine")
    failure = subprocess.run(
        [*command[:-1], str(invalid), "--apply"], env=environment, capture_output=True, text=True
    )
    assert failure.returncode == 1
    assert "ValueError" in failure.stderr
    assert "DO_NOT_LOG" not in failure.stderr + failure.stdout
    assert database_urls["migration"].get_secret_value() not in failure.stderr + failure.stdout


def test_input_byte_limit(tmp_path: Path) -> None:
    path = tmp_path / "oversized.csv"
    path.write_bytes(b"x" * 1_048_577)
    with pytest.raises(ValueError, match="1 MiB"):
        load_manifest(path)


def test_database_failure_rolls_back_all_three_tables(catalog_db: Engine) -> None:
    def fail_source_insert(
        connection: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        if statement.startswith("INSERT INTO app.catalog_sources"):
            raise RuntimeError("Simulated source persistence failure")

    event.listen(catalog_db, "before_cursor_execute", fail_source_insert)
    try:
        with pytest.raises(RuntimeError, match="persistence failure"):
            import_catalog(catalog_db, MANIFEST, apply=True)
    finally:
        event.remove(catalog_db, "before_cursor_execute", fail_source_insert)
    assert counts(catalog_db) == (0, 0, 0)


def test_populated_catalog_blocks_downgrade(
    catalog_db: Engine, database_urls: dict[str, SecretStr]
) -> None:
    import_catalog(catalog_db, MANIFEST, apply=True)
    environment = dict(os.environ)
    environment["WINE_JOURNAL_MIGRATION_DATABASE_URL"] = database_urls[
        "migration"
    ].get_secret_value()
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "0021_photo_write_attempts"],
        cwd=MANIFEST.parents[2] / "apps/api",
        env=environment,
        capture_output=True,
    )
    assert result.returncode != 0
    assert b"Catalog data exists" in result.stderr
    assert counts(catalog_db) == (16, 30, 30)
