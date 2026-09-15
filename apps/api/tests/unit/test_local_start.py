import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("binding", ["127.0.0.1", "0.0.0.0", "inspect-failure"])
def test_startup_verifies_bindings_and_stops_on_any_probe_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    binding: str,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import start_local

    (tmp_path / "supabase").mkdir()
    (tmp_path / "supabase/signing_keys.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(start_local, "ROOT", tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _: "npx")
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        body: object
        if command[:3] == ["docker", "network", "inspect"]:
            body = [{"Options": {"com.docker.network.bridge.host_binding_ipv4": "127.0.0.1"}}]
        elif command[:2] == ["docker", "inspect"]:
            if binding == "inspect-failure":
                raise subprocess.CalledProcessError(1, command)
            body = {"5432/tcp": [{"HostIp": binding, "HostPort": "54322"}]}
        else:
            body = {}
        return subprocess.CompletedProcess(command, 0, json.dumps(body), "")

    monkeypatch.setattr(subprocess, "run", run)
    if binding == "127.0.0.1":
        start_local.main()
        assert not any(command[-1] == "stop" for command in calls)
    else:
        with pytest.raises((RuntimeError, subprocess.CalledProcessError)):
            start_local.main()
        assert calls[-1][-1] == "stop"
