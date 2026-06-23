import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.rabbitmq import publish
from app.database.connection import get_async_session
from app.models.user import User
from app.schemas.order import OrderResponse
from app.services.order import OrderService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Заказы"])


class OrderRequest(BaseModel):
    address: str
    promo_code: str | None = None


@router.post("/order", response_model=OrderResponse)
async def create_order(
    body: OrderRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Создать заказ из корзины с опциональным промокодом."""
    order_service = OrderService(session)
    try:
        result = await order_service.create(user.id, body.address, body.promo_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Публикация в RabbitMQ
    publish("order.created", {
        "order_id": result["order_id"],
        "user_id": user.id,
        "email": user.email or user.username,
        "total": result["total"],
        "address": body.address,
    })

    # Фоновая задача (Celery)
    try:
        from app.tasks import send_order_notification
        send_order_notification.delay(
            order_id=result["order_id"],
            user_email=user.email or user.username,
            total=result["total"],
        )
    except Exception:
        logger.warning("Не удалось запустить задачу уведомления")

    logger.info("Заказ #%s создан: user=%d, total=%s ₽", result["order_id"], user.id, result["total"])
    return OrderResponse(status="ok", order_id=result["order_id"], total=result["total"])
