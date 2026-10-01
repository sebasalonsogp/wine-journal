"""R04 experiment, not an upload handler. Run from repo with the API dev environment."""

import argparse
import hashlib
import io
import json
import subprocess
import sys
import time
import warnings
from pathlib import Path

import pillow_heif
import psutil
from PIL import Image, ImageCms, ImageFile, ImageOps, UnidentifiedImageError
from PIL import __version__ as pillow_version

MAX_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 50_000_000
MAX_EDGE = 10_000
TIMEOUT_SECONDS = 20
RSS_LIMIT = 768 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]


class Rejected(ValueError):
    """Fixed reason code, safe to include in an evaluation report."""


def check_heif_boxes(source: Path) -> None:
    """Reject truncated top-level ISO BMFF boxes before libheif can conceal missing tiles."""
    length = source.stat().st_size
    with source.open("rb") as stream:
        while stream.tell() < length:
            start = stream.tell()
            header = stream.read(8)
            if len(header) != 8:
                raise Rejected("INVALID_IMAGE")
            size = int.from_bytes(header[:4], "big")
            minimum = 8
            if size == 1:
                extended = stream.read(8)
                if len(extended) != 8:
                    raise Rejected("INVALID_IMAGE")
                size, minimum = int.from_bytes(extended, "big"), 16
            elif size == 0:
                size = length - start
            if size < minimum or start + size > length:
                raise Rejected("INVALID_IMAGE")
            stream.seek(start + size)


def convert(source: Path, destination: Path) -> dict[str, object]:
    """Candidate decode path; caller must isolate it in a bounded subprocess."""
    if not 0 < source.stat().st_size <= MAX_BYTES:
        raise Rejected("INPUT_BYTES")
    pillow_heif.register_heif_opener(
        thumbnails=False, depth_images=False, aux_images=False, decode_threads=1
    )
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            with Image.open(source, formats=["JPEG", "PNG", "WEBP", "HEIF"]) as opened:
                width, height = opened.size
                if width * height > MAX_PIXELS or max(width, height) > MAX_EDGE:
                    raise Rejected("PIXEL_LIMIT")
                detected = opened.format
                if detected == "HEIF":
                    check_heif_boxes(source)
                # HEIF's plugin selects the primary frame and applies container transforms.
                frames = getattr(opened, "n_frames", 1)
                opened.load()  # verify() alone does not decode HEIF pixels.
                ImageOps.exif_transpose(opened, in_place=True)
                oriented = opened
                oriented_size = list(oriented.size)
                profile = opened.info.get("icc_profile")
                image = oriented if oriented.mode == "RGB" else oriented.convert("RGB")
                if profile:
                    try:
                        normalized = ImageCms.profileToProfile(
                            image,
                            ImageCms.ImageCmsProfile(io.BytesIO(profile)),
                            ImageCms.createProfile("sRGB"),
                            outputMode="RGB",
                        )
                        assert normalized is not None
                        image = normalized
                    except (ImageCms.PyCMSError, OSError, ValueError):
                        raise Rejected("COLOR_PROFILE") from None
                if "A" in oriented.getbands():
                    background = Image.new("RGB", image.size, "white")
                    background.paste(image, mask=oriented.getchannel("A"))
                    image = background
                image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                # A new pixel-only image prevents implicit EXIF/XMP/ICC/comment propagation.
                clean = Image.new("RGB", image.size)
                clean.paste(image)
                destination.mkdir(parents=True, exist_ok=False)
                clean.save(destination / "display.jpg", quality=85)
                clean.thumbnail((480, 480), Image.Resampling.LANCZOS)
                clean.save(destination / "thumbnail.webp", quality=80)
                outputs = {}
                for filename in ("display.jpg", "thumbnail.webp"):
                    path = destination / filename
                    with Image.open(path) as derivative:
                        derivative.load()
                        if derivative.getexif() or any(
                            key in derivative.info
                            for key in ("exif", "xmp", "comment", "icc_profile")
                        ):
                            raise Rejected("METADATA_RETAINED")
                        outputs[filename] = {
                            "size": list(derivative.size),
                            "bytes": path.stat().st_size,
                            "metadata_removed": True,
                        }
                return {
                    "status": "READY",
                    "format": detected,
                    "input_size": [width, height],
                    "oriented_size": oriented_size,
                    "frames": frames,
                    "outputs": outputs,
                }
        except (Image.DecompressionBombWarning, Image.DecompressionBombError):
            raise Rejected("PIXEL_LIMIT") from None
        except (UnidentifiedImageError, OSError, EOFError, SyntaxError, RuntimeError):
            raise Rejected("INVALID_IMAGE") from None
        except ValueError as error:
            if isinstance(error, Rejected):
                raise
            raise Rejected("INVALID_IMAGE") from None


def measure(source: Path, destination: Path) -> dict[str, object]:
    """Time limit + sampled RSS include native allocations, unlike tracemalloc."""
    started = time.monotonic()
    peak = 0
    with subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--one", str(source), str(destination)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    ) as child:
        process = psutil.Process(child.pid)
        reason = None
        while child.poll() is None:
            try:
                # Windows venv python.exe can launch another Python process.
                resident = 0
                for member in [process, *process.children(recursive=True)]:
                    try:
                        memory = member.memory_info()
                        resident += max(memory.rss, int(getattr(memory, "peak_wset", 0)))
                    except psutil.NoSuchProcess:
                        pass
                peak = max(peak, resident)
            except psutil.NoSuchProcess:
                break
            if peak > RSS_LIMIT or time.monotonic() - started > TIMEOUT_SECONDS:
                reason = "RESOURCE_LIMIT"
                for descendant in process.children(recursive=True):
                    try:
                        descendant.kill()
                    except psutil.NoSuchProcess:
                        pass
                child.kill()
                break
            time.sleep(0.02)
        output, _ = child.communicate(timeout=5)
        if reason:
            result: dict[str, object] = {"status": reason}
        elif child.returncode != 0:
            result = {"status": "DECODER_EXIT"}
        else:
            result = json.loads(output)
    result.update(
        elapsed_ms=round((time.monotonic() - started) * 1000), peak_rss_mib=round(peak / 2**20, 1)
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--one", nargs=2, metavar=("INPUT", "NEW_OUTPUT_DIR"))
    parser.add_argument("--samples", type=Path, default=ROOT / ".tools/photo-evaluation/inputs")
    parser.add_argument("--output", type=Path, default=ROOT / ".tools/photo-evaluation/results")
    args = parser.parse_args()
    if args.one:
        try:
            result = convert(Path(args.one[0]), Path(args.one[1]))
        except Rejected as error:
            result = {"status": str(error)}
        print(json.dumps(result))
        return 0
    manifest = json.loads((ROOT / "assets/evaluation/photo-manifest.json").read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    for fixture in manifest["fixtures"]:
        source = args.samples / fixture["file"]
        if (
            "sha256" in fixture
            and hashlib.sha256(source.read_bytes()).hexdigest() != fixture["sha256"]
        ):
            raise ValueError("Fixture checksum mismatch")
        result = measure(source, args.output / fixture["id"])
        result.update(id=fixture["id"], expected=fixture["expected"])
        results.append(result)
    report = {
        "pillow": pillow_version,
        "pillow_heif": pillow_heif.__version__,
        "libheif": pillow_heif.libheif_version(),
        "platform": sys.platform,
        "results": results,
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return int(any(item["status"] != item["expected"] for item in results))


if __name__ == "__main__":
    raise SystemExit(main())
