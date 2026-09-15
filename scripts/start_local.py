"""Start local Supabase only when its development ports bind to loopback."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from configure_local import write_new

ROOT = Path(__file__).resolve().parents[1]
NETWORK = "wine-journal-local"


def main() -> None:
    npx = shutil.which("npx.cmd" if os.name == "nt" else "npx")
    if npx is None:
        raise RuntimeError("Node.js and npx are required.")
    cli = [npx, "--yes", "supabase@2.117.0"]
    key_path = ROOT / "supabase/signing_keys.json"
    if not key_path.exists():
        print("Generating a local signing key; key output is suppressed.", flush=True)
        # The CLI reads config before generating. Our config references this not-yet
        # existing key, so generate outside the project to avoid a bootstrap cycle.
        with tempfile.TemporaryDirectory(prefix="wine-journal-keygen-") as directory:
            key = subprocess.run(
                cli + ["gen", "signing-key", "--algorithm", "ES256"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True,
            )
        write_new(key_path, json.dumps([json.loads(key.stdout)]) + "\n")
    network = subprocess.run(
        ["docker", "network", "inspect", NETWORK], capture_output=True, text=True
    )
    if network.returncode != 0:
        subprocess.run(
            [
                "docker",
                "network",
                "create",
                "-o",
                "com.docker.network.bridge.host_binding_ipv4=127.0.0.1",
                NETWORK,
            ],
            capture_output=True,
            check=True,
        )
    else:
        options = json.loads(network.stdout)[0]["Options"]
        if options.get("com.docker.network.bridge.host_binding_ipv4") != "127.0.0.1":
            raise RuntimeError("Existing local network is not configured for loopback.")
    print(
        "Starting Supabase; first run may download images. Credential output is suppressed.",
        flush=True,
    )
    try:
        subprocess.run(
            cli + ["start", "--network-id", NETWORK], cwd=ROOT, capture_output=True, check=True
        )
        for service in ("db", "kong", "studio", "inbucket"):
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{json .NetworkSettings.Ports}}",
                    f"supabase_{service}_wine-journal",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            ports = json.loads(result.stdout)
            if any(
                item["HostIp"] not in {"127.0.0.1", "::1"}
                for bindings in ports.values()
                if bindings
                for item in bindings
            ):
                raise RuntimeError(
                    "Docker published development ports outside loopback. "
                    "See supabase/README.md before restarting."
                )
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/configure_local.py")], cwd=ROOT, check=True
        )
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT / "apps/api", check=True
        )
        print("Local Supabase is ready on loopback; application migration applied.")
    except Exception:
        stopped = subprocess.run(cli + ["stop"], cwd=ROOT, capture_output=True)
        if stopped.returncode != 0:
            raise RuntimeError(
                "Local setup failed and shutdown could not be confirmed. "
                "Stop the Wine Journal development stack manually."
            ) from None
        print("Local Supabase stopped; database volumes retained.", flush=True)
        raise


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        sys.exit(str(exc))  # Only the fixed, credential-free messages above.
    except Exception as exc:
        sys.exit(f"Local startup failed ({type(exc).__name__}); no credentials were displayed.")
