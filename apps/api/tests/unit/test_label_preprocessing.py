import io
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[4]


def png(size: tuple[int, int], color: str = "white") -> bytes:
    output = io.BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("comment", "source-only metadata")
    Image.new("RGB", size, color).save(output, format="PNG", pnginfo=metadata)
    return output.getvalue()


def test_fixed_recipe_is_bounded_deterministic_and_drops_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from label_preprocessing import prepare

    source = png((500, 1500))
    output, details = prepare(source)
    assert prepare(source) == (output, details)
    assert details["crop_box"] == [25, 720, 475, 1230]
    assert details["inverted"] is False
    with Image.open(io.BytesIO(output)) as image:
        assert image.mode == "L"
        assert max(image.size) <= 1824
        assert image.width * image.height <= 4_000_000
        assert image.getpixel((0, 0)) == 255
        assert "comment" not in image.info
    assert b"source-only metadata" not in output


def test_flat_dark_label_keeps_full_image_and_inverts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from label_preprocessing import prepare

    output, details = prepare(png((400, 450), "black"))
    assert details["crop_box"] == [0, 0, 400, 450]
    assert details["inverted"] is True
    with Image.open(io.BytesIO(output)) as image:
        assert image.getpixel((100, 100)) == 255


@pytest.mark.parametrize(
    "content",
    [b"bad image", b"x" * (4 * 1024 * 1024 + 1), png((2001, 2000)), png((1, 2))],
    ids=["malformed", "byte-limit", "pixel-limit", "too-small"],
)
def test_preprocessing_rejects_malformed_or_oversized_images(
    monkeypatch: pytest.MonkeyPatch, content: bytes
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from label_preprocessing import prepare

    with pytest.raises(ValueError):
        prepare(content)


def test_exif_is_applied_before_crop_and_not_copied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from label_preprocessing import prepare

    source = io.BytesIO()
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = "source-only metadata"
    Image.new("RGB", (1500, 500), "white").save(source, format="JPEG", exif=exif)
    output, details = prepare(source.getvalue())
    assert details["crop_box"] == [25, 720, 475, 1230]
    with Image.open(io.BytesIO(output)) as image:
        assert not image.getexif()
    assert b"source-only metadata" not in output
