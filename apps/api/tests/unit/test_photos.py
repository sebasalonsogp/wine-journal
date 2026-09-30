import io
import json

import pytest
from PIL import Image

from wine_journal.media.photo_protocol import PhotoRejected, parse_result
from wine_journal.media.photos import convert


@pytest.mark.parametrize("mode", ["RGBA", "P", "L"])
def test_transparency_is_flattened_and_results_are_deterministic(mode: str) -> None:
    image = Image.new(mode, (40, 20))
    source = io.BytesIO()
    if mode in {"P", "L"}:
        image.info["transparency"] = 0
    image.save(source, format="PNG")
    first, second = convert(source.getvalue()), convert(source.getvalue())
    assert first == second and parse_result(first.encode()) == first
    with Image.open(io.BytesIO(first.display)) as result:
        assert result.getpixel((10, 10)) == (255, 255, 255)
        assert result.size == (40, 20)


@pytest.mark.parametrize("budget", ["MAX_DISPLAY_BYTES", "MAX_THUMBNAIL_BYTES"])
def test_output_bytes_are_enforced(monkeypatch: pytest.MonkeyPatch, budget: str) -> None:
    monkeypatch.setattr("wine_journal.media.photos." + budget, 1)
    source = io.BytesIO()
    Image.new("RGB", (20, 20)).save(source, format="JPEG")
    with pytest.raises(PhotoRejected, match="OUTPUT_BYTES"):
        convert(source.getvalue())


@pytest.mark.parametrize(
    "case", ["boolean", "dimensions", "format", "base64", "magic", "nested", "oversized"]
)
def test_decoder_output_is_treated_as_untrusted(case: str) -> None:
    source = io.BytesIO()
    Image.new("RGB", (10, 10)).save(source, format="JPEG")
    payload = json.loads(convert(source.getvalue()).encode())
    changes: dict[str, dict[str, object]] = {
        "boolean": {"width": True},
        "dimensions": {"height": 2049},
        "format": {"sourceFormat": "SVG"},
        "base64": {"display": "!"},
        "magic": {"display": "cHJpdmF0ZQ=="},
        "nested": {"sourceFormat": {}},
    }
    data = (
        b"x" * (8 * 1024 * 1024 + 1)
        if case == "oversized"
        else json.dumps({**payload, **changes[case]}).encode()
    )
    with pytest.raises(PhotoRejected, match="DECODER_PROTOCOL"):
        parse_result(data)


def test_large_source_is_resized_without_changing_aspect_ratio() -> None:
    source = io.BytesIO()
    Image.new("RGB", (3000, 1500)).save(source, format="JPEG")
    result = convert(source.getvalue())
    assert (result.width, result.height) == (2048, 1024)
    assert (result.thumbnail_width, result.thumbnail_height) == (480, 240)
    assert "display=" not in repr(result) and "thumbnail=" not in repr(result)
