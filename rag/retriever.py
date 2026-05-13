from __future__ import annotations

from datetime import datetime
from typing import Any

from .chunker import chunk_text
from .config import rag_config
from .document_loader import load_text_file
from .embedder import BaseEmbedder, create_embedder
from .vector_store import LanceDBVectorStore
from metrics import measure_ms, record_metric


class RAGService:
    def __init__(self, embedder: BaseEmbedder | None = None, vector_store: LanceDBVectorStore | None = None) -> None:
        self.embedder = embedder or create_embedder()
        self.vector_store = vector_store or LanceDBVectorStore()

    def add_document(self, file_path: str, metadata: dict, document: Any | None = None, replace_document: bool = False) -> dict:
        text = load_text_file(file_path)
        document_id = getattr(document, "id", metadata.get("document_id", ""))
        return self.add_text(
            text,
            {**metadata, "document_id": document_id, "file_path": file_path},
            replace_document_id=document_id if replace_document else None,
        )

    def add_text(self, text: str, metadata: dict, replace_document_id: str | None = None) -> dict:
        chunks = chunk_text(text, rag_config.chunk_size, rag_config.chunk_overlap)
        vectors = self.embedder.embed_many(chunks)
        now = datetime.utcnow().isoformat()
        records = [
            {
                "vector": vector,
                "text": chunk,
                "document_id": str(metadata.get("document_id", "")),
                "filename": str(metadata.get("filename", "")),
                "category": str(metadata.get("category", "")),
                "visibility": str(metadata.get("visibility", "")),
                "uploaded_by": str(metadata.get("uploaded_by", "")),
                "file_path": str(metadata.get("file_path", "")),
                "chunk_index": index,
                "created_at": now,
            }
            for index, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        self.vector_store.add_many(records, replace_document_id=replace_document_id)
        return {"chunks": len(records), "metadata": metadata}

    def delete_document(self, document_id: str) -> None:
        self.vector_store.delete_document(document_id)

    def search(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
        with measure_ms() as embedding_timing:
            vector = self.embedder.embed(query)
        with measure_ms() as search_timing:
            results = self.vector_store.search(vector, top_k=top_k, filters=filters)
        total_latency = embedding_timing["latency_ms"] + search_timing["latency_ms"]
        record_metric(
            "rag.search",
            total_latency,
            route="RAGService.search",
            metadata={
                "top_k": top_k,
                "filters": filters or {},
                "result_count": len(results),
                "embedding_latency_ms": embedding_timing["latency_ms"],
                "vector_search_latency_ms": search_timing["latency_ms"],
            },
        )
        return results
