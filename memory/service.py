from __future__ import annotations

from typing import Any

from django.utils import timezone

from .schemas import MemoryCandidate, MemoryContext, MemoryUpdatePlan
from .summarizer import MemorySummarizer
from .updater import MemoryUpdater


class MemoryService:
    """Main entrypoint for memory lifecycle operations."""

    def __init__(
        self,
        summarizer: MemorySummarizer | None = None,
        updater: MemoryUpdater | None = None,
        short_term_limit: int = 10,
    ) -> None:
        self.summarizer = summarizer or MemorySummarizer()
        self.updater = updater or MemoryUpdater()
        self.short_term_limit = short_term_limit

    def load_context(self, user: Any, session: Any | None = None) -> MemoryContext:
        """Read user/session memory and return a clean context for agents."""

        user = self._resolve_user(user)
        session = self._resolve_session(session, user)
        profile = getattr(user, "profile", None)
        memory = self._get_memory(user)

        preferences = []
        negative_preferences = []
        business_needs = []
        recall_signals = []
        tags = []

        if profile:
            preferences.extend(_as_list(getattr(profile, "preferred_categories", [])))
            preferences.extend(_as_list(getattr(profile, "preferred_platforms", [])))
            negative_preferences.extend(_as_list(getattr(profile, "negative_preferences", [])))

        if memory:
            preferences.extend(_preference_values(getattr(memory, "preferences", {})))
            negative_preferences.extend(_as_list(getattr(memory, "negative_preferences", [])))
            business_needs.extend(_summary_values(getattr(memory, "business_needs", [])))
            recall_signals.extend(_summary_values(getattr(memory, "recall_signals", [])))
            tags.extend(_as_list(getattr(memory, "tags", [])))

        return MemoryContext(
            user_id=user.id,
            session_id=getattr(session, "id", None),
            user_profile_summary=getattr(profile, "summary", "") if profile else "",
            short_term_summary=getattr(memory, "short_term_summary", "") if memory else "",
            long_term_summary=getattr(memory, "long_term_summary", "") if memory else "",
            session_summary=getattr(session, "session_summary", "") if session else "",
            recent_user_transcript=_tail(getattr(session, "user_transcript", "") if session else ""),
            preferences=_unique(preferences),
            negative_preferences=_unique(negative_preferences),
            business_needs=_unique(business_needs),
            recall_signals=_unique(recall_signals),
            tags=_unique(tags),
            metadata={
                "session_message_count": getattr(session, "message_count", 0) if session else 0,
                "profile_recall_score": getattr(profile, "recall_score", 0) if profile else 0,
                "memory_confidence": getattr(memory, "confidence", 0) if memory else 0,
            },
        )

    def _resolve_user(self, user: Any):
        from core.models import User

        if isinstance(user, User):
            return user
        resolved = User.objects.filter(id=str(user)).first()
        if not resolved:
            raise ValueError("User not found when loading memory context.")
        return resolved

    def _resolve_session(self, session: Any | None, user: Any):
        from core.models import ChatSession

        if session is None:
            return None
        if isinstance(session, ChatSession):
            return session if session.user_id == user.id else None
        return ChatSession.objects.filter(id=str(session), user=user).first()

    def _get_memory(self, user: Any):
        from core.models import UserMemory

        return UserMemory.objects.filter(user=user).first()

    def get_or_create_memory(self, user: Any):
        from core.models import UserMemory

        user = self._resolve_user(user)
        memory, _ = UserMemory.objects.get_or_create(user=user)
        return memory

    def record_interaction(
        self,
        *,
        user: Any,
        session: Any,
        user_message: str,
        assistant_message: str,
        trace_messages: list[dict] | None = None,
        memory_candidates: list[MemoryCandidate | dict] | None = None,
    ) -> MemoryContext:
        user = self._resolve_user(user)
        session = self._resolve_session(session, user)
        if not session:
            raise ValueError("Session not found when recording memory interaction.")

        now = timezone.now()
        trace_messages = trace_messages or []
        candidates = [
            candidate
            for candidate in (self._normalize_candidate(candidate) for candidate in (memory_candidates or []))
            if candidate.content
        ]
        interaction = {
            "time": now.isoformat(),
            "user_message": user_message,
            "assistant_message": assistant_message,
            "trace_messages": [self._trace_text(trace) for trace in trace_messages if self._trace_text(trace)],
            "memory_candidates": [candidate.to_dict() for candidate in candidates],
        }

        session.user_transcript = _append_transcript(session.user_transcript, now, user_message)
        session.assistant_transcript = _append_transcript(session.assistant_transcript, now, assistant_message)
        session.trace_summary = _tail(
            "\n".join([session.trace_summary, *interaction["trace_messages"]]).strip(),
            limit=4000,
        )
        session.recent_interactions = [*(session.recent_interactions or []), interaction]
        compressed = self._compress_if_needed(session)
        session.message_count = (session.message_count or 0) + 1
        session.last_message_at = now
        if session.title == "新的运营咨询":
            session.title = user_message[:36] or session.title
        session.save(
            update_fields=[
                "user_transcript",
                "assistant_transcript",
                "session_summary",
                "trace_summary",
                "recent_interactions",
                "message_count",
                "last_message_at",
                "title",
                "updated_at",
            ]
        )

        self._update_short_term_profile(user, session, user_message, candidates)
        if compressed:
            self._sync_short_term_summary(user, session.session_summary)
        return self.load_context(user, session)

    def build_long_term_update_plan(self, *, user: Any, session: Any) -> MemoryUpdatePlan:
        user = self._resolve_user(user)
        session = self._resolve_session(session, user)
        if not session:
            raise ValueError("Session not found when building long-term memory plan.")
        candidates = self._candidates_from_session(session)
        return self.updater.build_plan(
            user_id=user.id,
            session_id=session.id,
            memory_context=self.load_context(user, session).to_dict(),
            user_transcript=session.user_transcript,
            assistant_transcript=session.assistant_transcript,
            session_summary=session.session_summary,
            candidates=candidates,
        )

    def update_long_term(self, *, user: Any, session: Any) -> MemoryUpdatePlan:
        plan = self.build_long_term_update_plan(user=user, session=session)
        self.apply_update_plan(plan)
        return plan

    def apply_update_plan(self, plan: MemoryUpdatePlan) -> None:
        from core.models import User, UserProfile

        user = User.objects.filter(id=plan.user_id).first()
        if not user:
            return
        memory = self.get_or_create_memory(user)
        profile, _ = UserProfile.objects.get_or_create(user=user)

        if plan.short_term_summary:
            memory.short_term_summary = plan.short_term_summary
        if plan.long_term_summary:
            memory.long_term_summary = _join_summary(memory.long_term_summary, plan.long_term_summary)
        if plan.user_profile_summary:
            profile.summary = plan.user_profile_summary

        memory.preferences = _merge_preference_dict(memory.preferences, plan.preferences_to_add)
        memory.negative_preferences = _merge_list(memory.negative_preferences, plan.negative_preferences_to_add)
        memory.business_needs = _merge_list(memory.business_needs, plan.business_needs_to_add)
        memory.recall_signals = _merge_list(memory.recall_signals, plan.recall_signals_to_add)
        memory.tags = _merge_list(memory.tags, plan.tags_to_add)
        memory.confidence = max(float(memory.confidence or 0), plan.confidence)
        memory.last_used_at = timezone.now()
        memory.save()
        profile.save()

    def append_memory_list(self, *, user: Any, field_name: str, item: dict, limit: int = 20):
        memory = self.get_or_create_memory(user)
        current = getattr(memory, field_name) or []
        current.append(item)
        setattr(memory, field_name, current[-limit:])
        memory.last_used_at = timezone.now()
        memory.save(update_fields=[field_name, "last_used_at", "updated_at"])
        return memory

    def update_memory_from_payload(self, memory: Any, payload: dict):
        text_fields = ["short_term_summary", "long_term_summary"]
        json_fields = ["preferences", "negative_preferences", "business_needs", "behavior_notes", "recall_signals", "tags"]
        changed_fields: list[str] = []

        for field in text_fields:
            if field in payload:
                setattr(memory, field, str(payload.get(field, "")))
                changed_fields.append(field)

        for field in json_fields:
            if field in payload:
                default_value = {} if field == "preferences" else []
                setattr(memory, field, payload.get(field) if payload.get(field) is not None else default_value)
                changed_fields.append(field)

        if "confidence" in payload:
            memory.confidence = max(0.0, min(float(payload.get("confidence") or 0), 1.0))
            changed_fields.append("confidence")

        if not changed_fields:
            return memory
        memory.last_used_at = timezone.now()
        changed_fields.extend(["last_used_at", "updated_at"])
        memory.save(update_fields=sorted(set(changed_fields)))
        return memory

    def _compress_if_needed(self, session: Any) -> bool:
        interactions = list(session.recent_interactions or [])
        if len(interactions) <= self.short_term_limit:
            return False

        overflow = interactions[:-self.short_term_limit]
        session.session_summary = self.summarizer.summarize(session.session_summary, overflow)
        session.recent_interactions = interactions[-self.short_term_limit :]
        return True

    def _update_short_term_profile(
        self,
        user: Any,
        session: Any,
        user_message: str,
        candidates: list[MemoryCandidate],
    ) -> None:
        from agents.user_profile_agent import UserProfileAgent
        from core.models import UserProfile

        memory = self.get_or_create_memory(user)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        tags = UserProfileAgent().extract_tags(user_message)
        candidate_tags = [tag for candidate in candidates for tag in candidate.tags]
        all_tags = _merge_list(memory.tags, [*tags, *candidate_tags])

        memory.short_term_summary = _tail(session.session_summary or user_message, limit=1200)
        memory.tags = all_tags
        memory.confidence = max(float(memory.confidence or 0), 0.72)
        memory.last_used_at = timezone.now()
        memory.save()

        weights = dict(profile.interest_weights or {})
        for tag in [*tags, *candidate_tags]:
            weights[tag] = min(float(weights.get(tag, 0.2)) + 0.08, 1.0)
        profile.interest_weights = weights
        profile.interaction_frequency = (profile.interaction_frequency or 0) + 1
        profile.last_active_at = timezone.now()
        if tags:
            profile.summary = f"用户最近关注：{', '.join(sorted(set(tags)))}。"
        profile.save()

    def _sync_short_term_summary(self, user: Any, summary: str) -> None:
        memory = self.get_or_create_memory(user)
        memory.short_term_summary = summary
        memory.last_used_at = timezone.now()
        memory.save(update_fields=["short_term_summary", "last_used_at", "updated_at"])

    def _normalize_candidate(self, value: MemoryCandidate | dict) -> MemoryCandidate:
        if isinstance(value, MemoryCandidate):
            return value
        return MemoryCandidate(
            candidate_type=value.get("candidate_type") or value.get("type") or "behavior",
            content=str(value.get("content") or "").strip(),
            source_agent=str(value.get("source_agent") or value.get("agent") or ""),
            confidence=float(value.get("confidence") or 0.7),
            evidence=str(value.get("evidence") or ""),
            tags=_as_list(value.get("tags")),
        )

    def _candidates_from_session(self, session: Any) -> list[MemoryCandidate]:
        candidates: list[MemoryCandidate] = []
        for interaction in session.recent_interactions or []:
            for raw_candidate in interaction.get("memory_candidates", []) if isinstance(interaction, dict) else []:
                candidate = self._normalize_candidate(raw_candidate)
                if candidate.content:
                    candidates.append(candidate)
        return candidates

    @staticmethod
    def _trace_text(trace: dict) -> str:
        agent = trace.get("agent") or "Agent"
        content = trace.get("content") or ""
        return f"[{agent}] {content}".strip()


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple | set):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _preference_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(_as_list(item))
        return result
    return _as_list(value)


