"""Multi-tenant context management.

Provides middleware and dependency injection for tenant isolation.
Every request is scoped to a single tenant via:
  1. Subdomain (e.g. mystore.myshop.com)
  2. Header (X-Tenant-ID)
  3. JWT token tenant_id claim
"""
import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_session
from app.models.license import Tenant

logger = logging.getLogger("myshop.tenants")


class TenantContext:
    """Holds the current tenant for the request."""

    def __init__(self):
        self.tenant_id: Optional[int] = None
        self.tenant: Optional[Tenant] = None


# Request-scoped tenant context
_tenant_context = TenantContext()


def get_tenant_context() -> TenantContext:
    """Get the current tenant context (request-scoped)."""
    return _tenant_context


async def get_tenant_id(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> Optional[int]:
    """Extract tenant_id from request.

    Priority:
      1. X-Tenant-ID header
      2. Subdomain resolution
      3. None (platform admin / unauthenticated)
    """
    # 1. Explicit header
    tenant_id_header = request.headers.get("X-Tenant-ID")
    if tenant_id_header:
        try:
            return int(tenant_id_header)
        except ValueError:
            pass

    # 2. Subdomain resolution
    host = request.headers.get("host", "").split(":")[0]
    # Skip localhost and IP addresses
    if host in ("localhost", "127.0.0.1", "0.0.0.0") or host.replace(".", "").isdigit():
        # Check request.state for license middleware tenant_id
        if hasattr(request.state, "tenant_id"):
            return request.state.tenant_id
        return None

    # Resolve subdomain to tenant
    result = await session.execute(
        select(Tenant).where(Tenant.domain == host, Tenant.active == True)
    )
    tenant = result.scalar_one_or_none()
    if tenant:
        return tenant.id

    return None


async def get_current_tenant(
    tenant_id: Optional[int] = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
) -> Optional[Tenant]:
    """Get the current Tenant object (or None for platform admin)."""
    if tenant_id is None:
        return None
    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    return result.scalar_one_or_none()


async def require_tenant(
    tenant_id: Optional[int] = Depends(get_tenant_id),
) -> int:
    """Require a valid tenant_id. Raises 403 if missing."""
    if tenant_id is None:
        raise HTTPException(
            status_code=403,
            detail="Tenant context required. Set X-Tenant-ID header.",
        )
    return tenant_id
