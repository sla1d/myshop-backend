from fastapi import Request
from fastapi.responses import JSONResponse


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Обработка неожиданных ошибок."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"},
    )


async def http_exception_handler(request: Request, exc) -> JSONResponse:
    """Обработка HTTP ошибок."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
