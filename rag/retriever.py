from __future__ import annotations

from datetime import datetime

from .chunker import chunk_text
from .config import rag_config
from .document_loader import load_text_file
from .embedder import BaseEmbedder, MockEmbedder
from .vector_store import InMemoryVectorStore


class RAGService:
    def __init__(self, embedder: BaseEmbedder | None = None, vector_store: InMemoryVectorStore | None = None) -> None:
        self.embedder = embedder or MockEmbedder()
        self.vector_store = vector_store or InMemoryVectorStore()

    def add_document(self, file_path: str, metadata: dict) -> dict:
        text = load_text_file(file_path)
        return self.add_text(text, {**metadata, "file_path": file_path})

    def add_text(self, text: str, metadata: dict) -> dict:
        chunks = chunk_text(text, rag_config.chunk_size, rag_config.chunk_overlap)
        now = datetime.utcnow().isoformat()
        for index, chunk in enumerate(chunks):
            self.vector_store.add(
                text=chunk,
                vector=self.embedder.embed(chunk),
                metadata={**metadata, "chunk_index": index, "created_at": now},
            )
        return {"chunks": len(chunks), "metadata": metadata}

    def search(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
        return self.vector_store.search(self.embedder.embed(query), top_k=top_k, filters=filters)
