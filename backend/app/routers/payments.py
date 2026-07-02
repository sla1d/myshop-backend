"""Payment API — YooKassa integration for order payments."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.websocket import manager
from app.database.connection import get_async_session
from app.integrations.yookassa import yookassa
from app.models.order import Order
from app.models.user import User

logger = logging.getLogger("myshop.payments")

router = APIRouter(prefix="/payments", tags=["Платежи"])


class PaymentCreateRequest(BaseModel):
    order_id: int
    return_url: str = "https://myshop.com/payment/success"


class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    confirmation_url: str


class PaymentStatusResponse(BaseModel):
    order_id: int
    payment_id: str | None
    payment_status: str | None
    payment_method: str | None
    order_status: str


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    body: PaymentCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a YooKassa payment for an order. Returns redirect URL."""
    result = await session.execute(
        select(Order).where(Order.id == body.order_id, Order.user_id == user.id)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.payment_status == "succeeded":
        raise HTTPException(status_code=400, detail="Заказ уже оплачен")

    description = f"Заказ #{order.id} — MyShop"
    metadata = {"order_id": str(order.id), "user_id": str(user.id)}

    payment = await yookassa.create_payment(
        amount=order.total,
        description=description,
        return_url=body.return_url,
        metadata=metadata,
    )

    if not payment:
        raise HTTPException(status_code=502, detail="Не удалось создать платёж")

    # Save payment info to order
    order.payment_id = payment["id"]
    order.payment_status = payment.get("status", "pending")
    order.payment_method = payment.get("payment_method", {}).get("type")
    await session.commit()

    confirmation = payment.get("confirmation", {})
    confirmation_url = confirmation.get("confirmation_url", "")

    logger.info("Payment created for order #%s: %s", order.id, payment["id"])

    return PaymentResponse(
        payment_id=payment["id"],
        status=payment.get("status", "pending"),
        confirmation_url=confirmation_url,
    )


@router.get("/status/{order_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    order_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get payment status for an order."""
    result = await session.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user.id)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    return PaymentStatusResponse(
        order_id=order.id,
        payment_id=order.payment_id,
        payment_status=order.payment_status,
        payment_method=order.payment_method,
        order_status=order.status,
    )


@router.post("/webhook")
async def yookassa_webhook(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    """YooKassa webhook — receives payment status updates."""
    body = await request.json()
    event = body.get("event")
    payment_data = body.get("object", {})

    payment_id = payment_data.get("id")
    status = payment_data.get("status")
    metadata = payment_data.get("metadata", {})

    logger.info("YooKassa webhook: event=%s, payment=%s, status=%s", event, payment_id, status)

    if not payment_id:
        raise HTTPException(status_code=400, detail="Missing payment_id")

    # Find order by payment_id
    result = await session.execute(
        select(Order).where(Order.payment_id == payment_id)
    )
    order = result.scalars().first()
    if not order:
        logger.warning("Order not found for payment %s", payment_id)
        return {"status": "ok"}

    # Update order based on payment status
    if status == "succeeded":
        order.payment_status = "succeeded"
        order.status = "paid"
        logger.info("Order #%s marked as paid", order.id)

        # Notify user via WebSocket
        await manager.send(order.user_id, {
            "type": "payment_succeeded",
            "order_id": order.id,
            "total": order.total,
        })

    elif status == "canceled":
        order.payment_status = "canceled"
        order.status = "cancelled"
        logger.info("Order #%s payment canceled", order.id)

    elif status == "waiting_for_capture":
        order.payment_status = "waiting_for_capture"

    await session.commit()

    return {"status": "ok"}
