import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

# Initialize Sentry before other imports
from app.core.config import settings as _cfg
if _cfg.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=_cfg.SENTRY_DSN,
        environment="production" if not _cfg.DEBUG else "development",
        traces_sample_rate=0.1,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
    )

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from sqlalchemy import select, text

from datetime import datetime, timedelta, timezone

from app.core.cache import cache_close
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import AccessLogMiddleware, ExceptionLoggingMiddleware
from app.core.rabbitmq import close as rabbitmq_close
from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.database.connection import async_session_factory, engine
from app.database.base import Base
from app.exceptions import register_exception_handlers
from app.middleware.license import LicenseMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.tenant import TenantMiddleware
from app.models.product import Product
from app.models.promo import PromoCode
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.routers import ab_test, admin, ai_chat, analytics, auth, audit, banners, billing, cart, csv, flash_sales, i18n, integrations, licenses, loyalty, marketplace, orders, plugins, products, profile, promos, public, referral, reviews, saas, store, tracking, tfa, upload, whitelabel, wishlist, ws
from app.rbac.seed import seed_rbac, assign_owner_role

BACKEND_DIR = Path(__file__).resolve().parent.parent


async def _seed_data():
    """Заполнение БД начальными товарами и админом (если пусто)."""
    async with async_session_factory() as session:
        result = await session.execute(select(User))
        if result.scalars().first() is None:
            admin = User(
                username="admin",
                password=hash_password("admin123"),
                role="admin",
                email="admin@myshop.ru",
                full_name="Администратор",
                phone="+7 999 123-45-67",
                address="Москва, ул. Примерная, 1",
            )
            session.add(admin)
            await session.flush()
            # Assign owner role for demo tenant
            from app.models.license import Tenant
            tenant_result = await session.execute(select(Tenant).limit(1))
            demo_tenant = tenant_result.scalars().first()
            if demo_tenant:
                await assign_owner_role(session, admin.id, demo_tenant.id)
            else:
                # Create demo tenant
                demo_tenant = Tenant(
                    name="Demo Store", slug="demo", domain="localhost",
                    plan="pro", theme="midnight", store_name="Demo Store",
                )
                session.add(demo_tenant)
                await session.flush()
                admin.tenant_id = demo_tenant.id
                await assign_owner_role(session, admin.id, demo_tenant.id)

        result = await session.execute(select(Product))
        if result.scalars().first() is not None:
            await session.commit()
            return

        products_data = [
            Product(name="Смартфон X", price=29999, image="https://picsum.photos/seed/smartphone/300/300", category="electronics", brand="TechCo", rating=4.5, color="black", size="standard", in_stock=True, stock_quantity=50),
            Product(name="Ноутбук Pro", price=89999, image="https://picsum.photos/seed/laptop/300/300", category="electronics", brand="TechCo", rating=4.8, color="silver", size="standard", in_stock=True, stock_quantity=20),
            Product(name="Наушники Wireless", price=15999, image="https://picsum.photos/seed/headphones/300/300", category="electronics", brand="SoundMax", rating=4.3, color="white", size="standard", in_stock=True, stock_quantity=100),
            Product(name="Монитор 4K", price=45999, image="https://picsum.photos/seed/monitor/300/300", category="electronics", brand="VisualPro", rating=4.6, color="black", size="27inch", in_stock=True, stock_quantity=15),
            Product(name="Клавиатура Mechanical", price=12999, image="https://picsum.photos/seed/keyboard/300/300", category="electronics", brand="KeyMaster", rating=4.4, color="black", size="standard", in_stock=True, stock_quantity=80),
            Product(name="Мышь Gaming", price=8999, image="https://picsum.photos/seed/mouse/300/300", category="electronics", brand="KeyMaster", rating=4.2, color="black", size="standard", in_stock=True, stock_quantity=120),
            Product(name="SSD 1TB", price=9999, image="https://picsum.photos/seed/ssd/300/300", category="storage", brand="DataStore", rating=4.7, color="silver", size="2.5inch", in_stock=True, stock_quantity=200),
            Product(name="USB-C Hub", price=4999, image="https://picsum.photos/seed/hub/300/300", category="accessories", brand="ConnectAll", rating=4.1, color="silver", size="standard", in_stock=True, stock_quantity=150),
            Product(name="Power Bank 20000mAh", price=7999, image="https://picsum.photos/seed/powerbank/300/300", category="accessories", brand="PowerUp", rating=4.3, color="blue", size="standard", in_stock=True, stock_quantity=90),
            Product(name="Bluetooth Speaker", price=6999, image="https://picsum.photos/seed/speaker/300/300", category="electronics", brand="SoundMax", rating=4.0, color="red", size="standard", in_stock=True, stock_quantity=70),
            Product(name="Apple Watch", price=24999, image="https://picsum.photos/seed/watch/300/300", category="wearables", brand="Apple", rating=4.7, color="black", size="44mm", in_stock=True, stock_quantity=30),
            Product(name="AirPods Pro", price=19999, image="https://picsum.photos/seed/airpods/300/300", category="electronics", brand="Apple", rating=4.6, color="white", size="standard", in_stock=True, stock_quantity=60),
            Product(name="Smart Watch", price=21999, image="https://picsum.photos/seed/smartwatch/300/300", category="wearables", brand="TechCo", rating=4.2, color="black", size="42mm", in_stock=True, stock_quantity=40),
            Product(name="Gaming Console", price=39999, image="https://picsum.photos/seed/console/300/300", category="gaming", brand="GameStation", rating=4.8, color="white", size="standard", in_stock=True, stock_quantity=25),
            Product(name="VR Headset", price=49999, image="https://picsum.photos/seed/vr/300/300", category="gaming", brand="GameStation", rating=4.5, color="black", size="standard", in_stock=True, stock_quantity=10),
            Product(name="Drone", price=59999, image="https://picsum.photos/seed/drone/300/300", category="electronics", brand="SkyFly", rating=4.4, color="white", size="standard", in_stock=True, stock_quantity=8),
            Product(name="Action Camera", price=34999, image="https://picsum.photos/seed/camera/300/300", category="electronics", brand="SkyFly", rating=4.3, color="black", size="standard", in_stock=True, stock_quantity=35),
            Product(name="Fitness Tracker", price=7999, image="https://picsum.photos/seed/fitness/300/300", category="wearables", brand="HealthTech", rating=4.1, color="green", size="standard", in_stock=True, stock_quantity=100),
            Product(name="Smart Home Speaker", price=8999, image="https://picsum.photos/seed/speaker2/300/300", category="smart_home", brand="HomeAI", rating=4.5, color="gray", size="standard", in_stock=True, stock_quantity=45),
            Product(name="Smart Light Bulb", price=1999, image="https://picsum.photos/seed/lightbulb/300/300", category="smart_home", brand="HomeAI", rating=4.0, color="white", size="standard", in_stock=True, stock_quantity=300),
        ]
        session.add_all(products_data)

        promos_data = [
            PromoCode(code="SALE10", discount_percent=10, valid_until=datetime.now(timezone.utc) + timedelta(days=30), max_uses=100),
            PromoCode(code="WELCOME20", discount_percent=20, valid_until=datetime.now(timezone.utc) + timedelta(days=90), max_uses=0),
            PromoCode(code="SUMMER15", discount_percent=15, valid_until=datetime.now(timezone.utc) + timedelta(days=60), max_uses=50),
        ]
        session.add_all(promos_data)

        # Тестовые заказы для демонстрации карты
        admin_user = (await session.execute(select(User).where(User.username == "admin"))).scalar_one_or_none()
        if admin_user:
            test_orders = [
                Order(user_id=admin_user.id, total=29999, address="Москва, ул. Примерная, 1", status="delivered",
                      created_at=datetime.now(timezone.utc) - timedelta(days=5)),
                Order(user_id=admin_user.id, total=89999, address="Санкт-Петербург, Невский пр., 10", status="shipped",
                      created_at=datetime.now(timezone.utc) - timedelta(days=3)),
                Order(user_id=admin_user.id, total=15999, address="Казань, ул. Баумана, 5", status="processing",
                      created_at=datetime.now(timezone.utc) - timedelta(days=2)),
                Order(user_id=admin_user.id, total=45999, address="Новосибирск, Красный пр., 20", status="pending",
                      created_at=datetime.now(timezone.utc) - timedelta(days=1)),
                Order(user_id=admin_user.id, total=8999, address="Екатеринбург, ул. Мира, 15", status="delivered",
                      created_at=datetime.now(timezone.utc) - timedelta(days=7)),
                Order(user_id=admin_user.id, total=39999, address="Ростов-на-Дону, ул. Пушкинская, 30", status="delivered",
                      created_at=datetime.now(timezone.utc) - timedelta(days=4)),
                Order(user_id=admin_user.id, total=12999, address="Красноярск, пр. Мира, 12", status="shipped",
                      created_at=datetime.now(timezone.utc) - timedelta(days=6)),
                Order(user_id=admin_user.id, total=59999, address="Владивосток, ул. Сvetановская, 45", status="processing",
                      created_at=datetime.now(timezone.utc) - timedelta(days=2)),
            ]
            session.add_all(test_orders)
            await session.flush()
            for o in test_orders:
                session.add(OrderStatusHistory(order_id=o.id, status=o.status, comment="Тестовый заказ",
                                               created_at=datetime.now(timezone.utc)))

        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    logger = setup_logging(settings.LOG_DIR)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as session:
        await seed_rbac(session)
    await _seed_data()
    logger.info("MyShop API запущен")

    yield

    await engine.dispose()
    await cache_close()
    rabbitmq_close()
    logger.info("MyShop API остановлен")


