"""R03a: evaluate only reviewed public fixtures; no API integration or cloud upload."""

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from label_matching import candidates, read_words, year_tokens

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets/evaluation"
IMAGE = "wine-journal-label-evaluation:v1"
DOCKER = [
    "docker",
    "--host",
    "npipe:////./pipe/docker_engine" if os.name == "nt" else "unix:///var/run/docker.sock",
]


def checked_bytes(path: Path, expected_hash: str) -> bytes:
    if not path.resolve().is_relative_to((ASSETS / "barcode").resolve()):
        raise ValueError("Image must be an evaluation fixture")
    with path.open("rb") as source:
        content = source.read(4 * 1024 * 1024 + 1)
    if not content or len(content) > 4 * 1024 * 1024:
        raise ValueError("Image exceeds fixture byte limit")
    if hashlib.sha256(content).hexdigest() != expected_hash:
        raise ValueError("Fixture hash changed")
    return content


def recognize(content: bytes, image: str, psm: int) -> dict[str, object]:
    name = "wine-label-eval-" + uuid4().hex
    command = [
        *DOCKER,
        "run",
        "--name",
        name,
        "--pull",
        "never",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        "256m",
        "--memory-swap",
        "256m",
        "--pids-limit",
        "32",
        "--cpus",
        "1",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",
        "--log-driver",
        "none",
        "-i",
        image,
        "stdin",
        "stdout",
        "-l",
        "eng",
        "--psm",
        str(psm),
        "tsv",
    ]
    started = time.monotonic()
    result: dict[str, object] = {"status": "UNAVAILABLE", "text": "", "mean_word_confidence": None}
    try:
        output = subprocess.run(command, input=content, capture_output=True, timeout=15)
        if output.returncode == 0:
            text, confidence = read_words(output.stdout)
            result.update(
                status="READ" if text else "NO_READABLE_TEXT",
                text=text,
                mean_word_confidence=confidence,
            )
        elif output.returncode in (124, 137):
            result["status"] = "LIMIT_EXCEEDED"
        elif output.returncode == 1:
            result["status"] = "REJECTED_IMAGE"
    except subprocess.TimeoutExpired:
        result["status"] = "TIMEOUT"
    except (UnicodeError, ValueError):
        result["status"] = "INVALID_OUTPUT"
    finally:
        # Docker-client timeout alone does not stop its container. Abort the run
        # if cleanup cannot be confirmed; do not falsely report a clean evaluation.
        subprocess.run(
            [*DOCKER, "rm", "--force", name], capture_output=True, timeout=10, check=True
        )
    result["elapsed_ms_including_container"] = round((time.monotonic() - started) * 1000)
    return result


def evaluate(image: str, psm: int) -> dict[str, object]:
    with (ASSETS / "manifest.csv").open(encoding="utf-8", newline="") as source:
        catalog = list(csv.DictReader(source))
    results: list[dict[str, object]] = []
    manifests = {}
    for manifest_name in ("barcode-images.json", "barcode-images-ridge.json"):
        raw = (ASSETS / manifest_name).read_bytes()
        manifests[manifest_name] = hashlib.sha256(raw).hexdigest()
        manifest = json.loads(raw)
        for item in manifest["images"]:
            content = checked_bytes(ASSETS / "barcode" / item["file"], item["sha256"])
            if item["width"] * item["height"] > 4_000_000:
                raise ValueError("Fixture exceeds pixel limit")
            result = recognize(content, image, psm)
            text = str(result["text"])
            proposed = candidates(text, catalog)
            expected = item.get(
                "expected_fixture_ids", manifest.get("barcode_candidate_fixture_ids")
            )
            if not expected or not set(expected) <= {row["fixture_id"] for row in catalog}:
                raise ValueError("Missing independent ground truth")
            result.update(
                sample_id=item["id"],
                sha256=item["sha256"],
                candidate_fixture_ids=proposed,
                expected_fixture_ids=expected,
                expected_in_candidates=bool(set(proposed) & set(expected)),
                observed_year_tokens=year_tokens(text),
                expected_visible_year=item.get("observed_year"),
                vintage_resolved=False,
                requires_confirmation=True,
            )
            results.append(result)
    return {
        "evaluated_at": datetime.now(UTC).isoformat(),
        "engine": "Tesseract 5.3.0",
        "english_model_package": "1:4.1.0-2",
        "psm": psm,
        "image_id": image,
        "manifest_sha256": manifests,
        "catalog_sha256": hashlib.sha256((ASSETS / "manifest.csv").read_bytes()).hexdigest(),
        "source_images": len(results),
        "physical_bottles": 0,
        "network_enabled": False,
        "confirmed_releases": 0,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--psm", type=int, choices=[3, 11], default=11)
    parser.add_argument("--output", type=Path, help="Save only public-fixture results to this file")
    args = parser.parse_args()
    try:
        image = (
            subprocess.run(
                [*DOCKER, "image", "inspect", IMAGE, "--format", "{{.Id}}"],
                capture_output=True,
                timeout=10,
                check=True,
            )
            .stdout.decode()
            .strip()
        )
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
            raise ValueError("Unexpected evaluation image")
        report = json.dumps(evaluate(image, args.psm), indent=2) + "\n"
        if args.output:
            args.output.write_text(report, encoding="utf-8")
        else:
            print(report, end="")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        print(
            "Label evaluation failed input, engine or cleanup checks; diagnostics withheld.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
