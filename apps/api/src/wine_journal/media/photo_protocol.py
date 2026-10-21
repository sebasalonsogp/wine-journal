"""Bounded data exchanged with the credential-free decoder; no native image imports."""

import base64
import binascii
import json
from dataclasses import dataclass, field

MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_DISPLAY_BYTES = 5 * 1024 * 1024
MAX_THUMBNAIL_BYTES = 512 * 1024
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
REASONS = frozenset(
    {
        "INPUT_BYTES",
        "PIXEL_LIMIT",
        "INVALID_IMAGE",
        "COLOR_PROFILE",
        "OUTPUT_BYTES",
        "RESOURCE_LIMIT",
        "DECODER_UNAVAILABLE",
        "DECODER_PROTOCOL",
    }
)


class PhotoRejected(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason if reason in REASONS else "DECODER_PROTOCOL"
        super().__init__(self.reason)


@dataclass(frozen=True)
class PhotoResult:
    width: int
    height: int
    thumbnail_width: int
    thumbnail_height: int
    source_format: str
    display: bytes = field(repr=False)
    thumbnail: bytes = field(repr=False)

    def encode(self) -> bytes:
        return json.dumps(
            {
                "width": self.width,
                "height": self.height,
                "thumbnailWidth": self.thumbnail_width,
                "thumbnailHeight": self.thumbnail_height,
                "sourceFormat": self.source_format,
                "display": base64.b64encode(self.display).decode("ascii"),
                "thumbnail": base64.b64encode(self.thumbnail).decode("ascii"),
            },
            separators=(",", ":"),
        ).encode("ascii")


def parse_result(data: bytes) -> PhotoResult:
    if len(data) > MAX_RESPONSE_BYTES:
        raise PhotoRejected("DECODER_PROTOCOL")
    try:
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError()
        for name, limit in (
            ("width", 2048),
            ("height", 2048),
            ("thumbnailWidth", 480),
            ("thumbnailHeight", 480),
        ):
            if type(value[name]) is not int or not 0 < value[name] <= limit:
                raise ValueError()
        if value["sourceFormat"] not in {"JPEG", "PNG", "WEBP", "HEIF"}:
            raise ValueError()
        display = base64.b64decode(value["display"], validate=True)
        thumbnail = base64.b64decode(value["thumbnail"], validate=True)
        if (
            not 0 < len(display) <= MAX_DISPLAY_BYTES
            or not 0 < len(thumbnail) <= MAX_THUMBNAIL_BYTES
        ):
            raise ValueError()
        if (
            not display.startswith(b"\xff\xd8\xff")
            or thumbnail[:4] != b"RIFF"
            or thumbnail[8:12] != b"WEBP"
        ):
            raise ValueError()
        return PhotoResult(
            value["width"],
            value["height"],
            value["thumbnailWidth"],
            value["thumbnailHeight"],
            value["sourceFormat"],
            display,
            thumbnail,
        )
    except (ValueError, TypeError, KeyError, binascii.Error, RecursionError):
        raise PhotoRejected("DECODER_PROTOCOL") from None
