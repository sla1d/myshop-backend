from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.core.storage import storage, ALLOWED_TYPES, MAX_FILE_SIZE
from app.database.connection import get_async_session
from app.models.order import Order, OrderItem
from app.models.user import User
from app.schemas.order import OrderAdmin, OrderItemAdmin
from app.schemas.profile import PasswordChange, ProfileResponse, ProfileUpdate
from app.services.telegram import notify_order_created

router = APIRouter(prefix="/profile", tags=["Профиль"])


class MessageResponse(BaseModel):
    detail: str


class TelegramLink(BaseModel):
    chat_id: int


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user: User = Depends(get_current_user),
):
    """Получить профиль текущего пользователя."""
    return user


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Обновить профиль текущего пользователя."""
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: PasswordChange,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Сменить пароль."""
    if not verify_password(body.old_password, user.password):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")
    user.password = hash_password(body.new_password)
    await session.commit()
    return MessageResponse(detail="Пароль изменён")


@router.get("/orders", response_model=list[OrderAdmin])
async def get_my_orders(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """История заказов текущего пользователя."""
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.user_id == user.id)
        .order_by(Order.id.desc())
    )
    orders = result.scalars().unique().all()
    return [
        OrderAdmin(
            id=o.id,
            user_id=o.user_id,
            username=user.username,
            total=o.total,
            address=o.address,
            status=o.status,
            created_at=o.created_at.isoformat(),
            items=[
                OrderItemAdmin(
                    product_name=i.product.name,
                    quantity=i.quantity,
                    price=i.price,
                )
                for i in o.items
            ],
        )
        for o in orders
    ]


@router.post("/link-telegram", response_model=MessageResponse)
async def link_telegram(
    body: TelegramLink,
    user: User = Depends(get_current_user),
):
    """Привязать Telegram для уведомлений."""
    from app.services.telegram import send_message
    success = await send_message(body.chat_id, "✅ Telegram привязан к вашему магазину!")
    if not success:
        raise HTTPException(status_code=400, detail="Не удалось отправить сообщение")
    return MessageResponse(detail="Telegram привязан")


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Загрузить аватар пользователя."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Допустимые типы: {', '.join(ALLOWED_TYPES)}")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"Максимальный размер: {MAX_FILE_SIZE // (1024*1024)} МБ")

    result = await storage.upload_file(
        file_data=data,
        filename=f"avatar_{user.id}_{file.filename or 'avatar.jpg'}",
        content_type=file.content_type,
        tenant_id=user.tenant_id,
    )

    if result is None:
        raise HTTPException(status_code=500, detail="Не удалось загрузить файл")

    user.avatar_url = result["url"]
    await session.commit()
    return {"detail": "Аватар загружен", "avatar_url": result["url"]}


@router.delete("/avatar")
async def delete_avatar(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Удалить аватар пользователя."""
    user.avatar_url = None
    await session.commit()
    return {"detail": "Аватар удалён"}
