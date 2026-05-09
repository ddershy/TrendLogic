from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, UserProfile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/memory")
def get_memory(user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Cannot access this memory")
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    return {
        "user_id": user_id,
        "summary": profile.summary if profile else "",
        "interest_weights": profile.interest_weights if profile else {},
    }


@router.post("/{user_id}/memory/summarize")
def summarize_memory(user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Cannot summarize this memory")
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id, summary="暂无足够对话形成长期记忆。")
        db.add(profile)
        db.commit()
    return {"status": "ok", "summary": profile.summary}
