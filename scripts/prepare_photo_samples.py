"""Fetch only checksum-pinned public fixtures and generate synthetic photo boundary cases."""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

import pillow_heif
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def orientation_chart(path: Path, orientation: int, *, heif: bool = False) -> None:
    image = Image.new("RGB", (120, 80))
    draw = ImageDraw.Draw(image)
    for box, color in [
        ((0, 0, 59, 39), "red"),
        ((60, 0, 119, 39), "lime"),
        ((0, 40, 59, 79), "blue"),
        ((60, 40, 119, 79), "yellow"),
    ]:
        draw.rectangle(box, fill=color)
    exif = Image.Exif()
    exif[274] = orientation
    exif[34853] = {1: "N", 2: (1.0, 2.0, 3.0), 3: "E", 4: (4.0, 5.0, 6.0)}
    exif[270] = "SYNTHETIC_PRIVATE_METADATA"
    image.save(
        path,
        format="HEIF" if heif else "JPEG",
        quality=95,
        exif=exif.tobytes(),
        xmp=b'<x:xmpmeta xmlns:x="adobe:ns:meta/">SYNTHETIC_PRIVATE_METADATA</x:xmpmeta>',
    )


def generate(directory: Path) -> None:
    pillow_heif.register_heif_opener()
    for orientation in range(1, 9):
        orientation_chart(directory / f"orientation-{orientation}.jpg", orientation)
    orientation_chart(directory / "orientation-6.heic", 6, heif=True)
    # Full-size decode budget, not a claim about current iPhone camera/color fidelity.
    Image.new("RGB", (8064, 6048), "#73503e").save(directory / "48mp.jpg", quality=90)
    Image.new("L", (10001, 1)).save(directory / "excessive-edge.png")
    (directory / "svg-disguised.jpg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    original = (directory / "heif_other-arrow.heic").read_bytes()
    (directory / "truncated-primary.heic").write_bytes(original[: len(original) // 2])
    with (directory / "excessive-bytes.jpg").open("wb") as stream:
        stream.write((directory / "orientation-1.jpg").read_bytes())
        stream.truncate(20 * 1024 * 1024 + 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".tools/photo-evaluation/inputs")
    args = parser.parse_args()
    # A fresh directory avoids overwriting existing/private photos.
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((ROOT / "assets/evaluation/photo-manifest.json").read_text())
    for fixture in manifest["fixtures"]:
        if "url" not in fixture:
            continue
        url = fixture["url"]
        if (
            not url.startswith(
                "https://raw.githubusercontent.com/bigcat88/pillow_heif/"
                + manifest["revision"]
                + "/"
            )
            or Path(fixture["file"]).name != fixture["file"]
        ):
            raise ValueError("Unexpected fixture source or filename")
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read(20 * 1024 * 1024 + 1)
        if hashlib.sha256(data).hexdigest() != fixture["sha256"]:
            raise ValueError("Fixture checksum mismatch")
        (args.output / fixture["file"]).write_bytes(data)
    generate(args.output)
    print("Prepared pinned public fixtures and synthetic cases; no personal files were read.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
