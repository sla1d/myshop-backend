"""Tenant management service."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.license import License, Tenant, PLANS
from app.models.user import User

logger = logging.getLogger("myshop.tenants")


class TenantService:
    """Service for tenant CRUD and provisioning."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, tenant_id: int) -> Optional[Tenant]:
        result = await self.session.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        result = await self.session.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_domain(self, domain: str) -> Optional[Tenant]:
        result = await self.session.execute(
            select(Tenant).where(Tenant.domain == domain, Tenant.active == True)
        )
        return result.scalar_one_or_none()

    async def create_tenant(
        self,
        name: str,
        slug: str,
        domain: str,
        plan: str = "starter",
        admin_username: str = "admin",
        admin_password: str = "admin123",
        admin_email: str = "",
        theme: str = "midnight",
    ) -> dict:
        """Create a new tenant with admin user and license."""
        plan_config = PLANS.get(plan, PLANS["starter"])

        # Create tenant
        tenant = Tenant(
            name=name,
            slug=slug,
            domain=domain,
            plan=plan,
            subscription_status="active",
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=14),
            theme=theme,
            store_name=name,
        )
        self.session.add(tenant)
        await self.session.flush()

        # Create license
        license = License(
            tenant_id=tenant.id,
            key=f"{slug}-{tenant.id:06d}",
            plan=plan,
            expires_at=datetime.now(timezone.utc) + timedelta(days=14),
            max_products=plan_config["max_products"],
            max_orders=plan_config["max_orders"],
            max_images=plan_config["max_images"],
            max_admins=plan_config["max_admins"],
            active=True,
        )
        self.session.add(license)

        # Create admin user
        admin = User(
            username=admin_username,
            password=hash_password(admin_password),
            role="admin",
            email=admin_email or f"admin@{domain}",
            tenant_id=tenant.id,
        )
        self.session.add(admin)

        await self.session.commit()
        await self.session.refresh(tenant)

        logger.info("Tenant created: %s (slug=%s, plan=%s)", name, slug, plan)

        return {
            "tenant_id": tenant.id,
            "slug": tenant.slug,
            "domain": tenant.domain,
            "plan": plan,
            "admin_username": admin.username,
            "license_key": license.key,
            "expires_at": license.expires_at.isoformat(),
        }

    async def update_settings(
        self,
        tenant_id: int,
        theme: str | None = None,
        store_name: str | None = None,
        logo_url: str | None = None,
    ) -> Optional[Tenant]:
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        if theme is not None:
            tenant.theme = theme
        if store_name is not None:
            tenant.store_name = store_name
        if logo_url is not None:
            tenant.logo_url = logo_url

        await self.session.commit()
        await self.session.refresh(tenant)
        return tenant

    async def list_tenants(self, active_only: bool = True) -> list[Tenant]:
        stmt = select(Tenant)
        if active_only:
            stmt = stmt.where(Tenant.active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def deactivate(self, tenant_id: int) -> bool:
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return False
        tenant.active = False
        tenant.subscription_status = "cancelled"
        await self.session.commit()
        logger.info("Tenant deactivated: %s", tenant.slug)
        return True

    async def check_limits(self, tenant_id: int) -> dict:
        """Check current usage against plan limits."""
        from app.models.product import Product
        from app.models.order import Order

        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return {"error": "Tenant not found"}

        license_result = await self.session.execute(
            select(License).where(License.tenant_id == tenant_id)
        )
        license = license_result.scalar_one_or_none()

        product_count = (await self.session.execute(
            select(func.count(Product.id)).where(Product.tenant_id == tenant_id)
        )).scalar() or 0

        order_count = (await self.session.execute(
            select(func.count(Order.id)).where(Order.tenant_id == tenant_id)
        )).scalar() or 0

        return {
            "plan": tenant.plan,
            "products_used": product_count,
            "products_limit": license.max_products if license else 0,
            "orders_used": order_count,
            "orders_limit": license.max_orders if license else 0,
        }
