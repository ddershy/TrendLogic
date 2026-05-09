from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TrendingBase(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    category: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=5, max_length=3000)
    source: str = Field(default="user_upload", max_length=120)
    heat_score: float = Field(default=0.5, ge=0, le=1)
    tags: list[str] = Field(default_factory=list)
    visibility: Literal["public", "private_rag_only"] = "public"
    is_ai_generated: bool = False


class TrendingCreate(TrendingBase):
    pass


class TrendingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=180)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    summary: str | None = Field(default=None, min_length=5, max_length=3000)
    source: str | None = Field(default=None, max_length=120)
    heat_score: float | None = Field(default=None, ge=0, le=1)
    tags: list[str] | None = None
    visibility: Literal["public", "private_rag_only"] | None = None
    is_ai_generated: bool | None = None


class TrendingRead(TrendingBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_by: str
    created_at: datetime
    updated_at: datetime
