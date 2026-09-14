"""Export the implemented API contract without running an HTTP server."""

import json
from pathlib import Path

from wine_journal.main import create_app

destination = Path(__file__).resolve().parents[1] / "contracts" / "openapi.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(
    json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(f"Exported {destination.name}")
