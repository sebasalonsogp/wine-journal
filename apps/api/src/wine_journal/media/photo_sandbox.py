"""Host-worker adapter for one credential-free, bounded Linux container per photo."""

import json
import os
import re
import subprocess
import time
from threading import Thread
from uuid import uuid4

from wine_journal.media.photo_protocol import (
    MAX_INPUT_BYTES,
    MAX_RESPONSE_BYTES,
    PhotoRejected,
    PhotoResult,
    parse_result,
)

IMAGE = "wine-journal-photo:v1"
DOCKER_ENDPOINT = (
    "npipe:////./pipe/docker_engine" if os.name == "nt" else "unix:///var/run/docker.sock"
)
MEMORY_BYTES = 768 * 1024 * 1024
TIMEOUT_SECONDS = 20


def docker(*arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["docker", "--host", DOCKER_ENDPOINT, *arguments],
            capture_output=True,
            timeout=10,
            check=True,
        )
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        raise PhotoRejected("DECODER_UNAVAILABLE") from None


class PhotoSandbox:
    def __init__(self) -> None:
        try:
            info = json.loads(docker("info", "--format", "{{json .}}"))
            if info["OSType"] != "linux" or not all(
                info.get(name) is True
                for name in ("MemoryLimit", "SwapLimit", "PidsLimit", "CpuCfsPeriod", "CpuCfsQuota")
            ):
                raise ValueError()
            identifier = docker("image", "inspect", IMAGE, "--format", "{{.Id}}").decode().strip()
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", identifier):
                raise ValueError()
            self.image = identifier  # Resolve the trusted local build once; never pull per upload.
        except (ValueError, KeyError, TypeError):
            raise PhotoRejected("DECODER_UNAVAILABLE") from None

    def convert(self, contents: bytes) -> PhotoResult:
        if not 0 < len(contents) <= MAX_INPUT_BYTES:
            raise PhotoRejected("INPUT_BYTES")
        output, code = self._execute(contents)
        if code == 137:
            raise PhotoRejected("RESOURCE_LIMIT")
        if code == 2:
            raise PhotoRejected(output.decode("ascii", errors="replace"))
        if code != 0:
            raise PhotoRejected("DECODER_UNAVAILABLE")
        return parse_result(output)

    def _execute(self, contents: bytes) -> tuple[bytes, int]:
        name = "wine-photo-" + uuid4().hex
        child: subprocess.Popen[bytes] | None = None
        reader: Thread | None = None
        writer: Thread | None = None
        output: list[bytes] = []
        try:
            docker(
                "create",
                "--name",
                name,
                "--interactive",
                "--pull=never",
                "--network=none",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--user=65532:65532",
                "--memory",
                str(MEMORY_BYTES),
                "--memory-swap",
                str(MEMORY_BYTES),
                "--cpus=1",
                "--pids-limit=32",
                "--ulimit=core=0",
                "--ipc=none",
                "--log-driver=none",
                "--label=wine-journal.photo-decoder=true",
                self.image,
            )
            started = time.monotonic()
            child = subprocess.Popen(
                ["docker", "--host", DOCKER_ENDPOINT, "start", "--attach", "--interactive", name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            assert child.stdin is not None and child.stdout is not None
            input_pipe, output_pipe = child.stdin, child.stdout

            def send() -> None:
                try:
                    input_pipe.write(contents)
                    input_pipe.close()
                except OSError:
                    pass

            def receive() -> None:
                try:
                    output.append(output_pipe.read(MAX_RESPONSE_BYTES + 1))
                except OSError:
                    pass

            writer, reader = Thread(target=send, daemon=True), Thread(target=receive, daemon=True)
            writer.start()
            reader.start()
            reader.join(TIMEOUT_SECONDS)
            if reader.is_alive() or (output and len(output[0]) > MAX_RESPONSE_BYTES):
                raise PhotoRejected("RESOURCE_LIMIT")
            remaining = TIMEOUT_SECONDS - (time.monotonic() - started)
            try:
                code = child.wait(timeout=max(0, remaining))
            except subprocess.TimeoutExpired:
                raise PhotoRejected("RESOURCE_LIMIT") from None
            return (output[0] if output else b""), code
        except OSError:
            raise PhotoRejected("DECODER_UNAVAILABLE") from None
        finally:
            # Stop the attachment first: a hostile stdout flood can backpressure Docker's
            # streaming connection and otherwise delay container removal. Always remove
            # the actual container too, including after a CLI/pipe cleanup failure.
            try:
                if child is not None:
                    if child.poll() is None:
                        child.kill()
                    child.wait(timeout=5)
                    for thread in (reader, writer):
                        if thread is not None:
                            thread.join(timeout=2)
                    if child.stdout is not None:
                        child.stdout.close()
                    if child.stdin is not None and not child.stdin.closed:
                        child.stdin.close()
            finally:
                docker("rm", "--force", name)
