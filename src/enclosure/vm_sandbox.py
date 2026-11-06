"""Inspect VM provider: Docker manages controllers, all subject operations enter QEMU."""

from __future__ import annotations

import base64
import json

from inspect_ai.util import SandboxEnvironment, sandboxenv
from inspect_ai.util._sandbox.docker.docker import (
    DockerSandboxEnvironment,
    resolve_config_environment,
)
from inspect_ai.util._sandbox.environment import SandboxUserUnsupportedError
from inspect_ai.util._subprocess import ExecResult


class GuestEnvironment(DockerSandboxEnvironment):
    """The Docker service is only a transport, never a fallback execution target."""

    def __init__(self, controller: DockerSandboxEnvironment):
        self.__dict__.update(controller.__dict__)
        self.controller = controller

    async def exec(
        self,
        cmd,
        input=None,
        cwd=None,
        env=None,
        user=None,
        timeout=None,
        timeout_retry=True,
        concurrency=True,
    ):
        if user not in (None, "agent", "1000"):
            raise SandboxUserUnsupportedError(
                "VM subject runs as agent without privilege escalation"
            )
        body = input.encode() if isinstance(input, str) else input or b""
        payload = {
            "cmd": cmd,
            "input": base64.b64encode(body).decode(),
            "cwd": cwd,
            "env": env,
            "timeout": timeout or 30,
        }
        result = await self.controller.exec(
            ["python3", "/opt/vm/control.py", "exec"],
            input=json.dumps(payload),
            timeout=(timeout or 30) + 20,
        )
        if not result.success:
            raise RuntimeError("VM controller failed: " + result.stderr)
        response = json.loads(result.stdout)
        if response.get("timeout"):
            raise TimeoutError("Guest command timed out")
        return ExecResult(
            success=response["returncode"] == 0,
            returncode=response["returncode"],
            stdout=base64.b64decode(response["stdout"]).decode(),
            stderr=base64.b64decode(response["stderr"]).decode(),
        )

    async def write_file(self, file, contents, *, user=None):
        body = contents.encode() if isinstance(contents, str) else contents
        result = await self.exec(
            [
                "python3",
                "-c",
                "import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(sys.stdin.buffer.read())",
                file,
            ],
            input=body,
            user=user,
        )
        if not result.success:
            raise PermissionError(result.stderr)

    async def read_file(self, file, text=True, *, user=None):
        result = await self.exec(
            [
                "python3",
                "-c",
                "import pathlib,sys,base64; p=pathlib.Path(sys.argv[1]); print(base64.b64encode(p.read_bytes()).decode())",
                file,
            ],
            user=user,
        )
        if not result.success:
            if "FileNotFoundError" in result.stderr:
                raise FileNotFoundError(file)
            raise PermissionError(result.stderr)
        body = base64.b64decode(result.stdout.strip())
        return body.decode() if text else body


@sandboxenv(name="enclosure_vm")
class VMSandboxEnvironment(DockerSandboxEnvironment):
    @classmethod
    async def task_init_environment(cls, config, metadata):
        resolved = resolve_config_environment(config, metadata)
        return resolved.env if resolved else {}

    @classmethod
    async def sample_init(cls, task_name, config, metadata) -> dict[str, SandboxEnvironment]:
        environments = await super().sample_init(task_name, config, metadata)
        environments["default"] = GuestEnvironment(
            environments["default"].as_type(DockerSandboxEnvironment)
        )
        return environments


def is_vm(environment) -> bool:
    """Inspect wraps providers in an event recorder; unwrap through its public API."""
    try:
        environment.as_type(GuestEnvironment)
        return True
    except (TypeError, AttributeError):
        return False
