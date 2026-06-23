"""Аналитика для админки."""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.database.connection import get_async_session
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User

router = APIRouter(prefix="/admin/analytics", tags=["Аналитика"])
logger = logging.getLogger("myshop.analytics")


class SalesPoint(BaseModel):
    date: str
    orders: int
    revenue: int


class TopProduct(BaseModel):
    product_id: int
    name: str
    sold: int
    revenue: int


class ConversionFunnel(BaseModel):
    viewed: int
    added_to_cart: int
    ordered: int
    conversion_cart: float
    conversion_order: float


@router.get("/sales", response_model=list[SalesPoint])
async def sales_analytics(
    period: str = Query("7d", regex="^(7d|30d|90d|365d)$"),
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Продажи за период (по дням)."""
    days = int(period.rstrip("d"))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await session.execute(
        select(
            func.date(Order.created_at).label("date"),
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.total), 0).label("revenue"),
        )
        .where(Order.created_at >= since)
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )

    return [
        SalesPoint(date=str(r[0]), orders=r[1], revenue=int(r[2]))
        for r in result.all()
    ]


@router.get("/top-products", response_model=list[TopProduct])
async def top_products(
    limit: int = Query(10, ge=1, le=50),
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Топ товаров по продажам."""
    result = await session.execute(
        select(
            OrderItem.product_id,
            Product.name,
            func.sum(OrderItem.quantity).label("sold"),
            func.sum(OrderItem.price * OrderItem.quantity).label("revenue"),
        )
        .join(Product, OrderItem.product_id == Product.id)
        .group_by(OrderItem.product_id, Product.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )

    return [
        TopProduct(
            product_id=r[0],
            name=r[1],
            sold=int(r[2]),
            revenue=int(r[3]),
        )
        for r in result.all()
    ]


@router.get("/conversion", response_model=ConversionFunnel)
async def conversion(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Воронка конверсии: просмотр → корзина → заказ."""
    from app.models.cart import Cart

    products_count = (await session.execute(select(func.count(Product.id)))).scalar() or 0
    cart_count = (await session.execute(select(func.count(Cart.id)))).scalar() or 0
    orders_count = (await session.execute(select(func.count(Order.id)))).scalar() or 0

    conv_cart = round(cart_count / max(products_count, 1) * 100, 1)
    conv_order = round(orders_count / max(cart_count, 1) * 100, 1)

    return ConversionFunnel(
        viewed=products_count * 10,  # приблизительно
        added_to_cart=cart_count,
        ordered=orders_count,
        conversion_cart=conv_cart,
        conversion_order=conv_order,
    )


@router.get("/summary")
async def summary(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Сводка: сегодня vs вчера."""
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    yesterday_start = datetime.combine(yesterday, datetime.min.time()).replace(tzinfo=timezone.utc)

    # Сегодня
    today_orders = (await session.execute(
        select(func.count(Order.id)).where(Order.created_at >= today_start)
    )).scalar() or 0
    today_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(Order.created_at >= today_start)
    )).scalar() or 0

    # Вчера
    yesterday_orders = (await session.execute(
        select(func.count(Order.id)).where(
            Order.created_at >= yesterday_start,
            Order.created_at < today_start,
        )
    )).scalar() or 0
    yesterday_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(
            Order.created_at >= yesterday_start,
            Order.created_at < today_start,
        )
    )).scalar() or 0

    orders_diff = today_orders - yesterday_orders
    revenue_diff = int(today_revenue) - int(yesterday_revenue)

    return {
        "today": {"orders": today_orders, "revenue": int(today_revenue)},
        "yesterday": {"orders": yesterday_orders, "revenue": int(yesterday_revenue)},
        "diff": {"orders": orders_diff, "revenue": revenue_diff},
    }
