"""Аналитика для админки."""
import logging
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_id_from_request
from app.database.connection import get_async_session
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.rbac.deps import RequirePermission

router = APIRouter(prefix="/admin/analytics", tags=["Аналитика"])
logger = logging.getLogger("myshop.analytics")

# База координат российских городов
CITY_COORDS = {
    "москва": (55.7558, 37.6173),
    "санкт-петербург": (59.9343, 30.3351),
    "петербург": (59.9343, 30.3351),
    "спб": (59.9343, 30.3351),
    "новосибирск": (55.0084, 82.9357),
    "екатеринбург": (56.8389, 60.6057),
    "казань": (55.7879, 49.1233),
    "нижний новгород": (56.2965, 43.9361),
    "челябинск": (55.1644, 61.4368),
    "самара": (53.1959, 50.1002),
    "омск": (54.9885, 73.3242),
    "ростов-на-дону": (47.2357, 39.7015),
    "ростов": (47.2357, 39.7015),
    "уфа": (54.7388, 55.9721),
    "красноярск": (56.0153, 92.8932),
    "воронеж": (51.6683, 39.1843),
    "пермь": (58.0105, 56.2502),
    "волгоград": (48.708, 44.5133),
    "саратов": (51.5336, 46.0342),
    "тюмень": (57.1522, 65.5272),
    "тольятти": (53.5078, 49.4204),
    "ижевск": (56.8527, 53.2114),
    "барнаул": (53.3548, 83.7696),
    "иркутск": (52.2855, 104.2890),
    "хабаровск": (48.4827, 135.0837),
    "ярославль": (57.6261, 39.8845),
    "владивосток": (43.1332, 131.9113),
    "махачкала": (42.9849, 47.5047),
    "томск": (56.4977, 84.9744),
    "оренбург": (51.7681, 55.0968),
    "кемерово": (55.3333, 86.0833),
    "новокузнецк": (53.7575, 87.1150),
    "рязань": (54.6269, 39.6916),
    "калининград": (54.7104, 20.4522),
    "минск": (53.9, 27.5667),
    "алматы": (43.2380, 76.9455),
    "нур-султан": (51.1282, 71.4304),
    "ташкент": (41.2995, 69.2401),
    "кишинев": (47.0056, 28.8638),
    "баку": (40.4093, 49.8671),
    "тбилиси": (41.7151, 44.8271),
    "евпатория": (45.1906, 33.3775),
    "севастополь": (44.6054, 33.5220),
    "крым": (45.3, 34.0),
}


def parse_address_coords(address: str) -> tuple[float, float] | None:
    """Попытка извлечь координаты из адреса по названию города."""
    addr_lower = address.lower()
    for city, coords in CITY_COORDS.items():
        if city in addr_lower:
            # Добавляем небольшой рандом для разброса маркеров
            import random
            lat = coords[0] + random.uniform(-0.05, 0.05)
            lng = coords[1] + random.uniform(-0.05, 0.05)
            return (lat, lng)
    return None


class SalesPoint(BaseModel):
    date: str
    orders: int
    revenue: int


class TopProduct(BaseModel):
    product_id: int
    name: str
    sold: int
    revenue: int


class FunnelStage(BaseModel):
    name: str
    count: int
    conversion_from_prev: float


class FunnelData(BaseModel):
    stages: list[FunnelStage]
    overall_conversion: float


class PeriodComparison(BaseModel):
    current: dict
    previous: dict
    diff_orders: int
    diff_revenue: int
    diff_orders_pct: float
    diff_revenue_pct: float


class BuyerLevel(BaseModel):
    level: str
    min_orders: int
    min_spent: int
    discount_percent: int
    label: str


BUYER_LEVELS = [
    BuyerLevel(level="new", min_orders=0, min_spent=0, discount_percent=0, label="Новичок"),
    BuyerLevel(level="regular", min_orders=3, min_spent=10000, discount_percent=2, label="Постоянный"),
    BuyerLevel(level="vip", min_orders=10, min_spent=50000, discount_percent=5, label="VIP"),
    BuyerLevel(level="premium", min_orders=25, min_spent=150000, discount_percent=10, label="Премиум"),
]


def get_buyer_level(orders_count: int, total_spent: int) -> BuyerLevel:
    result = BUYER_LEVELS[0]
    for level in BUYER_LEVELS:
        if orders_count >= level.min_orders and total_spent >= level.min_spent:
            result = level
    return result


