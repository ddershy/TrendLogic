from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ChatMessage, ChatSession, User
from ..schemas.chat import AgentMessage, ChatMessageRead, ChatRequest, ChatResponse, ChatSessionRead
from ..services.chat_service import handle_chat_message

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
def send_message(payload: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ChatResponse:
    session_id, messages = handle_chat_message(db, current_user, payload.content, payload.session_id)
    return ChatResponse(session_id=session_id, messages=[AgentMessage(**message) for message in messages])


@router.get("/sessions", response_model=list[ChatSessionRead])
def list_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ChatSessionRead]:
    sessions = db.scalars(
        select(ChatSession).where(ChatSession.user_id == current_user.id).order_by(desc(ChatSession.updated_at))
    ).all()
    return [ChatSessionRead.model_validate(session) for session in sessions]


@router.post("/session", response_model=ChatSessionRead)
def create_session(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ChatSessionRead:
    session = ChatSession(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return ChatSessionRead.model_validate(session)


@router.get("/history", response_model=list[ChatMessageRead])
def history(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ChatMessageRead]:
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)).all()
    return [ChatMessageRead.model_validate(message) for message in messages]
