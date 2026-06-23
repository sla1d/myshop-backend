import json
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis = None
_available = False


async def get_redis():
    """Получить подключение к Redis (ленивая инициализация)."""
    global _redis, _available
    if _redis is not None:
        return _redis if _available else None
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2)
        await _redis.ping()
        _available = True
        logger.info("Redis подключён: %s", settings.REDIS_URL)
        return _redis
    except Exception:
        _available = False
        logger.warning("Redis недоступен — кэширование отключено (%s)", settings.REDIS_URL)
        return None


async def cache_get(key: str) -> Any | None:
    """Получить значение из кэша."""
    r = await get_redis()
    if not r:
        return None
    try:
        data = await r.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    """Сохранить значение в кэш."""
    r = await get_redis()
    if not r:
        return
    try:
        await r.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl or settings.CACHE_TTL)
    except Exception:
        pass


async def cache_delete(pattern: str) -> None:
    """Удалить ключи по паттерну."""
    r = await get_redis()
    if not r:
        return
    try:
        keys = []
        async for key in r.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await r.delete(*keys)
    except Exception:
        pass


async def cache_close() -> None:
    """Закрыть соединение."""
    global _redis, _available
    if _redis:
        try:
            await _redis.close()
        except Exception:
            pass
        _redis = None
        _available = False
