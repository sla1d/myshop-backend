import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.user import User

router = APIRouter(prefix="/referral", tags=["Рефералы"])
logger = logging.getLogger(__name__)


class ReferralStats(BaseModel):
    referral_code: str
    referral_link: str
    total_referrals: int
    referral_earnings: int


class ReferralRedeem(BaseModel):
    code: str


class ReferralResponse(BaseModel):
    message: str
    bonus: int = 0


REFERRAL_BONUS = 500  # бонус за приглашение (₽)


def generate_referral_code() -> str:
    return secrets.token_urlsafe(8).upper()


@router.get("/stats", response_model=ReferralStats)
async def get_referral_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить статистику реферальной программы."""
    if not user.referral_code:
        user.referral_code = generate_referral_code()
        await session.commit()

    result = await session.execute(
        select(User).where(User.referred_by == user.id)
    )
    referral_count = len(result.scalars().all())

    return ReferralStats(
        referral_code=user.referral_code,
        referral_link=f"/?ref={user.referral_code}",
        total_referrals=referral_count,
        referral_earnings=user.referral_earnings,
    )


@router.post("/redeem", response_model=ReferralResponse)
async def redeem_referral(
    body: ReferralRedeem,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Активировать реферальный код другого пользователя."""
    if user.referred_by:
        raise HTTPException(status_code=400, detail="Вы уже использовали реферальный код")

    code = body.code.strip().upper()
    result = await session.execute(
        select(User).where(User.referral_code == code)
    )
    referrer = result.scalar_one_or_none()

    if not referrer:
        raise HTTPException(status_code=404, detail="Реферальный код не найден")
    if referrer.id == user.id:
        raise HTTPException(status_code=400, detail="Нельзя использовать свой код")

    user.referred_by = referrer.id
    referrer.referral_earnings += REFERRAL_BONUS
    referrer.loyalty_points += REFERRAL_BONUS

    # Обновляем уровень лояльности реферера
    from app.routers.loyalty import calculate_level
    referrer.loyalty_level = calculate_level(referrer.loyalty_points)

    await session.commit()

    logger.info("Referral redeemed: %s invited by %s", user.username, referrer.username)
    return ReferralResponse(message=f"Бонус {REFERRAL_BONUS} ₽ начислен пригласившему!", bonus=REFERRAL_BONUS)
