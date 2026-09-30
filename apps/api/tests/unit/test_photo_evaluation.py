from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("heif", [False, True])
@pytest.mark.parametrize(
    ("orientation", "corners"),
    [
        (1, "RGBY"),
        (2, "GRYB"),
        (3, "YBGR"),
        (4, "BYRG"),
        (5, "RBGY"),
        (6, "BRYG"),
        (7, "YGBR"),
        (8, "GYRB"),
    ],
)
def test_orientation_and_private_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    heif: bool,
    orientation: int,
    corners: str,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import pillow_heif
    from evaluate_photos import convert
    from prepare_photo_samples import orientation_chart

    pillow_heif.register_heif_opener()
    source = tmp_path / ("source.heic" if heif else "source.jpg")
    orientation_chart(source, orientation, heif=heif)
    with Image.open(source) as original:
        assert 34853 in original.getexif()  # GPS exists before conversion.
        assert "xmp" in original.info
    destination = tmp_path / "outputs"
    result = convert(source, destination)
    assert result["status"] == "READY"
    palette = {"R": (255, 0, 0), "G": (0, 255, 0), "B": (0, 0, 255), "Y": (255, 255, 0)}
    for name in ("display.jpg", "thumbnail.webp"):
        assert b"SYNTHETIC_PRIVATE_METADATA" not in (destination / name).read_bytes()
        with Image.open(destination / name) as image:
            assert image.size == ((120, 80) if orientation < 5 else (80, 120))
            assert not image.getexif()
            assert not {"exif", "xmp", "comment", "icc_profile"}.intersection(image.info)
            positions = [
                (10, 10),
                (image.width - 10, 10),
                (10, image.height - 10),
                (image.width - 10, image.height - 10),
            ]
            for position, color in zip(positions, corners, strict=True):
                pixel = image.getpixel(position)
                assert isinstance(pixel, tuple)
                assert all(abs(a - b) < 25 for a, b in zip(pixel, palette[color], strict=True))


@pytest.mark.parametrize(
    "case", ["empty", "svg", "bytes", "pixels", "truncated", "truncated-heif", "profile"]
)
def test_rejection_never_publishes_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from evaluate_photos import MAX_BYTES, Rejected, convert

    source = tmp_path / "input.jpg"
    expected = "INVALID_IMAGE"
    if case == "empty":
        source.touch()
        expected = "INPUT_BYTES"
    elif case == "svg":
        source.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    elif case == "bytes":
        with source.open("wb") as stream:
            stream.truncate(MAX_BYTES + 1)
        expected = "INPUT_BYTES"
    elif case == "pixels":
        Image.new("L", (10001, 1)).save(source, format="PNG")
        expected = "PIXEL_LIMIT"
    elif case == "truncated":
        Image.new("RGB", (100, 100)).save(source)
        source.write_bytes(source.read_bytes()[:100])
    elif case == "truncated-heif":
        import pillow_heif
        from prepare_photo_samples import orientation_chart

        pillow_heif.register_heif_opener()
        orientation_chart(source, 6, heif=True)
        source.write_bytes(source.read_bytes()[:-20])
    else:
        Image.new("RGB", (20, 20)).save(source, icc_profile=b"not-a-profile")
        expected = "COLOR_PROFILE"
    destination = tmp_path / "outputs"
    with pytest.raises(Rejected, match=f"^{expected}$"):
        convert(source, destination)
    assert not destination.exists()


@pytest.mark.parametrize("budget", ["RSS_LIMIT", "TIMEOUT_SECONDS"])
def test_evaluation_kills_decoder_when_budget_is_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, budget: str
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import evaluate_photos

    source = tmp_path / "input.jpg"
    Image.new("RGB", (40, 40)).save(source)
    monkeypatch.setattr(evaluate_photos, budget, 0)
    assert evaluate_photos.measure(source, tmp_path / "output")["status"] == "RESOURCE_LIMIT"
