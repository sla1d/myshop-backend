import logging
import secrets

import pyotp
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.user import User

router = APIRouter(prefix="/2fa", tags=["2FA"])
logger = logging.getLogger(__name__)


class TFASecretResponse(BaseModel):
    secret: str
    otpauth_url: str


class TFAVerifyRequest(BaseModel):
    code: str


class TFAResponse(BaseModel):
    enabled: bool
    message: str


def generate_secret() -> str:
    return pyotp.random_base32()


@router.get("/setup", response_model=TFASecretResponse)
async def setup_2fa(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Генерация секрета для 2FA (TOTP)."""
    if user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA уже включена")

    secret = generate_secret()
    user.two_factor_secret = secret
    await session.commit()

    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(name=user.username, issuer_name="MyShop")

    logger.info("2FA secret generated for %s", user.username)
    return TFASecretResponse(secret=secret, otpauth_url=otpauth_url)


@router.post("/verify", response_model=TFAResponse)
async def verify_2fa(
    body: TFAVerifyRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Подтвердить код TOTP и включить 2FA."""
    if not user.two_factor_secret:
        raise HTTPException(status_code=400, detail="Сначала вызовите /2fa/setup")

    totp = pyotp.TOTP(user.two_factor_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Неверный код")

    user.two_factor_enabled = True
    await session.commit()

    logger.info("2FA enabled for %s", user.username)
    return TFAResponse(enabled=True, message="2FA включена")


@router.post("/disable", response_model=TFAResponse)
async def disable_2fa(
    body: TFAVerifyRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Отключить 2FA (требует текущий код)."""
    if not user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA не включена")

    totp = pyotp.TOTP(user.two_factor_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Неверный код")

    user.two_factor_enabled = False
    user.two_factor_secret = None
    await session.commit()

    logger.info("2FA disabled for %s", user.username)
    return TFAResponse(enabled=False, message="2FA отключена")


@router.get("/status")
async def get_2fa_status(user: User = Depends(get_current_user)):
    """Получить статус 2FA."""
    return {"enabled": user.two_factor_enabled}
