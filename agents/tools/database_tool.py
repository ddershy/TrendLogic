from __future__ import annotations


def query_user_profile_tool(user_id: str) -> dict:
    """Query a user profile from the Django database."""

    try:
        from core.models import User
    except Exception:
        return {"user_id": user_id, "summary": "数据库环境未初始化。"}

    user = User.objects.filter(id=user_id).first()
    if not user:
        return {"user_id": user_id, "found": False}
    profile = getattr(user, "profile", None)
    return {
        "user_id": user.id,
        "found": True,
        "display_name": user.display_name,
        "summary": profile.summary if profile else "",
        "preferred_categories": profile.preferred_categories if profile else user.preferences.get("preferred_categories", []),
        "preferred_platforms": profile.preferred_platforms if profile else user.preferences.get("preferred_platforms", []),
        "interest_weights": profile.interest_weights if profile else {},
        "negative_preferences": profile.negative_preferences if profile else [],
        "interaction_frequency": profile.interaction_frequency if profile else 0,
    }


def query_user_memory_tool(user_id: str) -> dict:
    """Query a user memory profile from the Django database."""

    try:
        from core.models import UserMemory
    except Exception:
        return {"user_id": user_id, "summary": "数据库环境未初始化。"}

    memory = UserMemory.objects.filter(user_id=user_id).first()
    if not memory:
        return {"user_id": user_id, "found": False}
    return {
        "user_id": user_id,
        "found": True,
        "long_term_summary": memory.long_term_summary,
        "preferences": memory.preferences,
        "negative_preferences": memory.negative_preferences,
        "business_needs": memory.business_needs,
        "behavior_notes": memory.behavior_notes,
        "recall_signals": memory.recall_signals,
        "tags": memory.tags,
    }


def query_recent_chat_sessions_tool(user_id: str, limit: int = 5) -> list[dict]:
    """Query recent chat sessions for a user."""

    try:
        from core.models import ChatSession
    except Exception:
        return []

    sessions = ChatSession.objects.filter(user_id=user_id).order_by("-updated_at")[: int(limit or 5)]
    return [
        {
            "id": session.id,
            "title": session.title,
            "message_count": session.message_count,
            "session_summary": session.session_summary,
            "recent_user_transcript": session.user_transcript[-800:],
            "last_message_at": session.last_message_at.isoformat() if session.last_message_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        }
        for session in sessions
    ]


def query_recall_records_tool(user_id: str, limit: int = 5) -> list[dict]:
    """Query recent recall records for a user."""

    try:
        from core.models import RecallRecord
    except Exception:
        return []

    records = RecallRecord.objects.filter(user_id=user_id).order_by("-created_at")[: int(limit or 5)]
    return [
        {
            "id": record.id,
            "recall_score": record.recall_score,
            "matched_trends": record.matched_trends,
            "generated_message": record.generated_message,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
        for record in records
    ]


def query_user_workspace_tool(user_id: str, session_limit: int = 5) -> dict:
    """Query a compact user-centric workspace snapshot."""

    return {
        "profile": query_user_profile_tool(user_id),
        "memory": query_user_memory_tool(user_id),
        "recent_sessions": query_recent_chat_sessions_tool(user_id, limit=session_limit),
        "recall_records": query_recall_records_tool(user_id, limit=5),
    }
