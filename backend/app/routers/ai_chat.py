"""AI Assistant chat API."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_id_from_request
from app.database.connection import get_async_session
from app.models.user import User
from app.plugins.ai_assistant import process_ai_message

router = APIRouter(prefix="/ai", tags=["ИИ-помощник"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    success: bool
    message: str
    intent: str = ""
    action: dict | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    tenant_id: int | None = Depends(get_tenant_id_from_request),
    session: AsyncSession = Depends(get_async_session),
):
    """Send a message to AI assistant (admin/owner only)."""
    if not tenant_id:
        tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(400, "Нет привязки к магазину")

    if user.role != "admin":
        from app.rbac.models import UserRole, Role
        from sqlalchemy import select
        owner_check = await session.execute(
            select(UserRole).join(Role).where(
                UserRole.user_id == user.id,
                UserRole.tenant_id == tenant_id,
                Role.name == "owner",
            )
        )
        if not owner_check.scalar_one_or_none():
            raise HTTPException(403, "ИИ-помощник доступен только администратору или владельцу")
        raise HTTPException(400, "Tenant context required for AI assistant")

    result = await process_ai_message(session, tenant_id, body.message)
    return ChatResponse(**result)


@router.get("/commands")
async def list_commands():
    """List available AI assistant commands."""
    return {
        "commands": [
            {
                "category": "Дизайн",
                "commands": [
                    {"command": "Смени тему на {theme}", "description": "Изменить тему магазина"},
                    {"command": "Название магазина = {name}", "description": "Изменить название"},
                ],
            },
            {
                "category": "Функции",
                "commands": [
                    {"command": "Включи отзывы", "description": "Активировать отзывы"},
                    {"command": "Выключи промокоды", "description": "Отключить промокоды"},
                    {"command": "Включи избранное", "description": "Активировать wishlist"},
                ],
            },
            {
                "category": "Контент",
                "commands": [
                    {"command": "Создай баннер {title}", "description": "Добавить баннер"},
                    {"command": "Создай промокод {code} на {n}%", "description": "Создать промокод"},
                ],
            },
            {
                "category": "Аналитика",
                "commands": [
                    {"command": "Покажи статистику", "description": "Вывод статистики магазина"},
                ],
            },
        ],
    }