def create_application() -> FastAPI:
    """Фабрика создания FastAPI приложения."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
## MyShop API — Backend для интернет-магазина электроники

### Возможности
- JWT авторизация (access + refresh токены)
- Ролевая модель: `user` / `admin`
- CRUD товаров с поиском, фильтрами (категория, бренд, рейтинг, цена) и сортировкой
- Корзина, заказы с промокодами
- Система отзывов и избранного
- Админ-панель: статистика, управление товарами/пользователями/заказами/промокодами
- Загрузка изображений товаров
- Redis кэширование
- RabbitMQ очередь сообщений
- Celery фоновые задачи

### Авторизация
Все защищённые эндпоинты требуют заголовок:
```
Authorization: Bearer <access_token>
```

### Тестовые данные
При первом запуске создаётся:
- **admin** / `admin123` (role=admin)
- 20 товаров, 3 промокода
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Авторизация", "description": "Регистрация, вход, обновление токенов"},
            {"name": "Товары", "description": "Каталог товаров с поиском, фильтрами, сортировкой"},
            {"name": "Корзина", "description": "Управление корзиной (добавление, изменение, удаление)"},
            {"name": "Заказы", "description": "Создание заказов с промокодами"},
            {"name": "Избранное", "description": "Список избранных товаров"},
            {"name": "Отзывы", "description": "Отзывы на товары"},
            {"name": "Промокоды", "description": "Проверка и применение промокодов"},
            {"name": "Профиль", "description": "Личные данные и история заказов"},
            {"name": "Админ", "description": "Управление товарами, пользователями, заказами, промокодами"},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    app.add_middleware(ExceptionLoggingMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LicenseMiddleware)
    app.add_middleware(TenantMiddleware)

    register_exception_handlers(app)

    app.state.limiter = limiter

    @app.get("/health")
    async def health_check():
        """Health check: DB pool + Redis + RabbitMQ."""
        import time
        start = time.perf_counter()
        status = {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat(), "version": settings.APP_VERSION}

        # DB check with pool stats
        from app.database.connection import check_db_health
        db_health = await check_db_health()
        status["database"] = db_health
        if db_health["status"] != "ok":
            status["status"] = "degraded"

        # Redis check
        from app.core.cache import cache_get
        try:
            cache_start = time.perf_counter()
            await cache_get("health")
            status["redis"] = {"status": "ok", "latency_ms": round((time.perf_counter() - cache_start) * 1000, 1)}
        except Exception:
            status["redis"] = {"status": "unavailable"}

        status["latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
        return status

    @app.get("/metrics")
    async def metrics():
        """Расширенные метрики для мониторинга."""
        from datetime import timedelta
        from sqlalchemy import func
        from app.models.order import Order
        from app.models.product import Product
        from app.models.user import User
        from app.models.license import Tenant
        from app.billing.models import Subscription, Payment

        now = datetime.now(timezone.utc)

        async with async_session_factory() as session:
            users_total = (await session.execute(select(func.count(User.id)))).scalar() or 0
            products_total = (await session.execute(select(func.count(Product.id)))).scalar() or 0
            orders_total = (await session.execute(select(func.count(Order.id)))).scalar() or 0
            tenants_total = (await session.execute(select(func.count(Tenant.id)))).scalar() or 0
            revenue = (await session.execute(select(func.coalesce(func.sum(Order.total), 0)))).scalar() or 0

            # Last 24h metrics
            since_24h = now - timedelta(hours=24)
            orders_24h = (await session.execute(
                select(func.count(Order.id)).where(Order.created_at >= since_24h)
            )).scalar() or 0
            revenue_24h = (await session.execute(
                select(func.coalesce(func.sum(Order.total), 0)).where(Order.created_at >= since_24h)
            )).scalar() or 0

            # Active subscriptions
            active_subs = (await session.execute(
                select(func.count(Subscription.id)).where(Subscription.status == "active")
            )).scalar() or 0

            return {
                "users_total": users_total,
                "products_total": products_total,
                "orders_total": orders_total,
                "tenants_total": tenants_total,
                "revenue_total": int(revenue),
                "orders_24h": orders_24h,
                "revenue_24h": int(revenue_24h),
                "active_subscriptions": active_subs,
            }

    app.include_router(auth.router)
    app.include_router(admin.router, prefix="/api")
    app.include_router(analytics.router, prefix="/api")
    app.include_router(licenses.router, prefix="/api")
    app.include_router(marketplace.router, prefix="/api")
    app.include_router(products.router, prefix="/api")
    app.include_router(cart.router, prefix="/api")
    app.include_router(orders.router, prefix="/api")
    app.include_router(profile.router, prefix="/api")
    app.include_router(promos.router, prefix="/api")
    app.include_router(reviews.router, prefix="/api")
    app.include_router(upload.router, prefix="/api")
    app.include_router(wishlist.router, prefix="/api")
    app.include_router(store.router)
    app.include_router(ws.router)
    app.include_router(tracking.router, prefix="/api")
    app.include_router(tfa.router, prefix="/api")
    app.include_router(referral.router, prefix="/api")
    app.include_router(loyalty.router, prefix="/api")
    app.include_router(audit.router, prefix="/api")
    app.include_router(flash_sales.router, prefix="/api")
    app.include_router(ab_test.router, prefix="/api")
    app.include_router(banners.router, prefix="/api")
    app.include_router(billing.router, prefix="/api")
    app.include_router(saas.router, prefix="/api")
    app.include_router(integrations.router, prefix="/api")
    app.include_router(ai_chat.router, prefix="/api")
    app.include_router(plugins.router, prefix="/api")
    app.include_router(csv.router, prefix="/api")
    app.include_router(i18n.router, prefix="/api")
    app.include_router(whitelabel.router, prefix="/api")
    app.include_router(public.router)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        """API root."""
        return HTMLResponse(content="<h1>MyShop API</h1><p>Docs: <a href='/docs'>/docs</a></p>")

    return app


app = create_application()
