import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.license import License, Tenant, LICENSE_PLANS
from app.models.user import User

router = APIRouter(prefix="/superadmin", tags=["Суперадмин"])
logger = logging.getLogger("myshop.superadmin")


async def get_superadmin(user: User = Depends(get_current_user)) -> User:
    """Проверка роли superadmin."""
    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Требуется роль superadmin")
    return user


class TenantResponse(BaseModel):
    id: int
    name: str
    domain: str
    active: bool
    plan: str
    expires_at: str
    users_count: int


class StatsResponse(BaseModel):
    total_tenants: int
    active_tenants: int
    total_users: int
    total_revenue: int


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    admin: User = Depends(get_superadmin),
    session: AsyncSession = Depends(get_async_session),
):
    """Глобальная статистика."""
    tenants = (await session.execute(select(func.count(Tenant.id)))).scalar() or 0
    active = (await session.execute(
        select(func.count(Tenant.id)).where(Tenant.active == True)
    )).scalar() or 0
    users = (await session.execute(select(func.count(User.id)))).scalar() or 0

    return StatsResponse(
        total_tenants=tenants,
        active_tenants=active,
        total_users=users,
        total_revenue=0,
    )


@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(
    admin: User = Depends(get_superadmin),
    session: AsyncSession = Depends(get_async_session),
):
    """Все клиенты с лицензиями."""
    result = await session.execute(
        select(Tenant, License)
        .outerjoin(License, Tenant.id == License.tenant_id)
    )
    out = []
    for tenant, lic in result.all():
        users_count = (await session.execute(
            select(func.count(User.id)).where(User.tenant_id == tenant.id)
        )).scalar() or 0
        out.append(TenantResponse(
            id=tenant.id,
            name=tenant.name,
            domain=tenant.domain,
            active=tenant.active,
            plan=lic.plan if lic else "none",
            expires_at=lic.expires_at.isoformat() if lic else "never",
            users_count=users_count,
        ))
    return out


@router.patch("/tenants/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: int,
    admin: User = Depends(get_superadmin),
    session: AsyncSession = Depends(get_async_session),
):
    """Приостановить клиента."""
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    tenant.active = not tenant.active
    await session.commit()
    logger.info("Tenant %s: active=%s", tenant.domain, tenant.active)
    return {"status": "active" if tenant.active else "suspended"}


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
    admin: User = Depends(get_superadmin),
    session: AsyncSession = Depends(get_async_session),
):
    """Удалить клиента и все данные."""
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    # Удаляем лицензию
    lic = await session.execute(select(License).where(License.tenant_id == tenant_id))
    for l in lic.scalars().all():
        await session.delete(l)

    # Удаляем пользователей
    users = await session.execute(select(User).where(User.tenant_id == tenant_id))
    for u in users.scalars().all():
        await session.delete(u)

    await session.delete(tenant)
    await session.commit()
    logger.info("Tenant deleted: %s", tenant.domain)
    return {"status": "deleted"}
