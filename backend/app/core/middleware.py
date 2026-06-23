import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("myshop.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Логирование каждого HTTP-запроса: метод, путь, статус, время."""

    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]
        start = time.perf_counter()

        logger.info(
            "[%s] %s %s started",
            request_id,
            request.method,
            request.url.path,
        )

        response = await call_next(request)

        elapsed = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "[%s] %s %s → %d (%sms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )

        response.headers["X-Request-ID"] = request_id
        return response


class ExceptionLoggingMiddleware(BaseHTTPMiddleware):
    """Перехват и логирование необработанных исключений."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled error: %s %s",
                request.method,
                request.url.path,
            )
            raise
