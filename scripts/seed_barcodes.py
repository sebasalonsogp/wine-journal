"""Preview or import reviewed barcode evidence using offline migration credentials."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from wine_journal.catalog.barcode_importer import import_barcodes
from wine_journal.core.config import MigrationSettings
from wine_journal.core.database import database_engine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--apply", action="store_true", help="Commit; the default only previews.")
    parser.add_argument(
        "--retract", action="store_true", help="Remove only exact reviewed evidence matches."
    )
    args = parser.parse_args()
    try:
        settings = MigrationSettings.model_validate({})
        engine = database_engine(settings.migration_database_url, role="wine_migrator")
        try:
            result = import_barcodes(engine, args.manifest, apply=args.apply, retract=args.retract)
        finally:
            engine.dispose()
        print(json.dumps(asdict(result), sort_keys=True))
        return 0
    except Exception as exc:
        print(
            f"Barcode import failed ({type(exc).__name__}); no values were logged.", file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
