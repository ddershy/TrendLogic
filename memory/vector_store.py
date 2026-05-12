from __future__ import annotations


class MemoryVectorStore:
    """Replaceable vector-memory boundary reserved for LanceDB or similar stores."""

    def add_memory(self, *, user_id: str, content: str, metadata: dict | None = None) -> None:
        return None

    def search_memory(self, *, user_id: str, query: str, limit: int = 5) -> list[dict]:
        return []

    def delete_memory(self, *, user_id: str, memory_id: str) -> None:
        return None
