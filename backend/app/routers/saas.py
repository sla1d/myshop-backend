"""SaaS management API — features, domains, plugins."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_id_from_request
from app.rbac.deps import RequirePermission
from app.database.connection import get_async_session
from app.models.user import User
from app.saas.models import FEATURE_FLAGS
from app.saas.service import DomainService, FeatureService

router = APIRouter(prefix="/saas", tags=["SaaS"])


class FeatureToggleRequest(BaseModel):
    feature_key: str
    enabled: bool


class DomainRequest(BaseModel):
    domain: str


# ─── Features ───────────────────────────────────────
@router.get("/features")
async def list_features(
    current_user: User = Depends(get_current_user),
    _perm: None = Depends(RequirePermission("tenant.manage")),
    tenant_id: int | None = Depends(get_tenant_id_from_request),
    session: AsyncSession = Depends(get_async_session),
):
    """List all available features with tenant status."""
    service = FeatureService(session)
    available = await service.get_available_features()

    tenant_features = {}
    if tenant_id:
        tenant_features = await service.get_features(tenant_id)

    return {
        "available": available,
        "enabled": tenant_features,
    }


@router.post("/features/toggle")
async def toggle_feature(
    body: FeatureToggleRequest,
    current_user: User = Depends(get_current_user),
    _perm: None = Depends(RequirePermission("tenant.manage")),
    tenant_id: int | None = Depends(get_tenant_id_from_request),
    session: AsyncSession = Depends(get_async_session),
):
    """Enable or disable a feature."""
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    service = FeatureService(session)
    try:
        feature = await service.set_feature(tenant_id, body.feature_key, body.enabled)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "feature_key": body.feature_key,
        "enabled": feature.enabled,
    }


# ─── Domains ────────────────────────────────────────
@router.get("/domains")
async def list_domains(
    current_user: User = Depends(get_current_user),
    _perm: None = Depends(RequirePermission("tenant.manage")),
    tenant_id: int | None = Depends(get_tenant_id_from_request),
    session: AsyncSession = Depends(get_async_session),
):
    """List custom domains."""
    if not tenant_id:
        return {"domains": []}

    service = DomainService(session)
    domains = await service.get_domains(tenant_id)
    return {
        "domains": [
            {
                "id": d.id,
                "domain": d.domain,
                "verified": d.verified,
                "ssl_enabled": d.ssl_enabled,
                "dns_configured": d.dns_configured,
            }
            for d in domains
        ]
    }


@router.post("/domains/add")
async def add_domain(
    body: DomainRequest,
    current_user: User = Depends(get_current_user),
    _perm: None = Depends(RequirePermission("tenant.manage")),
    tenant_id: int | None = Depends(get_tenant_id_from_request),
    session: AsyncSession = Depends(get_async_session),
):
    """Add a custom domain."""
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    service = DomainService(session)
    domain = await service.add_domain(tenant_id, body.domain)
    return {
        "id": domain.id,
        "domain": domain.domain,
        "verified": domain.verified,
        "message": "Add CNAME record pointing to myshop.ai",
    }
