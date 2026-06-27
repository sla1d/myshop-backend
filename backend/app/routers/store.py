from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_session
from app.models.license import Tenant
from app.schemas.tenant import TenantSettingsUpdate, TenantSettingsResponse

router = APIRouter(prefix="/api/store", tags=["Store Settings"])

THEMES = ["midnight", "light", "nature", "rose", "cyber", "minimal"]


@router.get("/settings", response_model=TenantSettingsResponse)
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


@router.put("/settings", response_model=TenantSettingsResponse)
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
