import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.order import Order, OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.models.user import User

router = APIRouter(prefix="/tracking", tags=["Трекинг"])
logger = logging.getLogger(__name__)


class TrackingStatus(BaseModel):
    status: str
    comment: str | None = None


class StatusHistoryItem(BaseModel):
    status: str
    comment: str | None = None
    created_at: str


class OrderTracking(BaseModel):
    order_id: int
    status: str
    tracking_number: str | None = None
    history: list[StatusHistoryItem]


@router.get("/{order_id}", response_model=OrderTracking)
async def get_order_tracking(
    order_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить трекинг заказа (историю статусов)."""
    result = await session.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    history_result = await session.execute(
        select(OrderStatusHistory)
        .where(OrderStatusHistory.order_id == order_id)
        .order_by(OrderStatusHistory.created_at)
    )
    history = history_result.scalars().all()

    return OrderTracking(
        order_id=order.id,
        status=order.status,
        tracking_number=order.tracking_number,
        history=[
            StatusHistoryItem(
                status=h.status,
                comment=h.comment,
                created_at=h.created_at.isoformat(),
            )
            for h in history
        ],
    )
