import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_session
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit", tags=["Аудит"])
logger = logging.getLogger(__name__)


class AuditLogItem(BaseModel):
    id: int
    user_id: int | None = None
    username: str | None = None
    action: str
    entity: str | None = None
    entity_id: int | None = None
    details: str | None = None
    ip_address: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


async def log_action(
    session: AsyncSession,
    action: str,
    user_id: int | None = None,
    username: str | None = None,
    entity: str | None = None,
    entity_id: int | None = None,
    details: str | None = None,
    ip_address: str | None = None,
):
    """Утилита для записи аудита."""
    entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
    session.add(entry)
    await session.flush()
    return entry


@router.get("/logs", response_model=list[AuditLogItem])
async def get_audit_logs(
    limit: int = 50,
    session: AsyncSession = Depends(get_async_session),
):
    """Получить последние записи аудита (только admin)."""
    from sqlalchemy import desc
    result = await session.execute(
        select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    )
    logs = result.scalars().all()
    return logs
