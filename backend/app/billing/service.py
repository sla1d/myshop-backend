"""Billing service — subscription management, invoices, payments."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.models import Invoice, Payment, Subscription
from app.models.license import Tenant, PLANS

logger = logging.getLogger("myshop.billing")


class BillingService:
    """Service for subscription and billing management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_subscription(self, tenant_id: int) -> Optional[Subscription]:
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.tenant_id == tenant_id,
                Subscription.status == "active",
            ).order_by(Subscription.created_at.desc())
        )
        return result.scalars().first()

    async def create_subscription(
        self,
        tenant_id: int,
        plan: str,
        billing_period: str = "monthly",
    ) -> dict:
        """Create a new subscription for a tenant."""
        plan_config = PLANS.get(plan, PLANS["starter"])

        if billing_period == "yearly":
            price = plan_config["price_yearly"]
            days = 365
        else:
            price = plan_config["price_monthly"]
            days = 30

        # Cancel existing active subscription
        existing = await self.get_active_subscription(tenant_id)
        if existing:
            existing.status = "cancelled"
            await self.session.flush()

        # Create subscription
        now = datetime.now(timezone.utc)
        subscription = Subscription(
            tenant_id=tenant_id,
            plan=plan,
            status="active",
            billing_period=billing_period,
            price=price,
            starts_at=now,
            expires_at=now + timedelta(days=days),
            auto_renew=True,
        )
        self.session.add(subscription)
        await self.session.flush()

        # Update tenant plan
        tenant = await self.session.get(Tenant, tenant_id)
        if tenant:
            tenant.plan = plan
            tenant.subscription_status = "active"
            tenant.subscription_expires_at = subscription.expires_at

        # Create invoice
        invoice = Invoice(
            tenant_id=tenant_id,
            subscription_id=subscription.id,
            amount=price,
            currency="RUB",
            status="pending",
            description=f"Подписка {plan_config['name']} ({billing_period})",
            due_at=now + timedelta(days=7),
        )
        self.session.add(invoice)
        await self.session.commit()
        await self.session.refresh(subscription)

        logger.info("Subscription created: tenant=%d, plan=%s, price=%d", tenant_id, plan, price)

        return {
            "subscription_id": subscription.id,
            "plan": plan,
            "price": price,
            "billing_period": billing_period,
            "expires_at": subscription.expires_at.isoformat(),
            "invoice_id": invoice.id,
        }

    async def cancel_subscription(self, tenant_id: int) -> bool:
        subscription = await self.get_active_subscription(tenant_id)
        if not subscription:
            return False

        subscription.status = "cancelled"
        subscription.auto_renew = False

        tenant = await self.session.get(Tenant, tenant_id)
        if tenant:
            tenant.subscription_status = "cancelled"

        await self.session.commit()
        logger.info("Subscription cancelled: tenant=%d", tenant_id)
        return True

    async def process_payment(
        self,
        invoice_id: int,
        amount: int,
        method: str = "card",
        provider: str = "",
        provider_payment_id: str = "",
    ) -> Optional[Payment]:
        """Record a payment for an invoice."""
        invoice = await self.session.get(Invoice, invoice_id)
        if not invoice:
            return None

        payment = Payment(
            tenant_id=invoice.tenant_id,
            invoice_id=invoice.id,
            amount=amount,
            currency=invoice.currency,
            method=method,
            provider=provider,
            provider_payment_id=provider_payment_id,
            status="completed",
        )
        self.session.add(payment)

        invoice.status = "paid"
        invoice.paid_at = datetime.now(timezone.utc)

        # Activate subscription if it was pending
        subscription = await self.session.get(Subscription, invoice.subscription_id)
        if subscription and subscription.status == "pending":
            subscription.status = "active"

        # Update tenant
        tenant = await self.session.get(Tenant, invoice.tenant_id)
        if tenant:
            tenant.subscription_status = "active"

        await self.session.commit()
        await self.session.refresh(payment)

        logger.info("Payment processed: invoice=%d, amount=%d", invoice_id, amount)
        return payment

    async def get_invoices(self, tenant_id: int, limit: int = 20) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice).where(Invoice.tenant_id == tenant_id)
            .order_by(Invoice.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def check_expired_subscriptions(self) -> int:
        """Mark expired subscriptions. Returns count of expired."""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.status == "active",
                Subscription.expires_at < now,
            )
        )
        expired = result.scalars().all()
        count = 0
        for sub in expired:
            sub.status = "expired"
            tenant = await self.session.get(Tenant, sub.tenant_id)
            if tenant:
                tenant.subscription_status = "expired"
            count += 1

        if count:
            await self.session.commit()
            logger.info("Expired %d subscriptions", count)
        return count
