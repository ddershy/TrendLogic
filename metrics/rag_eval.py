from __future__ import annotations

from dataclasses import dataclass

from .service import measure_ms
from rag import RAGService


@dataclass
class RAGEvalCaseResult:
    case_id: str
    query: str
    retrieved_count: int
    relevant_retrieved: int
    expected_count: int
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    latency_ms: float
    retrieved_sources: list[str]


def evaluate_rag_cases(cases, top_k: int | None = None) -> dict:
    service = RAGService()
    case_results: list[RAGEvalCaseResult] = []
    for case in cases:
        current_top_k = int(top_k or case.top_k or 5)
        filters = {"category": case.category} if case.category else {}
        with measure_ms() as timing:
            results = service.search(case.query, top_k=current_top_k, filters=filters)
        case_results.append(_score_case(case, results, current_top_k, timing["latency_ms"]))

    count = len(case_results) or 1
    metrics = {
        "case_count": len(case_results),
        "top_k": int(top_k or 0),
        "precision_at_k": _avg([item.precision_at_k for item in case_results], count),
        "recall_at_k": _avg([item.recall_at_k for item in case_results], count),
        "mrr": _avg([item.reciprocal_rank for item in case_results], count),
        "avg_latency_ms": _avg([item.latency_ms for item in case_results], count),
        "cases": [item.__dict__ for item in case_results],
    }
    return metrics


def _score_case(case, results: list[dict], top_k: int, latency_ms: float) -> RAGEvalCaseResult:
    relevant_flags = [_is_relevant(case, result) for result in results[:top_k]]
    relevant_retrieved = sum(1 for flag in relevant_flags if flag)
    expected_count = _expected_count(case)
    reciprocal_rank = 0.0
    for index, is_relevant in enumerate(relevant_flags, start=1):
        if is_relevant:
            reciprocal_rank = 1 / index
            break
    return RAGEvalCaseResult(
        case_id=case.id,
        query=case.query,
        retrieved_count=len(results[:top_k]),
        relevant_retrieved=relevant_retrieved,
        expected_count=expected_count,
        precision_at_k=relevant_retrieved / max(1, len(results[:top_k])),
        recall_at_k=min(1.0, relevant_retrieved / max(1, expected_count)),
        reciprocal_rank=reciprocal_rank,
        latency_ms=latency_ms,
        retrieved_sources=[_source_key(result) for result in results[:top_k]],
    )


def _is_relevant(case, result: dict) -> bool:
    metadata = result.get("metadata") or {}
    document_id = str(metadata.get("document_id") or "")
    filename = str(metadata.get("filename") or "")
    text = str(result.get("text") or "")
    expected_document_ids = {str(item) for item in case.expected_document_ids or []}
    expected_filenames = {str(item) for item in case.expected_filenames or []}
    expected_keywords = [str(item) for item in case.expected_keywords or []]
    if expected_document_ids and document_id in expected_document_ids:
        return True
    if expected_filenames and filename in expected_filenames:
        return True
    if expected_keywords and all(keyword in text for keyword in expected_keywords):
        return True
    return False


def _expected_count(case) -> int:
    values = [case.expected_document_ids or [], case.expected_filenames or [], case.expected_keywords or []]
    return max(1, max(len(value) for value in values))


def _source_key(result: dict) -> str:
    metadata = result.get("metadata") or {}
    filename = str(metadata.get("filename") or "")
    chunk_index = metadata.get("chunk_index", "")
    return f"{filename}#{chunk_index}" if filename else str(metadata.get("document_id") or "")


def _avg(values: list[float], count: int) -> float:
    return round(sum(values) / max(1, count), 4)
