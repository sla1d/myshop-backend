"""Auth API — JWT auth with refresh token rotation, login attempts, 2FA."""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database.connection import get_async_session
from app.models.user import User
from app.security.models import LoginAttempt, RefreshToken

router = APIRouter(tags=["Авторизация"])
logger = logging.getLogger("myshop.auth")

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _hash_token(token: str) -> str:
    """Hash token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str
    role: str
    user_id: int = 0
    requires_2fa: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str | None = None


# ─── Login Attempts ─────────────────────────────────
async def _check_login_attempts(session: AsyncSession, email: str, ip: str) -> None:
    """Check if login is blocked due to too many attempts."""
    result = await session.execute(
        select(LoginAttempt)
        .where(LoginAttempt.email == email, LoginAttempt.ip == ip)
        .order_by(LoginAttempt.created_at.desc())
        .limit(1)
    )
    attempt = result.scalar_one_or_none()

    if attempt and attempt.blocked_until:
        if attempt.blocked_until > datetime.now(timezone.utc):
            remaining = (attempt.blocked_until - datetime.now(timezone.utc)).seconds
            raise HTTPException(
                status_code=429,
                detail=f"Слишком много попыток. Попробуйте через {remaining // 60} мин.",
            )


async def _record_login_attempt(
    session: AsyncSession, email: str, ip: str, success: bool, user_agent: str = "",
) -> None:
    """Record a login attempt and apply lockout if needed."""
    result = await session.execute(
        select(LoginAttempt)
        .where(LoginAttempt.email == email, LoginAttempt.ip == ip)
        .order_by(LoginAttempt.created_at.desc())
        .limit(1)
    )
    attempt = result.scalar_one_or_none()

    if success:
        if attempt:
            attempt.attempts = 0
            attempt.blocked_until = None
        return

    if attempt and attempt.blocked_until and attempt.blocked_until > datetime.now(timezone.utc):
        return  # Already blocked

    if attempt and not attempt.blocked_until:
        attempt.attempts += 1
        attempt.user_agent = user_agent
        if attempt.attempts >= MAX_LOGIN_ATTEMPTS:
            attempt.blocked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
            logger.warning("Login blocked: %s (attempts=%d)", email, attempt.attempts)
    else:
        new_attempt = LoginAttempt(
            email=email,
            ip=ip,
            user_agent=user_agent,
            attempts=1,
        )
        session.add(new_attempt)

    await session.flush()


# ─── Refresh Token Management ──────────────────────
async def _create_refresh_token(
    session: AsyncSession, user_id: int, ip: str = "", device: str = "",
) -> tuple[str, RefreshToken]:
    """Create and store a refresh token."""
    token = create_refresh_token({"sub": str(user_id)})
    token_hash = _hash_token(token)

    refresh = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        ip_address=ip,
        device_info=device,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    session.add(refresh)
    await session.flush()
    return token, refresh


async def _revoke_refresh_token(session: AsyncSession, token_hash: str) -> None:
    """Revoke a refresh token."""
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token = result.scalar_one_or_none()
    if token:
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)
        await session.flush()


async def _revoke_all_user_tokens(session: AsyncSession, user_id: int) -> int:
    """Revoke all refresh tokens for a user (logout all devices)."""
    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,
        )
    )
    tokens = result.scalars().all()
    count = 0
    for token in tokens:
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)
        count += 1
    await session.flush()
    return count


# ─── Endpoints ──────────────────────────────────────
@router.post("/register", response_model=dict)
@limiter.limit("3/minute")
async def register(
    request: Request,
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
    await session.flush()

    from app.models.license import Tenant
    from app.rbac.models import UserRole, Role
    from sqlalchemy import select as sel
    tenant_result = await session.execute(sel(Tenant).limit(1))
    tenant = tenant_result.scalar_one_or_none()
    if tenant and tenant.default_role:
        role_result = await session.execute(sel(Role).where(Role.name == tenant.default_role))
        default_role = role_result.scalar_one_or_none()
        if default_role:
            session.add(UserRole(
                user_id=user.id,
                tenant_id=tenant.id,
                role_id=default_role.id,
            ))

    await session.commit()
    logger.info("Зарегистрирован: %s", username)
    return {"status": "ok"}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    username: str,
    password: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Вход с refresh token rotation и блокировкой."""
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Имя и пароль обязательны")

    # Check lockout
    await _check_login_attempts(session, username, ip)

    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password):
        await _record_login_attempt(session, username, ip, False, user_agent)
        raise HTTPException(status_code=401, detail="Неверные данные")

    # 2FA check
    if user.two_factor_enabled:
        await _record_login_attempt(session, username, ip, True, user_agent)
        return TokenResponse(
            access_token="",
            refresh_token="",
            username=user.username,
            role=user.role,
            user_id=user.id,
            requires_2fa=True,
        )

    # Create tokens
    access = create_access_token({"sub": str(user.id)})
    refresh_token, _ = await _create_refresh_token(session, user.id, ip, user_agent)

    await _record_login_attempt(session, username, ip, True, user_agent)
    await session.commit()

    logger.info("Вход: %s (role=%s)", user.username, user.role)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_token,
        username=user.username,
        role=user.role,
        user_id=user.id,
    )