@router.get("/sales", response_model=list[SalesPoint])
async def sales_analytics(
    period: str = Query("7d", pattern="^(7d|30d|90d|365d)$"),
    user: User = Depends(RequirePermission("analytics.view")),
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
    user: User = Depends(RequirePermission("analytics.view")),
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


@router.get("/funnel", response_model=FunnelData)
async def conversion_funnel(
    user: User = Depends(RequirePermission("analytics.view")),
    session: AsyncSession = Depends(get_async_session),
):
    """Воронка: просмотр → каталог → товар → корзина → заказ."""
    from app.models.cart import Cart
    from app.models.wishlist import Wishlist

    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    catalog_visitors = total_users * 12  # приблизительно
    product_views = (await session.execute(select(func.count(OrderItem.id)))).scalar() or 0
    product_views = max(product_views * 3, catalog_visitors // 3)
    cart_items = (await session.execute(select(func.count(Cart.id)))).scalar() or 0
    wishlist_items = (await session.execute(select(func.count(Wishlist.id)))).scalar() or 0
    orders_count = (await session.execute(select(func.count(Order.id)))).scalar() or 0
    completed_orders = (await session.execute(
        select(func.count(Order.id)).where(Order.status.in_(["delivered", "shipped"]))
    )).scalar() or 0

    stages = [
        FunnelStage(name="Пользователи", count=total_users, conversion_from_prev=100.0),
        FunnelStage(name="Каталог", count=catalog_visitors, conversion_from_prev=round(catalog_visitors / max(total_users, 1) * 100, 1)),
        FunnelStage(name="Просмотр товара", count=product_views, conversion_from_prev=round(product_views / max(catalog_visitors, 1) * 100, 1)),
        FunnelStage(name="В корзину", count=cart_items, conversion_from_prev=round(cart_items / max(product_views, 1) * 100, 1)),
        FunnelStage(name="В избранное", count=wishlist_items, conversion_from_prev=round(wishlist_items / max(product_views, 1) * 100, 1)),
        FunnelStage(name="Заказ оформлен", count=orders_count, conversion_from_prev=round(orders_count / max(cart_items, 1) * 100, 1)),
        FunnelStage(name="Заказ доставлен", count=completed_orders, conversion_from_prev=round(completed_orders / max(orders_count, 1) * 100, 1)),
    ]

    overall = round(completed_orders / max(total_users, 1) * 100, 2)
    return FunnelData(stages=stages, overall_conversion=overall)


@router.get("/period-comparison", response_model=PeriodComparison)
async def period_comparison(
    user: User = Depends(RequirePermission("analytics.view")),
    session: AsyncSession = Depends(get_async_session),
):
    """Сравнение: эта неделя vs прошлая."""
    now = datetime.now(timezone.utc)
    this_week_start = now - timedelta(days=now.weekday())
    last_week_start = this_week_start - timedelta(days=7)

    # Эта неделя
    curr_orders = (await session.execute(
        select(func.count(Order.id)).where(Order.created_at >= this_week_start)
    )).scalar() or 0
    curr_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(Order.created_at >= this_week_start)
    )).scalar() or 0

    # Прошлая неделя
    prev_orders = (await session.execute(
        select(func.count(Order.id)).where(
            Order.created_at >= last_week_start,
            Order.created_at < this_week_start,
        )
    )).scalar() or 0
    prev_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(
            Order.created_at >= last_week_start,
            Order.created_at < this_week_start,
        )
    )).scalar() or 0

    diff_orders = curr_orders - prev_orders
    diff_revenue = int(curr_revenue) - int(prev_revenue)
    diff_orders_pct = round(diff_orders / max(prev_orders, 1) * 100, 1)
    diff_revenue_pct = round(diff_revenue / max(int(prev_revenue), 1) * 100, 1)

    return PeriodComparison(
        current={"orders": curr_orders, "revenue": int(curr_revenue)},
        previous={"orders": prev_orders, "revenue": int(prev_revenue)},
        diff_orders=diff_orders,
        diff_revenue=diff_revenue,
        diff_orders_pct=diff_orders_pct,
        diff_revenue_pct=diff_revenue_pct,
    )


@router.get("/buyer-levels")
async def get_buyer_levels(
    user: User = Depends(RequirePermission("analytics.view")),
    session: AsyncSession = Depends(get_async_session),
):
    """Уровни покупателей."""
    result = await session.execute(
        select(
            User.id,
            User.username,
            func.count(Order.id).label("orders_count"),
            func.coalesce(func.sum(Order.total), 0).label("total_spent"),
        )
        .outerjoin(Order, Order.user_id == User.id)
        .group_by(User.id, User.username)
    )

    buyers = []
    for r in result.all():
        level = get_buyer_level(r[2], int(r[3]))
        buyers.append({
            "user_id": r[0],
            "username": r[1],
            "orders_count": r[2],
            "total_spent": int(r[3]),
            "level": level.level,
            "level_label": level.label,
            "discount_percent": level.discount_percent,
        })
    return buyers


@router.get("/summary")
async def summary(
    user: User = Depends(RequirePermission("analytics.view")),
    session: AsyncSession = Depends(get_async_session),
):
    """Сводка: сегодня vs вчера."""
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    yesterday_start = datetime.combine(yesterday, datetime.min.time()).replace(tzinfo=timezone.utc)

    today_orders = (await session.execute(
        select(func.count(Order.id)).where(Order.created_at >= today_start)
    )).scalar() or 0
    today_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(Order.created_at >= today_start)
    )).scalar() or 0

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

    return {
        "today": {"orders": today_orders, "revenue": int(today_revenue)},
        "yesterday": {"orders": yesterday_orders, "revenue": int(yesterday_revenue)},
        "diff": {"orders": today_orders - yesterday_orders, "revenue": int(today_revenue) - int(yesterday_revenue)},
    }


class MapPoint(BaseModel):
    lat: float
    lng: float
    city: str
    orders: int
    revenue: int


@router.get("/map", response_model=list[MapPoint])
async def orders_map(
    user: User = Depends(RequirePermission("analytics.view")),
    session: AsyncSession = Depends(get_async_session),
):
    """Карта заказов — группы по городам."""
    result = await session.execute(
        select(Order.address, func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .group_by(Order.address)
    )

    city_data: dict[str, dict] = {}
    for address, count, revenue in result.all():
        coords = parse_address_coords(address)
        if coords:
            # Определяем город из адреса
            addr_lower = address.lower()
            city = "Другой"
            for city_name in CITY_COORDS:
                if city_name in addr_lower:
                    city = city_name.title()
                    break
            key = city
            if key not in city_data:
                city_data[key] = {"lat": coords[0], "lng": coords[1], "city": city, "orders": 0, "revenue": 0}
            city_data[key]["orders"] += count
            city_data[key]["revenue"] += int(revenue)

    return [
        MapPoint(lat=d["lat"], lng=d["lng"], city=d["city"], orders=d["orders"], revenue=d["revenue"])
        for d in city_data.values()
    ]
