"""Админ-эндпоинты для маркетплейсов."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.database.connection import get_async_session
from app.models.user import User

router = APIRouter(prefix="/admin/marketplace", tags=["Маркетплейсы"])
logger = logging.getLogger("myshop.marketplace.admin")


class WBSyncRequest(BaseModel):
    api_token: str


class OzonSyncRequest(BaseModel):
    client_id: str
    api_key: str


class SyncResponse(BaseModel):
    task_id: str
    status: str


@router.post("/wildberries/sync", response_model=SyncResponse)
async def sync_wildberries(
    body: WBSyncRequest,
    admin: User = Depends(get_current_admin),
):
    """Синхронизировать товары с Wildberries."""
    from app.tasks.marketplace import sync_wildberries as sync_wb
    task = sync_wb.delay(admin.tenant_id or 0, body.api_token)
    logger.info("WB sync started: task=%s", task.id)
    return SyncResponse(task_id=task.id, status="queued")


@router.post("/ozon/sync", response_model=SyncResponse)
async def sync_ozon(
    body: OzonSyncRequest,
    admin: User = Depends(get_current_admin),
):
    """Синхронизировать товары с Ozon."""
    from app.tasks.marketplace import sync_ozon as sync_oz
    task = sync_oz.delay(admin.tenant_id or 0, body.client_id, body.api_key)
    logger.info("Ozon sync started: task=%s", task.id)
    return SyncResponse(task_id=task.id, status="queued")


@router.get("/wildberries/orders")
async def get_wb_orders(
    api_token: str,
    admin: User = Depends(get_current_admin),
):
    """Получить заказы с Wildberries."""
    from app.services.marketplace import WildberriesExporter
    exporter = WildberriesExporter(api_token)
    orders = await exporter.get_orders()
    return {"orders": orders, "count": len(orders)}


@router.get("/ozon/orders")
async def get_ozon_orders(
    client_id: str,
    api_key: str,
    admin: User = Depends(get_current_admin),
):
    """Получить заказы с Ozon."""
    from app.services.marketplace import OzonExporter
    exporter = OzonExporter(client_id, api_key)
    orders = await exporter.get_orders()
    return {"orders": orders, "count": len(orders)}
