from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserInsightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    display_name: str
    account_id: str
    preferred_categories: list[str]
    preferred_platforms: list[str]
    summary: str
    interest_weights: dict
    negative_preferences: list[str]
    recall_score: float
    interaction_frequency: int
    last_active_at: datetime | None
    updated_at: datetime | None


class RagDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    category: str
    visibility: str
    vectorized: bool
    created_at: datetime
