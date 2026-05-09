from __future__ import annotations

from pydantic import BaseModel


class RecallCandidate(BaseModel):
    user_id: str
    display_name: str
    account_id: str
    last_active_at: str | None
    preferred_categories: list[str]
    recall_score: float
    reason: str


class RecallGenerateRequest(BaseModel):
    user_id: str


class RecallGenerateResponse(BaseModel):
    user_id: str
    recall_score: float
    matched_trends: list[str]
    reason: str
    message: str
