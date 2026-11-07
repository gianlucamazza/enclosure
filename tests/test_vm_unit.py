"""VM transport boundaries must fail closed."""

import asyncio
from types import SimpleNamespace

import pytest
from inspect_ai.util._sandbox.environment import SandboxUserUnsupportedError

from enclosure.vm_sandbox import GuestEnvironment


def test_guest_rejects_root_before_transport():
    class Controller:
        async def exec(self, *args, **kwargs):
            pytest.fail("root request reached the controller")

    guest = GuestEnvironment(Controller())
    with pytest.raises(SandboxUserUnsupportedError):
        asyncio.run(guest.exec(["id"], user="root"))


def test_transport_failure_never_executes_on_controller():
    calls = []

    class Controller:
        async def exec(self, command, **kwargs):
            calls.append(command)
            return SimpleNamespace(success=False, stderr="guest disconnected")

    guest = GuestEnvironment(Controller())
    with pytest.raises(RuntimeError, match="VM controller failed"):
        asyncio.run(guest.exec(["touch", "/subject-file"]))
    assert calls == [["python3", "/opt/vm/control.py", "exec"]]
