import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_forced_credential_file_is_rejected_but_examples_are_allowed(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    (tmp_path / ".env.example").write_text("# Safe example only\n", encoding="utf-8")
    subprocess.run(["git", "add", "-f", ".env.example"], cwd=tmp_path, check=True)
    command = [sys.executable, str(ROOT / "scripts/check_secret_files.py")]
    assert subprocess.run(command, cwd=tmp_path, capture_output=True).returncode == 0
    (tmp_path / ".env.local").write_text(
        "# No actual credentials needed for this test\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "-f", ".env.local"], cwd=tmp_path, check=True)
    assert subprocess.run(command, cwd=tmp_path, capture_output=True).returncode == 1
