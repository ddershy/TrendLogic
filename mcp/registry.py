from __future__ import annotations

from collections.abc import Callable

ToolCallable = Callable[..., object]
TOOL_REGISTRY: dict[str, ToolCallable] = {}


def register_tool(name: str, tool: ToolCallable) -> None:
    TOOL_REGISTRY[name] = tool


def get_tool(name: str) -> ToolCallable:
    if name not in TOOL_REGISTRY:
        raise KeyError(f"Tool is not registered: {name}")
    return TOOL_REGISTRY[name]
