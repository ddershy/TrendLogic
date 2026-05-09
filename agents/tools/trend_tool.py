from __future__ import annotations


def summarize_trends(items: list[dict]) -> list[str]:
    return [str(item.get("title", "")) for item in items if item.get("title")]
