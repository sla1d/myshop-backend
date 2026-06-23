from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Настройки приложения."""

    APP_NAME: str = "MyShop API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # SQLite (по умолчанию) или PostgreSQL
    # Локально: sqlite+aiosqlite:///./shop.db
    # прод: postgresql+asyncpg://user:pass@localhost:5432/myshop
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'shop.db'}"

    CORS_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    LOG_DIR: str = str(BASE_DIR / "logs")
    LOG_FILE: str = str(BASE_DIR / "logs" / "server.log")

    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300

    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
