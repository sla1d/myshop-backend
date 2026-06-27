"""Billing API — subscription management."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_id_or_raise
from app.rbac.deps import RequirePermission
from app.billing.models import Invoice, Subscription
from app.billing.service import BillingService
from app.database.connection import get_async_session
from app.models.license import PLANS

router = APIRouter(prefix="/billing", tags=["Биллинг"])


class SubscriptionCreateRequest(BaseModel):
    plan: str
    billing_period: str = "monthly"


class PlanResponse(BaseModel):
    id: str
    name: str
    max_products: int
    max_orders: int
    max_images: int
    max_admins: int
    price_monthly: int
    price_yearly: int
    features: list[str]


class SubscriptionResponse(BaseModel):
    id: int
    plan: str
    status: str
    billing_period: str
    price: int
    expires_at: str
    auto_renew: bool


class InvoiceResponse(BaseModel):
    id: int
    amount: int
    currency: str
    status: str
    description: str | None
    created_at: str
    paid_at: str | None


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans():
    """List available subscription plans."""
    return [
        PlanResponse(
            id=key,
            name=val["name"],
            max_products=val["max_products"],
            max_orders=val["max_orders"],
            max_images=val["max_images"],
            max_admins=val["max_admins"],
            price_monthly=val["price_monthly"],
            price_yearly=val["price_yearly"],
            features=val["features"],
        )
        for key, val in PLANS.items()
    ]


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    tenant_id: int = Depends(get_tenant_id_or_raise),
    session: AsyncSession = Depends(get_async_session),
):
    """Get current active subscription."""
    service = BillingService(session)
    sub = await service.get_active_subscription(tenant_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Нет активной подписки")

    return SubscriptionResponse(
        id=sub.id,
        plan=sub.plan,
        status=sub.status,
        billing_period=sub.billing_period,
        price=sub.price,
        expires_at=sub.expires_at.isoformat(),
        auto_renew=sub.auto_renew,
    )


@router.post("/subscribe")
async def create_subscription(
    body: SubscriptionCreateRequest,
    tenant_id: int = Depends(get_tenant_id_or_raise),
    session: AsyncSession = Depends(get_async_session),
    _perm=Depends(RequirePermission("billing.manage")),
):
    """Create or change subscription."""
    if body.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {body.plan}")

    service = BillingService(session)
    result = await service.create_subscription(tenant_id, body.plan, body.billing_period)
    return result


@router.post("/cancel")
async def cancel_subscription(
    tenant_id: int = Depends(get_tenant_id_or_raise),
    session: AsyncSession = Depends(get_async_session),
    _perm=Depends(RequirePermission("billing.manage")),
):
    """Cancel active subscription."""
    service = BillingService(session)
    cancelled = await service.cancel_subscription(tenant_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Нет активной подписки")
    return {"status": "cancelled"}


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    tenant_id: int = Depends(get_tenant_id_or_raise),
    session: AsyncSession = Depends(get_async_session),
    _perm=Depends(RequirePermission("billing.view")),
):
    """List invoices for tenant."""
    service = BillingService(session)
    invoices = await service.get_invoices(tenant_id)
    return [
        InvoiceResponse(
            id=inv.id,
            amount=inv.amount,
            currency=inv.currency,
            status=inv.status,
            description=inv.description,
            created_at=inv.created_at.isoformat(),
            paid_at=inv.paid_at.isoformat() if inv.paid_at else None,
        )
        for inv in invoices
    ]
