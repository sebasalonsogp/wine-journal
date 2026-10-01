import io
import json
import os
import shutil
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from wine_journal.media.photo_protocol import PhotoRejected
from wine_journal.media.photo_sandbox import (
    DOCKER_ENDPOINT,
    IMAGE,
    MEMORY_BYTES,
    PhotoSandbox,
    docker,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("WINE_JOURNAL_TEST_PHOTO_SANDBOX") != "1",
    reason="Build the local photo decoder and opt in to Docker sandbox tests.",
)


@pytest.fixture(scope="module")
def probe_image(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    directory = tmp_path_factory.mktemp("photo-probe")
    tag = "wine-photo-probe:" + uuid4().hex
    (directory / "Dockerfile").write_text(
        f"FROM {IMAGE}\nCOPY probe.py /probe.py\n"
        'ENTRYPOINT ["timeout", "--signal=KILL", "20s", "python", "/probe.py"]\n'
    )
    shutil.copyfile(
        Path(__file__).parents[1] / "fixtures/photo_sandbox_probe.py", directory / "probe.py"
    )
    built = subprocess.run(
        ["docker", "--host", DOCKER_ENDPOINT, "build", "-t", tag, str(directory)],
        capture_output=True,
        timeout=60,
    )
    assert built.returncode == 0, "Synthetic sandbox probe image could not build."
    try:
        yield docker("image", "inspect", tag, "--format", "{{.Id}}").decode().strip()
    finally:
        docker("image", "rm", tag)


@pytest.mark.parametrize("heif", [False, True])
def test_real_container_converts_and_strips_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    heif: bool,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[4] / "scripts"))
    import pillow_heif
    from prepare_photo_samples import orientation_chart

    pillow_heif.register_heif_opener()
    source = tmp_path / "source"
    orientation_chart(source, 6, heif=heif)
    sandbox = PhotoSandbox()
    first = sandbox.convert(source.read_bytes())
    assert first == sandbox.convert(source.read_bytes())
    assert (first.width, first.height) == (80, 120)
    for data in (first.display, first.thumbnail):
        assert b"SYNTHETIC_PRIVATE_METADATA" not in data
        with Image.open(io.BytesIO(data)) as output:
            output.load()
            assert not output.getexif()
            assert not {"exif", "xmp", "comment", "icc_profile"}.intersection(output.info)
    with pytest.raises(PhotoRejected, match="INVALID_IMAGE"):
        sandbox.convert(b"not a photo")


def test_container_restrictions_are_enforced(
    probe_image: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WINE_JOURNAL_TEST_SECRET", "synthetic-must-not-reach-decoder")
    sandbox = PhotoSandbox()
    sandbox.image = probe_image
    output, code = sandbox._execute(b"inspect")
    assert code == 0
    assert json.loads(output) == {
        "uid": 65532,
        "readonly": True,
        "network": ["lo"],
        "credentials_absent": True,
        "socket_absent": True,
        "no_new_privileges": True,
        "no_capabilities": True,
        "memory": str(MEMORY_BYTES),
        "swap": "0",
        "pids": "32",
        "cpu": "100000 100000",
    }


@pytest.mark.parametrize("mode", ["memory", "hang", "output", "internal-deadline"])
def test_real_resource_violations_terminate_and_remove_container(
    probe_image: str,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    sandbox = PhotoSandbox()
    sandbox.image = probe_image
    if mode == "memory":
        monkeypatch.setattr("wine_journal.media.photo_sandbox.MEMORY_BYTES", 64 * 1024 * 1024)
    elif mode == "hang":
        monkeypatch.setattr("wine_journal.media.photo_sandbox.TIMEOUT_SECONDS", 1)
    elif mode == "internal-deadline":
        # The container's own timeout must end it, even if the host supervisor waits longer.
        monkeypatch.setattr("wine_journal.media.photo_sandbox.TIMEOUT_SECONDS", 30)
    started = time.monotonic()
    with pytest.raises(PhotoRejected, match="RESOURCE_LIMIT"):
        sandbox.convert(b"hang" if mode == "internal-deadline" else mode.encode())
    assert time.monotonic() - started < (26 if mode == "internal-deadline" else 10)
    assert not docker(
        "ps", "--all", "--filter", f"ancestor={probe_image}", "--format", "{{.ID}}"
    ).strip()
