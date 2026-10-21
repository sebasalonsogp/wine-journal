import json
import os
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, event, func, select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.catalog.barcode_importer import import_barcodes, load_barcode_manifest
from wine_journal.catalog.importer import import_catalog
from wine_journal.catalog.models import CatalogBarcodeObservation, CatalogDefinition, CatalogRelease
from wine_journal.core.database import database_engine

ROOT = Path(__file__).resolve().parents[4]
MANIFEST = ROOT / "assets/catalog/barcode-evidence.json"


@pytest.fixture
def barcode_db(database_urls: dict[str, SecretStr]) -> Iterator[Engine]:
    engine = database_engine(database_urls["migration"], role="wine_migrator")
    import_catalog(engine, ROOT / "assets/evaluation/manifest.csv", apply=True)
    try:
        yield engine
    finally:
        with engine.begin() as connection:
            for table in (
                "catalog_barcode_observations",
                "catalog_sources",
                "catalog_releases",
                "catalog_definitions",
            ):
                connection.execute(text(f"DELETE FROM app.{table}"))
        engine.dispose()


def count(engine: Engine) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(CatalogBarcodeObservation)) or 0


def changed(tmp_path: Path, **changes: object) -> Path:
    rows = json.loads(MANIFEST.read_text())
    rows[-1].update(changes)
    path = tmp_path / "barcodes.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def test_preview_repeat_and_parallel_import_preserve_offering_scope(barcode_db: Engine) -> None:
    preview = import_barcodes(barcode_db, MANIFEST)
    assert (preview.observations, preview.package_codes, preview.applied) == (5, 4, False)
    assert count(barcode_db) == 0
    with Session(barcode_db) as session:
        releases_before = set(session.scalars(select(CatalogRelease.id)))
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: import_barcodes(barcode_db, MANIFEST, apply=True), [1, 2])
        )
    assert sorted(r.observations for r in results) == [0, 5]
    assert sorted(r.package_codes for r in results) == [0, 4]
    with Session(barcode_db) as session:
        ids_before = set(session.scalars(select(CatalogBarcodeObservation.id)))
        seven_oaks = session.scalars(
            select(CatalogBarcodeObservation).where(
                CatalogBarcodeObservation.gtin == "00089121288122"
            )
        ).all()
        assert len(seven_oaks) == 2
        assert len({row.definition_id for row in seven_oaks}) == 1
        # Two sourced vintages remain independent releases; neither source wins.
        years = session.scalars(
            select(CatalogRelease.year).where(
                CatalogRelease.definition_id == seven_oaks[0].definition_id
            )
        ).all()
        assert set(years) == {2022, 2023}
    assert import_barcodes(barcode_db, MANIFEST, apply=True).observations == 0
    with Session(barcode_db) as session:
        assert set(session.scalars(select(CatalogRelease.id))) == releases_before
        assert set(session.scalars(select(CatalogBarcodeObservation.id))) == ids_before


@pytest.mark.parametrize(
    "changes",
    [
        {"gtin": 744442479009},
        {"gtin": "744442409009"},
        {"gtin": "10089121288129"},
        {"gtin": "00000000000000"},
        {"bottle_ml": True},
        {"bottle_ml": 0},
        {"source_url": "https://user:DO_NOT_LOG@example.com/wine"},
        {"source_url": "https://example.com/wine?token=DO_NOT_LOG"},
        {"retrieved_on": "2999-01-01"},
        {"market": "WORLDWIDE"},
        {"source_sha256": None},
        {"evidence_status": "CAMERA_VERIFIED"},
        {"year": 2023},
        {"definition_key": "missing"},
        {"wine_name": "Different offering"},
    ],
)
def test_invalid_late_row_never_partially_writes(
    barcode_db: Engine, tmp_path: Path, changes: dict[str, object]
) -> None:
    with pytest.raises(ValueError):
        import_barcodes(barcode_db, changed(tmp_path, **changes), apply=True)
    assert count(barcode_db) == 0


def test_normalized_duplicate_and_input_limits(tmp_path: Path) -> None:
    row = json.loads(MANIFEST.read_text())[0]
    path = tmp_path / "invalid.json"
    invalid: list[object] = [[], {}, [row, {**row, "gtin": "00089121288122"}], [row] * 101]
    for data in invalid:
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError):
            load_barcode_manifest(path)
    path.write_bytes(b"x" * 65537)
    with pytest.raises(ValueError, match="64 KiB"):
        load_barcode_manifest(path)


def test_conflicting_existing_evidence_does_not_overwrite_or_add(
    barcode_db: Engine, tmp_path: Path
) -> None:
    import_barcodes(barcode_db, MANIFEST, apply=True)
    rows = json.loads(MANIFEST.read_text())
    rows[0]["source_url"] = "https://example.com/new-review"
    rows[-1]["bottle_ml"] = 375
    path = tmp_path / "conflict.json"
    path.write_text(json.dumps(rows))
    for apply in (False, True):
        with pytest.raises(ValueError, match="conflicts"):
            import_barcodes(barcode_db, path, apply=apply)
    assert count(barcode_db) == 5
    with Session(barcode_db) as session:
        assert set(session.scalars(select(CatalogBarcodeObservation.bottle_ml))) == {750}


