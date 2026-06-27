"""Публичные эндпоинты для баннеров и уведомлений."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_session
from app.models.ad_banner import AdBanner, WishlistPrice
from app.models.product import Product
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter(tags=["Публичные"])
logger = logging.getLogger(__name__)


@router.get("/api/banners/active")
async def get_active_banners(session: AsyncSession = Depends(get_async_session)):
    """Получить активные баннеры для главной."""
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(AdBanner)
        .where(AdBanner.active == True)
        .order_by(AdBanner.position)
    )
    banners = result.scalars().all()
    active = []
    for b in banners:
        if b.start_at and b.start_at > now:
            continue
        if b.end_at and b.end_at < now:
            continue
        active.append({
            "id": b.id,
            "title": b.title,
            "image_url": b.image_url,
            "link_url": b.link_url,
        })
    return active


@router.get("/api/wishlist/alerts")
async def get_wishlist_alerts(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Проверить тревоги wishlist: подорожание / мало остатков."""
    from app.models.wishlist import Wishlist

    wl_result = await session.execute(
        select(Wishlist).where(Wishlist.user_id == user.id)
    )
    wl_items = wl_result.scalars().all()
    alerts = []

    for wl in wl_items:
        prod = await session.get(Product, wl.product_id)
        if not prod:
            continue

        wp_result = await session.execute(
            select(WishlistPrice).where(
                WishlistPrice.user_id == user.id,
                WishlistPrice.product_id == wl.product_id,
            )
        )
        wp = wp_result.scalar_one_or_none()

        if wp:
            if prod.price > wp.price_at_add:
                alerts.append({
                    "product_id": prod.id,
                    "product_name": prod.name,
                    "type": "price_increase",
                    "old_price": wp.price_at_add,
                    "new_price": prod.price,
                    "message": f"Цена выросла: {wp.price_at_add} → {prod.price} ₽",
                })
            elif prod.price < wp.price_at_add:
                alerts.append({
                    "product_id": prod.id,
                    "product_name": prod.name,
                    "type": "price_drop",
                    "old_price": wp.price_at_add,
                    "new_price": prod.price,
                    "message": f"Цена снизилась: {wp.price_at_add} → {prod.price} ₽",
                })

            if prod.stock_quantity <= 3 and not wp.notified_low_stock:
                alerts.append({
                    "product_id": prod.id,
                    "product_name": prod.name,
                    "type": "low_stock",
                    "stock": prod.stock_quantity,
                    "message": f"Осталось всего {prod.stock_quantity} шт!",
                })
        else:
            session.add(WishlistPrice(
                user_id=user.id,
                product_id=wl.product_id,
                price_at_add=prod.price,
            ))

    await session.commit()
    return alerts
