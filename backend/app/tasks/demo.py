"""Демо-режим: автоматический сброс данных каждые 24 часа."""
import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.database.connection import async_session_factory
from app.models.cart import Cart
from app.models.license import License, Tenant
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.promo import PromoCode
from app.models.review import Review
from app.models.user import User
from app.models.wishlist import Wishlist

logger = logging.getLogger("myshop.demo")


async def _reset_demo_data():
    """Сброс демо-данных к начальному состоянию."""
    async with async_session_factory() as session:
        # Удаляем заказы
        await session.execute(delete(OrderItem))
        await session.execute(delete(Order))

        # Удаляем корзины
        await session.execute(delete(Cart))

        # Удаляем отзывы
        await session.execute(delete(Review))

        # Удаляем избранное
        await session.execute(delete(Wishlist))

        # Удаляем тестовых пользователей (не admin)
        await session.execute(delete(User).where(User.username != "admin"))

        # Сбрасываем промокоды
        promos = await session.execute(select(PromoCode))
        for p in promos.scalars().all():
            p.used_count = 0
            p.active = True

        # Проверяем товары
        result = await session.execute(select(Product))
        if result.scalars().first() is None:
            # Если товаров нет — создаём заново
            products_data = [
                Product(name="Смартфон X", price=29999, image="https://picsum.photos/seed/smartphone/300/300", category="electronics", brand="TechCo", rating=4.5),
                Product(name="Ноутбук Pro", price=89999, image="https://picsum.photos/seed/laptop/300/300", category="electronics", brand="TechCo", rating=4.8),
                Product(name="Наушники Wireless", price=15999, image="https://picsum.photos/seed/headphones/300/300", category="electronics", brand="SoundMax", rating=4.3),
                Product(name="Монитор 4K", price=45999, image="https://picsum.photos/seed/monitor/300/300", category="electronics", brand="VisualPro", rating=4.6),
                Product(name="Клавиатура Mechanical", price=12999, image="https://picsum.photos/seed/keyboard/300/300", category="electronics", brand="KeyMaster", rating=4.4),
            ]
            session.add_all(products_data)

        await session.commit()
        logger.info("Demo data reset complete")


@shared_task(name="app.tasks.demo.reset_demo")
def reset_demo():
    """Задача: сброс демо-данных."""
    import asyncio
    asyncio.run(_reset_demo_data())
    return {"status": "reset_complete", "timestamp": datetime.now(timezone.utc).isoformat()}
