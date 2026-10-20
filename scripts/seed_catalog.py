"""Preview or apply reviewed wine identities with offline migration credentials."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from wine_journal.catalog.importer import import_catalog
from wine_journal.core.config import MigrationSettings
from wine_journal.core.database import database_engine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--apply", action="store_true", help="Commit the import; default is preview."
    )
    args = parser.parse_args()
    try:
        settings = MigrationSettings.model_validate({})
        engine = database_engine(settings.migration_database_url, role="wine_migrator")
        try:
            result = import_catalog(engine, args.manifest, apply=args.apply)
        finally:
            engine.dispose()
        print(json.dumps(asdict(result), sort_keys=True))
        return 0
    except Exception as exc:
        # Validation and driver errors may contain input or a DSN. Never echo them.
        print(
            f"Catalog import failed ({type(exc).__name__}); no values were logged.", file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
