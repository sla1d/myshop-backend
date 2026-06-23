import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger("myshop.errors")


class AppError(Exception):
    """Базовая ошибка приложения."""
    status_code: int = 400
    detail: str = "Ошибка приложения"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "Не найдено"


class ForbiddenError(AppError):
    status_code = 403
    detail = "Доступ запрещён"


class UnauthorizedError(AppError):
    status_code = 401
    detail = "Необходима авторизация"


class ConflictError(AppError):
    status_code = 409
    detail = "Конфликт данных"


class ValidationError(AppError):
    status_code = 422
    detail = "Ошибка валидации"


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрация глобальных обработчиков исключений."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("AppError: %s %s → %d: %s", request.method, request.url.path, exc.status_code, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error_type": exc.__class__.__name__},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.error("IntegrityError: %s %s: %s", request.method, request.url.path, exc.orig)
        return JSONResponse(
            status_code=409,
            content={"detail": "Нарушение целостности данных", "error_type": "IntegrityError"},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("SQLAlchemyError: %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Ошибка базы данных", "error_type": "DatabaseError"},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.warning("ValueError: %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error_type": "ValueError"},
        )

    @app.exception_handler(Exception)
    async def global_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled: %s %s: %s\n%s",
            request.method, request.url.path, exc,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка сервера", "error_type": "InternalServerError"},
        )