def _summary_values(value: Any) -> list[str]:
    if not isinstance(value, list):
        return _as_list(value)
    result = []
    for item in value:
        if isinstance(item, dict):
            result.append(str(item.get("summary") or item.get("content") or item.get("message") or "").strip())
        else:
            result.append(str(item).strip())
    return [item for item in result if item]


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _tail(value: str, limit: int = 2000) -> str:
    return value[-limit:] if len(value) > limit else value


def _append_transcript(existing: str, when, content: str) -> str:
    line = f"[{when:%Y-%m-%d %H:%M:%S}] {content}".strip()
    return f"{existing}\n{line}".strip()


def _merge_list(existing: Any, additions: list[str], limit: int = 50) -> list[str]:
    return _unique([*_as_list(existing), *_as_list(additions)])[-limit:]


def _merge_preference_dict(existing: Any, additions: list[str]) -> dict:
    preferences = dict(existing or {}) if isinstance(existing, dict) else {}
    current = _as_list(preferences.get("memory_preferences"))
    preferences["memory_preferences"] = _merge_list(current, additions)
    return preferences


def _join_summary(existing: str, addition: str, limit: int = 2000) -> str:
    if not existing:
        return addition[-limit:]
    if addition in existing:
        return existing[-limit:]
    return f"{existing}\n{addition}"[-limit:]
