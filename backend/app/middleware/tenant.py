"""Tenant middleware — resolves tenant for every request."""
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings

logger = logging.getLogger("myshop.tenants")

# Paths that don't need tenant context
SKIP_PATHS = {
    "/health", "/metrics", "/docs", "/redoc", "/openapi.json",
    "/register", "/login", "/refresh", "/login/2fa",
    "/api/store/settings", "/api/public/",
}


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve tenant from host and attach to request.state."""

    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0]

        # Allow explicit tenant via header (for admin/API usage)
        header_tenant = request.headers.get("x-tenant-id")
        if header_tenant:
            try:
                request.state.tenant_id = int(header_tenant)
            except (ValueError, TypeError):
                request.state.tenant_id = None
            return await call_next(request)

        # Skip for localhost, docs, health
        if (
            host in ("localhost", "127.0.0.1", "0.0.0.0", "test")
            or host.replace(".", "").isdigit()
            or any(request.url.path.startswith(p) for p in SKIP_PATHS)
            or settings.DEBUG
        ):
            request.state.tenant_id = None
            return await call_next(request)

        # Try to resolve tenant from host
        try:
            from app.database.connection import async_session_factory
            from app.models.license import Tenant
            from sqlalchemy import select

            async with async_session_factory() as session:
                result = await session.execute(
                    select(Tenant).where(Tenant.domain == host, Tenant.active == True)
                )
                tenant = result.scalar_one_or_none()
                if tenant:
                    request.state.tenant_id = tenant.id
                    request.state.tenant = tenant
                else:
                    request.state.tenant_id = None
                    logger.debug("No tenant for host: %s", host)
        except Exception as e:
            logger.error("Tenant resolution error: %s", e)
            request.state.tenant_id = None

        return await call_next(request)
