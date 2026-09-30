"""Synthetic sandbox abuse fixture. Never included in the production decoder image."""

import json
import os
import sys
import time
from pathlib import Path

mode = sys.stdin.buffer.read().decode("ascii")
if mode == "memory":
    allocations = []
    while True:
        allocations.append(bytearray(1024 * 1024))
elif mode == "hang":
    time.sleep(60)
elif mode == "output":
    while True:
        sys.stdout.buffer.write(b"x" * 65536)
        sys.stdout.buffer.flush()
else:
    try:
        Path("/app/should-not-write").write_text("test")
        readonly = False
    except OSError:
        readonly = True
    status = Path("/proc/self/status").read_text()
    uid = int(next(line for line in status.splitlines() if line.startswith("Uid:")).split()[1])
    print(
        json.dumps(
            {
                "uid": uid,
                "readonly": readonly,
                "network": sorted(path.name for path in Path("/sys/class/net").iterdir()),
                "credentials_absent": not any(
                    name.startswith("WINE_JOURNAL_") for name in os.environ
                ),
                "socket_absent": not Path("/var/run/docker.sock").exists(),
                "no_new_privileges": "NoNewPrivs:\t1" in status,
                "no_capabilities": "CapEff:\t0000000000000000" in status,
                "memory": Path("/sys/fs/cgroup/memory.max").read_text().strip(),
                "swap": Path("/sys/fs/cgroup/memory.swap.max").read_text().strip(),
                "pids": Path("/sys/fs/cgroup/pids.max").read_text().strip(),
                "cpu": Path("/sys/fs/cgroup/cpu.max").read_text().strip(),
            }
        )
    )
