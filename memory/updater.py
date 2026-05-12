from __future__ import annotations

import os
from typing import Any

from agents.llm_client import LLMClient

from .prompts import LONG_TERM_UPDATE_PROMPT
from .schemas import MemoryCandidate, MemoryUpdatePlan


class MemoryUpdater:
    """Builds and applies long-term memory update plans."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        try:
            self.llm_client = llm_client or LLMClient(model=os.getenv("SUMMARY_MODEL") or None)
        except Exception:
            self.llm_client = None

    def build_plan(
        self,
        *,
        user_id: str,
        session_id: str | None,
        memory_context: dict[str, Any],
        user_transcript: str,
        assistant_transcript: str,
        session_summary: str,
        candidates: list[MemoryCandidate] | None = None,
    ) -> MemoryUpdatePlan:
        if self.llm_client and self.llm_client.is_configured:
            try:
                return self._build_plan_with_llm(
                    user_id=user_id,
                    session_id=session_id,
                    memory_context=memory_context,
                    user_transcript=user_transcript,
                    assistant_transcript=assistant_transcript,
                    session_summary=session_summary,
                    candidates=candidates or [],
                )
            except Exception:
                pass
        return self._build_plan_without_llm(user_id=user_id, session_id=session_id, candidates=candidates or [])

    def _build_plan_with_llm(
        self,
        *,
        user_id: str,
        session_id: str | None,
        memory_context: dict[str, Any],
        user_transcript: str,
        assistant_transcript: str,
        session_summary: str,
        candidates: list[MemoryCandidate],
    ) -> MemoryUpdatePlan:
        payload = {
            "memory_context": memory_context,
            "user_transcript": user_transcript[-6000:],
            "assistant_transcript": assistant_transcript[-4000:],
            "session_summary": session_summary,
            "memory_candidates": [candidate.to_dict() for candidate in candidates],
        }
        result = self.llm_client.chat_json(
            [
                {"role": "system", "content": LONG_TERM_UPDATE_PROMPT},
                {"role": "user", "content": str(payload)},
            ]
        )
        return MemoryUpdatePlan(
            user_id=user_id,
            session_id=session_id,
            candidates=candidates,
            short_term_summary=str(result.get("short_term_summary") or ""),
            long_term_summary=str(result.get("long_term_summary") or ""),
            user_profile_summary=str(result.get("user_profile_summary") or ""),
            preferences_to_add=_ensure_list(result.get("preferences_to_add")),
            negative_preferences_to_add=_ensure_list(result.get("negative_preferences_to_add")),
            business_needs_to_add=_ensure_list(result.get("business_needs_to_add")),
            recall_signals_to_add=_ensure_list(result.get("recall_signals_to_add")),
            tags_to_add=_ensure_list(result.get("tags_to_add")),
            confidence=_safe_confidence(result.get("confidence"), 0.7),
        )

    def _build_plan_without_llm(
        self,
        *,
        user_id: str,
        session_id: str | None,
        candidates: list[MemoryCandidate],
    ) -> MemoryUpdatePlan:
        plan = MemoryUpdatePlan(user_id=user_id, session_id=session_id, candidates=candidates)
        for candidate in candidates:
            if candidate.candidate_type == "preference":
                plan.preferences_to_add.append(candidate.content)
            elif candidate.candidate_type == "negative_preference":
                plan.negative_preferences_to_add.append(candidate.content)
            elif candidate.candidate_type == "business_need":
                plan.business_needs_to_add.append(candidate.content)
            elif candidate.candidate_type == "recall_signal":
                plan.recall_signals_to_add.append(candidate.content)
            elif candidate.candidate_type == "behavior":
                plan.tags_to_add.append(candidate.content)
            plan.tags_to_add.extend(candidate.tags)
            plan.confidence = max(plan.confidence, candidate.confidence)
        return plan


def _ensure_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _safe_confidence(value: object, default: float) -> float:
    try:
        return max(0.0, min(float(value), 1.0))
    except (TypeError, ValueError):
        return default
