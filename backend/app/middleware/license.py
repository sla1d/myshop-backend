import logging
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from sqlalchemy import select

from app.core.config import settings
from app.database.connection import async_session_factory
from app.models.license import License, Tenant

logger = logging.getLogger("myshop.license")

# Пути, не требующие лицензии
SKIP_PATHS = {
    "/health", "/metrics", "/docs", "/redoc", "/openapi.json",
    "/register", "/login", "/refresh", "/api/promos/validate",
}

# Демо-режим: пропускаем проверку лицензии
DEMO_MODE = settings.DEBUG


class LicenseMiddleware(BaseHTTPMiddleware):
    """Проверка лицензии по домену."""

    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0]

        # Пропуск для демо-режима и служебных путей
        if DEMO_MODE or any(request.url.path.startswith(p) for p in SKIP_PATHS):
            return await call_next(request)

        # Локальная разработка и тесты
        if host in ("localhost", "127.0.0.1", "test"):
            return await call_next(request)

        # Проверка лицензии
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(License)
                    .join(Tenant, License.tenant_id == Tenant.id)
                    .where(Tenant.domain == host, License.active == True)
                )
                license = result.scalar_one_or_none()

                if not license:
                    logger.warning("No license for domain: %s", host)
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Лицензия не найдена",
                            "message": "Обратитесь к администратору для получения лицензии",
                            "contact": "support@myshop.com",
                        },
                    )

                if license.expires_at < datetime.now(timezone.utc):
                    logger.warning("License expired for domain: %s", host)
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Лицензия истекла",
                            "expires_at": license.expires_at.isoformat(),
                            "message": "Продлите лицензию для продолжения работы",
                        },
                    )

                # Добавляем лицензию в request state
                request.state.license = license
                request.state.tenant_id = license.tenant_id

        except Exception as e:
            logger.error("License check error: %s", e)
            # В случае ошибки БД — пропускаем (graceful degradation)
            pass

        return await call_next(request)
