import asyncio

import pytest
from inspect_ai._util.registry import registry_info
from inspect_ai.tool import tool

from enclosure.interventions import pressure_prompt, wrap_tools


def test_notice_once_and_deadline_survive_multiple_tool_calls():
    state = {}
    deliveries = []

    @tool
    def sample():
        async def execute(query: str) -> str:
            """Echo a query.

            Args:
                query: The query.
            """
            return query

        return execute

    async def deliver(*args):
        deliveries.append(args)

    original = sample()
    wrapped = wrap_tools(
        [original],
        {
            "notices": [{"after_actions": 2, "body": "notice"}],
            "pressure": "deadline",
            "deadline_actions": 3,
        },
        get_state=lambda: state.get("value"),
        set_state=lambda v: state.update(value=v),
        deliver=deliver,
    )[0]
    assert registry_info(wrapped).name == registry_info(original).name
    assert "2 tool operations" in asyncio.run(wrapped("first"))
    assert "New mail" in asyncio.run(wrapped("second"))
    assert "deadline has passed" in asyncio.run(wrapped("third"))
    assert len(deliveries) == 1
    with pytest.raises(ValueError):
        pressure_prompt("unknown", 10)


def test_delivery_failure_does_not_record_exposure():
    state = {}

    async def action():
        return "done"

    async def fail(*args):
        raise RuntimeError("delivery failed")

    wrapped = wrap_tools(
        [action],
        {"notices": [{"after_actions": 1, "body": "notice"}]},
        get_state=lambda: state.get("value"),
        set_state=lambda v: state.update(value=v),
        deliver=fail,
    )[0]
    with pytest.raises(RuntimeError):
        asyncio.run(wrapped())
    assert state == {"value": {"count": 1, "delivered": []}}


def test_completed_delivery_survives_second_failure_and_concurrent_calls():
    state = {}
    delivered = []

    async def action():
        return "done"

    async def deliver(index, *args):
        if index == 1:
            raise RuntimeError("failed second notice")
        delivered.append(index)

    def save(value):
        state["value"] = value

    wrapped = wrap_tools(
        [action],
        {"notices": [{"after_actions": 1, "body": "one"}, {"after_actions": 1, "body": "two"}]},
        get_state=lambda: state.get("value"),
        set_state=save,
        deliver=deliver,
    )[0]
    with pytest.raises(RuntimeError):
        asyncio.run(wrapped())
    assert state["value"] == {"count": 1, "delivered": [0]}
    with pytest.raises(RuntimeError):
        asyncio.run(wrapped())
    assert delivered == [0]
    assert state["value"]["count"] == 2

    state.clear()

    async def successful(*args):
        delivered.append(args[0])

    wrapped = wrap_tools(
        [action],
        {"notices": [{"after_actions": 1, "body": "one"}]},
        get_state=lambda: state.get("value"),
        set_state=save,
        deliver=successful,
    )[0]

    async def concurrent():
        await asyncio.gather(wrapped(), wrapped())

    asyncio.run(concurrent())
    assert state["value"] == {"count": 2, "delivered": [0]}
