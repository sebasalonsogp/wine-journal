import json
from unittest.mock import Mock

import pytest

from wine_journal.media.photo_protocol import MAX_INPUT_BYTES, PhotoRejected
from wine_journal.media.photo_sandbox import PhotoSandbox


@pytest.mark.parametrize(
    "missing", ["MemoryLimit", "SwapLimit", "PidsLimit", "OSType", "CpuCfsPeriod", "CpuCfsQuota"]
)
def test_missing_container_limits_fail_closed(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    info: dict[str, object] = {
        "MemoryLimit": True,
        "SwapLimit": True,
        "PidsLimit": True,
        "OSType": "linux",
        "CpuCfsPeriod": True,
        "CpuCfsQuota": True,
    }
    info[missing] = False
    command = Mock(return_value=json.dumps(info).encode())
    monkeypatch.setattr("wine_journal.media.photo_sandbox.docker", command)
    with pytest.raises(PhotoRejected, match="DECODER_UNAVAILABLE"):
        PhotoSandbox()
    assert command.call_count == 1


def test_invalid_input_never_starts_a_decoder(monkeypatch: pytest.MonkeyPatch) -> None:
    command = Mock(
        side_effect=[
            json.dumps(
                {
                    "MemoryLimit": True,
                    "SwapLimit": True,
                    "PidsLimit": True,
                    "OSType": "linux",
                    "CpuCfsPeriod": True,
                    "CpuCfsQuota": True,
                }
            ).encode(),
            b"sha256:" + b"a" * 64,
        ]
    )
    monkeypatch.setattr("wine_journal.media.photo_sandbox.docker", command)
    sandbox = PhotoSandbox()
    for data in (b"", b"x" * (MAX_INPUT_BYTES + 1)):
        with pytest.raises(PhotoRejected, match="INPUT_BYTES"):
            sandbox.convert(data)
    assert command.call_count == 2
