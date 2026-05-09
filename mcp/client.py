from __future__ import annotations

from .registry import get_tool


class MCPToolClient:
    """Minimal local tool client; reserved for future MCP protocol integration."""

    def call(self, name: str, **kwargs: object) -> object:
        return get_tool(name)(**kwargs)
