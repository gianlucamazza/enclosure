"""One live DeepSeek call with tools. Prints status, never the key."""

from __future__ import annotations

import asyncio
import os
import sys

from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.tool import tool


@tool
def echo():
    async def execute(text: str) -> str:
        """Return the text unchanged.

        Args:
            text: Text to return.
        """
        return text

    return execute


async def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is unset")
        return 1
    model = get_model(
        "deepseek/deepseek-flash",
        base_url="https://api.deepseek.com",
        config=GenerateConfig(
            temperature=0,
            reasoning_effort="none",
            max_tokens=64,
        ),
    )
    output = await model.generate(
        "Call the echo tool with text pong. Do not answer in prose.",
        tools=[echo()],
    )
    calls = []
    if output.choices:
        calls = list(output.choices[0].message.tool_calls or [])
    names = [call.function for call in calls]
    print(f"model={model}")
    print(f"stop={output.stop_reason}")
    print(f"tools={names or 'none'}")
    ok = "echo" in names
    print("tool_call_ok" if ok else "tool_call_missing")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
