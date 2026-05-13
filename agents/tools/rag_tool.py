from __future__ import annotations

from rag import RAGService

_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def rag_search_tool(query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
    return get_rag_service().search(query, top_k=top_k, filters=filters)
