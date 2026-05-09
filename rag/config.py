from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RAGConfig:
    lancedb_uri: str = os.getenv("LANCEDB_URI", "./lancedb")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "mock")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "mock-local")
    chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))


rag_config = RAGConfig()
