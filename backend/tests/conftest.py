import asyncio
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.database.connection import get_async_session
from app.main import create_application
from app.models.product import Product
from app.models.promo import PromoCode
from app.models.user import User
from app.core.security import hash_password, create_access_token
from app.rbac.models import Role, Permission, RolePermission, UserRole
from app.rbac.seed import seed_rbac, assign_owner_role

# Тесты работают на SQLite in-memory для скорости
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session():
    async with TestSessionLocal() as s:
        yield s


@pytest_asyncio.fixture
async def app():
    _app = create_application()
    _app.dependency_overrides[get_async_session] = override_get_session
    yield _app
    _app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seed_products(session):
    products = [
        Product(name="Смартфон X", price=29999, image="https://picsum.photos/seed/sp/300/300",
                category="electronics", brand="TechCo", rating=4.5),
        Product(name="Ноутбук Pro", price=89999, image="https://picsum.photos/seed/lp/300/300",
                category="electronics", brand="TechCo", rating=4.8),
        Product(name="Наушники", price=15999, image="https://picsum.photos/seed/hp/300/300",
                category="electronics", brand="SoundMax", rating=4.3),
        Product(name="Мышь Gaming", price=8999, image="https://picsum.photos/seed/ms/300/300",
                category="electronics", brand="KeyMaster", rating=4.2),
    ]
    session.add_all(products)
    await session.commit()
    for p in products:
        await session.refresh(p)
    return products


@pytest_asyncio.fixture
async def seed_admin(session):
    await seed_rbac(session)
    admin = User(
        username="admin",
        password=hash_password("admin123"),
        role="admin",
        email="admin@test.ru",
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    await assign_owner_role(session, admin.id, tenant_id=1)
    await session.commit()
    return admin


@pytest_asyncio.fixture
async def seed_user(session):
    user = User(
        username="testuser",
        password=hash_password("test123"),
        role="user",
        email="user@test.ru",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def seed_promo(session):
    promo = PromoCode(
        code="TEST20",
        discount_percent=20,
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        max_uses=100,
    )
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return promo


@pytest_asyncio.fixture
def user_token(seed_user):
    return create_access_token({"sub": str(seed_user.id)})


@pytest_asyncio.fixture
def admin_token(seed_admin):
    return create_access_token({"sub": str(seed_admin.id)})
