from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import TrendingCategory, TrendingItem, User
from ..schemas.trending import TrendingCreate, TrendingRead, TrendingUpdate

router = APIRouter(prefix="/trending", tags=["trending"])


@router.get("/categories", response_model=list[str])
def list_categories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[str]:
    categories = db.scalars(
        select(TrendingCategory.name)
        .where(TrendingCategory.is_active.is_(True))
        .order_by(TrendingCategory.sort_order, TrendingCategory.name)
    ).all()
    return list(categories)


@router.get("", response_model=list[TrendingRead])
def list_trending(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TrendingRead]:
    query = select(TrendingItem).where(TrendingItem.visibility == "public").order_by(
        desc(TrendingItem.heat_score), desc(TrendingItem.created_at)
    )
    items = db.scalars(query).all()
    return [TrendingRead.model_validate(item) for item in items]


@router.post("", response_model=TrendingRead)
def create_trending(payload: TrendingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TrendingRead:
    if payload.visibility == "private_rag_only" and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can create private RAG items")
    item = TrendingItem(**payload.model_dump(), created_by=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return TrendingRead.model_validate(item)


@router.put("/{item_id}", response_model=TrendingRead)
def update_trending(
    item_id: str,
    payload: TrendingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrendingRead:
    item = db.get(TrendingItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Trending item not found")
    if current_user.role != "admin" and item.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit this item")
    values = payload.model_dump(exclude_unset=True)
    if values.get("visibility") == "private_rag_only" and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can mark private RAG items")
    for key, value in values.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return TrendingRead.model_validate(item)


@router.delete("/{item_id}", status_code=204, response_class=Response)
def delete_trending(item_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    item = db.get(TrendingItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Trending item not found")
    if current_user.role != "admin" and item.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this item")
    db.delete(item)
    db.commit()
    return Response(status_code=204)
