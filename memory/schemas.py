from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


MemoryCandidateType = Literal[
    "preference",
    "negative_preference",
    "business_need",
    "behavior",
    "recall_signal",
]


@dataclass(slots=True)
class MemoryContext:
    """A clean memory snapshot passed from backend/memory to agents."""

    user_id: str
    session_id: str | None = None
    user_profile_summary: str = ""
    short_term_summary: str = ""
    short_messages: dict[str, Any] = field(default_factory=dict)
    long_term_summary: str = ""
    session_summary: str = ""
    recent_user_transcript: str = ""
    preferences: list[str] = field(default_factory=list)
    negative_preferences: list[str] = field(default_factory=list)
    business_needs: list[str] = field(default_factory=list)
    recall_signals: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MemoryCandidate:
    """A possible memory item produced by agents, not written directly."""

    candidate_type: MemoryCandidateType
    content: str
    source_agent: str = ""
    confidence: float = 0.7
    evidence: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MemoryUpdatePlan:
    """A planned memory/profile update created by the memory module."""

    user_id: str
    session_id: str | None = None
    candidates: list[MemoryCandidate] = field(default_factory=list)
    short_term_summary: str = ""
    long_term_summary: str = ""
    user_profile_summary: str = ""
    preferences_to_add: list[str] = field(default_factory=list)
    negative_preferences_to_add: list[str] = field(default_factory=list)
    business_needs_to_add: list[str] = field(default_factory=list)
    recall_signals_to_add: list[str] = field(default_factory=list)
    tags_to_add: list[str] = field(default_factory=list)
    confidence: float = 0.7

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["candidates"] = [candidate.to_dict() for candidate in self.candidates]
        return data
