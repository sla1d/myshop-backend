from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.database.connection import get_async_session
from app.models.promo import PromoCode
from app.models.user import User
from app.schemas.promo import PromoApply, PromoResponse

router = APIRouter(prefix="/promos", tags=["Промокоды"])


@router.post("/validate", response_model=PromoResponse)
async def validate_promo(
    body: PromoApply,
    session: AsyncSession = Depends(get_async_session),
):
    """Проверить и применить промокод."""
    result = await session.execute(
        select(PromoCode).where(PromoCode.code == body.code.upper())
    )
    promo = result.scalar_one_or_none()

    if not promo:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    if not promo.active:
        raise HTTPException(status_code=400, detail="Промокод деактивирован")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if promo.valid_until.replace(tzinfo=None) < now:
        raise HTTPException(status_code=400, detail="Промокод истёк")
    if promo.max_uses > 0 and promo.used_count >= promo.max_uses:
        raise HTTPException(status_code=400, detail="Промокод использован максимальное количество раз")

    promo.used_count += 1
    await session.commit()

    return PromoResponse(
        code=promo.code,
        discount_percent=promo.discount_percent,
        message=f"Скидка {promo.discount_percent}% применена!",
    )
