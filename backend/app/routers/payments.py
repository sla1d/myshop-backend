"""Payment API — YooKassa integration for order payments."""
import ipaddress
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.websocket import manager
from app.database.connection import get_async_session
from app.integrations.yookassa import yookassa
from app.models.user import User
from app.repositories.order_repo import OrderRepository

logger = logging.getLogger("myshop.payments")

router = APIRouter(prefix="/payments", tags=["Платежи"])

# YooKassa official subnets (https://yookassa.ru/developers/api#ip-whitelist)
YOOKASSA_IPS = [
    ipaddress.ip_network("185.71.76.0/27"),
    ipaddress.ip_network("185.71.77.0/27"),
    ipaddress.ip_network("77.75.153.0/25"),
    ipaddress.ip_network("77.75.154.128/25"),
    ipaddress.ip_address("77.75.156.11"),
    ipaddress.ip_address("77.75.156.35"),
]


async def verify_yookassa_ip(request: Request):
    """Dependency — validates that webhook originates from YooKassa."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip_str = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host

    try:
        client_ip = ipaddress.ip_address(client_ip_str)
    except ValueError:
        logger.warning("YooKassa webhook: invalid IP format: %s", client_ip_str)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid IP")

    is_valid = any(
        client_ip in net if isinstance(net, ipaddress.IPv4Network) else client_ip == net
        for net in YOOKASSA_IPS
    )

    if not is_valid:
        logger.warning("YooKassa webhook: untrusted IP: %s", client_ip_str)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Untrusted IP")


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
    repo = OrderRepository(session)

    order = await repo.get_by_id(body.order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.payment_status == "succeeded":
        raise HTTPException(status_code=400, detail="Заказ уже оплачен")

    idempotency_key = f"order-{order.id}-pay"
    description = f"Заказ #{order.id} — MyShop"
    metadata = {"order_id": str(order.id), "user_id": str(user.id)}

    payment = await yookassa.create_payment(
        amount=order.total,
        description=description,
        return_url=body.return_url,
        metadata=metadata,
        idempotency_key=idempotency_key,
    )

    if not payment:
        raise HTTPException(status_code=502, detail="Не удалось создать платёж")

    order.payment_id = payment["id"]
    order.payment_status = payment.get("status", "pending")
    order.payment_method = payment.get("payment_method", {}).get("type")
    await session.commit()

    confirmation_url = payment.get("confirmation", {}).get("confirmation_url", "")
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
    repo = OrderRepository(session)

    order = await repo.get_by_id(order_id)
    if not order or order.user_id != user.id:
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
    _ip_check=Depends(verify_yookassa_ip),
):
    """YooKassa webhook — receives payment status updates securely."""
    body = await request.json()
    event = body.get("event")
    payment_data = body.get("object", {})

    payment_id = payment_data.get("id")
    new_status = payment_data.get("status")

    logger.info("YooKassa webhook: event=%s, payment=%s, status=%s", event, payment_id, new_status)

    if not payment_id:
        raise HTTPException(status_code=400, detail="Missing payment_id")

    repo = OrderRepository(session)
    order = await repo.get_by_payment_id(payment_id)

    if not order:
        logger.warning("Order not found for payment %s", payment_id)
        return {"status": "ok"}

    # Idempotency: skip if already processed
    if order.payment_status == "succeeded":
        return {"status": "already_processed"}

    if new_status == "succeeded":
        await repo.mark_paid(order, payment_id, order.payment_method)
        logger.info("Order #%s marked as paid", order.id)

        await manager.send(order.user_id, {
            "type": "payment_succeeded",
            "order_id": order.id,
            "total": order.total,
        })

    elif new_status == "canceled":
        await repo.mark_canceled(order)
        logger.info("Order #%s payment canceled", order.id)

    elif new_status == "waiting_for_capture":
        await repo.update_payment_status(order, "waiting_for_capture")

    return {"status": "ok"}
