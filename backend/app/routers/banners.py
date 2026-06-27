import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.ad_banner import AdBanner
from app.models.user import User
from app.rbac.deps import RequirePermission

router = APIRouter(prefix="/admin/banners", tags=["Баннеры"])
logger = logging.getLogger(__name__)


class BannerCreate(BaseModel):
    title: str
    image_url: str
    link_url: str | None = None
    position: int = 0
    start_at: str | None = None
    end_at: str | None = None


class BannerResponse(BaseModel):
    id: int
    title: str
    image_url: str
    link_url: str | None = None
    position: int
    active: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=list[BannerResponse])
async def list_banners(
    _: User = Depends(RequirePermission("product.view")),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(AdBanner).order_by(AdBanner.position))
    return result.scalars().all()


@router.post("", response_model=BannerResponse, status_code=201)
async def create_banner(
    body: BannerCreate,
    _: User = Depends(RequirePermission("product.create")),
    session: AsyncSession = Depends(get_async_session),
):
    banner = AdBanner(
        title=body.title,
        image_url=body.image_url,
        link_url=body.link_url,
        position=body.position,
        start_at=datetime.fromisoformat(body.start_at) if body.start_at else None,
        end_at=datetime.fromisoformat(body.end_at) if body.end_at else None,
    )
    session.add(banner)
    await session.commit()
    await session.refresh(banner)
    return banner


@router.delete("/{banner_id}")
async def delete_banner(
    banner_id: int,
    _: User = Depends(RequirePermission("product.delete")),
    session: AsyncSession = Depends(get_async_session),
):
    banner = await session.get(AdBanner, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Баннер не найден")
    await session.delete(banner)
    await session.commit()
    return {"detail": "Удалён"}


@router.patch("/{banner_id}/toggle")
async def toggle_banner(
    banner_id: int,
    _: User = Depends(RequirePermission("product.update")),
    session: AsyncSession = Depends(get_async_session),
):
    banner = await session.get(AdBanner, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Баннер не найден")
    banner.active = not banner.active
    await session.commit()
    return {"active": banner.active}
