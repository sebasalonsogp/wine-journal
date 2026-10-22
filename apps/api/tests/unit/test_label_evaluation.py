import csv
import hashlib
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[4]


def test_label_candidates_keep_vintages_and_do_not_use_unrelated_years(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from label_matching import candidates, year_tokens

    with (ROOT / "assets/evaluation/manifest.csv").open(encoding="utf-8", newline="") as source:
        catalog = list(csv.DictReader(source))
    text = "J. Lohr Seven Oaks Cabernet Sauvignon Family owned since 1974"
    assert candidates(text, catalog) == ["W015", "W016"]
    assert year_tokens(text) == [1974]
    text = "2023 Geyserville bottled February 2025 www.ridgewine.com"
    assert candidates(text, catalog) == ["W007", "W008"]
    assert year_tokens(text) == [2023, 2025]
    assert candidates("2023 Cabernet Sauvignon", catalog) == []
    assert candidates("Unknown producer Unknown wine 2023", catalog) == []
    assert candidates("Ridge Vineyards Three Valleys", catalog) == ["W013", "W014"]


def test_ocr_filters_low_confidence_words_and_rejects_malformed_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from label_matching import read_words

    assert read_words(b"level\tconf\ttext\n5\t90\tRidge\n5\t20\t2025\n") == ("Ridge", 55.0)
    assert read_words(b"level\tconf\ttext\n") == ("", None)
    for bad in [b"bad", b"x" * 262145, b"level\tconf\ttext\n5\tnan\tRidge\n"]:
        with pytest.raises(ValueError):
            read_words(bad)


@pytest.mark.parametrize(
    "row", [b"5\t80", b"5\t80\tRidge\textra", b"5\t101\tRidge", b"5\t-1\tRidge"]
)
def test_malformed_ocr_rows_are_not_identity_evidence(
    monkeypatch: pytest.MonkeyPatch, row: bytes
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from label_matching import read_words

    with pytest.raises(ValueError):
        read_words(b"level\tconf\ttext\n" + row + b"\n")


def test_fixture_validation_rejects_hash_changes_and_outside_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from evaluate_label import checked_bytes

    sample = ROOT / "assets/evaluation/barcode/seven-oaks-label-front.jpg"
    assert (
        checked_bytes(sample, hashlib.sha256(sample.read_bytes()).hexdigest())
        == sample.read_bytes()
    )
    with pytest.raises(ValueError):
        checked_bytes(sample, "0" * 64)
    unrelated = tmp_path / "not-a-fixture.jpg"
    unrelated.write_bytes(b"not public fixture data")
    with pytest.raises(ValueError):
        checked_bytes(unrelated, hashlib.sha256(unrelated.read_bytes()).hexdigest())


@pytest.mark.parametrize(
    ("code", "status"),
    [
        (0, "READ"),
        (1, "REJECTED_IMAGE"),
        (124, "LIMIT_EXCEEDED"),
        (137, "LIMIT_EXCEEDED"),
        (125, "UNAVAILABLE"),
    ],
)
def test_container_outcomes_always_confirm_cleanup(
    monkeypatch: pytest.MonkeyPatch, code: int, status: str
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from evaluate_label import recognize

    with patch(
        "evaluate_label.subprocess.run",
        side_effect=[
            subprocess.CompletedProcess(
                [], code, b"level\tconf\ttext\n5\t90\tRidge\n", b"private diagnostic"
            ),
            subprocess.CompletedProcess([], 0, b"removed", b""),
        ],
    ) as run:
        result = recognize(b"public fixture", "sha256:fixture", 11)
    assert result["status"] == status
    assert "private diagnostic" not in str(result)
    command = run.call_args_list[0].args[0]
    assert command[command.index("--network") + 1] == "none"
    assert command[command.index("--pull") + 1] == "never"
    assert "--read-only" in command and "--memory" in command and "--cpus" in command
    assert "--mount" not in command and "--env" not in command
    assert run.call_args_list[1].args[0][-3:-1] == ["rm", "--force"]
    assert run.call_args_list[1].kwargs["check"] is True


def test_timeout_cleans_up_and_unconfirmed_cleanup_aborts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from evaluate_label import recognize

    with patch(
        "evaluate_label.subprocess.run",
        side_effect=[
            subprocess.TimeoutExpired("docker", 15),
            subprocess.CompletedProcess([], 0),
        ],
    ):
        assert recognize(b"fixture", "image", 11)["status"] == "TIMEOUT"
    with (
        patch(
            "evaluate_label.subprocess.run",
            side_effect=[
                subprocess.CompletedProcess([], 0, b"malformed output", b""),
                subprocess.CalledProcessError(1, "docker rm"),
            ],
        ),
        pytest.raises(subprocess.CalledProcessError),
    ):
        recognize(b"fixture", "image", 11)
