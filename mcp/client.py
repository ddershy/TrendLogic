from __future__ import annotations

from .bootstrap import register_builtin_tools
from .registry import get_tool, list_openai_tools


class MCPToolClient:
    """Minimal local tool client; reserved for future MCP protocol integration."""

    def __init__(self) -> None:
        register_builtin_tools()

    def call(self, name: str, **kwargs: object) -> object:
        return get_tool(name)(**kwargs)

    def openai_tools(self, names: list[str] | None = None) -> list[dict]:
        return list_openai_tools(names)
