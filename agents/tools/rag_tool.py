from __future__ import annotations

from rag import RAGService

_rag_service = RAGService()


def rag_search_tool(query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
    return _rag_service.search(query, top_k=top_k, filters=filters)
