import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database.connection import get_async_session
from app.models.user import User

router = APIRouter(tags=["Авторизация"])
logger = logging.getLogger("myshop.auth")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=dict)
async def register(
    username: str,
    password: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Регистрация нового пользователя."""
    if not username or not password:
        raise HTTPException(status_code=400, detail="Имя и пароль обязательны")

    result = await session.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    user = User(username=username, password=hash_password(password))
    session.add(user)
    await session.commit()
    logger.info("Зарегистрирован: %s", username)
    return {"status": "ok"}


@router.post("/login", response_model=TokenResponse)
async def login(
    username: str,
    password: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Вход — возвращает access + refresh токены."""
    if not username or not password:
        raise HTTPException(status_code=400, detail="Имя и пароль обязательны")

    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Неверные данные")

    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token({"sub": str(user.id)})

    logger.info("Вход: %s (role=%s)", user.username, user.role)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        username=user.username,
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Обновить access token через refresh token."""
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Невалидный refresh токен")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Невалидный refresh токен")

    result = await session.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        username=user.username,
        role=user.role,
    )