@router.post("/login/2fa", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login_2fa(
    request: Request,
    username: str,
    password: str,
    totp_code: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Вход с 2FA — подтверждение TOTP кодом."""
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    if not username or not password or not totp_code:
        raise HTTPException(status_code=400, detail="Все поля обязательны")

    await _check_login_attempts(session, username, ip)

    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password):
        await _record_login_attempt(session, username, ip, False, user_agent)
        raise HTTPException(status_code=401, detail="Неверные данные")

    if not user.two_factor_enabled or not user.two_factor_secret:
        raise HTTPException(status_code=400, detail="2FA не настроена")

    totp = pyotp.TOTP(user.two_factor_secret)
    if not totp.verify(totp_code, valid_window=1):
        await _record_login_attempt(session, username, ip, False, user_agent)
        raise HTTPException(status_code=401, detail="Неверный код 2FA")

    access = create_access_token({"sub": str(user.id)})
    refresh_token, _ = await _create_refresh_token(session, user.id, ip, user_agent)

    await _record_login_attempt(session, username, ip, True, user_agent)
    await session.commit()

    logger.info("Вход (2FA): %s (role=%s)", user.username, user.role)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_token,
        username=user.username,
        role=user.role,
        user_id=user.id,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    """Refresh token rotation — old token is revoked, new pair issued."""
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Невалидный refresh токен")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Невалидный refresh токен")

    # Check if token is revoked
    token_hash = _hash_token(body.refresh_token)
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored_token = result.scalar_one_or_none()

    if stored_token is None or stored_token.revoked:
        # Token reuse detected — revoke ALL tokens for this user
        if user_id:
            await _revoke_all_user_tokens(session, int(user_id))
            await session.commit()
        raise HTTPException(status_code=401, detail="Токен отозван. Все сессии завершены.")

    expires_at = stored_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh токен истёк")

    # Revoke old token
    await _revoke_refresh_token(session, token_hash)

    # Get user
    user_result = await session.execute(select(User).where(User.id == int(user_id)))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    # Create new token pair
    access = create_access_token({"sub": str(user.id)})
    refresh_new, _ = await _create_refresh_token(session, user.id, ip, user_agent)

    await session.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=refresh_new,
        username=user.username,
        role=user.role,
        user_id=user.id,
    )


@router.post("/logout")
async def logout(
    body: RefreshRequest,
    user: User = Depends(lambda: None),  # Optional auth
    session: AsyncSession = Depends(get_async_session),
):
    """Logout — revoke the refresh token."""
    payload = decode_token(body.refresh_token)
    if payload and payload.get("sub"):
        token_hash = _hash_token(body.refresh_token)
        await _revoke_refresh_token(session, token_hash)
        await session.commit()
    return {"status": "ok"}


@router.post("/logout-all")
async def logout_all(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Logout all devices — revoke all refresh tokens for the user."""
    payload = decode_token(body.refresh_token)
    if payload and payload.get("sub"):
        count = await _revoke_all_user_tokens(session, int(payload["sub"]))
        await session.commit()
        return {"status": "ok", "revoked": count}
    return {"status": "ok", "revoked": 0}
