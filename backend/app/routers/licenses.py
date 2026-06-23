import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from secrets import token_hex
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.database.connection import get_async_session
from app.models.license import License, Tenant, LICENSE_PLANS
from app.models.user import User

router = APIRouter(prefix="/admin/licenses", tags=["Лицензии"])
logger = logging.getLogger("myshop.licenses")


class TenantCreate(BaseModel):
    name: str
    domain: str
    plan: str = "starter"


class LicenseResponse(BaseModel):
    id: int
    tenant_name: str
    domain: str
    key: str
    plan: str
    expires_at: str
    max_products: int
    max_users: int
    active: bool


class LicenseExtend(BaseModel):
    days: int = 30


@router.get("", response_model=list[LicenseResponse])
async def list_licenses(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Все лицензии."""
    result = await session.execute(
        select(License, Tenant).join(Tenant, License.tenant_id == Tenant.id)
    )
    return [
        LicenseResponse(
            id=lic.id,
            tenant_name=t.name,
            domain=t.domain,
            key=lic.key,
            plan=lic.plan,
            expires_at=lic.expires_at.isoformat(),
            max_products=lic.max_products,
            max_users=lic.max_users,
            active=lic.active,
        )
        for lic, t in result.all()
    ]


@router.post("", response_model=LicenseResponse, status_code=201)
async def create_license(
    body: TenantCreate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Создать клиента с лицензией."""
    # Проверка уникальности домена
    existing = await session.execute(select(Tenant).where(Tenant.domain == body.domain))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Домен уже зарегистрирован")

    if body.plan not in LICENSE_PLANS:
        raise HTTPException(status_code=400, detail=f"План: {', '.join(LICENSE_PLANS.keys())}")

    plan = LICENSE_PLANS[body.plan]

    tenant = Tenant(name=body.name, domain=body.domain)
    session.add(tenant)
    await session.flush()

    license = License(
        tenant_id=tenant.id,
        key=f"MYSHOP-{token_hex(16).upper()}",
        plan=body.plan,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        max_products=plan["max_products"],
        max_users=plan["max_users"],
    )
    session.add(license)
    await session.commit()
    await session.refresh(license)

    logger.info("License created: %s (%s) — %s", body.name, body.domain, body.plan)

    return LicenseResponse(
        id=license.id,
        tenant_name=tenant.name,
        domain=tenant.domain,
        key=license.key,
        plan=license.plan,
        expires_at=license.expires_at.isoformat(),
        max_products=license.max_products,
        max_users=license.max_users,
        active=license.active,
    )


@router.post("/{license_id}/extend", response_model=LicenseResponse)
async def extend_license(
    license_id: int,
    body: LicenseExtend,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Продлить лицензию."""
    result = await session.execute(
        select(License, Tenant).join(Tenant, License.tenant_id == Tenant.id).where(License.id == license_id)
    )
    lic, tenant = result.one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")

    lic.expires_at += timedelta(days=body.days)
    lic.active = True
    await session.commit()
    await session.refresh(lic)

    logger.info("License extended: %s +%d days", tenant.domain, body.days)

    return LicenseResponse(
        id=lic.id,
        tenant_name=tenant.name,
        domain=tenant.domain,
        key=lic.key,
        plan=lic.plan,
        expires_at=lic.expires_at.isoformat(),
        max_products=lic.max_products,
        max_users=lic.max_users,
        active=lic.active,
    )


@router.patch("/{license_id}/toggle")
async def toggle_license(
    license_id: int,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Включить/выключить лицензию."""
    result = await session.execute(select(License).where(License.id == license_id))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")

    lic.active = not lic.active
    await session.commit()

    return {"status": "active" if lic.active else "suspended"}
