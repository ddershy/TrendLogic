from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import UploadedDocument, User, UserProfile
from ..schemas.admin import RagDocumentRead, UserInsightRead

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[dict])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return [
        {
            "id": user.id,
            "account_id": user.account_id,
            "display_name": user.display_name,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
        }
        for user in users
    ]


@router.get("/user-insights", response_model=list[UserInsightRead])
def user_insights(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[UserInsightRead]:
    rows = db.execute(select(User, UserProfile).join(UserProfile, User.id == UserProfile.user_id, isouter=True)).all()
    result = []
    for user, profile in rows:
        profile = profile or UserProfile(user_id=user.id)
        result.append(
            UserInsightRead(
                user_id=user.id,
                display_name=user.display_name,
                account_id=user.account_id,
                preferred_categories=profile.preferred_categories or user.preferences.get("preferred_categories", []),
                preferred_platforms=profile.preferred_platforms or user.preferences.get("preferred_platforms", []),
                summary=profile.summary,
                interest_weights=profile.interest_weights or {},
                negative_preferences=profile.negative_preferences or [],
                recall_score=profile.recall_score or 0,
                interaction_frequency=profile.interaction_frequency or 0,
                last_active_at=profile.last_active_at,
                updated_at=profile.updated_at,
            )
        )
    return result


@router.post("/rag/upload", response_model=RagDocumentRead)
def upload_rag_document(
    file: UploadFile = File(...),
    category: str = Form("选品资料"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RagDocumentRead:
    upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"{admin.id}_{file.filename}"
    with target.open("wb") as buffer:
        buffer.write(file.file.read())
    document = UploadedDocument(
        filename=file.filename,
        file_path=str(target),
        category=category,
        visibility="private_rag_only",
        uploaded_by=admin.id,
        vectorized=False,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return RagDocumentRead.model_validate(document)


@router.get("/rag/documents", response_model=list[RagDocumentRead])
def rag_documents(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[RagDocumentRead]:
    documents = db.scalars(select(UploadedDocument).order_by(UploadedDocument.created_at.desc())).all()
    return [RagDocumentRead.model_validate(document) for document in documents]
