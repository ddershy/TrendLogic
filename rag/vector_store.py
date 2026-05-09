from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class VectorRecord:
    text: str
    vector: list[float]
    metadata: dict = field(default_factory=dict)


class InMemoryVectorStore:
    """LanceDB-compatible seam for MVP; replace with LanceDB implementation later."""

    def __init__(self) -> None:
        self.records: list[VectorRecord] = []

    def add(self, text: str, vector: list[float], metadata: dict) -> None:
        self.records.append(VectorRecord(text=text, vector=vector, metadata=metadata))

    def search(self, vector: list[float], top_k: int = 5, filters: dict | None = None) -> list[dict]:
        filtered = [
            record
            for record in self.records
            if not filters or all(record.metadata.get(key) == value for key, value in filters.items())
        ]
        scored = sorted(
            filtered,
            key=lambda record: cosine_similarity(vector, record.vector),
            reverse=True,
        )
        return [
            {
                "text": record.text,
                "metadata": record.metadata,
                "score": cosine_similarity(vector, record.vector),
            }
            for record in scored[:top_k]
        ]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left)) or 1.0
    right_norm = math.sqrt(sum(b * b for b in right)) or 1.0
    return numerator / (left_norm * right_norm)
