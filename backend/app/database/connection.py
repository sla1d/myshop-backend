"""Database connection — PostgreSQL with production-ready pooling."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.database.base import Base

# Production pool settings (PgBouncer compatible)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
    # Disable prepared statements for PgBouncer compatibility
    execution_options={"compiled_cache": {}},
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency — отдаёт async-сессию, закрывает после запроса."""
    async with async_session_factory() as session:
        yield session


async def init_db():
    """Создание таблиц (при первом запуске или после миграции)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_health() -> dict:
    """Check database connectivity and pool stats."""
    import time
    from sqlalchemy import text

    start = time.perf_counter()
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - start) * 1000, 1)
        pool = engine.pool
        return {
            "status": "ok",
            "latency_ms": latency,
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}
