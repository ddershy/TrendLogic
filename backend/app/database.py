from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from .models import entities  # noqa: F401

    Base.metadata.create_all(bind=engine)
    seed_default_categories()


def seed_default_categories() -> None:
    from .models import TrendingCategory

    default_categories = [
        ("美妆个护", "美妆、护肤、香氛、个护清洁"),
        ("服饰穿搭", "服装、鞋靴、配饰、穿搭内容"),
        ("箱包配饰", "女包、通勤包、饰品、帽子"),
        ("家居收纳", "家居用品、收纳整理、租房好物"),
        ("数码配件", "手机配件、桌面设备、智能硬件"),
        ("母婴亲子", "母婴用品、玩具、亲子内容"),
        ("宠物用品", "宠物食品、清洁、玩具和出行用品"),
        ("食品饮料", "零食、饮品、轻食、地方特产"),
        ("运动户外", "运动装备、户外用品、健身内容"),
        ("跨境电商", "TikTok、Amazon、独立站相关选品"),
    ]
    with SessionLocal() as db:
        exists = db.scalar(select(TrendingCategory.id).limit(1))
        if exists:
            return
        for index, (name, description) in enumerate(default_categories, start=1):
            db.add(TrendingCategory(name=name, description=description, sort_order=index))
        db.commit()
