from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import serpapi

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def search_tool(query: str, limit: int = 3, hl: str = "zh-cn", gl: str = "cn") -> list[dict[str, Any]]:
    """Search Google through SerpApi and return normalized organic results."""

    api_key = os.getenv("SERPAPI_API_KEY") or os.getenv("SERPAPI_KEY")
    if not api_key:
        return [
            {
                "title": query,
                "link": "",
                "summary": "SERPAPI_API_KEY 或 SERPAPI_KEY 未配置，无法执行外部搜索。",
                "source": "serpapi",
            }
        ]

    client = serpapi.Client(api_key=api_key)

    try:
        results = client.search(
            {
                "engine": "google",
                "q": query,
                "hl": hl,
                "gl": gl,
                "num": int(limit or 3),
            }
        )
    except Exception as exc:
        return [
            {
                "title": query,
                "link": "",
                "summary": f"SerpApi 搜索失败：{_redact_secret(str(exc))}",
                "source": "serpapi",
            }
        ]

    payload = _to_dict(results)
    if payload.get("error"):
        return [
            {
                "title": query,
                "link": "",
                "summary": f"SerpApi 返回错误：{payload.get('error')}",
                "source": "serpapi",
            }
        ]

    organic_results = _collect_results(payload)
    normalized = []

    for item in organic_results[: int(limit or 3)]:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "summary": item.get("snippet") or item.get("description") or item.get("snippet_highlighted_words") or "",
                "source": "serpapi",
                "position": item.get("position"),
            }
        )

    return normalized


def _to_dict(results: Any) -> dict[str, Any]:
    if isinstance(results, dict):
        return results
    if hasattr(results, "as_dict"):
        value = results.as_dict()
        return value if isinstance(value, dict) else {}
    if hasattr(results, "data"):
        value = results.data
        return value if isinstance(value, dict) else {}
    return {}


def _collect_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ["organic_results", "news_results", "shopping_results", "local_results", "top_stories"]:
        value = payload.get(key)
        if isinstance(value, list) and value:
            return value
    answer_box = payload.get("answer_box")
    if isinstance(answer_box, dict):
        title = answer_box.get("title") or answer_box.get("answer") or answer_box.get("snippet")
        if title:
            return [answer_box]
    return []


def _redact_secret(message: str) -> str:
    if "api_key=" not in message:
        return message
    prefix, _, rest = message.partition("api_key=")
    for separator in ["&", " ", ")"]:
        if separator in rest:
            _, _, suffix = rest.partition(separator)
            return f"{prefix}api_key=***{separator}{suffix}"
    return f"{prefix}api_key=***"
