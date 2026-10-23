"""Fixed R03b recipe for reviewed fixture bytes only, not public uploads."""

import hashlib
import io

from PIL import Image, ImageOps, ImageStat, __version__


def prepare(content: bytes) -> tuple[bytes, dict[str, object]]:
    if not content or len(content) > 4 * 1024 * 1024:
        raise ValueError("Fixture byte limit exceeded")
    try:
        with Image.open(io.BytesIO(content)) as source:
            if (
                source.format not in {"JPEG", "PNG"}
                or not 32 <= min(source.size)
                or source.width * source.height > 4_000_000
            ):
                raise ValueError("Unsupported fixture or pixel limit exceeded")
            if getattr(source, "n_frames", 1) != 1:
                raise ValueError("Only single-frame fixtures are supported")
            rgba = ImageOps.exif_transpose(source).convert("RGBA")
            background = Image.new("RGBA", rgba.size, "white")
            background.alpha_composite(rgba)
            width, height = background.size
            box = (0, 0, width, height)
            if height >= 2 * width:
                # Geometric hypothesis for upright producer bottle renderings.
                # No per-file crop, expected identity or OCR output is consulted.
                box = (width * 5 // 100, height * 48 // 100, width * 95 // 100, height * 82 // 100)
            gray = ImageOps.grayscale(background.crop(box))
            inverted = ImageStat.Stat(gray).median[0] < 128
            if inverted:
                gray = ImageOps.invert(gray)
            gray = ImageOps.autocontrast(gray, cutoff=1)
            scale = min(2.0, 1800 / max(gray.size))
            gray = gray.resize(
                (max(1, round(gray.width * scale)), max(1, round(gray.height * scale))),
                Image.Resampling.LANCZOS,
            )
            gray = ImageOps.expand(gray, border=12, fill=255)
            gray.info.clear()
            output = io.BytesIO()
            gray.save(output, format="PNG")
            encoded = output.getvalue()
            if len(encoded) > 4 * 1024 * 1024:
                raise ValueError("Transformed fixture byte limit exceeded")
            return encoded, {
                "recipe": "portrait-crop-contrast-v1",
                "pillow": __version__,
                "crop_box": list(box),
                "inverted": inverted,
                "output_dimensions": list(gray.size),
                "sha256": hashlib.sha256(encoded).hexdigest(),
            }
    except (OSError, Image.DecompressionBombError) as error:
        raise ValueError("Invalid fixture image") from error
