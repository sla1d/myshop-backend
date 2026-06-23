from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.database.base import Base

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency — отдаёт async-сессию, закрывает после запроса."""
    async with async_session_factory() as session:
        yield session


async def init_db():
    """Создание таблиц (при первом запуске или после миграции)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
