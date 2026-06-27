"""Store generation API — create a complete store in one call."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.billing.service import BillingService
from app.database.connection import get_async_session
from app.models.user import User
from app.rbac.deps import RequirePermission
from app.services.tenant import TenantService

logger = logging.getLogger("myshop.store")

router = APIRouter(prefix="/store", tags=["Генерация магазина"])

AVAILABLE_THEMES = ["midnight", "light", "nature", "rose", "cyber", "minimal"]
AVAILABLE_INDUSTRIES = [
    "electronics", "clothing", "food", "beauty", "sports",
    "home", "kids", "books", "auto", "health",
]


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

    # Feature toggles
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


@router.post("/generate-store", response_model=GenerateStoreResponse)
async def generate_store(
    body: GenerateStoreRequest,
    session: AsyncSession = Depends(get_async_session),
    _perm: None = Depends(RequirePermission("tenant.manage")),
):
    """Generate a complete store with one API call.

    Creates: tenant, license, admin user, subscription.
    Returns: store URL and admin credentials.
    """
    # Validate
    if body.theme not in AVAILABLE_THEMES:
        raise HTTPException(400, f"Invalid theme. Available: {AVAILABLE_THEMES}")
    if body.industry not in AVAILABLE_INDUSTRIES:
        raise HTTPException(400, f"Invalid industry. Available: {AVAILABLE_INDUSTRIES}")

    tenant_service = TenantService(session)

    # Check slug uniqueness
    existing = await tenant_service.get_by_slug(body.slug)
    if existing:
        raise HTTPException(400, f"Slug '{body.slug}' already taken")

    # Auto-generate domain if not provided
    domain = body.domain or f"{body.slug}.myshop.com"

    # Create tenant
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

    # Create subscription
    billing_service = BillingService(session)
    sub_result = await billing_service.create_subscription(
        tenant_id=result["tenant_id"],
        plan=body.plan,
    )

    # Build feature flags
    features = {
        "reviews": body.reviews,
        "promocodes": body.promocodes,
        "wishlist": body.wishlist,
        "flash_sales": body.flash_sales,
        "loyalty": body.loyalty,
        "referral": body.referral,
    }

    # Store features in tenant settings
    import json
    from app.models.license import Tenant
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
