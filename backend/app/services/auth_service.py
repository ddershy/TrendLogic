from __future__ import annotations

import secrets
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import User, UserProfile
from ..schemas.auth import RegisterRequest
from ..utils.security import create_access_token, hash_password, verify_password


def generate_account_id(db: Session) -> str:
    for _ in range(20):
        account_id = f"TL{datetime.utcnow():%Y%m%d}{secrets.randbelow(10000):04d}"
        if not db.scalar(select(User).where(User.account_id == account_id)):
            return account_id
    raise HTTPException(status_code=500, detail="Failed to generate account id")


def register_user(db: Session, payload: RegisterRequest) -> tuple[User, str]:
    exists = db.scalar(select(User).where(User.display_name == payload.display_name))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Display name already exists")
    role = "admin" if payload.admin_invite_code and payload.admin_invite_code == settings.admin_invite_code else "normal_user"
    user = User(
        account_id=generate_account_id(db),
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=role,
        preferences={
            "preferred_categories": payload.preferred_categories,
            "preferred_platforms": payload.preferred_platforms,
            "business_focus": payload.business_focus,
        },
    )
    db.add(user)
    db.flush()
    db.add(
        UserProfile(
            user_id=user.id,
            summary="新用户，等待更多对话形成长期偏好。",
            preferred_categories=payload.preferred_categories,
            preferred_platforms=payload.preferred_platforms,
            interest_weights={tag: 0.45 for tag in payload.preferred_categories + payload.preferred_platforms},
        )
    )
    db.commit()
    db.refresh(user)
    return user, create_access_token(user.id, user.role)


def login_user(db: Session, identifier: str, password: str) -> tuple[User, str]:
    user = db.scalar(select(User).where(or_(User.account_id == identifier, User.display_name == identifier)))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid account or password")
    return user, create_access_token(user.id, user.role)
