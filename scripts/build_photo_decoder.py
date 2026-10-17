"""Build a pinned decoder from an allowlisted, credential-free temporary build context."""

import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

from wine_journal.media.photo_sandbox import DOCKER_ENDPOINT

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "wine-journal-photo:v1"


def requirements() -> str:
    lock = tomllib.loads((ROOT / "apps/api/uv.lock").read_text(encoding="utf-8"))
    project = next(package for package in lock["package"] if package["name"] == "wine-journal-api")
    names = {item["name"] for item in project["optional-dependencies"]["photo-decoder"]}
    if names != {"pillow", "pillow-heif"}:
        raise ValueError("Review the decoder dependency allowlist before building.")
    lines = []
    for package in lock["package"]:
        if package["name"] in names:
            if any(item["name"] not in names for item in package.get("dependencies", [])):
                raise ValueError("Unexpected decoder dependency.")
            hashes = " ".join("--hash=" + wheel["hash"] for wheel in package["wheels"])
            lines.append(f"{package['name']}=={package['version']} {hashes}")
    if len(lines) != 2:
        raise ValueError("Decoder lock entries missing.")
    return "\n".join(lines) + "\n"


def main() -> None:
    # Never send the repository root (including ignored .env files) to the Docker daemon.
    with tempfile.TemporaryDirectory(prefix="wine-photo-build-") as directory:
        context = Path(directory)
        (context / "requirements.txt").write_text(requirements(), encoding="utf-8")
        shutil.copyfile(ROOT / "apps/api/photo-decoder.Dockerfile", context / "Dockerfile")
        for name in ("photos.py", "photo_protocol.py"):
            shutil.copyfile(ROOT / "apps/api/src/wine_journal/media" / name, context / name)
        subprocess.run(
            ["docker", "--host", DOCKER_ENDPOINT, "build", "--tag", IMAGE, str(context)], check=True
        )
    print("Photo decoder built from locked wheels and allowlisted source files.")


if __name__ == "__main__":
    main()
