from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("u"))
    account_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(24), default="normal_user")
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user")
    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("s"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(160), default="新的运营咨询")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("m"))
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(24))
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(24), default="final")
    agent_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    agent_function: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class TrendingItem(Base):
    __tablename__ = "trending_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("t"))
    title: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(120), default="user_upload")
    summary: Mapped[str] = mapped_column(Text)
    heat_score: Mapped[float] = mapped_column(Float, default=0.5)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    visibility: Mapped[str] = mapped_column(String(32), default="public")
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TrendingCategory(Base):
    __tablename__ = "trending_categories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("tc"))
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(240), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("doc"))
    filename: Mapped[str] = mapped_column(String(240))
    file_path: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(80), default="选品资料")
    visibility: Mapped[str] = mapped_column(String(32), default="private_rag_only")
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    vectorized: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("p"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    interest_weights: Mapped[dict] = mapped_column(JSON, default=dict)
    negative_preferences: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_platforms: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    recall_score: Mapped[float] = mapped_column(Float, default=0.0)
    interaction_frequency: Mapped[int] = mapped_column(Integer, default=0)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="profile")


class MemorySummary(Base):
    __tablename__ = "memory_summaries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("mem"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("chat_sessions.id"), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    extracted_preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RecallRecord(Base):
    __tablename__ = "recall_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("r"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    recall_score: Mapped[float] = mapped_column(Float, default=0.0)
    matched_trends: Mapped[list[str]] = mapped_column(JSON, default=list)
    generated_message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
