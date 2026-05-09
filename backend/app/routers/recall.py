from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from agents.user_recall_agent import RecallAgent

from ..database import get_db
from ..deps import require_admin
from ..models import RecallRecord, TrendingItem, User, UserProfile
from ..schemas.recall import RecallCandidate, RecallGenerateRequest, RecallGenerateResponse

router = APIRouter(prefix="/recall", tags=["recall"])


@router.get("/candidates", response_model=list[RecallCandidate])
def candidates(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[RecallCandidate]:
    rows = db.execute(select(User, UserProfile).join(UserProfile, User.id == UserProfile.user_id, isouter=True)).all()
    result = []
    for user, profile in rows:
        if user.role == "admin":
            continue
        profile = profile or UserProfile(user_id=user.id)
        score = min(0.25 + (profile.interaction_frequency or 0) * 0.06 + len(profile.interest_weights or {}) * 0.04, 0.98)
        result.append(
            RecallCandidate(
                user_id=user.id,
                display_name=user.display_name,
                account_id=user.account_id,
                last_active_at=profile.last_active_at.isoformat() if profile.last_active_at else None,
                preferred_categories=profile.preferred_categories or user.preferences.get("preferred_categories", []),
                recall_score=round(score, 2),
                reason="基于历史关注类目、交互频率和近期爆品匹配度生成。",
            )
        )
    return sorted(result, key=lambda item: item.recall_score, reverse=True)


@router.post("/generate", response_model=RecallGenerateResponse)
def generate_recall(
    payload: RecallGenerateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RecallGenerateResponse:
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = user.profile or UserProfile(user_id=user.id)
    trends = list(
        db.scalars(
            select(TrendingItem.title)
            .where(TrendingItem.visibility == "public")
            .order_by(desc(TrendingItem.heat_score), desc(TrendingItem.created_at))
            .limit(5)
        )
    )
    score = min(0.35 + (profile.interaction_frequency or 0) * 0.06 + len(profile.interest_weights or {}) * 0.04, 0.98)
    categories = profile.preferred_categories or user.preferences.get("preferred_categories", [])
    generated = RecallAgent().generate(user.display_name, categories, trends, score)
    record = RecallRecord(
        user_id=user.id,
        recall_score=generated["recall_score"],
        matched_trends=generated["matched_trends"],
        generated_message=generated["message"],
        created_by=admin.id,
    )
    db.add(record)
    db.commit()
    return RecallGenerateResponse(user_id=user.id, **generated)
