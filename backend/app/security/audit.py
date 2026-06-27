"""Audit logging service — tracks all significant actions."""
import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.security.models import AuditLog, SecurityEvent

logger = logging.getLogger("myshop.audit")


class AuditService:
    """Service for audit logging."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        action: str,
        tenant_id: int | None = None,
        user_id: int | None = None,
        username: str | None = None,
        entity: str | None = None,
        entity_id: int | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Log an audit event."""
        log_entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=json.dumps(details, ensure_ascii=False, default=str) if details else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(log_entry)
        await self.session.flush()

        logger.info("AUDIT: %s by user=%s (tenant=%s)", action, username, tenant_id)
        return log_entry

    async def log_security_event(
        self,
        event_type: str,
        tenant_id: int | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
        details: str | None = None,
        severity: str = "info",
    ) -> SecurityEvent:
        """Log a security event."""
        event = SecurityEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            details=details,
            severity=severity,
        )
        self.session.add(event)
        await self.session.flush()

        if severity in ("warning", "critical"):
            logger.warning("SECURITY: %s (severity=%s, user=%s)", event_type, severity, user_id)
        else:
            logger.info("SECURITY: %s (user=%s)", event_type, user_id)

        return event


# Convenience functions
async def audit_product_delete(session: AsyncSession, tenant_id: int, user_id: int, username: str, product_id: int):
    audit = AuditService(session)
    await audit.log(
        action="product.delete",
        tenant_id=tenant_id,
        user_id=user_id,
        username=username,
        entity="product",
        entity_id=product_id,
    )


async def audit_price_change(session: AsyncSession, tenant_id: int, user_id: int, username: str, product_id: int, old_price: int, new_price: int):
    audit = AuditService(session)
    await audit.log(
        action="product.update_price",
        tenant_id=tenant_id,
        user_id=user_id,
        username=username,
        entity="product",
        entity_id=product_id,
        details={"old_price": old_price, "new_price": new_price},
    )


async def audit_role_change(session: AsyncSession, tenant_id: int, user_id: int, username: str, target_user_id: int, old_role: str, new_role: str):
    audit = AuditService(session)
    await audit.log(
        action="user.role_change",
        tenant_id=tenant_id,
        user_id=user_id,
        username=username,
        entity="user",
        entity_id=target_user_id,
        details={"old_role": old_role, "new_role": new_role},
    )


async def audit_subscription_change(session: AsyncSession, tenant_id: int, user_id: int, username: str, old_plan: str, new_plan: str):
    audit = AuditService(session)
    await audit.log(
        action="subscription.change",
        tenant_id=tenant_id,
        user_id=user_id,
        username=username,
        entity="subscription",
        details={"old_plan": old_plan, "new_plan": new_plan},
    )


async def audit_user_delete(session: AsyncSession, tenant_id: int, user_id: int, username: str, target_user_id: int):
    audit = AuditService(session)
    await audit.log(
        action="user.delete",
        tenant_id=tenant_id,
        user_id=user_id,
        username=username,
        entity="user",
        entity_id=target_user_id,
    )


async def audit_discount_create(session: AsyncSession, tenant_id: int, user_id: int, username: str, code: str, discount: int):
    audit = AuditService(session)
    await audit.log(
        action="promo.create",
        tenant_id=tenant_id,
        user_id=user_id,
        username=username,
        entity="promo",
        details={"code": code, "discount_percent": discount},
    )
