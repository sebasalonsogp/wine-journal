"""Native image conversion. Production callers must use photo_sandbox, never import this in API."""

import io
import sys
import warnings

import pillow_heif
from PIL import Image, ImageCms, ImageFile, ImageOps, UnidentifiedImageError

from wine_journal.media.photo_protocol import (
    MAX_DISPLAY_BYTES,
    MAX_INPUT_BYTES,
    MAX_THUMBNAIL_BYTES,
    PhotoRejected,
    PhotoResult,
)

MAX_PIXELS = 50_000_000
MAX_EDGE = 10_000


def check_heif_boxes(data: bytes) -> None:
    """libheif can conceal missing tiles: reject incomplete top-level BMFF boxes first."""
    start, length = 0, len(data)
    while start < length:
        if start + 8 > length:
            raise PhotoRejected("INVALID_IMAGE")
        size, minimum = int.from_bytes(data[start : start + 4], "big"), 8
        if size == 1:
            if start + 16 > length:
                raise PhotoRejected("INVALID_IMAGE")
            size, minimum = int.from_bytes(data[start + 8 : start + 16], "big"), 16
        elif size == 0:
            size = length - start
        if size < minimum or start + size > length:
            raise PhotoRejected("INVALID_IMAGE")
        start += size


def encoded(image: Image.Image, format: str, quality: int, limit: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=format, quality=quality)
    if buffer.tell() > limit:
        raise PhotoRejected("OUTPUT_BYTES")
    return buffer.getvalue()


def convert(data: bytes) -> PhotoResult:
    if not 0 < len(data) <= MAX_INPUT_BYTES:
        raise PhotoRejected("INPUT_BYTES")
    pillow_heif.register_heif_opener(
        thumbnails=False, depth_images=False, aux_images=False, decode_threads=1
    )
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            with Image.open(io.BytesIO(data), formats=["JPEG", "PNG", "WEBP", "HEIF"]) as opened:
                width, height = opened.size
                if width * height > MAX_PIXELS or max(width, height) > MAX_EDGE:
                    raise PhotoRejected("PIXEL_LIMIT")
                detected = opened.format
                assert detected is not None
                if detected == "HEIF":
                    check_heif_boxes(data)
                opened.load()
                ImageOps.exif_transpose(opened, in_place=True)
                profile = opened.info.get("icc_profile")
                # Preserve a CMYK/L source mode for its ICC transform. Converting to RGB
                # first would interpret those pixels using the wrong source profile.
                image = opened if opened.mode in {"RGB", "CMYK", "L"} else opened.convert("RGB")
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
                        raise PhotoRejected("COLOR_PROFILE") from None
                elif image.mode != "RGB":
                    image = image.convert("RGB")
                if "A" in opened.getbands() or "transparency" in opened.info:
                    alpha = opened.convert("RGBA").getchannel("A")
                    background = Image.new("RGB", image.size, "white")
                    background.paste(image, mask=alpha)
                    image = background
                image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                clean = Image.new("RGB", image.size)
                clean.paste(image)  # Pixel-only reconstruction strips all source metadata.
                width, height = clean.size
                display = encoded(clean, "JPEG", 85, MAX_DISPLAY_BYTES)
                clean.thumbnail((480, 480), Image.Resampling.LANCZOS)
                thumbnail = encoded(clean, "WEBP", 80, MAX_THUMBNAIL_BYTES)
                return PhotoResult(
                    width, height, clean.width, clean.height, detected, display, thumbnail
                )
        except (Image.DecompressionBombWarning, Image.DecompressionBombError):
            raise PhotoRejected("PIXEL_LIMIT") from None
        except (UnidentifiedImageError, OSError, EOFError, SyntaxError, RuntimeError):
            raise PhotoRejected("INVALID_IMAGE") from None
        except ValueError as error:
            if isinstance(error, PhotoRejected):
                raise
            raise PhotoRejected("INVALID_IMAGE") from None


def main() -> int:
    try:
        result = convert(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
    except PhotoRejected as error:
        sys.stdout.buffer.write(error.reason.encode("ascii"))
        return 2
    except MemoryError:
        sys.stdout.buffer.write(b"RESOURCE_LIMIT")
        return 2
    except Exception:
        # Native library errors may include source metadata; do not emit a traceback.
        sys.stdout.buffer.write(b"INVALID_IMAGE")
        return 2
    sys.stdout.buffer.write(result.encode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
