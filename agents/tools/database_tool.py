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
