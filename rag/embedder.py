from __future__ import annotations

import hashlib
import math

from openai import OpenAI

from .config import rag_config


class BaseEmbedder:
    dimensions: int

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


class DashScopeEmbedder(BaseEmbedder):
    """阿里云 DashScope OpenAI 兼容 embedding 客户端。"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self.api_key = api_key or rag_config.dashscope_api_key
        self.base_url = base_url or rag_config.dashscope_base_url
        self.model = model or rag_config.embedding_model
        self.dimensions = dimensions or rag_config.embedding_dimensions
        if not self.api_key:
            raise RuntimeError("缺少 DASHSCOPE_API_KEY，无法调用阿里云 text-embedding-v4。")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        clean_texts = [text.strip() for text in texts if text and text.strip()]
        if not clean_texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(clean_texts), rag_config.embedding_batch_size):
            batch = clean_texts[start : start + rag_config.embedding_batch_size]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions,
            )
            vectors.extend([item.embedding for item in response.data])
        return vectors


class MockEmbedder(BaseEmbedder):
    """只用于离线自测；正式 RAG 默认不会走这里。"""

    dimensions = 64

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = digest[0] % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def create_embedder() -> BaseEmbedder:
    provider = rag_config.embedding_provider.lower()
    if provider in {"dashscope", "aliyun", "alibaba"}:
        return DashScopeEmbedder()
    if provider == "mock":
        return MockEmbedder()
    raise RuntimeError(f"不支持的 EMBEDDING_PROVIDER: {rag_config.embedding_provider}")
