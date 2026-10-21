import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("binding", ["127.0.0.1", "0.0.0.0", "inspect-failure", "fresh-key"])
def test_startup_verifies_bindings_and_stops_on_any_probe_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    binding: str,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import start_local

    (tmp_path / "supabase").mkdir()
    if binding != "fresh-key":
        (tmp_path / "supabase/signing_keys.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(start_local, "ROOT", tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _: "npx")
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        body: object
        if "signing-key" in command:
            assert Path(str(kwargs["cwd"])) != tmp_path
            assert not (Path(str(kwargs["cwd"])) / "supabase/config.toml").exists()
            body = {"kty": "EC", "kid": "synthetic-key"}
        elif command[:3] == ["docker", "network", "inspect"]:
            body = [{"Options": {"com.docker.network.bridge.host_binding_ipv4": "127.0.0.1"}}]
        elif command[:2] == ["docker", "inspect"]:
            if binding == "inspect-failure":
                raise subprocess.CalledProcessError(1, command)
            host = "127.0.0.1" if binding == "fresh-key" else binding
            body = {"5432/tcp": [{"HostIp": host, "HostPort": "54322"}]}
        else:
            body = {}
        return subprocess.CompletedProcess(command, 0, json.dumps(body), "")

    monkeypatch.setattr(subprocess, "run", run)
    if binding in {"127.0.0.1", "fresh-key"}:
        start_local.main()
        assert not any(command[-1] == "stop" for command in calls)
        if binding == "fresh-key":
            keys = json.loads((tmp_path / "supabase/signing_keys.json").read_text())
            assert keys == [{"kty": "EC", "kid": "synthetic-key"}]
    else:
        with pytest.raises((RuntimeError, subprocess.CalledProcessError)):
            start_local.main()
        assert calls[-1][-1] == "stop"
