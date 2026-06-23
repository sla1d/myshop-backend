import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from datetime import datetime, timedelta, timezone

from app.core.cache import cache_close
from app.core.config import settings
from app.core.rabbitmq import close as rabbitmq_close
from app.core.security import hash_password
from app.database.connection import async_session_factory, engine
from app.models.product import Product
from app.models.promo import PromoCode
from app.models.user import User
from app.routers import admin, auth, cart, orders, products, profile, promos, reviews, upload, wishlist

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
UPLOAD_DIR = BACKEND_DIR.parent / "uploads"


async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Обработка HTTP ошибок — красивый JSON."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


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

        result = await session.execute(select(Product))
        if result.scalars().first() is not None:
            await session.commit()
            return

        products_data = [
            Product(name="Смартфон X", price=29999, image="https://picsum.photos/seed/smartphone/300/300", category="electronics", brand="TechCo", rating=4.5),
            Product(name="Ноутбук Pro", price=89999, image="https://picsum.photos/seed/laptop/300/300", category="electronics", brand="TechCo", rating=4.8),
            Product(name="Наушники Wireless", price=15999, image="https://picsum.photos/seed/headphones/300/300", category="electronics", brand="SoundMax", rating=4.3),
            Product(name="Монитор 4K", price=45999, image="https://picsum.photos/seed/monitor/300/300", category="electronics", brand="VisualPro", rating=4.6),
            Product(name="Клавиатура Mechanical", price=12999, image="https://picsum.photos/seed/keyboard/300/300", category="electronics", brand="KeyMaster", rating=4.4),
            Product(name="Мышь Gaming", price=8999, image="https://picsum.photos/seed/mouse/300/300", category="electronics", brand="KeyMaster", rating=4.2),
            Product(name="SSD 1TB", price=9999, image="https://picsum.photos/seed/ssd/300/300", category="storage", brand="DataStore", rating=4.7),
            Product(name="USB-C Hub", price=4999, image="https://picsum.photos/seed/hub/300/300", category="accessories", brand="ConnectAll", rating=4.1),
            Product(name="Power Bank 20000mAh", price=7999, image="https://picsum.photos/seed/powerbank/300/300", category="accessories", brand="PowerUp", rating=4.3),
            Product(name="Bluetooth Speaker", price=6999, image="https://picsum.photos/seed/speaker/300/300", category="electronics", brand="SoundMax", rating=4.0),
            Product(name="Apple Watch", price=24999, image="https://picsum.photos/seed/watch/300/300", category="wearables", brand="Apple", rating=4.7),
            Product(name="AirPods Pro", price=19999, image="https://picsum.photos/seed/airpods/300/300", category="electronics", brand="Apple", rating=4.6),
            Product(name="Smart Watch", price=21999, image="https://picsum.photos/seed/smartwatch/300/300", category="wearables", brand="TechCo", rating=4.2),
            Product(name="Gaming Console", price=39999, image="https://picsum.photos/seed/console/300/300", category="gaming", brand="GameStation", rating=4.8),
            Product(name="VR Headset", price=49999, image="https://picsum.photos/seed/vr/300/300", category="gaming", brand="GameStation", rating=4.5),
            Product(name="Drone", price=59999, image="https://picsum.photos/seed/drone/300/300", category="electronics", brand="SkyFly", rating=4.4),
            Product(name="Action Camera", price=34999, image="https://picsum.photos/seed/camera/300/300", category="electronics", brand="SkyFly", rating=4.3),
            Product(name="Fitness Tracker", price=7999, image="https://picsum.photos/seed/fitness/300/300", category="wearables", brand="HealthTech", rating=4.1),
            Product(name="Smart Home Speaker", price=8999, image="https://picsum.photos/seed/speaker2/300/300", category="smart_home", brand="HomeAI", rating=4.5),
            Product(name="Smart Light Bulb", price=1999, image="https://picsum.photos/seed/lightbulb/300/300", category="smart_home", brand="HomeAI", rating=4.0),
        ]
        session.add_all(products_data)

        promos_data = [
            PromoCode(code="SALE10", discount_percent=10, valid_until=datetime.now(timezone.utc) + timedelta(days=30), max_uses=100),
            PromoCode(code="WELCOME20", discount_percent=20, valid_until=datetime.now(timezone.utc) + timedelta(days=90), max_uses=0),
            PromoCode(code="SUMMER15", discount_percent=15, valid_until=datetime.now(timezone.utc) + timedelta(days=60), max_uses=50),
        ]
        session.add_all(promos_data)

        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(settings.LOG_FILE),
            logging.StreamHandler(),
        ],
    )

    await _seed_data()
    logging.info("MyShop API запущен")

    yield

    await engine.dispose()
    await cache_close()
    rabbitmq_close()
    logging.info("MyShop API остановлен")


def create_application() -> FastAPI:
    """Фабрика создания FastAPI приложения."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    app.add_exception_handler(HTTPException, _http_exception_handler)

    app.include_router(auth.router)
    app.include_router(admin.router, prefix="/api")
    app.include_router(products.router, prefix="/api")
    app.include_router(cart.router, prefix="/api")
    app.include_router(orders.router, prefix="/api")
    app.include_router(profile.router, prefix="/api")
    app.include_router(promos.router, prefix="/api")
    app.include_router(reviews.router, prefix="/api")
    app.include_router(upload.router, prefix="/api")
    app.include_router(wishlist.router, prefix="/api")

    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        """Отдаём главную страницу."""
        html_path = FRONTEND_DIR / "index.html"
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

    return app


app = create_application()
