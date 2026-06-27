"""Integration API — Telegram, YooKassa, CDEK management."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.integrations.cdek import cdek
from app.integrations.telegram import telegram
from app.integrations.yookassa import yookassa
from app.rbac.deps import RequirePermission

router = APIRouter(prefix="/integrations", tags=["Интеграции"])


class TelegramTestRequest(BaseModel):
    chat_id: int | str
    message: str = "Test notification from MyShop"


class PaymentCreateRequest(BaseModel):
    amount: int
    description: str = ""
    return_url: str = ""


class DeliveryCalcRequest(BaseModel):
    from_city_code: int = 44
    to_city_code: int = 78
    weight: int = 500


# ─── Telegram ─────────────────────────────────────
@router.post("/telegram/test")
async def test_telegram(
    body: TelegramTestRequest,
    _perm=Depends(RequirePermission("telegram.send")),
):
    """Send a test Telegram message."""
    result = await telegram.send_message(body.chat_id, body.message)
    if result is None:
        raise HTTPException(500, "Telegram not configured or unreachable")
    return {"status": "ok", "result": result}


# ─── YooKassa ─────────────────────────────────────
@router.post("/payments/create")
async def create_payment(
    body: PaymentCreateRequest,
    _perm=Depends(RequirePermission("payment.process")),
):
    """Create a YooKassa payment."""
    result = await yookassa.create_payment(
        amount=body.amount,
        description=body.description,
        return_url=body.return_url,
    )
    if result is None:
        raise HTTPException(500, "Payment creation failed")
    return result


@router.get("/payments/{payment_id}")
async def get_payment_status(
    payment_id: str,
    _perm=Depends(RequirePermission("payment.view")),
):
    """Get payment status from YooKassa."""
    result = await yookassa.get_payment(payment_id)
    if result is None:
        raise HTTPException(404, "Payment not found")
    return result


# ─── CDEK ──────────────────────────────────────────
@router.post("/delivery/calculate")
async def calculate_delivery(
    body: DeliveryCalcRequest,
    _perm=Depends(RequirePermission("delivery.calculate")),
):
    """Calculate CDEK delivery cost and time."""
    result = await cdek.calculate_delivery(
        from_city_code=body.from_city_code,
        to_city_code=body.to_city_code,
        weight=body.weight,
    )
    if result is None:
        raise HTTPException(500, "Delivery calculation failed")
    return result


@router.get("/delivery/tracking/{cdek_number}")
async def track_delivery(
    cdek_number: str,
    _perm=Depends(RequirePermission("delivery.tracking")),
):
    """Track CDEK delivery by number."""
    result = await cdek.get_tracking(cdek_number)
    if result is None:
        raise HTTPException(404, "Tracking not found")
    return result


@router.get("/delivery/cities")
async def search_cities(
    query: str = "",
    _perm=Depends(get_current_user),
):
    """Search CDEK cities."""
    result = await cdek.get_cities(query)
    return result or []
