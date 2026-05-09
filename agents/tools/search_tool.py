from __future__ import annotations


def search_tool(query: str) -> list[dict]:
    return [{"title": query, "summary": "外部搜索工具尚未接入，当前返回占位结果。"}]
