from pathlib import Path
from secrets import token_urlsafe

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _generate_secret() -> str:
    """Генерация случайного ключа при первом запуске."""
    key_file = BASE_DIR / ".secret_key"
    if key_file.exists():
        return key_file.read_text().strip()
    key = token_urlsafe(64)
    key_file.write_text(key)
    return key


class Settings(BaseSettings):
    """Настройки приложения."""

    APP_NAME: str = "MyShop Platform"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    SECRET_KEY: str = ""

    # PostgreSQL (по умолчанию)
    DATABASE_URL: str = "postgresql+asyncpg://myshop:myshop_secret@localhost:5432/myshop"

    # CORS — whitelist only trusted domains
    CORS_ORIGINS: list[str] = [
        "https://myshop.ai",
        "https://admin.myshop.ai",
        "https://*.myshop.ai",
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    LOG_DIR: str = str(BASE_DIR / "logs")
    LOG_FILE: str = str(BASE_DIR / "logs" / "server.log")

    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300

    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    TELEGRAM_BOT_TOKEN: str = ""

    # S3 / MinIO
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "myshop-uploads"
    S3_REGION: str = "us-east-1"

    # Sentry
    SENTRY_DSN: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

if not settings.SECRET_KEY:
    settings.SECRET_KEY = _generate_secret()
