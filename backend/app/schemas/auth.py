from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=128)
    preferred_categories: list[str] = Field(default_factory=list)
    preferred_platforms: list[str] = Field(default_factory=list)
    business_focus: str | None = None
    admin_invite_code: str | None = None


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=2, max_length=80)
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    display_name: str
    role: Literal["normal_user", "admin"]
    preferences: dict
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
