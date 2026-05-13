from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

ToolCallable = Callable[..., object]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    callable: ToolCallable

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


TOOL_REGISTRY: dict[str, ToolDefinition] = {}


def register_tool(
    name: str,
    tool: ToolCallable,
    *,
    description: str = "",
    parameters: dict[str, Any] | None = None,
) -> None:
    TOOL_REGISTRY[name] = ToolDefinition(
        name=name,
        description=description or tool.__doc__ or f"Tool: {name}",
        parameters=parameters or {"type": "object", "properties": {}, "additionalProperties": False},
        callable=tool,
    )


def get_tool(name: str) -> ToolCallable:
    return get_tool_definition(name).callable


def get_tool_definition(name: str) -> ToolDefinition:
    if name not in TOOL_REGISTRY:
        raise KeyError(f"Tool is not registered: {name}")
    return TOOL_REGISTRY[name]


def list_tool_definitions(names: list[str] | None = None) -> list[ToolDefinition]:
    if names is None:
        return list(TOOL_REGISTRY.values())
    return [get_tool_definition(name) for name in names if name in TOOL_REGISTRY]


def list_openai_tools(names: list[str] | None = None) -> list[dict[str, Any]]:
    return [tool.to_openai_tool() for tool in list_tool_definitions(names)]
