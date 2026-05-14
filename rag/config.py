from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
load_dotenv(PROJECT_ROOT / ".env")


def _resolve_lancedb_uri(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str(BACKEND_ROOT / path)


@dataclass(frozen=True)
class RAGConfig:
    lancedb_uri: str = _resolve_lancedb_uri(os.getenv("LANCEDB_URI", "./lancedb"))
    lancedb_table: str = os.getenv("LANCEDB_TABLE", "trendlogic_rag_chunks")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "dashscope")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
    embedding_dimensions: int = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", os.getenv("EMBEDDING_API_KEY", ""))
    dashscope_base_url: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))


rag_config = RAGConfig()
