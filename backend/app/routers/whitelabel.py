"""White-label API — customize store branding."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.license import Tenant
from app.models.user import User
from app.rbac.deps import RequirePermission

router = APIRouter(prefix="/whitelabel", tags=["White-label"])
logger = logging.getLogger("myshop.whitelabel")


class WhiteLabelConfig(BaseModel):
    brand_name: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    footer_text: str | None = None
    favicon_url: str | None = None
    custom_css: str | None = None
    hide_myshop_branding: bool | None = None
    custom_email_domain: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    og_image_url: str | None = None
    store_name: str | None = None
    logo_url: str | None = None
    theme: str | None = None


class WhiteLabelResponse(BaseModel):
    brand_name: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    footer_text: str | None = None
    favicon_url: str | None = None
    custom_css: str | None = None
    hide_myshop_branding: bool = False
    custom_email_domain: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    og_image_url: str | None = None
    store_name: str | None = None
    logo_url: str | None = None
    theme: str | None = None


@router.get("", response_model=WhiteLabelResponse)
async def get_whitelabel_config(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get white-label configuration for current tenant."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant не определён")

    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Магазин не найден")

    return WhiteLabelResponse(
        brand_name=tenant.brand_name,
        primary_color=tenant.primary_color,
        secondary_color=tenant.secondary_color,
        footer_text=tenant.footer_text,
        favicon_url=tenant.favicon_url,
        custom_css=tenant.custom_css,
        hide_myshop_branding=tenant.hide_myshop_branding,
        custom_email_domain=tenant.custom_email_domain,
        meta_title=tenant.meta_title,
        meta_description=tenant.meta_description,
        og_image_url=tenant.og_image_url,
        store_name=tenant.store_name,
        logo_url=tenant.logo_url,
        theme=tenant.theme,
    )


@router.put("", response_model=WhiteLabelResponse)
async def update_whitelabel_config(
    body: WhiteLabelConfig,
    request: Request,
    user: User = Depends(RequirePermission("tenant.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    """Update white-label configuration for current tenant."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant не определён")

    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Магазин не найден")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(tenant, field):
            setattr(tenant, field, value)

    await session.commit()
    await session.refresh(tenant)

    logger.info("White-label updated for tenant %d: %s", tenant_id, list(update_data.keys()))

    return WhiteLabelResponse(
        brand_name=tenant.brand_name,
        primary_color=tenant.primary_color,
        secondary_color=tenant.secondary_color,
        footer_text=tenant.footer_text,
        favicon_url=tenant.favicon_url,
        custom_css=tenant.custom_css,
        hide_myshop_branding=tenant.hide_myshop_branding,
        custom_email_domain=tenant.custom_email_domain,
        meta_title=tenant.meta_title,
        meta_description=tenant.meta_description,
        og_image_url=tenant.og_image_url,
        store_name=tenant.store_name,
        logo_url=tenant.logo_url,
        theme=tenant.theme,
    )


@router.get("/preview")
async def preview_store(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get store config for frontend rendering (public-safe)."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant не определён")

    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Магазин не найден")

    return {
        "store_name": tenant.store_name or tenant.name,
        "logo_url": tenant.logo_url,
        "theme": tenant.theme,
        "brand_name": tenant.brand_name,
        "primary_color": tenant.primary_color or "#3B82F6",
        "secondary_color": tenant.secondary_color or "#10B981",
        "footer_text": tenant.footer_text,
        "favicon_url": tenant.favicon_url,
        "hide_myshop_branding": tenant.hide_myshop_branding,
        "meta": {
            "title": tenant.meta_title or tenant.store_name or tenant.name,
            "description": tenant.meta_description or f"Интернет-магазин {tenant.store_name or tenant.name}",
            "og_image": tenant.og_image_url,
        },
    }
