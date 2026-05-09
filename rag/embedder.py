from __future__ import annotations

import hashlib
import math


class BaseEmbedder:
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class MockEmbedder(BaseEmbedder):
    """Deterministic local embedder for MVP tests before connecting a provider."""

    dimensions = 64

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = digest[0] % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