def test_different_offering_or_package_evidence_preserves_ambiguity(
    barcode_db: Engine, tmp_path: Path
) -> None:
    import_barcodes(barcode_db, MANIFEST, apply=True)
    rows = json.loads(MANIFEST.read_text())
    # Synthetic conflicting sources exercise cardinality, not real wine claims.
    additional = {**rows[0], "source_url": "https://example.com/other-source", "bottle_ml": 375}
    with Session(barcode_db) as session:
        other = session.scalar(
            select(CatalogDefinition).where(CatalogDefinition.key == "ridge-monte-bello")
        )
        assert other is not None
        other_row = {
            **rows[0],
            "definition_key": other.key,
            "producer": other.producer,
            "wine_name": other.name,
        }
    path = tmp_path / "ambiguous.json"
    path.write_text(json.dumps([additional, other_row]))
    result = import_barcodes(barcode_db, path, apply=True)
    assert (result.observations, result.package_codes) == (2, 0)
    assert count(barcode_db) == 7


def test_database_failure_rolls_back_the_batch(barcode_db: Engine) -> None:
    def fail(
        connection: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        if statement.startswith("INSERT INTO app.catalog_barcode_observations"):
            raise RuntimeError("Simulated persistence failure")

    event.listen(barcode_db, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="persistence"):
            import_barcodes(barcode_db, MANIFEST, apply=True)
    finally:
        event.remove(barcode_db, "before_cursor_execute", fail)
    assert count(barcode_db) == 0


def test_runtime_is_read_only_and_provider_roles_have_no_access(
    barcode_db: Engine, database_urls: dict[str, SecretStr]
) -> None:
    import_barcodes(barcode_db, MANIFEST, apply=True)
    engine = database_engine(database_urls["runtime"])
    try:
        assert count(engine) == 5
        for sql in [
            "DELETE FROM app.catalog_barcode_observations",
            "UPDATE app.catalog_barcode_observations SET bottle_ml = 375",
            "INSERT INTO app.catalog_barcode_observations "
            "SELECT * FROM app.catalog_barcode_observations WHERE false",
            "TRUNCATE app.catalog_barcode_observations",
        ]:
            with engine.begin() as connection, pytest.raises(ProgrammingError):
                connection.execute(text(sql))
        with barcode_db.connect() as connection:
            for role in ("anon", "authenticated"):
                assert (
                    connection.scalar(
                        text(
                            "SELECT has_table_privilege(:role, "
                            "'app.catalog_barcode_observations', 'SELECT')"
                        ),
                        {"role": role},
                    )
                    is False
                )
    finally:
        engine.dispose()


def test_cli_redaction_and_populated_downgrade_guard(
    barcode_db: Engine, database_urls: dict[str, SecretStr], tmp_path: Path
) -> None:
    environment = dict(os.environ)
    environment["WINE_JOURNAL_MIGRATION_DATABASE_URL"] = database_urls[
        "migration"
    ].get_secret_value()
    command = [sys.executable, str(ROOT / "scripts/seed_barcodes.py"), str(MANIFEST)]
    for args, expected in [
        (command, {"applied": False, "observations": 5, "package_codes": 4}),
        ([*command, "--apply"], {"applied": True, "observations": 5, "package_codes": 4}),
        ([*command, "--apply"], {"applied": True, "observations": 0, "package_codes": 0}),
    ]:
        result = subprocess.run(args, env=environment, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, "Barcode CLI failed"
        assert json.loads(result.stdout) == expected
    invalid = changed(tmp_path, source_url="https://user:DO_NOT_LOG@example.com/wine")
    result = subprocess.run(
        [*command[:-1], str(invalid), "--apply"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1 and "DO_NOT_LOG" not in result.stdout + result.stderr
    assert environment["WINE_JOURNAL_MIGRATION_DATABASE_URL"] not in result.stdout + result.stderr
    downgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "0025_wine_identity"],
        cwd=ROOT / "apps/api",
        env=environment,
        capture_output=True,
        timeout=30,
    )
    assert downgrade.returncode != 0
    assert count(barcode_db) == 5
    for flags, expected, remaining in [
        (["--retract"], {"applied": False, "observations": 5, "package_codes": 4}, 5),
        (["--retract", "--apply"], {"applied": True, "observations": 5, "package_codes": 4}, 0),
        (["--retract", "--apply"], {"applied": True, "observations": 0, "package_codes": 0}, 0),
    ]:
        result = subprocess.run(
            [*command, *flags], env=environment, capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, "Barcode retraction CLI failed"
        assert json.loads(result.stdout) == expected
        assert count(barcode_db) == remaining
