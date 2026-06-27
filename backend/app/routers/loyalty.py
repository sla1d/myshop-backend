from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.user import User

router = APIRouter(prefix="/loyalty", tags=["Лояльность"])


LEVELS = {
    "bronze": {"min": 0, "cashback_percent": 1, "label": "Бронза"},
    "silver": {"min": 5000, "cashback_percent": 3, "label": "Серебро"},
    "gold": {"min": 20000, "cashback_percent": 5, "label": "Золото"},
    "platinum": {"min": 50000, "cashback_percent": 8, "label": "Платина"},
}


def calculate_level(points: int) -> str:
    level = "bronze"
    for name, cfg in LEVELS.items():
        if points >= cfg["min"]:
            level = name
    return level


def get_cashback_percent(level: str) -> int:
    return LEVELS.get(level, LEVELS["bronze"])["cashback_percent"]


class LoyaltyStats(BaseModel):
    points: int
    level: str
    level_label: str
    cashback_percent: int
    next_level: str | None = None
    points_to_next: int = 0


@router.get("/stats", response_model=LoyaltyStats)
async def get_loyalty_stats(
    user: User = Depends(get_current_user),
):
    """Получить статистику лояльности."""
    level_cfg = LEVELS[user.loyalty_level]
    next_level = None
    points_to_next = 0

    level_names = list(LEVELS.keys())
    idx = level_names.index(user.loyalty_level) if user.loyalty_level in level_names else 0
    if idx < len(level_names) - 1:
        next_level_name = level_names[idx + 1]
        next_level = LEVELS[next_level_name]["label"]
        points_to_next = LEVELS[next_level_name]["min"] - user.loyalty_points

    return LoyaltyStats(
        points=user.loyalty_points,
        level=user.loyalty_level,
        level_label=level_cfg["label"],
        cashback_percent=level_cfg["cashback_percent"],
        next_level=next_level,
        points_to_next=max(0, points_to_next),
    )
