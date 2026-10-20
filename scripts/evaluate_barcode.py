"""R02a: offline-by-default preflight; --live probes public product facts only."""

import argparse
import asyncio
import csv
import json
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError

from wine_journal.identification.gtin import canonical_gtin
from wine_journal.integrations.barcode_probe import probe_product

ROOT = Path(__file__).resolve().parents[1]


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_id: str = Field(pattern=r"^B[0-9]{3}$")
    gtin: str = Field(max_length=14, strict=True)
    expected_fixture_ids: list[str] = Field(min_length=1, max_length=30)
    bottle_ml: int = Field(gt=0, le=30000, strict=True)
    source_url: HttpUrl
    retrieved_on: date
    evidence_status: Literal["WEB_TEXT"]
    market: Literal["UNVERIFIED"]


def load_observations(path: Path) -> list[Observation]:
    if path.stat().st_size > 65536:
        raise ValueError("Observation file exceeds 64 KiB.")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not 1 <= len(raw) <= 10:
        raise ValueError("Provide one to ten observations.")
    observations = [Observation.model_validate(item) for item in raw]
    with (ROOT / "assets/evaluation/manifest.csv").open(encoding="utf-8", newline="") as source:
        known = {row["fixture_id"] for row in csv.DictReader(source)}
    identifiers = set()
    codes = set()
    for item in observations:
        if item.sample_id in identifiers or not set(item.expected_fixture_ids) <= known:
            raise ValueError("Duplicate sample or unknown expected fixture.")
        if len(set(item.expected_fixture_ids)) != len(item.expected_fixture_ids):
            raise ValueError("Duplicate expected fixture.")
        if (
            item.source_url.scheme != "https"
            or item.source_url.username
            or item.source_url.password
        ):
            raise ValueError("Sources require HTTPS without credentials.")
        if item.retrieved_on > datetime.now(UTC).date():
            raise ValueError("Source date is in the future.")
        identifiers.add(item.sample_id)
        codes.add(canonical_gtin(item.gtin))
    if len(codes) > 5:
        raise ValueError("At most five distinct package codes per evaluation.")
    return observations


async def evaluate(observations: list[Observation], live: bool) -> dict[str, object]:
    # The sample list is independent ground truth, never inferred from provider output.
    grouped: dict[str, list[Observation]] = {}
    for item in observations:
        grouped.setdefault(canonical_gtin(item.gtin), []).append(item)
    results: list[dict[str, object]] = []
    async with httpx.AsyncClient(trust_env=False) as client:
        for index, (code, samples) in enumerate(grouped.items()):
            row: dict[str, object] = {
                "canonical_gtin": code,
                "sample_ids": [item.sample_id for item in samples],
                "expected_fixture_ids": sorted(
                    {key for item in samples for key in item.expected_fixture_ids}
                ),
                "status": "NOT_REQUESTED",
            }
            if live:
                if index:
                    await asyncio.sleep(4.2)  # Below the documented 15 read requests/minute/IP.
                started = time.monotonic()
                result = await probe_product(client, samples[0].gtin)
                row.update(result.model_dump(mode="json"))
                row["elapsed_ms"] = round((time.monotonic() - started) * 1000)
            results.append(row)
            if row["status"] in ("RATE_LIMITED", "UNAVAILABLE", "TIMEOUT"):
                break  # Do not turn an outage into retries or additional provider traffic.
    return {
        "evaluated_at": datetime.now(UTC).isoformat(),
        "mode": "LIVE_PUBLIC_READ" if live else "OFFLINE_PREFLIGHT",
        "provider": "Open Food Facts API v3",
        "source_observations": len(observations),
        "distinct_package_codes": len(grouped),
        "requested_package_codes": len(results) if live else 0,
        "unrequested_package_codes": len(grouped) - (len(results) if live else 0),
        "confirmed_wine_releases": 0,
        "camera_decoding_tested": False,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--live", action="store_true", help="Read public provider data; no retries or writes."
    )
    args = parser.parse_args()
    try:
        observations = load_observations(args.manifest)
        print(json.dumps(asyncio.run(evaluate(observations, args.live)), indent=2))
        return 0
    except (OSError, ValueError, ValidationError):
        print("Barcode evaluation rejected its input; contents withheld.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
