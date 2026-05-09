from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from agents import AgentOrchestrator
from agents.user_profile_agent import UserProfileAgent

from ..models import ChatMessage, ChatSession, TrendingItem, User, UserProfile


def get_or_create_session(db: Session, user: User, session_id: str | None, first_message: str) -> ChatSession:
    if session_id:
        session = db.get(ChatSession, session_id)
        if session and session.user_id == user.id:
            return session
    session = ChatSession(user_id=user.id, title=first_message[:36] or "新的运营咨询")
    db.add(session)
    db.flush()
    return session


def handle_chat_message(db: Session, user: User, content: str, session_id: str | None = None) -> tuple[str, list[dict]]:
    session = get_or_create_session(db, user, session_id, content)
    db.add(ChatMessage(session_id=session.id, user_id=user.id, role="user", content=content, message_type="final"))
    trend_titles = list(
        db.scalars(
            select(TrendingItem.title)
            .where(TrendingItem.visibility == "public")
            .order_by(desc(TrendingItem.heat_score), desc(TrendingItem.created_at))
            .limit(5)
        )
    )
    result_messages = AgentOrchestrator().run(content, trend_titles)
    for message in result_messages:
        db.add(
            ChatMessage(
                session_id=session.id,
                user_id=user.id,
                role="assistant",
                content=message["content"],
                message_type=message["type"],
                agent_name=message["agent"],
                agent_function=message.get("function"),
            )
        )
    update_profile_from_text(db, user, content)
    session.updated_at = datetime.utcnow()
    db.commit()
    return session.id, result_messages


def update_profile_from_text(db: Session, user: User, content: str) -> None:
    profile = user.profile or UserProfile(user_id=user.id)
    tags = UserProfileAgent().extract_tags(content)
    weights = dict(profile.interest_weights or {})
    for tag in tags:
        weights[tag] = min(float(weights.get(tag, 0.2)) + 0.08, 1.0)
    profile.interest_weights = weights
    profile.interaction_frequency = (profile.interaction_frequency or 0) + 1
    profile.last_active_at = datetime.utcnow()
    if tags:
        profile.summary = f"用户最近关注：{', '.join(sorted(set(tags)))}。"
    db.add(profile)
