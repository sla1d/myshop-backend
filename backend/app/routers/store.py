"""Store settings + one-click store generation."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_session
from app.models.license import Tenant
from app.models.user import User
from app.rbac.deps import RequirePermission
from app.schemas.tenant import TenantSettingsUpdate, TenantSettingsResponse

logger = logging.getLogger("myshop.store")

router = APIRouter(tags=["Store"])

THEMES = ["midnight", "light", "nature", "rose", "cyber", "minimal"]
AVAILABLE_INDUSTRIES = [
    "electronics", "clothing", "food", "beauty", "sports",
    "home", "kids", "books", "auto", "health",
]


# ── Settings ──────────────────────────────────────────────

@router.get("/api/store/settings", response_model=TenantSettingsResponse)
async def get_store_settings(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Tenant).limit(1))
    tenant = result.scalars().first()
    if not tenant:
        return TenantSettingsResponse(theme="midnight")
    return TenantSettingsResponse(
        theme=tenant.theme or "midnight",
        logo_url=tenant.logo_url,
        store_name=tenant.store_name,
    )


@router.put("/api/store/settings", response_model=TenantSettingsResponse)
async def update_store_settings(
    data: TenantSettingsUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Tenant).limit(1))
    tenant = result.scalars().first()
    if not tenant:
        tenant = Tenant(name="Default Store", domain="localhost", theme="midnight")
        session.add(tenant)
        await session.flush()

    if data.theme is not None:
        if data.theme not in THEMES:
            raise HTTPException(400, f"Invalid theme. Available: {THEMES}")
        tenant.theme = data.theme
    if data.logo_url is not None:
        tenant.logo_url = data.logo_url
    if data.store_name is not None:
        tenant.store_name = data.store_name

    await session.commit()
    await session.refresh(tenant)
    return TenantSettingsResponse.model_validate(tenant)


# ── One-click store generation ────────────────────────────

class GenerateStoreRequest(BaseModel):
    name: str
    slug: str
    domain: str = ""
    industry: str = "electronics"
    theme: str = "dark"
    plan: str = "starter"
    admin_username: str = "admin"
    admin_password: str = "admin123"
    admin_email: str = ""
    reviews: bool = True
    promocodes: bool = True
    wishlist: bool = True
    flash_sales: bool = False
    loyalty: bool = False
    referral: bool = False


class GenerateStoreResponse(BaseModel):
    tenant_id: int
    slug: str
    domain: str
    store_url: str
    admin_panel_url: str
    admin_username: str
    license_key: str
    plan: str
    expires_at: str
    theme: str
    features: dict


@router.post("/api/store/generate-store", response_model=GenerateStoreResponse)
async def generate_store(
    body: GenerateStoreRequest,
    session: AsyncSession = Depends(get_async_session),
    _perm: None = Depends(RequirePermission("tenant.manage")),
):
    from app.billing.service import BillingService
    from app.services.tenant import TenantService

    if body.theme not in THEMES:
        raise HTTPException(400, f"Invalid theme. Available: {THEMES}")
    if body.industry not in AVAILABLE_INDUSTRIES:
        raise HTTPException(400, f"Invalid industry. Available: {AVAILABLE_INDUSTRIES}")

    tenant_service = TenantService(session)
    existing = await tenant_service.get_by_slug(body.slug)
    if existing:
        raise HTTPException(400, f"Slug '{body.slug}' already taken")

    domain = body.domain or f"{body.slug}.myshop.com"

    result = await tenant_service.create_tenant(
        name=body.name,
        slug=body.slug,
        domain=domain,
        plan=body.plan,
        admin_username=body.admin_username,
        admin_password=body.admin_password,
        admin_email=body.admin_email,
        theme=body.theme if body.theme != "dark" else "midnight",
    )

    billing_service = BillingService(session)
    await billing_service.create_subscription(
        tenant_id=result["tenant_id"],
        plan=body.plan,
    )

    features = {
        "reviews": body.reviews,
        "promocodes": body.promocodes,
        "wishlist": body.wishlist,
        "flash_sales": body.flash_sales,
        "loyalty": body.loyalty,
        "referral": body.referral,
    }

    tenant = await session.get(Tenant, result["tenant_id"])
    if tenant:
        tenant.settings = json.dumps(features)
        await session.commit()

    logger.info("Store generated: %s (slug=%s, plan=%s)", body.name, body.slug, body.plan)

    return GenerateStoreResponse(
        tenant_id=result["tenant_id"],
        slug=result["slug"],
        domain=result["domain"],
        store_url=f"https://{result['domain']}",
        admin_panel_url=f"https://{result['domain']}/admin",
        admin_username=result["admin_username"],
        license_key=result["license_key"],
        plan=result["plan"],
        expires_at=result["expires_at"],
        theme=body.theme if body.theme != "dark" else "midnight",
        features=features,
    )
