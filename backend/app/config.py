from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "TrendLogic API"
    api_prefix: str = "/api"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./trendlogic.db")
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production")
    jwt_expires_minutes: int = int(os.getenv("JWT_EXPIRES_MINUTES", "1440"))
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    )
    admin_invite_code: str = os.getenv("ADMIN_INVITE_CODE", "trendlogic-admin")


settings = Settings()
