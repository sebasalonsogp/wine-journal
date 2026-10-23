"""Opt-in evidence from the real, network-isolated OCR container."""

import io
import os
import subprocess
from pathlib import Path

import pytest
from PIL import Image

pytestmark = pytest.mark.skipif(
    os.getenv("WINE_JOURNAL_TEST_LABEL_OCR") != "1", reason="OCR evaluation image not requested"
)
ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize(
    ("preprocess", "expected_matches"),
    [(False, {"I001", "I005"}), (True, {"I001", "I002"})],
    ids=["baseline", "fixed-preprocessing"],
)
def test_real_ocr_positive_blank_and_malformed_cleanup(
    monkeypatch: pytest.MonkeyPatch, preprocess: bool, expected_matches: set[str]
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from evaluate_label import DOCKER, IMAGE, evaluate, recognize

    image = (
        subprocess.run(
            [*DOCKER, "image", "inspect", IMAGE, "--format", "{{.Id}}"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        .stdout.decode()
        .strip()
    )
    report = evaluate(image, 11, preprocess)
    results = report["results"]
    assert isinstance(results, list)
    assert len(results) == 7
    # Observed successes, not a claim all supplied images resolve.
    assert {
        row["sample_id"] for row in results if row["expected_in_candidates"]
    } == expected_matches
    assert all(not row["vintage_resolved"] for row in results)
    assert all(not row["withheld_false_positive"] for row in results)
    assert report["preprocessing"] == ("portrait-crop-contrast-v1" if preprocess else "none")
    blank = io.BytesIO()
    Image.new("RGB", (400, 400), "white").save(blank, format="PNG")
    assert recognize(blank.getvalue(), image, 11)["status"] == "NO_READABLE_TEXT"
    assert recognize(b"not an image", image, 11)["status"] == "REJECTED_IMAGE"
    remaining = subprocess.run(
        [*DOCKER, "ps", "--all", "--filter", "name=wine-label-eval-", "--format", "{{.Names}}"],
        capture_output=True,
        check=True,
        timeout=10,
    )
    assert not remaining.stdout.strip()
