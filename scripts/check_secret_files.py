"""Reject tracked local credential files, including forced additions."""

import subprocess
import sys
from pathlib import PurePosixPath


def main() -> int:
    result = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True)
    allowed = {".env.example", ".env.migrations.example"}
    forbidden: list[str] = []
    for raw in result.stdout.decode().split("\0"):
        if not raw:
            continue
        path = PurePosixPath(raw.lower())
        if (
            (path.name.startswith(".env") and path.name not in allowed)
            or path.name == "signing_keys.json"
            or path.suffix in {".pem", ".key", ".p12", ".pfx", ".keystore"}
            or any(
                part in {".secrets", "secrets", ".tools", "uploads", "backups"}
                for part in path.parts
            )
        ):
            forbidden.append(raw)
    if forbidden:
        print("Refusing tracked credential/private-data paths:")
        for name in forbidden:
            print(repr(name))
        return 1
    print("Tracked file boundaries passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
