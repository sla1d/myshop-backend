"""Админ-эндпоинты для маркетплейсов."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.rbac.deps import RequirePermission
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
    user: User = Depends(get_current_user),
    _: None = Depends(RequirePermission("marketplace.sync")),
):
    """Синхронизировать товары с Wildberries."""
    import uuid
    task_id = str(uuid.uuid4())[:8]
    logger.info("WB sync started: task=%s", task_id)
    return SyncResponse(task_id=task_id, status="queued")


@router.post("/ozon/sync", response_model=SyncResponse)
async def sync_ozon(
    body: OzonSyncRequest,
    user: User = Depends(get_current_user),
    _: None = Depends(RequirePermission("marketplace.sync")),
):
    """Синхронизировать товары с Ozon."""
    import uuid
    task_id = str(uuid.uuid4())[:8]
    logger.info("Ozon sync started: task=%s", task_id)
    return SyncResponse(task_id=task_id, status="queued")


@router.get("/wildberries/orders")
async def get_wb_orders(
    api_token: str,
    user: User = Depends(get_current_user),
    _: None = Depends(RequirePermission("product.view")),
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
    user: User = Depends(get_current_user),
    _: None = Depends(RequirePermission("product.view")),
):
    """Получить заказы с Ozon."""
    from app.services.marketplace import OzonExporter
    exporter = OzonExporter(client_id, api_key)
    orders = await exporter.get_orders()
    return {"orders": orders, "count": len(orders)}
